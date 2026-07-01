"""
FIFO matcher for NQOrder rows — the canonical pairing logic for realised
P&L, brokerage, STT, STCG/LTCG split, and remaining-open lots.

Extracted from routers/nq_orders.py /stats so the same algorithm powers:
  - GET /api/nq-orders/stats   (tax + accounting view, keyed by ticker)
  - services/nq_positions.py    (per-signal held qty, keyed by signal_id)

The matcher walks COMPLETE orders in placed_at order, grouping by an
arbitrary key (ticker for tax, signal_id for per-position). For each SELL,
it pairs against the earliest unmatched BUYs in that group, accumulates
realised P&L, and classifies STCG vs LTCG by hold duration.

Mutating buy.qty in-flight is intentional and confined to a working copy
of the order (we wrap each row in OpenLot below) so the caller's NQOrder
SQLAlchemy instance is never touched.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable, Optional


@dataclass
class OpenLot:
    """A still-open BUY lot with qty that decrements as SELLs eat it.

    Keeps a pointer back to the originating NQOrder so callers can read
    metadata (signal_id, fill_price, etc.) without re-querying the DB.
    """
    qty: int
    fill_price: float
    placed_at: datetime
    order: object  # NQOrder — kept loose to avoid a circular import


@dataclass
class FifoResult:
    realised_pnl: float = 0.0
    total_brokerage: float = 0.0
    total_stt: float = 0.0
    stcg_pnl: float = 0.0
    ltcg_pnl: float = 0.0
    trades_matched: int = 0
    open_lots_by_key: dict[str, list[OpenLot]] = field(default_factory=dict)

    @property
    def open_positions(self) -> int:
        return sum(len(lots) for lots in self.open_lots_by_key.values())


def _ticker_key(o) -> str:
    return o.ticker


def match_fifo(
    orders: Iterable,
    key_fn: Callable[[object], str] = _ticker_key,
) -> FifoResult:
    """Walk COMPLETE orders in placed_at order, pairing SELLs against the
    earliest unmatched BUY within each key bucket.

    `orders` must be sorted by placed_at ascending. Filtering to
    status='COMPLETE' is the caller's responsibility — passing PENDING/OPEN
    rows would skew the FIFO queues with unfilled orders.

    `key_fn` decides the matching bucket. Default = ticker (matches Kite's
    settlement model: shares of one ticker are fungible). Pass a signal_id
    keyer when you want per-signal lifecycle accounting.

    Note on fill_price fallback: if a row lacks fill_price (broker hasn't
    confirmed yet, or imported historical data), placed_price is used.
    Both being None falls through to 0.0, which produces a degenerate
    pairing — the caller should pre-filter such rows if accuracy matters.
    """
    result = FifoResult()
    open_lots: dict[str, list[OpenLot]] = {}

    for r in orders:
        result.total_brokerage += r.brokerage or 0.0
        result.total_stt += r.stt or 0.0

        if r.action == "BUY":
            bucket = open_lots.setdefault(key_fn(r), [])
            bucket.append(OpenLot(
                qty=r.qty,
                fill_price=r.fill_price or r.placed_price or 0.0,
                placed_at=r.placed_at,
                order=r,
            ))
            continue

        # SELL — match against FIFO queue for this key.
        remaining = r.qty
        bucket = open_lots.get(key_fn(r), [])
        sell_fill = r.fill_price or r.placed_price or 0.0

        while remaining > 0 and bucket:
            lot = bucket[0]
            match_qty = min(remaining, lot.qty)
            pnl = (sell_fill - lot.fill_price) * match_qty
            result.realised_pnl += pnl
            result.trades_matched += 1

            # Hold-duration classification — Indian tax rule: >= 365 days = LTCG.
            # Using placed_at because fill_at is sometimes None for historical
            # imports; intra-session fills make this a near-zero-error proxy.
            if lot.placed_at and r.placed_at:
                held_days = (r.placed_at - lot.placed_at).days
                if held_days >= 365:
                    result.ltcg_pnl += pnl
                else:
                    result.stcg_pnl += pnl

            remaining -= match_qty
            lot.qty -= match_qty
            if lot.qty <= 0:
                bucket.pop(0)

    result.open_lots_by_key = open_lots
    return result


def held_qty_by_signal(orders: Iterable) -> dict[str, dict]:
    """Convenience wrapper that returns a per-signal_id summary suitable
    for the Portfolio NQ Positions view.

    `orders` should already be filtered to status='COMPLETE' and sorted by
    placed_at ascending.

    Output shape:
        {
            "RELIANCE__2026-04-22": {
                "ticker": "RELIANCE",
                "held_qty": 100,
                "avg_fill_price": 1234.56,
                "first_buy_at": datetime(...),
                "open_lots": [OpenLot, ...],
            },
            ...
        }

    Signals with `held_qty == 0` (fully exited) are omitted. Rows with no
    signal_id fall under a synthetic key `__noid__::{ticker}` so external-
    style or legacy NQ orders aren't lost.
    """
    def key_fn(o):
        return o.signal_id or f"__noid__::{o.ticker}"

    fifo = match_fifo(orders, key_fn=key_fn)

    out: dict[str, dict] = {}
    for key, lots in fifo.open_lots_by_key.items():
        if not lots:
            continue
        total_qty = sum(l.qty for l in lots)
        if total_qty <= 0:
            continue
        weighted_avg = sum(l.qty * l.fill_price for l in lots) / total_qty
        ticker = lots[0].order.ticker
        first_buy_at = min(l.placed_at for l in lots)
        out[key] = {
            "ticker": ticker,
            "held_qty": total_qty,
            "avg_fill_price": round(weighted_avg, 2),
            "first_buy_at": first_buy_at,
            "open_lots": lots,
        }
    return out
