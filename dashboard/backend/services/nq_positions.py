"""
Per-user NQ position view — joins three independent sources into a single
read model that powers the Portfolio "NiftyQuant Positions" section,
Signals "Held with Sell Guidance" tier, and `/api/positions/external`.

Sources joined:
  1. nq_orders (Postgres)         — what the user actually traded via NQ
  2. signals_history.json (repo)  — entry/stop/target/status context
  3. Kite holdings (live)         — current LTP + qty truth

The per-(user, signal) state machine `status_for_user` is computed here.
The cron is intentionally not aware of any of this: it writes the
market-only `actionability` field on signals; the per-user fusion happens
at request time so we never have to invalidate per-user state in the JSON.

Strict-overlap rule: when total NQ-attributed qty for a ticker exceeds
the live Kite qty (drift — user externally sold some), each NQ position's
`held_qty` is reduced FIFO by signal_date so the sum never exceeds Kite
truth. Drift is surfaced via `status_for_user = HOLDING_PARTIAL_SOLD`
and a `kite_qty_for_ticker` field for the UI banner.

The `signals_history.json` reader uses `fetch_github_json` so this works
both on Render (where the cron pushes to GitHub) and in local dev (where
the file is on disk). The reader is module-cached for ~30s to avoid
re-parsing on every request — see `_get_history_index`.
"""

import logging
import time
from datetime import datetime, date
from typing import Optional

from sqlalchemy.orm import Session

from database import NQOrder
from github_data import fetch_github_json
from services.fifo_matcher import held_qty_by_signal

logger = logging.getLogger("nq_positions")

# Module-level cache for parsed signals_history.json. Cron writes once per
# trading day, so 30s is generous; saves ~5ms per request under load.
_HISTORY_CACHE: dict = {"loaded_at": 0.0, "by_id": {}, "active_by_ticker": {}}
_HISTORY_TTL = 30.0

# The Bhanushali weekly book is the only live model (momentum removed 2026-07-13). Held-position
# exit context comes from signals_history_weekly.json.
_HISTORY_FILES = ("results/signals_history_weekly.json",)


def _load_history() -> None:
    now = time.time()
    if (now - _HISTORY_CACHE["loaded_at"]) < _HISTORY_TTL and _HISTORY_CACHE["by_id"]:
        return
    by_id: dict[str, dict] = {}
    active: dict[str, list] = {}
    for path in _HISTORY_FILES:
        raw = fetch_github_json(path)
        if not isinstance(raw, list):
            continue
        for sig in raw:
            tk = sig.get("ticker")
            sd = sig.get("signal_date")
            if tk and sd:
                by_id[f"{tk}__{sd}"] = sig
            st = (sig.get("status") or "").upper()
            act = (sig.get("actionability") or "").upper()
            if tk and (st == "ACTIVE" or act == "EXIT_REQUIRED"):
                active.setdefault(tk.upper(), []).append(sig)
    _HISTORY_CACHE["by_id"] = by_id
    # Only UNAMBIGUOUS tickers (exactly one open record) are eligible for the ticker fallback,
    # so a stacked same-ticker position is never mis-attributed (fault F6).
    _HISTORY_CACHE["active_by_ticker"] = {t: recs[0] for t, recs in active.items() if len(recs) == 1}
    _HISTORY_CACHE["loaded_at"] = now


def _get_history_index() -> dict[str, dict]:
    """{ '{ticker}__{signal_date}': record } unioned from BOTH the momentum and weekly history files."""
    _load_history()
    return _HISTORY_CACHE["by_id"]


def _history_active_by_ticker() -> dict[str, dict]:
    """{ ticker_upper: record } for tickers with exactly ONE open history record — the safe fallback
    when the order's signal_id (setup-Friday key) does not match the history record's fill-date key
    on the weekly book (fault F6)."""
    _load_history()
    return _HISTORY_CACHE["active_by_ticker"]


_CLOSED_STATUSES = {"HIT_TARGET", "HIT_STOP", "EXPIRED"}


