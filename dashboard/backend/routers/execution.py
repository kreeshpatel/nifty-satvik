"""Self-reported execution ledger router — the Stage-4 capture endpoints (EXECUTION_CAPTURE_SPEC.md).

The site instructs; the user executes on their own broker and reports each fill (qty + price) here.
Every write is an APPEND to the immutable `execution_events` ledger (services/execution_ledger.py):

  POST   /api/execution/buy                 append a BUY fill (qty + price); allows averaging in
  POST   /api/execution/sell                append a partial-aware SELL fill (qty + price + tranche)
  POST   /api/execution/correct             append a CORRECTING event (supersedes a prior row, audit-safe)
  GET    /api/execution/positions           the user's durable positions (remaining qty, cost, realized P&L)
  GET    /api/execution/position/{sig}      one position: derived state + its full event audit trail

Tenant-isolated: every row is scoped to the authenticated user (the bearer token is the authority; the
frontend never sends a user id). Self-report-only: fill_source is always 'self_reported', never verified.
Validation WARNS but never blocks — it is the user's capital and their report (spec §3).
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, User, ExecutionEvent
from auth import get_current_user
from services import execution_ledger as ledger
from services.signal_snapshots import get_snapshot

logger = logging.getLogger("execution")

router = APIRouter(prefix="/execution", tags=["execution"])

# signal_id == "{TICKER}__{YYYY-MM-DD}" — the canonical key shared with UserHolding / SignalSnapshot.
_SIGNAL_ID_RE = re.compile(r"^([A-Z0-9&._-]{1,32})__(\d{4}-\d{2}-\d{2})$")


def _parse_signal_id(signal_id: str) -> tuple[str, str]:
    m = _SIGNAL_ID_RE.match((signal_id or "").strip().upper())
    if not m:
        raise HTTPException(status_code=422, detail="Invalid signal_id (expected '{TICKER}__{YYYY-MM-DD}')")
    return m.group(1), (signal_id or "").strip()


def _frozen_stop(signal_id: str, db) -> float | None:
    """The model's frozen stop for this signal (from the immutable snapshot), for realized-R maths."""
    try:
        snap = get_snapshot(db, signal_id)
        return float(snap["stop"]) if snap and snap.get("stop") is not None else None
    except Exception:  # noqa: BLE001 — realized R is best-effort; never break a capture
        return None


def _events_for(db, user_id: int, signal_id: str) -> list[ExecutionEvent]:
    return (
        db.query(ExecutionEvent)
        .filter(ExecutionEvent.user_id == user_id, ExecutionEvent.signal_id == signal_id)
        .all()
    )


def _position_payload(db, user_id: int, signal_id: str, ticker: str) -> dict:
    evs = _events_for(db, user_id, signal_id)
    state = ledger.position_state(evs, stop=_frozen_stop(signal_id, db))
    return {"signal_id": signal_id, "ticker": ticker, **state}


# ── request models ────────────────────────────────────

class BuyRequest(BaseModel):
    signal_id: str = Field(..., min_length=3, max_length=128)
    ticker: str | None = Field(default=None, max_length=32)
    qty: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    executed_at: str | None = None
    risk_tier_at_buy: str | None = None
    note: str | None = Field(default=None, max_length=256)


class SellRequest(BaseModel):
    signal_id: str = Field(..., min_length=3, max_length=128)
    qty: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    tranche: str | None = None                  # target | pattern | runner | manual
    executed_at: str | None = None
    note: str | None = Field(default=None, max_length=256)
    day_low: float | None = None                # optional: today's traded low  (frontend has the quote)
    day_high: float | None = None               # optional: today's traded high


class CorrectRequest(BaseModel):
    corrects_event_id: int = Field(..., gt=0)
    signal_id: str = Field(..., min_length=3, max_length=128)
    ticker: str | None = Field(default=None, max_length=32)
    side: str = Field(..., pattern="^(BUY|SELL|buy|sell)$")
    qty: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    tranche: str | None = None
    executed_at: str | None = None
    note: str | None = Field(default=None, max_length=256)


