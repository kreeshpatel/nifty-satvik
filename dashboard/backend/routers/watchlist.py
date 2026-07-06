"""
Watchlist router — the per-user saved-stocks list behind the left watchlist rail.

Stores only membership (user_id, ticker); prices come from the shared quote
endpoints (/api/yahoo/quote-batch, /api/kite/quote). Tenant-isolated: every
query is scoped to the authenticated user — a user only ever sees/edits their own.

NOTE: distinct from /api/signals/watchlist, which is the model's signal-tier
watchlist (same for all users, regenerated daily). This one is personal.

Endpoints:
  GET    /api/watchlist            list the user's tickers
  POST   /api/watchlist            add a ticker (idempotent)
  DELETE /api/watchlist/{ticker}   remove a ticker
"""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db, User, UserWatchlist
from auth import get_current_user

logger = logging.getLogger("watchlist")

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

MAX_WATCHLIST = 100
_TICKER_RE = re.compile(r"^[A-Z0-9&._-]{1,32}$")


class AddWatchlistRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32)


def _norm(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(status_code=422, detail="Invalid ticker")
    return t


def _list(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == user_id)
        .order_by(UserWatchlist.sort_order.asc(), UserWatchlist.added_at.asc())
        .all()
    )
    return [r.ticker for r in rows]


@router.get("")
def get_watchlist(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The authenticated user's saved tickers, in display order."""
    return {"watchlist": _list(db, user.id)}


@router.post("", status_code=201)
def add_watchlist(
    req: AddWatchlistRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a ticker. Idempotent: adding an existing ticker is a no-op (200)."""
    ticker = _norm(req.ticker)

    existing = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == user.id, UserWatchlist.ticker == ticker)
        .first()
    )
    if existing:
        return {"watchlist": _list(db, user.id)}

    count = db.query(UserWatchlist).filter(UserWatchlist.user_id == user.id).count()
    if count >= MAX_WATCHLIST:
        raise HTTPException(status_code=400, detail=f"Watchlist is full (max {MAX_WATCHLIST})")

    row = UserWatchlist(
        user_id=user.id,
        ticker=ticker,
        sort_order=count,  # append to the end
        added_at=datetime.utcnow(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race on the unique (user_id, ticker) constraint — fine, it's there now.
        db.rollback()
    logger.info("watchlist add user=%s ticker=%s", user.id, ticker)
    return {"watchlist": _list(db, user.id)}


@router.delete("/{ticker}", status_code=204)
def remove_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a ticker from the user's watchlist."""
    t = _norm(ticker)
    row = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == user.id, UserWatchlist.ticker == t)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    db.delete(row)
    db.commit()
    logger.info("watchlist remove user=%s ticker=%s", user.id, t)
    return None