def signal_lifecycle_state(signal_id: str, ticker: str) -> str:
    """'open' | 'closed' | 'unknown' for a per-user ephemeral holding, from the weekly history.

    Powers erase-on-completion in routers/holdings.py: a holding whose trade the model has
    COMPLETED (target/stop/expiry) returns 'closed' and is deleted. 'unknown' (a fresh buy not
    yet written to history) is KEPT — only a positive 'closed' erases.

    Matches signal_id ('{ticker}__{signal_date}') exactly first; falls back to the ticker because
    a held position's history record can be re-keyed by fill date, not the setup-Friday the buy
    card (and thus the holding) was keyed by (fault F6, nq_positions docstring)."""
    idx = _get_history_index()
    rec = idx.get(signal_id)
    if rec is not None:
        st = (rec.get("status") or "").upper()
        if st in _CLOSED_STATUSES:
            return "closed"
        if st == "ACTIVE" or (rec.get("actionability") or "").upper() == "EXIT_REQUIRED":
            return "open"
    tku = (ticker or "").upper()
    has_active = has_closed = False
    for key, r in idx.items():
        if key.split("__", 1)[0].upper() != tku:
            continue
        st = (r.get("status") or "").upper()
        if st == "ACTIVE" or (r.get("actionability") or "").upper() == "EXIT_REQUIRED":
            has_active = True
        elif st in _CLOSED_STATUSES:
            has_closed = True
    if has_active:
        return "open"
    if has_closed:
        return "closed"
    return "unknown"


def invalidate_history_cache() -> None:
    """Force re-read on next call — used by tests and by the optional
    /api/positions/refresh hook if added later."""
    _HISTORY_CACHE["loaded_at"] = 0.0
    _HISTORY_CACHE["by_id"] = {}
    _HISTORY_CACHE["active_by_ticker"] = {}


def _compute_actionability(sig: dict, today: date) -> str:
    """Mirror of the cron-side helper for back-compat: if the signal
    record predates PR2 and lacks 'actionability', derive it from
    status + signal_date + buy_window_until.

    Once PR2 ships and old signals naturally roll out, this fallback
    becomes mostly inert.
    """
    explicit = sig.get("actionability")
    if explicit:
        return explicit

    status = (sig.get("status") or "ACTIVE").upper()
    if status in ("HIT_TARGET", "HIT_STOP", "EXPIRED"):
        return "EXIT_REQUIRED"
    if status in ("REJECTED",):
        return "IRRELEVANT"

    # ACTIVE / NEAR_TARGET — gauge against buy window.
    bw = sig.get("buy_window_until")
    if bw:
        try:
            bw_d = datetime.strptime(bw, "%Y-%m-%d").date()
            return "BUY_OPEN" if today <= bw_d else "BUY_CLOSED"
        except Exception:
            pass

    # Fallback: 2 calendar-day window from signal_date.
    sd = sig.get("signal_date")
    if sd:
        try:
            sd_d = datetime.strptime(sd, "%Y-%m-%d").date()
            return "BUY_OPEN" if (today - sd_d).days <= 2 else "BUY_CLOSED"
        except Exception:
            pass
    return "BUY_OPEN"


def _classify_status_for_user(
    held_qty: int,
    kite_qty: int,
    actionability: str,
    signal_status: str,
) -> str:
    """The per-(user, signal) state used by the frontend to choose what
    affordance to show (Buy / Hold / Sell / Missed)."""
    if held_qty <= 0:
        if actionability == "BUY_OPEN":
            return "ACTIONABLE_BUY"
        if actionability == "EXIT_REQUIRED":
            return "INFORMATIONAL"
        return "MISSED"

    # held_qty > 0
    if held_qty > kite_qty:
        return "HOLDING_PARTIAL_SOLD"
    if actionability == "EXIT_REQUIRED":
        return "ACTIONABLE_SELL"
    return "HOLDING"


def _build_sell_guidance(sig: dict, last_price: Optional[float]) -> Optional[dict]:
    """Surface a clear sell recommendation when the signal has hit its
    exit conditions. Returns None for signals still in the Hold or Buy
    states — the UI shouldn't render a sell banner for those.

    We expose `original_target` and `original_stop` separately from the
    live `target`/`stop` so the user can see post-issuance breakeven
    migrations without losing the issue-time frame of reference.
    """
    status = (sig.get("status") or "").upper()
    if status not in ("HIT_TARGET", "HIT_STOP", "EXPIRED"):
        return None

    if status == "HIT_TARGET":
        return {
            "reason": "target",
            "tone": "bull",
            "headline": "Target hit — exit recommended",
            "suggested_exit_price": sig.get("original_target") or sig.get("target"),
            "urgency": "normal",
        }
    if status == "HIT_STOP":
        return {
            "reason": "stop",
            "tone": "bear",
            "headline": "Stop triggered — exit at market",
            "suggested_exit_price": last_price or sig.get("stop"),
            "urgency": "high",
        }
    return {
        "reason": "time",
        "tone": "warn",
        "headline": "Time exit reached — close position",
        "suggested_exit_price": last_price,
        "urgency": "normal",
    }


