"""Discipline score — the Stage-6 behavioral gauge (docs/PRODUCT_SYNTHESIS.md §1).

The product's thesis: the signal is nearly free (a cherry-picked book regresses to the ~0.74 null);
the value is the DELTA between the disciplined whole-book and the cherry-picked null. This service
turns that finding into a live per-user money gauge, computed ONLY from ground truth we actually
hold — the append-only execution ledger (Stage 4), the frozen signal snapshots (Stage 2), and the
shared model envelope. Nothing is asked of the user; the score falls out of what they recorded.

Six legs, each in [0, 1], combined GEOMETRICALLY (one broken leg tanks the score — by design;
discipline is conjunctive, not additive). Legs with no observable data yet are omitted from the mean
(neutral), never assumed perfect or broken:

  coverage        took the model's actionable buys (skipping names is where the 0.74 null lives)
  fidelity        buy prices inside the frozen entry band (chasing re-prices the edge away)
  timing          buys recorded within the entry window days of the signal date
  exit_adherence  model-closed positions are closed in the ledger too (no stale holds)
  hold_through    no early manual sells on names the model still holds (winner-cut guard)
  concentration   cost spread across the book instead of piled into one favourite name

The score is PRICED on the null segment: sharpe_now = 0.67 + score x (1.03 - 0.67) — the measured
span between the cherry-picked null (~0.74 sits just above the floor) and the disciplined base
book. Also computes the counterfactual "take the skipped buys" score so the UI can say "taking the
2 names you skipped moves you from ~0.92 to ~1.00".

Honesty rules: never a fabricated number — a leg without data is omitted and reported null; the
Sharpe position is framed as the null-segment estimate, not a promised return.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from services import execution_ledger as ledger

logger = logging.getLogger("discipline")

SHARPE_FLOOR = 0.67          # bottom of the null segment (base gross Sharpe)
SHARPE_CEIL = 1.03           # disciplined whole-book segment top
ENTRY_WINDOW_DAYS = 7        # calendar days after signal_date a buy still counts as on-time
BAND_SOFT_PCT = 0.02         # price ≤2% outside the frozen band = soft miss, not a chase
MAX_COST_SHARE = 0.35        # one name above 35% of book cost = concentration leg decays

_BUY_ACTIONABILITY = {"BUY_OPEN", "ACTIONABLE_BUY"}
_EXIT_STATUS = {"HIT_TARGET", "HIT_STOP", "EXPIRED", "CLOSED", "RESOLVED"}


def _sid(sig: dict) -> str | None:
    s = sig.get("signal_id")
    if s:
        return str(s)
    t, d = sig.get("ticker"), sig.get("signal_date")
    return f"{t}__{d}" if t and d else None


def _date_of(sid: str) -> datetime | None:
    try:
        return datetime.fromisoformat(sid.split("__")[1])
    except Exception:  # noqa: BLE001
        return None


def _geo_mean(vals: list[float]) -> float | None:
    xs = [max(1e-6, min(1.0, v)) for v in vals if v is not None]
    if not xs:
        return None
    p = 1.0
    for x in xs:
        p *= x
    return p ** (1.0 / len(xs))


def _sharpe_at(score: float | None) -> float | None:
    if score is None:
        return None
    return round(SHARPE_FLOOR + score * (SHARPE_CEIL - SHARPE_FLOOR), 2)


def compute_legs(events_by_sig: dict, envelope: dict, snapshots: dict) -> dict:
    """The six legs from raw ground truth. Pure. events_by_sig: signal_id -> [ExecutionEvent];
    snapshots: signal_id -> frozen snapshot dict (entry band); envelope: the weekly model book."""
    signals = (envelope or {}).get("signals", [])
    states = {sid: ledger.position_state(evs) for sid, evs in events_by_sig.items()}

    # ── coverage: of the CURRENT actionable buys, how many has the user taken? ──
    buyable = [s for s in signals
               if (s.get("actionability") or "").upper() in _BUY_ACTIONABILITY and not s.get("bought_date")]
    buyable_ids = [_sid(s) for s in buyable if _sid(s)]
    taken = [b for b in buyable_ids if states.get(b, {}).get("total_bought_qty", 0) > 0]
    skipped = [b for b in buyable_ids if b not in taken]
    coverage = (len(taken) / len(buyable_ids)) if buyable_ids else None

    # ── fidelity + timing: over every buy the user ever recorded ──
    fid_scores, tim_scores = [], []
    for sid, evs in events_by_sig.items():
        snap = snapshots.get(sid) or {}
        lo, hi = snap.get("entry_low"), snap.get("entry_high")
        sig_date = _date_of(sid)
        for e in evs:
            if e.side != "BUY" or e.corrects_event_id is not None:
                continue
            if lo and hi:
                if float(lo) <= e.price <= float(hi):
                    fid_scores.append(1.0)
                elif float(lo) * (1 - BAND_SOFT_PCT) <= e.price <= float(hi) * (1 + BAND_SOFT_PCT):
                    fid_scores.append(0.7)
                else:
                    fid_scores.append(0.4)
            when = e.executed_at or e.created_at
            if sig_date and when:
                days = (when - sig_date).days
                tim_scores.append(1.0 if days <= ENTRY_WINDOW_DAYS else 0.5 if days <= 2 * ENTRY_WINDOW_DAYS else 0.25)
    fidelity = sum(fid_scores) / len(fid_scores) if fid_scores else None
    timing = sum(tim_scores) / len(tim_scores) if tim_scores else None

    # ── exit-adherence: model closed it -> user closed it too? ──
    model_closed = {_sid(s) for s in signals
                    if (s.get("status") or "").upper() in _EXIT_STATUS
                    or (s.get("actionability") or "").upper() == "EXIT_REQUIRED"}
    judged, adhered = 0, 0
    for sid in model_closed:
        st = states.get(sid)
        if st and st.get("total_bought_qty", 0) > 0:
            judged += 1
            if st.get("remaining_qty", 0) == 0:
                adhered += 1
    exit_adherence = (adhered / judged) if judged else None

    # ── hold-through: no early manual sells on names the model still HOLDS ──
    model_holds = {_sid(s) for s in signals if s.get("bought_date")
                   and (s.get("status") or "").upper() not in _EXIT_STATUS}
    held_judged, held_clean = 0, 0
    for sid in model_holds:
        evs = events_by_sig.get(sid)
        st = states.get(sid)
        if not evs or not st or st.get("total_bought_qty", 0) == 0:
            continue
        held_judged += 1
        early_sell = any(e.side == "SELL" and (e.tranche in (None, "manual")) for e in evs)
        if not early_sell:
            held_clean += 1
    hold_through = (held_clean / held_judged) if held_judged else None

    # ── concentration: cost spread across OPEN positions ──
    open_costs = [st.get("cost_basis_remaining") or 0.0 for st in states.values()
                  if st.get("remaining_qty", 0) > 0]
    concentration = None
    total_cost = sum(open_costs)
    if len(open_costs) >= 2 and total_cost > 0:
        max_share = max(open_costs) / total_cost
        concentration = 1.0 if max_share <= MAX_COST_SHARE else max(0.2, MAX_COST_SHARE / max_share)

    return {
        "coverage": coverage, "fidelity": fidelity, "timing": timing,
        "exit_adherence": exit_adherence, "hold_through": hold_through,
        "concentration": concentration,
        "_n_buyable": len(buyable_ids), "_n_taken": len(taken), "_skipped": skipped,
    }


def compute_score(db, user_id: int, envelope: dict, snapshots: dict) -> dict:
    """Full per-user gauge: legs, geometric score, Sharpe position on the null segment, and the
    counterfactual 'take the skipped buys' position."""
    from database import ExecutionEvent
    rows = (db.query(ExecutionEvent).filter(ExecutionEvent.user_id == user_id)
            .order_by(ExecutionEvent.id.asc()).all())
    events_by_sig: dict[str, list] = {}
    for r in rows:
        events_by_sig.setdefault(r.signal_id, []).append(r)

    legs = compute_legs(events_by_sig, envelope, snapshots)
    leg_vals = {k: v for k, v in legs.items() if not k.startswith("_")}
    score = _geo_mean(list(leg_vals.values()))

    # Counterfactual: coverage -> 1.0 (all current buys taken), other legs unchanged.
    cf_vals = dict(leg_vals)
    if cf_vals.get("coverage") is not None and cf_vals["coverage"] < 1.0:
        cf_vals["coverage"] = 1.0
    cf_score = _geo_mean(list(cf_vals.values()))

    return {
        "legs": {k: (round(v, 3) if v is not None else None) for k, v in leg_vals.items()},
        "score": round(score, 3) if score is not None else None,
        "sharpe_now": _sharpe_at(score),
        "sharpe_floor": SHARPE_FLOOR, "sharpe_ceiling": SHARPE_CEIL,
        "n_buyable": legs["_n_buyable"], "n_taken": legs["_n_taken"],
        "skipped_signal_ids": legs["_skipped"],
        "sharpe_if_full_coverage": _sharpe_at(cf_score),
        "note": ("Position on the measured null segment (cherry-picked ~0.74 -> disciplined whole-book "
                 "1.03). An estimate from your recorded behaviour, not a promised return."),
    }
