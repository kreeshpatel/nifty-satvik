"""
Watchlist router — the per-user saved-stocks lists behind the left watchlist rail.

Each user has TWO independent lists (list_no 1 and 2):
  - List 1 ("core") is seeded with a few liquid Nifty-50 names the first time a
    brand-new user opens the rail, so it's never blank on first look. Fully
    editable afterwards.
  - List 2 starts empty for the user to build their own.

Stores only membership (user_id, list_no, ticker); prices come from the shared
quote endpoints (/api/yahoo/quote-batch, /api/kite/quote). Tenant-isolated:
every query is scoped to the authenticated user.

NOTE: distinct from /api/signals/watchlist, which is the model's signal-tier
watchlist (same for all users, regenerated daily). This one is personal.

Endpoints (all take an optional ?list=1|2, default 1):
  GET    /api/watchlist            list the user's tickers for a list
  POST   /api/watchlist            add a ticker to a list (idempotent)
  PATCH  /api/watchlist/reorder    persist display order within a list
  DELETE /api/watchlist/{ticker}   remove a ticker from a list
"""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db, User, UserWatchlist
from auth import get_current_user

logger = logging.getLogger("watchlist")

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

MAX_WATCHLIST = 100
_TICKER_RE = re.compile(r"^[A-Z0-9&._-]{1,32}$")

# Seed for a brand-new user's list 1 — a handful of liquid Nifty-50 large caps
# so the rail is never blank on first look. Order here is the display order.
DEFAULT_LIST_1 = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "LT", "ITC"]


class AddWatchlistRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32)
    list: int = Field(default=1, ge=1, le=2)


def _norm(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(status_code=422, detail="Invalid ticker")
    return t


def _norm_list(list_no) -> int:
    try:
        n = int(list_no)
    except (TypeError, ValueError):
        n = 1
    return n if n in (1, 2) else 1


def _list(db: Session, user_id: int, list_no: int) -> list[str]:
    rows = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == user_id, UserWatchlist.list_no == list_no)
        .order_by(UserWatchlist.sort_order.asc(), UserWatchlist.added_at.asc())
        .all()
    )
    return [r.ticker for r in rows]


def _seed_if_empty(db: Session, user_id: int) -> None:
    """Seed list 1 with DEFAULT_LIST_1 the first time a user has *no* rows in
    any list. Idempotent: once the user has a single row (in either list) this
    is a no-op, so a user who intentionally clears both lists won't be re-seeded
    on the same session — only a truly fresh account gets the seed."""
    total = db.query(UserWatchlist).filter(UserWatchlist.user_id == user_id).count()
    if total > 0:
        return
    now = datetime.utcnow()
    for i, ticker in enumerate(DEFAULT_LIST_1):
        db.add(UserWatchlist(
            user_id=user_id, ticker=ticker, list_no=1, sort_order=i, added_at=now,
        ))
    try:
        db.commit()
        logger.info("watchlist seeded user=%s n=%d", user_id, len(DEFAULT_LIST_1))
    except IntegrityError:
        db.rollback()  # lost a race — another request seeded first, fine.


@router.get("")
def get_watchlist(
    list: int = Query(default=1, ge=1, le=2),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The authenticated user's saved tickers for `list`, in display order.
    Seeds list 1 for brand-new users so the rail is never blank on first look."""
    list_no = _norm_list(list)
    _seed_if_empty(db, user.id)
    return {"watchlist": _list(db, user.id, list_no), "list": list_no}


@router.post("", status_code=201)
def add_watchlist(
    req: AddWatchlistRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a ticker to a list. Idempotent: adding an existing ticker is a no-op."""
    ticker = _norm(req.ticker)
    list_no = _norm_list(req.list)

    existing = (
        db.query(UserWatchlist)
        .filter(
            UserWatchlist.user_id == user.id,
            UserWatchlist.list_no == list_no,
            UserWatchlist.ticker == ticker,
        )
        .first()
    )
    if existing:
        return {"watchlist": _list(db, user.id, list_no), "list": list_no}

    count = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == user.id, UserWatchlist.list_no == list_no)
        .count()
    )
    if count >= MAX_WATCHLIST:
        raise HTTPException(status_code=400, detail=f"Watchlist is full (max {MAX_WATCHLIST})")

    row = UserWatchlist(
        user_id=user.id,
        ticker=ticker,
        list_no=list_no,
        sort_order=count,  # append to the end
        added_at=datetime.utcnow(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race on the unique (user_id, list_no, ticker) constraint — fine.
        db.rollback()
    logger.info("watchlist add user=%s list=%s ticker=%s", user.id, list_no, ticker)
    return {"watchlist": _list(db, user.id, list_no), "list": list_no}


class ReorderRequest(BaseModel):
    order: list[str] = Field(default_factory=list)
    list: int = Field(default=1, ge=1, le=2)


@router.patch("/reorder")
def reorder_watchlist(
    req: ReorderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist a new display order within a list. Lenient: unknown/invalid
    tickers are skipped; rows not named keep their prior order after the rest."""
    list_no = _norm_list(req.list)
    rows = {
        r.ticker: r
        for r in db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == user.id, UserWatchlist.list_no == list_no)
        .all()
    }
    seen = set()
    pos = 0
    for raw in req.order[:MAX_WATCHLIST]:
        t = str(raw or "").strip().upper()
        row = rows.get(t)
        if row is None or t in seen:
            continue
        row.sort_order = pos
        seen.add(t)
        pos += 1
    # Rows the client didn't mention keep a stable order after the named ones.
    for t, row in rows.items():
        if t not in seen:
            row.sort_order = pos
            pos += 1
    db.commit()
    return {"watchlist": _list(db, user.id, list_no), "list": list_no}


@router.delete("/{ticker}", status_code=204)
def remove_watchlist(
    ticker: str,
    list: int = Query(default=1, ge=1, le=2),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a ticker from a list."""
    t = _norm(ticker)
    list_no = _norm_list(list)
    row = (
        db.query(UserWatchlist)
        .filter(
            UserWatchlist.user_id == user.id,
            UserWatchlist.list_no == list_no,
            UserWatchlist.ticker == t,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    db.delete(row)
    db.commit()
    logger.info("watchlist remove user=%s list=%s ticker=%s", user.id, list_no, t)
    return None
