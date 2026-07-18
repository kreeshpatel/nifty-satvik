"""Onboarding-journey memory router (Stage-6, docs/PRODUCT_SYNTHESIS.md Phase D).

The onboarding journey is event-driven: lessons unlock off the user's OWN recorded events (first
buy, first 2R, first drawdown, first runner) and each is shown once. This router is the durable
"already seen" memory behind that — a set-once per-user flag store.

  GET  /api/journey            -> { flags: { flag: {set_at, value} } }
  POST /api/journey/{flag}     -> set a flag (idempotent; first write wins), optional context body

Tenant-isolated on the bearer token. Flags are set-once by design — the journey never un-shows a
lesson, and a re-POST is a cheap no-op, so the frontend can fire-and-forget.
"""
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db, User, UserJourneyFlag
from auth import get_current_user

logger = logging.getLogger("journey")

router = APIRouter(prefix="/journey", tags=["journey"])

_FLAG_RE = re.compile(r"^[a-z0-9_]{2,64}$")
MAX_FLAGS = 200


class FlagBody(BaseModel):
    value: dict | None = None


@router.get("")
def get_flags(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(UserJourneyFlag).filter(UserJourneyFlag.user_id == user.id).all()
    return {"flags": {
        r.flag: {"set_at": r.created_at.isoformat() if r.created_at else None,
                 "value": json.loads(r.value_json) if r.value_json else None}
        for r in rows
    }}


@router.post("/{flag}", status_code=201)
def set_flag(flag: str, body: FlagBody | None = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Set-once: the first write wins; re-POST returns the existing row (200-shaped body, 201 code
    kept for simplicity). Never overwrites — journey memory is append-only like everything per-user."""
    f = (flag or "").strip().lower()
    if not _FLAG_RE.match(f):
        raise HTTPException(status_code=422, detail="Invalid flag (a-z0-9_ , 2-64 chars)")
    existing = (db.query(UserJourneyFlag)
                .filter(UserJourneyFlag.user_id == user.id, UserJourneyFlag.flag == f).first())
    if existing:
        return {"flag": f, "already_set": True,
                "set_at": existing.created_at.isoformat() if existing.created_at else None}
    if db.query(UserJourneyFlag).filter(UserJourneyFlag.user_id == user.id).count() >= MAX_FLAGS:
        raise HTTPException(status_code=400, detail=f"Too many flags (max {MAX_FLAGS})")
    row = UserJourneyFlag(user_id=user.id, flag=f,
                          value_json=json.dumps(body.value) if body and body.value else None)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:               # lost a race on (user, flag) — treat as already set
        db.rollback()
        return {"flag": f, "already_set": True}
    logger.info("journey flag user=%s flag=%s", user.id, f)
    return {"flag": f, "already_set": False,
            "set_at": row.created_at.isoformat() if row.created_at else None}
