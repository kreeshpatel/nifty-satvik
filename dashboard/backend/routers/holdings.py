"""
Sizer router — the per-user sizing preferences behind the position sizer.

- GET  /api/sizer/config        the tier %s + single-position cap (from config.py; one source)
- GET  /api/me/sizing-prefs     the user's saved risk_tier + default_capital
- PUT  /api/me/sizing-prefs     update them

WHAT LEFT, AND WHY (2026-08-27). This router also owned an EPHEMERAL "bought" mark
(GET/POST/DELETE /api/holdings, table `user_holdings`): the user marked a recommendation as
bought, and the row was erased the moment the model completed the trade. It has been removed.

It answered the same question as the durable execution ledger — did you buy this — and only the
ledger survives trade completion, so the two disagreed exactly when it mattered: a real recorded
position whose mark had been pruned read back as "not held", and the Research page offered to
record a buy on shares the user already owned. Reconciliation, P&L, the discipline score and the
missed-exit items were all already derived from the ledger; the mark was a second, weaker copy of
a fact with an owner.

The `user_holdings` TABLE is deliberately left in place rather than dropped. Nothing reads or
writes it now, and an orphan table costs a line in the schema; a destructive migration against
rows a user entered by hand costs those rows, and is not reversible if this call is wrong.

Tenant-isolated: every query is scoped to the authenticated user (the bearer token is the
authority — the frontend never sends a user id).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import RISK_TIERS, POSITION_CAP_PCT
from database import get_db, User
from auth import get_current_user

logger = logging.getLogger("holdings")

router = APIRouter(tags=["sizer"])


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
