"""
NQ Orders router — tracks orders placed through NiftyQuant Buy/Sell buttons.

These endpoints power the Accounting and Journal pages. External Kite trades
(placed directly on kite.zerodha.com) are intentionally NOT reflected here —
per product decision, those pages show only what the user executed via our UI.

Flow (each order):
  1. Frontend: POST /api/kite/orders/:variety  → Kite returns { order_id }
  2. Frontend: POST /api/nq-orders              → creates tracking row (PENDING)
  3. WS: order_update from Kite                 → ws_manager patches status/fill/net

Endpoints:
  POST   /api/nq-orders                  create tracking row after Kite order placed
  GET    /api/nq-orders                  list rows (filters: year, month, ticker, status)
  GET    /api/nq-orders/{id}             single row
  GET    /api/nq-orders/stats            FY P&L + STCG/LTCG split + brokerage/STT
  PATCH  /api/nq-orders/{id}/notes       journal rationale (append or replace)
  DELETE /api/nq-orders/{id}             cancel local record (does NOT cancel Kite order)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db, User, NQOrder
from auth import get_current_user
from config import BROKERAGE_PCT, STT_PCT

logger = logging.getLogger("nq_orders")

router = APIRouter(prefix="/nq-orders", tags=["nq-orders"])


def _compute_costs(action: str, fill_price: float, qty: int) -> tuple[float, float]:
    """Transaction costs for a filled leg → (brokerage, stt), rounded to paise.

    Delivery equity (config.py): brokerage = BROKERAGE_PCT on BOTH legs, and
    STT = STT_PCT on BOTH legs (buy AND sell — 0.1% per leg; sell-only is the
    intraday/F&O rule and does NOT apply to our delivery swing trades). This
    matches the backtest cost model + config.delivery_leg_cost so the displayed
    cost reflects what the user actually paid. These feed fifo_matcher (which
    sums row.brokerage/row.stt) so the Accounting 'Tax costs' KPIs and
    net_pnl = realised − brokerage − STT are correct.
    """
    notional = float(fill_price) * int(qty)
    brokerage = round(BROKERAGE_PCT * notional, 2)
    stt = round(STT_PCT * notional, 2)
    return brokerage, stt


# ── Request / response schemas ────────────────────────

class CreateNQOrderRequest(BaseModel):
    """Input when the frontend records a placed order."""
    kite_order_id: Optional[str] = None
    signal_id: Optional[str] = None       # "{ticker}__{signal_date}"
    ticker: str
    action: str                            # BUY | SELL
    qty: int = Field(ge=1)
    placed_price: Optional[float] = None
    notes: Optional[str] = None


class UpdateNotesRequest(BaseModel):
    notes: str


class ReconcileDriftRequest(BaseModel):
    """Manual close for the drift case — user externally sold (or transferred)
    a position without going through NQ's UI, so /positions/nq shows
    HOLDING_PARTIAL_SOLD until a synthetic SELL row brings the books in line.
    """
    signal_id: str
    qty: int = Field(ge=1)
    fill_price: float = Field(gt=0)
    sold_at: Optional[datetime] = None     # default: now
    notes: Optional[str] = None            # journal — defaults to "Reconciled drift"


class NQOrderOut(BaseModel):
    id: int
    user_id: int
    kite_order_id: Optional[str] = None
    signal_id: Optional[str] = None
    ticker: str
    action: str
    qty: int
    placed_price: Optional[float] = None
    fill_price: Optional[float] = None
    brokerage: float = 0.0
    stt: float = 0.0
    net_amount: Optional[float] = None
    status: str
    placed_at: datetime
    filled_at: Optional[datetime] = None
    source: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class NQStatsOut(BaseModel):
    period: str
    realised_pnl: float
    unrealised_pnl: float
    total_brokerage: float
    total_stt: float
    net_pnl: float
    stcg_pnl: float       # short-term capital gains (held < 1 year)
    ltcg_pnl: float       # long-term capital gains (held >= 1 year)
    trades_matched: int
    open_positions: int


# ── Helpers ────────────────────────────────────────────

def _serialize(order: NQOrder) -> dict:
    """Hand-rolled serializer — Pydantic v2 from_attributes works, but we
    want deterministic ordering and no ORM lazy-load surprises."""
    return {
        "id": order.id,
        "user_id": order.user_id,
        "kite_order_id": order.kite_order_id,
        "signal_id": order.signal_id,
        "ticker": order.ticker,
        "action": order.action,
        "qty": order.qty,
        "placed_price": order.placed_price,
        "fill_price": order.fill_price,
        "brokerage": order.brokerage or 0.0,
        "stt": order.stt or 0.0,
        "net_amount": order.net_amount,
        "status": order.status,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "filled_at": order.filled_at.isoformat() if order.filled_at else None,
        "source": order.source,
        "notes": order.notes,
    }


# ── Endpoints ──────────────────────────────────────────

@router.post("", status_code=201)
async def create_nq_order(
    req: CreateNQOrderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Record a tracking row after the frontend successfully placed the order
    on Kite. The Kite-side result (kite_order_id) is required if the frontend
    wants the row to be WS-patchable on fills. Without it the row stays in
    PENDING until manually reconciled.

    Idempotent on kite_order_id — if a row already exists for this broker order,
    we return the existing row instead of creating a duplicate. Lets the
    frontend retry safely on network failure without double-recording.
    """
    action = req.action.upper()
    if action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="action must be BUY or SELL")

    if req.kite_order_id:
        existing = (
            db.query(NQOrder)
            .filter(NQOrder.kite_order_id == req.kite_order_id)
            .first()
        )
        if existing:
            if existing.user_id != user.id:
                # Same kite_order_id on a different user is an integrity fault —
                # broker order ids are globally unique per account.
                raise HTTPException(status_code=409, detail="kite_order_id conflict")
            return {"status": "exists", "order": _serialize(existing)}

    order = NQOrder(
        user_id=user.id,
        kite_order_id=req.kite_order_id,
        signal_id=req.signal_id,
        ticker=req.ticker.upper(),
        action=action,
        qty=req.qty,
        placed_price=req.placed_price,
        status="PENDING",
        placed_at=datetime.utcnow(),
        source="niftyquant_signal",
        notes=req.notes,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    logger.info(
        "nq_order created: user=%s kite=%s %s %d %s @ %s",
        user.id, req.kite_order_id, action, req.qty, req.ticker, req.placed_price,
    )
    return {"status": "created", "order": _serialize(order)}


@router.get("")
async def list_nq_orders(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    ticker: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(200, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the user's tracked orders, most recent first.

    The Accounting page uses (year, month) for its ledger view; the Journal
    page uses status='COMPLETE' to surface filled orders as review entries.
    """
    q = db.query(NQOrder).filter(NQOrder.user_id == user.id)
    if year is not None:
        q = q.filter(func.extract("year", NQOrder.placed_at) == year)
    if month is not None:
        q = q.filter(func.extract("month", NQOrder.placed_at) == month)
    if ticker:
        q = q.filter(NQOrder.ticker == ticker.upper())
    if status:
        q = q.filter(NQOrder.status == status.upper())

    rows = q.order_by(NQOrder.placed_at.desc()).limit(limit).all()
    return {"orders": [_serialize(r) for r in rows], "count": len(rows)}


@router.get("/stats")
async def nq_order_stats(
    period: str = Query("fy", pattern="^(fy|ytd|all|30d)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate P&L / tax / brokerage for the requested period.

    Matching logic (FIFO): pair each SELL row with the earliest still-open
    BUY for the same ticker. Realised P&L = (sell_fill - buy_fill) * qty
    minus brokerage/STT on both legs. Remaining unmatched BUY rows contribute
    `open_positions` (unrealised is left as 0 — live prices aren't in this
    endpoint's scope; frontend composes that from /kite/holdings).
    """
    q = db.query(NQOrder).filter(
        NQOrder.user_id == user.id,
        NQOrder.status == "COMPLETE",
    )

    now = datetime.utcnow()
    if period == "fy":
        # Indian FY: Apr 1 — Mar 31
        fy_start_year = now.year if now.month >= 4 else now.year - 1
        fy_start = datetime(fy_start_year, 4, 1)
        q = q.filter(NQOrder.placed_at >= fy_start)
    elif period == "ytd":
        q = q.filter(NQOrder.placed_at >= datetime(now.year, 1, 1))
    elif period == "30d":
        from datetime import timedelta
        q = q.filter(NQOrder.placed_at >= now - timedelta(days=30))
    # period == "all" → no date filter

    rows = q.order_by(NQOrder.placed_at.asc()).all()

    # Tax/accounting view — match by ticker (shares are fungible by
    # symbol for FIFO tax purposes). The per-signal lifecycle view used
    # by /positions/nq keys by signal_id instead; both use the same
    # underlying matcher in services/fifo_matcher.
    from services.fifo_matcher import match_fifo
    fifo = match_fifo(rows)  # default key = ticker

    return {
        "period": period,
        "realised_pnl": round(fifo.realised_pnl, 2),
        "unrealised_pnl": 0.0,             # frontend composes from /kite/holdings
        "total_brokerage": round(fifo.total_brokerage, 2),
        "total_stt": round(fifo.total_stt, 2),
        "net_pnl": round(fifo.realised_pnl - fifo.total_brokerage - fifo.total_stt, 2),
        "stcg_pnl": round(fifo.stcg_pnl, 2),
        "ltcg_pnl": round(fifo.ltcg_pnl, 2),
        "trades_matched": fifo.trades_matched,
        "open_positions": fifo.open_positions,
    }


@router.post("/reconcile", status_code=201)
async def reconcile_drift(
    req: ReconcileDriftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Insert a synthetic SELL nq_orders row for a position the user
    closed externally (i.e. on kite.zerodha.com directly).

    Why a separate endpoint vs reusing POST /api/nq-orders: the regular
    create endpoint expects a Kite order to actually exist (PENDING
    awaiting fill). Reconciliation is for trades that already happened
    outside our UI, so we mark the row COMPLETE up front with the
    user-supplied fill price. FIFO matching in /api/nq-orders/stats and
    /api/positions/nq immediately reflects the close.

    The ticker is parsed from the signal_id ("{ticker}__{date}") so the
    caller doesn't have to look it up; the signal_id is also what links
    this SELL to the originating BUY for FIFO matching.

    Source is set to 'manual_reconcile' so the Journal page can
    distinguish reconciled rows from regular trades. Notes default to
    a stamp the user can edit later from the Journal.
    """
    # Parse the signal_id to derive ticker. Defensive: if the format is
    # unexpected, refuse rather than guess and risk creating an
    # unrecoverable orphan row.
    try:
        ticker, sig_date = req.signal_id.split("__", 1)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="signal_id must be '<TICKER>__<YYYY-MM-DD>'",
        )

    sold_at = req.sold_at or datetime.utcnow()
    note_default = f"Reconciled drift — closed externally on Kite (signal_date {sig_date})"
    _brokerage, _stt = _compute_costs("SELL", req.fill_price, req.qty)

    order = NQOrder(
        user_id=user.id,
        kite_order_id=None,                 # No Kite order — user closed externally
        signal_id=req.signal_id,
        ticker=ticker.upper(),
        action="SELL",
        qty=req.qty,
        placed_price=req.fill_price,
        fill_price=req.fill_price,
        status="COMPLETE",                  # Trade already happened
        placed_at=sold_at,
        filled_at=sold_at,
        net_amount=req.fill_price * req.qty,    # SELL credits — sign convention
        brokerage=_brokerage,
        stt=_stt,
        source="manual_reconcile",
        notes=req.notes or note_default,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    logger.info(
        "nq_order reconciled drift: user=%s signal=%s sold %d @ %.2f",
        user.id, req.signal_id, req.qty, req.fill_price,
    )
    return {"status": "reconciled", "order": _serialize(order)}


@router.get("/{order_id}")
async def get_nq_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = (
        db.query(NQOrder)
        .filter(NQOrder.id == order_id, NQOrder.user_id == user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize(order)


@router.patch("/{order_id}/notes")
async def update_notes(
    order_id: int,
    req: UpdateNotesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Journal rationale — called from the Journal page TradeCard edit flow."""
    order = (
        db.query(NQOrder)
        .filter(NQOrder.id == order_id, NQOrder.user_id == user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.notes = req.notes
    db.commit()
    db.refresh(order)
    return {"status": "ok", "order": _serialize(order)}


@router.delete("/{order_id}", status_code=204)
async def delete_nq_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes only the local tracking row. Does NOT cancel the Kite order —
    that has its own endpoint. Useful if the user placed a test order and
    wants to scrub it from their journal history."""
    order = (
        db.query(NQOrder)
        .filter(NQOrder.id == order_id, NQOrder.user_id == user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return None


# ── Internal helpers for WS patching ───────────────────

def patch_from_kite_update(db: Session, update: dict) -> Optional[NQOrder]:
    """Called from ws_manager when a Kite order_update arrives.

    Returns the patched row if a matching nq_orders entry exists, else None.
    The caller (ws_manager) is responsible for opening/closing the DB session.

    Field map (Kite order_update → nq_orders):
      status 'COMPLETE'  → status=COMPLETE, fill_price=average_price, filled_at=now,
                           net_amount = fill_price * filled_quantity (signed by action)
      status 'REJECTED'  → status=REJECTED
      status 'CANCELLED' → status=CANCELLED
      status 'OPEN'      → status=OPEN
    """
    kite_order_id = update.get("order_id") or update.get("kite_order_id")
    if not kite_order_id:
        return None

    order = (
        db.query(NQOrder).filter(NQOrder.kite_order_id == str(kite_order_id)).first()
    )
    if not order:
        return None

    kite_status = (update.get("status") or "").upper()
    if kite_status in ("COMPLETE", "COMPLETED", "FILLED"):
        order.status = "COMPLETE"
        avg_price = update.get("average_price") or update.get("price")
        filled_qty = update.get("filled_quantity") or update.get("quantity") or order.qty
        if avg_price is not None:
            order.fill_price = float(avg_price)
            sign = 1 if order.action == "SELL" else -1   # SELL credits, BUY debits
            order.net_amount = sign * float(avg_price) * int(filled_qty)
            order.brokerage, order.stt = _compute_costs(order.action, avg_price, filled_qty)
        order.filled_at = datetime.utcnow()
    elif kite_status == "REJECTED":
        order.status = "REJECTED"
    elif kite_status == "CANCELLED":
        order.status = "CANCELLED"
    elif kite_status in ("OPEN", "TRIGGER PENDING", "MODIFIED"):
        order.status = "OPEN"

    db.commit()
    return order