def _index_kite_holdings(holdings: list[dict]) -> dict[str, dict]:
    """Build a tradingsymbol → holding map. Tradingsymbol uppercased.

    Normalizes Kite's split between `quantity` (settled, T+0) and
    `t1_quantity` (just-bought, settling tomorrow) into a single
    `quantity` field representing the effective held position. Without
    this, a freshly-bought NQ signal would report `quantity=0` from Kite
    and the drift detector would flip the position to
    HOLDING_PARTIAL_SOLD on day 0 — a false alarm that resolves itself
    on day 1 when the share settles and quantity catches up.
    """
    out: dict[str, dict] = {}
    for h in holdings or []:
        ts = (h.get("tradingsymbol") or "").upper()
        if not ts:
            continue
        settled = int(h.get("quantity") or 0)
        t1 = int(h.get("t1_quantity") or 0)
        h_copy = dict(h)
        h_copy["quantity"] = settled + t1
        h_copy["settled_quantity"] = settled
        h_copy["t1_quantity"] = t1
        out[ts] = h_copy
    return out


def build_nq_positions(
    user_id: int,
    db: Session,
    kite_holdings: Optional[list[dict]] = None,
) -> list[dict]:
    """Build the user's NQ position list.

    Args:
        user_id: target user's id.
        db: SQLAlchemy session.
        kite_holdings: optional pre-fetched Kite holdings. If None, the
          live-price / drift fields default to entry price / no-drift.
          Pass live holdings whenever possible for accurate P&L.

    Returns a list of NQ position dicts, oldest-signal-first (so drift
    capping in same-ticker scenarios biases toward newer positions).
    """
    today = date.today()
    completed = (
        db.query(NQOrder)
        .filter(NQOrder.user_id == user_id, NQOrder.status == "COMPLETE")
        .order_by(NQOrder.placed_at.asc())
        .all()
    )
    by_signal = held_qty_by_signal(completed)
    if not by_signal:
        return []

    history = _get_history_index()
    kite_idx = _index_kite_holdings(kite_holdings or [])

    # Sort signal_ids by signal_date so older signals claim Kite qty first
    # (strict-overlap rule). Synthetic '__noid__' keys sort last.
    def _sort_key(item):
        sig_id, _ = item
        if sig_id.startswith("__noid__::"):
            return ("9999-99-99", sig_id)
        try:
            sd = sig_id.split("__", 1)[1]
        except IndexError:
            sd = ""
        return (sd, sig_id)

    sorted_items = sorted(by_signal.items(), key=_sort_key)

    # Track remaining Kite qty per ticker for drift-capping.
    kite_remaining: dict[str, int] = {
        t: int(h.get("quantity") or 0) for t, h in kite_idx.items()
    }

    positions: list[dict] = []
    for sig_id, info in sorted_items:
        ticker = info["ticker"]
        nq_qty = info["held_qty"]
        avg_buy = info["avg_fill_price"]
        first_buy_at = info["first_buy_at"]

        kite_holding = kite_idx.get(ticker.upper())
        kite_qty_total = int((kite_holding or {}).get("quantity") or 0)
        last_price = (kite_holding or {}).get("last_price")

        # Strict-overlap: cap nq_qty at remaining Kite qty for this ticker.
        # Older signals claim qty first.
        avail = kite_remaining.get(ticker.upper(), nq_qty if not kite_holding else 0)
        attributed_qty = min(nq_qty, avail) if kite_holding else nq_qty
        if kite_holding:
            kite_remaining[ticker.upper()] = max(0, avail - attributed_qty)

        # Pull signal context. If the signal was pruned from history (long
        # hold past prune-window pre-PR5, or fresh deploy with empty
        # history), we degrade gracefully with whatever the order itself
        # tells us.
        # Exact signal_id first; fall back to the unique open record for this ticker so a weekly
        # hold (order keyed by setup-Friday, history keyed by fill date) still resolves its exit
        # context / sell guidance (faults F5 + F6).
        sig = history.get(sig_id) or _history_active_by_ticker().get(ticker.upper()) or {}
        actionability = _compute_actionability(sig, today) if sig else "BUY_CLOSED"
        signal_status = (sig.get("status") or "ACTIVE").upper()

        # P&L — uses NQ-attributed qty, not raw nq_qty. If drift dropped
        # held_qty to 0 the P&L is also 0 (which is correct — the position
        # is effectively gone).
        pnl_rupees = 0.0
        pnl_pct = 0.0
        if last_price and avg_buy and attributed_qty > 0:
            pnl_rupees = round((last_price - avg_buy) * attributed_qty, 2)
            pnl_pct = round((last_price / avg_buy - 1) * 100, 2)

        # days_since / days_left from the signal record if available.
        days_since = sig.get("days_since")
        days_left = sig.get("days_left")
        if days_since is None and sig.get("signal_date"):
            try:
                sd = datetime.strptime(sig["signal_date"], "%Y-%m-%d").date()
                days_since = (today - sd).days
            except Exception:
                pass

        status_for_user = _classify_status_for_user(
            held_qty=nq_qty,
            kite_qty=kite_qty_total if kite_holding else nq_qty,
            actionability=actionability,
            signal_status=signal_status,
        )

        sell_guidance = _build_sell_guidance(sig, last_price)

        positions.append({
            "signal_id": sig_id,
            "ticker": ticker,
            "held_qty": attributed_qty,
            "nq_recorded_qty": nq_qty,
            "kite_qty_for_ticker": kite_qty_total,
            "avg_fill_price": avg_buy,
            "last_price": last_price,
            "pnl_rupees": pnl_rupees,
            "pnl_pct": pnl_pct,
            # Signal context (may be missing for orphan / pre-PR2 records)
            "entry": sig.get("entry"),
            "stop": sig.get("stop"),
            "original_stop": sig.get("original_stop") or sig.get("stop"),
            "target": sig.get("target"),
            "original_target": sig.get("original_target") or sig.get("target"),
            "signal_date": sig.get("signal_date"),
            "days_since": days_since,
            "days_left": days_left,
            "signal_status": signal_status,
            "actionability": actionability,
            "status_for_user": status_for_user,
            "sell_guidance": sell_guidance,
            "first_buy_at": first_buy_at.isoformat() if first_buy_at else None,
        })

    return positions