# ── endpoints ─────────────────────────────────────────

@router.post("/buy", status_code=201)
def record_buy(req: BuyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Append a self-reported BUY. Multiple buys on one signal are allowed (averaging in)."""
    ticker, signal_id = _parse_signal_id(req.signal_id)
    warnings = ledger.validate("BUY", req.qty, req.price, remaining=None,
                               day_range=None)
    event = ledger.record_event(
        db, user_id=user.id, signal_id=signal_id, ticker=(req.ticker or ticker),
        side="BUY", qty=req.qty, price=req.price, executed_at=req.executed_at,
        risk_tier_at_buy=req.risk_tier_at_buy, note=req.note,
    )
    return {"event": event, "position": _position_payload(db, user.id, signal_id, (req.ticker or ticker).upper()),
            "warnings": warnings}


@router.post("/sell", status_code=201)
def record_sell(req: SellRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Append a partial-aware self-reported SELL. Computes the remaining qty BEFORE this sell so it can
    warn on an oversell / out-of-range price — but records the event regardless (warn, never block)."""
    ticker, signal_id = _parse_signal_id(req.signal_id)
    before = ledger.position_state(_events_for(db, user.id, signal_id))
    day_range = (req.day_low, req.day_high) if (req.day_low and req.day_high) else None
    warnings = ledger.validate("SELL", req.qty, req.price, remaining=before["remaining_qty"], day_range=day_range)
    event = ledger.record_event(
        db, user_id=user.id, signal_id=signal_id, ticker=ticker,
        side="SELL", qty=req.qty, price=req.price, tranche=req.tranche,
        executed_at=req.executed_at, note=req.note,
    )
    return {"event": event, "position": _position_payload(db, user.id, signal_id, ticker),
            "warnings": warnings}


@router.post("/correct", status_code=201)
def record_correction(req: CorrectRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Append a CORRECTING event that supersedes a prior one (never edits it in place). The corrected
    row stays in the ledger, flagged superseded in the audit trail; the maths use only this event."""
    ticker, signal_id = _parse_signal_id(req.signal_id)
    prior = (
        db.query(ExecutionEvent)
        .filter(ExecutionEvent.user_id == user.id, ExecutionEvent.id == req.corrects_event_id,
                ExecutionEvent.signal_id == signal_id)
        .first()
    )
    if prior is None:
        raise HTTPException(status_code=404, detail="No such prior event on this position to correct")
    event = ledger.record_event(
        db, user_id=user.id, signal_id=signal_id, ticker=(req.ticker or ticker),
        side=req.side, qty=req.qty, price=req.price, tranche=req.tranche,
        executed_at=req.executed_at, corrects_event_id=req.corrects_event_id, note=req.note,
    )
    return {"event": event, "position": _position_payload(db, user.id, signal_id, (req.ticker or ticker).upper())}


@router.get("/positions")
def list_positions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every durable position (OPEN and CLOSED) with derived remaining qty, cost basis, realized P&L."""
    rows = db.query(ExecutionEvent).filter(ExecutionEvent.user_id == user.id).all()
    sigs = {r.signal_id for r in rows}
    stops = {s: _frozen_stop(s, db) for s in sigs}
    return {"positions": ledger.get_positions(db, user.id, stops=stops)}


@router.get("/position/{signal_id}")
def get_position(signal_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One position: its derived state PLUS the full event audit trail (incl. superseded corrections)."""
    _ticker, sig = _parse_signal_id(signal_id)
    events = ledger.get_events(db, user.id, sig)
    if not events:
        raise HTTPException(status_code=404, detail="No events for this position")
    state = _position_payload(db, user.id, sig, events[0]["ticker"])
    return {**state, "events": events}
