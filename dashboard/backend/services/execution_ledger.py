"""The durable, append-only self-reported execution ledger — Stage-4 keystone.

Spec: docs/EXECUTION_CAPTURE_SPEC.md. With no broker connection (ADR 0011) the site only INSTRUCTS;
the user executes on their own broker and reports each fill (qty + price). Those reports are immutable
`ExecutionEvent` rows; this module is the ONLY place that (a) appends an event and (b) derives a
position's remaining quantity, cost basis, and realized P&L from the raw events.

Two invariants shape the math:
  * APPEND-ONLY — a correction is a NEW event whose `corrects_event_id` points at the row it
    supersedes. `_effective_events` walks those chains so a corrected row is dropped from the maths but
    kept in the table (audit trail). We NEVER update or delete a row here.
  * TRUTH-FROM-EVENTS — remaining qty and realized P&L come from the user's actual fills
    (quantity-weighted, average-cost basis), never from the model's clean 2R/2.5R/SMA numbers.

Public API:
    record_event(db, user_id, signal_id, ticker, side, qty, price, ...) -> dict     # append one fill
    position_state(events, stop=None) -> dict                                        # derive one position
    get_positions(db, user_id) -> list[dict]                                         # all durable positions
    get_events(db, user_id, signal_id) -> list[dict]                                 # raw audit trail
    validate(side, qty, price, remaining, day_range=None) -> list[str]               # warnings, never blocks
"""
from __future__ import annotations

import logging

from database import ExecutionEvent

logger = logging.getLogger("execution_ledger")

BUY, SELL = "BUY", "SELL"
_SIDES = {BUY, SELL}
_TRANCHES = {"target", "pattern", "runner", "manual"}


# ── append ────────────────────────────────────────────