def build_external_holdings(
    nq_positions: list[dict],
    kite_holdings: list[dict],
) -> list[dict]:
    """Subtract NQ-attributed qty from Kite holdings to produce the
    'Other Kite Holdings' section.

    Each Kite holding becomes a row with `quantity = kite_qty - nq_attributed`.
    Rows with zero remaining qty are dropped. Rows for tickers with no NQ
    overlap pass through unchanged.
    """
    nq_by_ticker: dict[str, int] = {}
    for p in nq_positions:
        nq_by_ticker[p["ticker"].upper()] = nq_by_ticker.get(p["ticker"].upper(), 0) + (p["held_qty"] or 0)

    external: list[dict] = []
    for h in kite_holdings or []:
        ts = (h.get("tradingsymbol") or "").upper()
        # Same T+1 normalization the indexer applies — Kite splits a fresh
        # buy across `quantity` (settled) and `t1_quantity` (settling
        # tomorrow), and the effective held position is the sum. Without
        # this, a freshly-bought non-NQ stock looks like quantity=0 and
        # gets filtered out of the External list entirely.
        settled = int(h.get("quantity") or 0)
        t1 = int(h.get("t1_quantity") or 0)
        kite_qty = settled + t1
        nq_share = nq_by_ticker.get(ts, 0)
        remainder = kite_qty - nq_share
        if remainder <= 0:
            continue

        # Pass through Kite's shape but with the remainder qty so the UI
        # can compute pnl from average_price × remainder cleanly.
        copy = dict(h)
        copy["quantity"] = remainder
        copy["settled_quantity"] = settled
        copy["t1_quantity"] = t1
        copy["nq_attributed_qty"] = nq_share
        external.append(copy)
    return external


def held_signal_ids_all_users(db: Session) -> list[str]:
    """Union of signal_ids with held_qty > 0 across all users.

    Used by the cron prune exemption (PR5) to avoid deleting a signal
    record that any user is still holding. No per-user data leaves this
    function — only the set of signal_ids, which is itself derivable from
    public-side data (signals_history.json contains all signal_ids).
    """
    completed = (
        db.query(NQOrder)
        .filter(NQOrder.status == "COMPLETE")
        .order_by(NQOrder.user_id.asc(), NQOrder.placed_at.asc())
        .all()
    )

    # Group by user, run held-qty computation per user, union the keys.
    by_user: dict[int, list] = {}
    for r in completed:
        by_user.setdefault(r.user_id, []).append(r)

    held_keys: set[str] = set()
    for orders in by_user.values():
        per_user = held_qty_by_signal(orders)
        for k in per_user.keys():
            if not k.startswith("__noid__::"):
                held_keys.add(k)
    return sorted(held_keys)
