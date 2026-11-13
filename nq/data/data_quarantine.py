"""Per-ticker data QUARANTINE: one bad name must not cost the whole weekly scan.

The adjustment guard (``adjustment_guard``) is right every time it fires, but it raises, and a raise
halts the scan for ALL ~500 names. It halted the 2026-10-10 scan (ADR-0013 escalation), the 2026-10-31
scan and the 2026-11-07 scan (CONCORDBIO, a 2:1 split): one stock each, a whole week lost each.

This module turns "the guard found a problem on NAME X" into three escalating responses:

1. SELF-HEAL  - a full-depth re-fetch of just that ticker, then re-check it.
2. QUARANTINE - if it still fails AND the problem is KNOWN (a registered seam / the ADR-0013 live-exposure
   escalation; owner decision 2026-11-13), the name is set aside for this scan only. An UNKNOWN problem (a new,
   unregistered violation that survives the re-fetch) still HALTS the scan as before. A name that is not held is
   excluded from new signals; a held name keeps its position, is NOT exited on suspect data and has its
   stop frozen at the last good value (the engine's ``quarantine`` hook). The record lands in
   ``results/data_quarantine.json``.
3. HALT       - still, when the problem is SYSTEMIC: more than ``systemic_limit(universe)`` names fail
   at once, or the index series the CRS ranking divides by is itself bad. One name is a data defect;
   many names is an outage, and an outage must stop the scan exactly as before.

Nothing here weakens detection: the same checks run, and the guard still flags every seam. Only the
consequence is narrowed from "halt everything" to "set this name aside".
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

import pandas as pd

from nq.data.adjustment_guard import (
    assert_no_new_seams, evaluate_new_seams, live_exposure,
)

# Systemic breaker. A real vendor outage corrupts many names at once; a split or a re-adjustment hits
# one. max(5, 2% of the universe): ~10 names on the ~500-name live universe, never fewer than 5 on a
# small one. More than this and the scan halts as it always did.
SYSTEMIC_MIN_NAMES = 5
SYSTEMIC_UNIVERSE_FRAC = 0.02

# Index-series sanity (the CRS denominator). A daily move this large is not a market, it is a bad row;
# and a series that stops more than this many calendar days before the price data is stale.
INDEX_MAX_DAILY_MOVE = 0.20
INDEX_MAX_LAG_DAYS = 14
INDEX_MIN_ROWS = 250

# A re-fetch replaces a series only if it is at least this fraction as DEEP (bars) as the one it replaces.
# A throttled or truncated vendor answer is short and would otherwise swap deep history for a stub that
# happens to pass the seam check; the original is kept and the name quarantined instead.
REFETCH_MIN_DEPTH_FRAC = 0.90


class SystemicDataFailure(ValueError):
    """Too many names (or the index) are bad at once: a data outage, not a per-name defect. Halts the scan."""


def systemic_limit(universe_size: int) -> int:
    """Largest number of quarantined names still treated as per-name defects."""
    return max(SYSTEMIC_MIN_NAMES, math.ceil(SYSTEMIC_UNIVERSE_FRAC * int(universe_size)))


def check_index_series(csv_path, as_of=None) -> None:
    """Raise :class:`SystemicDataFailure` when the Nifty-50 series is missing, thin, non-positive, has an
    impossible one-day move, or lags the price data. Index trouble moves every name's CRS rank, so it is
    never a per-name quarantine."""
    p = Path(csv_path)
    if not p.exists():
        raise SystemicDataFailure(f"index series missing: {p}")
    df = pd.read_csv(p, parse_dates=["date"]).dropna(subset=["nifty50_close"]).sort_values("date")
    if len(df) < INDEX_MIN_ROWS:
        raise SystemicDataFailure(f"index series too short: {len(df)} rows (< {INDEX_MIN_ROWS})")
    c = df["nifty50_close"].astype(float)
    if (c <= 0).any():
        raise SystemicDataFailure("index series has non-positive closes")
    worst = c.pct_change().abs().dropna()
    if len(worst) and float(worst.max()) > INDEX_MAX_DAILY_MOVE:
        at = df["date"].iloc[int(worst.to_numpy().argmax()) + 1]
        raise SystemicDataFailure(f"index series has a {float(worst.max()):.0%} one-day move on {at.date()}")
    if as_of is not None:
        lag = (pd.Timestamp(as_of) - df["date"].iloc[-1]).days
        if lag > INDEX_MAX_LAG_DAYS:
            raise SystemicDataFailure(f"index series ends {df['date'].iloc[-1].date()}, {lag}d behind the "
                                      f"price data ({pd.Timestamp(as_of).date()})")


KNOWN = "known_seam"          # flagged by the registry: a REGISTERED seam (ADR-0013 live-exposure escalation)
UNKNOWN = "unknown"           # a new, unregistered violation of the adjustment-monotonicity guard


def offender_class(d: dict) -> str:
    """UNKNOWN if any finding on the name is an unregistered violation, else KNOWN."""
    return UNKNOWN if "adjustment_monotonicity" in d["kinds"] else KNOWN


def find_offenders(ohlcv: dict, positions, entry_dates=None, *, ref=None, known: dict | None = None,
                   as_of=None) -> dict[str, dict]:
    """{ticker: {"reasons": [...], "kinds": [...], "seams": [...]}} for every name the guards reject.

    Runs the same two checks the cron used to raise on - a dangerous unregistered monotonicity seam, and
    the ADR-0013 live-escalation (a registered seam that is in-window and unaccepted, or on a held name) -
    but reports per name instead of raising.
    """
    held = {str(p).upper() for p in (positions or [])}
    if as_of is None:
        ends = [pd.DatetimeIndex(df.index).max() for df in ohlcv.values() if df is not None and len(df)]
        as_of = max(ends) if ends else pd.Timestamp.today().normalize()
    out: dict[str, dict] = {}

    def _add(sym, kind, reason, seam):
        d = out.setdefault(sym, {"reasons": [], "kinds": [], "seams": []})
        d["kinds"].append(kind); d["reasons"].append(reason); d["seams"].append(seam)

    rep = evaluate_new_seams(ohlcv, ref, known=known, positions=list(held), as_of=as_of,
                             entry_dates=entry_dates)
    for s in rep.new_seams:
        _add(s["symbol"], "adjustment_monotonicity",
             f"adjustment factor fell x{s['step_factor']:.4f} between {s['window_start']} and "
             f"{s['window_end']}", s)
    ex = live_exposure(ohlcv, held, as_of=as_of, known=known)
    for s in ex["escalations"]:
        _add(s["symbol"], "live_seam_escalation",
             f"registered seam {s['seam_session']} x{s['step_factor']} "
             f"({'open position' if s['held'] else 'inside the 44-week window, not accepted'})", s)
    return out


def quarantine_or_halt(ohlcv: dict, positions, entry_dates, *, universe_size: int,
                       refetch: Callable[[list], dict] | None = None, ref=None,
                       known: dict | None = None) -> tuple[dict, dict]:
    """Self-heal each offending name, quarantine what stays broken, halt if it is systemic.

    ``refetch(tickers)`` must return ``{ticker: full-depth DataFrame}`` (empty/short results are ignored).
    Returns ``(ohlcv, record)``; ``ohlcv`` carries any healed series. Raises :class:`SystemicDataFailure`
    when more than ``systemic_limit(universe_size)`` names fail the guards, before or after self-heal.
    """
    held = {str(p).upper() for p in (positions or [])}
    ends = [pd.DatetimeIndex(df.index).max() for df in ohlcv.values() if df is not None and len(df)]
    as_of = max(ends) if ends else pd.Timestamp.today().normalize()
    kw = dict(ref=ref, known=known, as_of=as_of)
    limit = systemic_limit(universe_size)
    offenders = find_offenders(ohlcv, held, entry_dates, **kw)
    record = {"as_of": str(pd.Timestamp(as_of).date()), "systemic_limit": limit,
              "universe_size": int(universe_size), "flagged": sorted(offenders),
              "flagged_class": {t: offender_class(d) for t, d in sorted(offenders.items())}, "healed": [],
              "quarantined": [], "refetch_rejected_too_short": []}

    def _halt(names, when):
        raise SystemicDataFailure(
            f"SYSTEMIC DATA FAILURE - {len(names)} names fail the data guards {when} (limit {limit} = "
            f"max({SYSTEMIC_MIN_NAMES}, {SYSTEMIC_UNIVERSE_FRAC:.0%} of {universe_size})): "
            f"{sorted(names)[:15]}. This looks like a vendor outage, not a per-name defect; halting.")

    if len(offenders) > limit:
        _halt(offenders, "on the first check")
    if not offenders:
        return ohlcv, record

    attempted = set()
    if refetch is not None:
        try:
            fresh = refetch(sorted(offenders)) or {}
        except Exception as exc:  # noqa: BLE001 - a failed re-fetch means "could not heal", not "halt"
            print(f"  self-heal re-fetch failed ({type(exc).__name__}: {exc})", flush=True)
            fresh = {}
        attempted = set(offenders)
        ohlcv = dict(ohlcv)
        short: list = []
        for t, df in fresh.items():
            if t not in offenders or df is None or not len(df):
                continue
            old_n = len(ohlcv[t]) if ohlcv.get(t) is not None else 0
            if len(df) < REFETCH_MIN_DEPTH_FRAC * old_n:
                short.append(t)            # throttled/truncated re-fetch: never replace deep history with it
                continue
            ohlcv[t] = df                  # a re-fetched series is kept even if it still fails: it is the better one
        recheck = find_offenders({t: ohlcv[t] for t in offenders}, held, entry_dates, **kw)
        record["healed"] = sorted(t for t in offenders if t not in recheck)
        record["refetch_rejected_too_short"] = sorted(short)
        offenders = recheck

    if len(offenders) > limit:
        _halt(offenders, "after self-heal")
    # OWNER DECISION 2026-11-13: a KNOWN problem (a registered seam; the ADR-0013 escalation) is quarantined
    # and the scan continues. An UNKNOWN one - a new, unregistered violation that survived the full-depth
    # re-fetch - still HALTS exactly as before: nobody has diagnosed it, so the book does not trade around it.
    unknown = sorted(t for t, d in offenders.items() if offender_class(d) == UNKNOWN)
    if unknown:
        assert_no_new_seams({t: ohlcv[t] for t in unknown}, ref, known=known, positions=list(held),
                            as_of=as_of, entry_dates=entry_dates)      # raises ADJUSTMENT MONOTONICITY VIOLATED
        raise ValueError(f"UNKNOWN DATA PROBLEM survived the full re-fetch: {unknown}")   # unreachable guard
    for t, d in sorted(offenders.items()):
        is_held = t in held
        record["quarantined"].append({
            "ticker": t, "held": is_held, "class": offender_class(d),
            "kinds": sorted(set(d["kinds"])), "reason": "; ".join(d["reasons"]),
            "self_heal_attempted": t in attempted,
            "action": "position_kept_stop_frozen_no_exit" if is_held else "excluded_from_new_signals",
        })
    return ohlcv, record


_TRADE_FIELDS = ("entry", "close_price", "close_date", "r_multiple", "status", "exit_reason")
# The owner's single approval file for any change to the past (ADR-0018, 2026-11-13), relative to results/.
RESTATEMENTS_FILE = "forward_record/amendments.json"


def _closed(history) -> dict:
    out = {}
    for h in history if isinstance(history, list) else []:
        if isinstance(h, dict) and h.get("status") != "ACTIVE":
            out[f"{h.get('ticker')}|{h.get('signal_date')}"] = (str(h.get("ticker")), {f: h.get(f) for f in _TRADE_FIELDS})
    return out


def pending_restatements(prev_history, new_history, healed, declared: dict | None = None, *,
                         carried=None, is_rebase=None) -> list[dict]:
    """Closed trades of a name that was quarantined and has now HEALED, whose rebuilt history differs from the
    last published one - flagged for OWNER APPROVAL, never declared here (owner decision 2026-11-13).

    Declaring a restatement is the owner's act (an entry in ``results/forward_record/amendments.json``); this only
    lists what needs one, with the exact key and old-vs-new, so the health report can say so. Entries carried
    from the previous record stay listed until the owner declares their key. ``is_rebase(changed)`` lets the
    caller skip routine dividend-scale re-basing, which the drift check already treats as a warning.
    """
    healed = {str(t) for t in (healed or ())}
    declared = declared or {}
    prev, new = _closed(prev_history), _closed(new_history)
    out: dict[str, dict] = {}
    for k in sorted(prev):
        tk, old = prev[k]
        if tk not in healed:
            continue
        if k not in new:
            out[k] = {"ticker": tk, "trade": k, "kind": "vanished", "old": old, "new": None}
            continue
        cur = new[k][1]
        moved = {f: [old[f], cur[f]] for f in _TRADE_FIELDS if old[f] != cur[f]}
        if moved and not (is_rebase and is_rebase(moved)):
            out[k] = {"ticker": tk, "trade": k, "kind": "restated", "old": old, "new": cur, "changed": moved}
    for c in carried or []:
        if isinstance(c, dict) and c.get("trade") and c["trade"] not in out:
            out[c["trade"]] = c
    res = []
    for k, e in sorted(out.items()):
        if str(declared.get(k, "")).strip():
            continue                                    # the owner approved it: no longer pending
        e = dict(e)
        e["approve"] = (f'To approve, add "{k}": "<date> <reason>" to results/{RESTATEMENTS_FILE}. '
                        "Until then the history-drift check stays RED; the scan never declares it itself.")
        res.append(e)
    return res


def write_quarantine_record(path, record: dict) -> None:
    """Persist this scan's quarantine record (overwritten every run: an empty ``quarantined`` list is
    itself the statement that nothing was set aside this week)."""
    Path(path).write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