def record_event(
    db, *, user_id: int, signal_id: str, ticker: str, side: str, qty: int, price: float,
    tranche: str | None = None, executed_at=None, corrects_event_id: int | None = None,
    note: str | None = None, risk_tier_at_buy: str | None = None,
) -> dict:
    """Append ONE self-reported fill. Never overwrites (append-only); returns the new event as a dict.
    Caller is responsible for validation warnings (validate()); this records exactly what was said."""
    side = (side or "").strip().upper()
    if side not in _SIDES:
        raise ValueError(f"side must be BUY or SELL (got {side!r})")
    if qty is None or int(qty) <= 0:
        raise ValueError("qty must be a positive integer")
    if price is None or float(price) <= 0:
        raise ValueError("price must be > 0")
    tr = (tranche or "").strip().lower() or None
    if tr is not None and tr not in _TRANCHES:
        tr = "manual"
    row = ExecutionEvent(
        user_id=user_id, signal_id=signal_id, ticker=(ticker or "").upper(),
        side=side, qty=int(qty), price=float(price), tranche=tr,
        fill_source="self_reported", corrects_event_id=corrects_event_id,
        note=(note or None), executed_at=executed_at, risk_tier_at_buy=risk_tier_at_buy,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("exec-event user=%s signal=%s %s qty=%s px=%s%s", user_id, signal_id, side, qty, price,
                f" corrects={corrects_event_id}" if corrects_event_id else "")
    return _event_dict(row)


# ── derive ────────────────────────────────────────────

def _event_dict(r: ExecutionEvent, superseded: bool = False) -> dict:
    return {
        "id": r.id, "signal_id": r.signal_id, "ticker": r.ticker, "side": r.side,
        "qty": r.qty, "price": r.price, "tranche": r.tranche, "fill_source": r.fill_source,
        "corrects_event_id": r.corrects_event_id, "note": r.note,
        "executed_at": r.executed_at.isoformat() if r.executed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "superseded": superseded,
    }


def _effective_events(events: list[ExecutionEvent]) -> list[ExecutionEvent]:
    """Drop any event that a later event corrects (via corrects_event_id). The correcting event stays;
    the corrected one is superseded. Chains resolve transitively (a correction can itself be corrected)."""
    superseded_ids = {e.corrects_event_id for e in events if e.corrects_event_id is not None}
    return [e for e in events if e.id not in superseded_ids]


def _sort_key(e: ExecutionEvent):
    # Order by when the fill happened (self-reported), falling back to insertion order.
    return (e.executed_at or e.created_at, e.id)


def position_state(events: list[ExecutionEvent], stop: float | None = None) -> dict:
    """Derive one position from its events (average-cost basis). Pure — no DB, no mutation.

    Returns remaining qty, average buy price, realized P&L (Rs and %), realized R (if a stop is given),
    cost basis of the remaining shares, and a status (OPEN | CLOSED | EMPTY). Oversell (selling more
    than held, a self-report error) is tolerated: realized P&L still uses the last known average cost
    and remaining is floored at 0 — validate() warns at capture time so it rarely reaches here."""
    eff = sorted(_effective_events(events), key=_sort_key)
    shares = 0            # current share count (for average-cost tracking)
    cost = 0.0            # total cost of the CURRENT shares
    total_buy_qty = 0
    total_buy_cost = 0.0
    total_sold_qty = 0
    realized = 0.0        # Rs realized across all sells
    sold_basis = 0.0      # cost basis of the sold shares (for realized %)

    for e in eff:
        if e.side == BUY:
            shares += e.qty
            cost += e.qty * e.price
            total_buy_qty += e.qty
            total_buy_cost += e.qty * e.price
        else:  # SELL
            avg = (cost / shares) if shares > 0 else (total_buy_cost / total_buy_qty if total_buy_qty else 0.0)
            realized += e.qty * (e.price - avg)
            sold_basis += e.qty * avg
            total_sold_qty += e.qty
            reduce = min(e.qty, shares)
            cost -= avg * reduce
            shares = max(0, shares - reduce)

    remaining = total_buy_qty - total_sold_qty
    avg_buy = (total_buy_cost / total_buy_qty) if total_buy_qty else None
    status = "EMPTY" if total_buy_qty == 0 else ("OPEN" if remaining > 0 else "CLOSED")
    realized_pct = round(realized / sold_basis * 100, 2) if sold_basis > 0 else None

    realized_r = None
    if stop is not None and avg_buy is not None and total_sold_qty > 0:
        risk_per_share = avg_buy - float(stop)
        if risk_per_share > 0:
            realized_r = round(realized / (risk_per_share * total_sold_qty), 3)

    return {
        "remaining_qty": max(0, remaining),
        "raw_remaining_qty": remaining,                 # can be negative if oversold (data error)
        "avg_buy_price": round(avg_buy, 2) if avg_buy is not None else None,
        "total_bought_qty": total_buy_qty,
        "total_sold_qty": total_sold_qty,
        "realized_pnl": round(realized, 2),
        "realized_pnl_pct": realized_pct,
        "realized_r": realized_r,
        "cost_basis_remaining": round((avg_buy or 0.0) * max(0, remaining), 2) if avg_buy else None,
        "status": status,
        "n_events": len(eff),
    }


def get_positions(db, user_id: int, stops: dict | None = None) -> list[dict]:
    """Every durable position for a user (one per signal_id), derived from the append-only events.

    `stops` optionally maps signal_id -> frozen model stop so realized R can be computed. Positions are
    returned newest-first by their most recent event; CLOSED positions are kept (durable track record)."""
    rows = (
        db.query(ExecutionEvent)
        .filter(ExecutionEvent.user_id == user_id)
        .order_by(ExecutionEvent.id.asc())
        .all()
    )
    by_sig: dict[str, list[ExecutionEvent]] = {}
    for r in rows:
        by_sig.setdefault(r.signal_id, []).append(r)

    out = []
    for sig, evs in by_sig.items():
        stop = (stops or {}).get(sig)
        st = position_state(evs, stop=stop)
        last = max(evs, key=_sort_key)
        out.append({
            "signal_id": sig,
            "ticker": evs[0].ticker,
            "last_event_at": (last.executed_at or last.created_at).isoformat() if (last.executed_at or last.created_at) else None,
            **st,
        })
    out.sort(key=lambda p: p["last_event_at"] or "", reverse=True)
    return out


def get_events(db, user_id: int, signal_id: str) -> list[dict]:
    """The raw event list for one position — the full audit trail, INCLUDING superseded (corrected)
    rows, each flagged `superseded`. Ordered as they occurred (executed_at, then insertion)."""
    rows = (
        db.query(ExecutionEvent)
        .filter(ExecutionEvent.user_id == user_id, ExecutionEvent.signal_id == signal_id)
        .all()
    )
    superseded_ids = {e.corrects_event_id for e in rows if e.corrects_event_id is not None}
    rows.sort(key=_sort_key)
    return [_event_dict(r, superseded=(r.id in superseded_ids)) for r in rows]


# ── validate (warn, never block) ──────────────────────

def validate(side: str, qty: int, price: float, remaining: int,
             day_range: tuple[float, float] | None = None) -> list[str]:
    """Soft sanity checks (spec §3). Returns human-readable warnings; the caller records the event
    regardless — it is the user's capital and their self-report."""
    warns: list[str] = []
    side = (side or "").upper()
    if qty is None or qty <= 0:
        warns.append("Quantity should be greater than zero.")
    if price is None or price <= 0:
        warns.append("Price should be greater than zero.")
    if side == SELL and qty is not None and remaining is not None and qty > remaining:
        warns.append(f"You're selling {qty} but only {remaining} remain on this position — sure?")
    if day_range and price:
        lo, hi = day_range
        if lo and hi and not (lo <= price <= hi):
            warns.append(f"That price {price:g} is outside today's traded range [{lo:g}, {hi:g}] — sure?")
    return warns
