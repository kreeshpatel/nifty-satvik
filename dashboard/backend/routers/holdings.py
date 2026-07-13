"""
Holdings + sizer router — the per-user layer of the Signals page (added 2026-07-13).

Two concerns, one router:

1. **Sizer prefs / config** — the position sizer's risk tier + capital.
   - GET  /api/sizer/config        the tier %s + single-position cap (from config.py; one source)
   - GET  /api/me/sizing-prefs     the user's saved risk_tier + default_capital
   - PUT  /api/me/sizing-prefs     update them

2. **Ephemeral "bought" marks** — the user MANUALLY marks a research recommendation as bought;
   the mark lives ONLY while the trade is open and is ERASED the moment the model completes the
   trade. No Kite sync, no permanent per-user track record (that's the model's shared
   signals_history_weekly.json). Keyed by signal_id = "{ticker}__{signal_date}".
   - GET    /api/holdings              the user's STILL-OPEN marks (prunes completed ones on read)
   - POST   /api/holdings              mark bought (idempotent: re-POST overwrites qty)
   - DELETE /api/holdings/{signal_id}  manual unmark (sold early / fat-finger)

Tenant-isolated: every query is scoped to the authenticated user (the bearer token is the
authority — the frontend never sends a user id). `GET /api/signals` is deliberately left
model-only; the page merges the held signal_id set client-side.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import RISK_TIERS, POSITION_CAP_PCT
from database import get_db, User, UserHolding
from auth import get_current_user
from services.nq_positions import signal_lifecycle_state

logger = logging.getLogger("holdings")

router = APIRouter(tags=["holdings"])

MAX_HOLDINGS = 100
# signal_id == "{TICKER}__{YYYY-MM-DD}" — the canonical key (NQOrder.signal_id / nq_position_id).
_SIGNAL_ID_RE = re.compile(r"^([A-Z0-9&._-]{1,32})__(\d{4}-\d{2}-\d{2})$")


def _valid_tier(tier: str) -> str:
    t = (tier or "").strip().lower()
    if t not in RISK_TIERS:
        raise HTTPException(status_code=422, detail=f"Invalid risk_tier (expected {list(RISK_TIERS)})")
    return t


def _parse_signal_id(signal_id: str) -> tuple[str, str]:
    """→ (ticker, signal_date); 422 if malformed."""
    m = _SIGNAL_ID_RE.match((signal_id or "").strip().upper())
    if not m:
        raise HTTPException(status_code=422, detail="Invalid signal_id (expected '{TICKER}__{YYYY-MM-DD}')")
    return m.group(1), signal_id.strip()


# ── Sizer config + prefs ──────────────────────────────

@router.get("/sizer/config")
def sizer_config(user: User = Depends(get_current_user)):
    """The sizing policy constants (single source in config.py). Static; cache hard on the client."""
    return {"tiers": RISK_TIERS, "position_cap_pct": POSITION_CAP_PCT}


class SizingPrefs(BaseModel):
    risk_tier: str | None = Field(default=None)
    default_capital: float | None = Field(default=None, ge=0)


def _prefs_dict(u: User) -> dict:
    return {"risk_tier": u.risk_tier or "medium", "default_capital": u.default_capital}


@router.get("/me/sizing-prefs")
def get_sizing_prefs(user: User = Depends(get_current_user)):
    return _prefs_dict(user)


@router.put("/me/sizing-prefs")
def put_sizing_prefs(
    req: SizingPrefs,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the user's risk tier and/or remembered capital. Only fields present are changed."""
    u = db.query(User).filter(User.id == user.id).first()
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    if req.risk_tier is not None:
        u.risk_tier = _valid_tier(req.risk_tier)
    if req.default_capital is not None:
        u.default_capital = float(req.default_capital)
    db.commit()
    logger.info("sizing-prefs update user=%s tier=%s cap=%s", u.id, u.risk_tier, u.default_capital)
    return _prefs_dict(u)


# ── Ephemeral holdings ────────────────────────────────

def _row_dict(r: UserHolding) -> dict:
    return {
        "signal_id": r.signal_id, "ticker": r.ticker, "entry": r.entry, "stop": r.stop,
        "qty": r.qty, "risk_tier_at_buy": r.risk_tier_at_buy,
        "bought_at": r.bought_at.isoformat() if r.bought_at else None,
    }


@router.get("/holdings")
def get_holdings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The user's STILL-OPEN bought-marks. Erase-on-completion: any mark whose signal the model
    has completed (target/stop/expiry) is deleted here and omitted — this write-in-fetch IS the
    'remembered till the trade completes, then erased' semantic, and touches only the caller's rows."""
    rows = db.query(UserHolding).filter(UserHolding.user_id == user.id).all()
    open_rows, pruned = [], 0
    for r in rows:
        if signal_lifecycle_state(r.signal_id, r.ticker) == "closed":
            db.delete(r)
            pruned += 1
        else:
            open_rows.append(r)
    if pruned:
        db.commit()
        logger.info("holdings erase-on-completion user=%s pruned=%d", user.id, pruned)
    open_rows.sort(key=lambda r: r.bought_at or 0, reverse=True)
    return {"holdings": [_row_dict(r) for r in open_rows]}


class MarkBoughtRequest(BaseModel):
    signal_id: str = Field(..., min_length=3, max_length=128)
    ticker: str | None = Field(default=None, max_length=32)
    entry: float | None = None
    stop: float | None = None
    qty: int | None = Field(default=None, ge=0)      # None = mark-only (no capital known)
    risk_tier_at_buy: str | None = None


@router.post("/holdings", status_code=201)
def mark_bought(
    req: MarkBoughtRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a signal bought. Idempotent: re-POST of the same signal_id OVERWRITES qty/entry/stop
    (a 'mark', not order accumulation)."""
    ticker, signal_id = _parse_signal_id(req.signal_id)
    tier = _valid_tier(req.risk_tier_at_buy) if req.risk_tier_at_buy else "medium"

    existing = (
        db.query(UserHolding)
        .filter(UserHolding.user_id == user.id, UserHolding.signal_id == signal_id)
        .first()
    )
    if existing is not None:
        existing.qty = req.qty
        if req.entry is not None:
            existing.entry = req.entry
        if req.stop is not None:
            existing.stop = req.stop
        existing.risk_tier_at_buy = tier
        db.commit()
        return _row_dict(existing)

    count = db.query(UserHolding).filter(UserHolding.user_id == user.id).count()
    if count >= MAX_HOLDINGS:
        raise HTTPException(status_code=400, detail=f"Too many holdings (max {MAX_HOLDINGS})")

    row = UserHolding(
        user_id=user.id, signal_id=signal_id, ticker=(req.ticker or ticker).upper(),
        entry=req.entry, stop=req.stop, qty=req.qty, risk_tier_at_buy=tier,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # lost a race on the unique (user_id, signal_id) — re-read below
        row = (
            db.query(UserHolding)
            .filter(UserHolding.user_id == user.id, UserHolding.signal_id == signal_id)
            .first()
        )
    logger.info("holdings mark user=%s signal=%s qty=%s", user.id, signal_id, req.qty)
    return _row_dict(row)


@router.delete("/holdings/{signal_id}", status_code=204)
def unmark_bought(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manual unmark (sold early / fat-finger). Unrestricted — nothing permanent to protect."""
    row = (
        db.query(UserHolding)
        .filter(UserHolding.user_id == user.id, UserHolding.signal_id == signal_id.strip())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Not held")
    db.delete(row)
    db.commit()
    logger.info("holdings unmark user=%s signal=%s", user.id, signal_id)
    return None
