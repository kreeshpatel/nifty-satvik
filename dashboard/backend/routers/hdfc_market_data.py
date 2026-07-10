"""
HDFC Securities market data — the live-quote path for all signed-in users.

MARKET DATA ONLY, read-only. Uses the single shared access token an admin
obtains via /api/admin/hdfc/login/* (routers/hdfc.py, HdfcMarketDataSession) —
mirrors Kite's "owner token powers quotes for everyone" pattern in
routers/kite.py, just via a manual admin login instead of a cron (HDFC's 2FA
is a real OTP, not a TOTP secret — see services/hdfc_client.py).

Endpoint:
  GET /api/hdfc/ltp?symbols=RELIANCE,TCS,HDFCBANK
    -> {"RELIANCE": {"ltp": 1279.8, "prev_close": 1277.1, "change_pct": 0.21},
        "TCS": {...}, ...}
    Symbols this backend can't resolve to an HDFC token (services/hdfc_master.py
    covers ~9.4k NSE/BSE cash-equity names) are simply omitted from the
    response — never a fabricated/zero price.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db, HdfcMarketDataSession, User
from auth import get_current_user
from services import hdfc_client, hdfc_master
from services.hdfc_client import HdfcApiError
import crypto

logger = logging.getLogger("hdfc_market_data")

router = APIRouter(prefix="/hdfc", tags=["hdfc-market-data"])


def _get_access_token(db: Session) -> str:
    session = db.query(HdfcMarketDataSession).order_by(HdfcMarketDataSession.id).first()
    if not session:
        raise HTTPException(status_code=503, detail="HDFC market data isn't connected yet.")
    return crypto.decrypt(session.access_token_encrypted)


@router.get("/ltp")
def get_ltp(
    symbols: str = Query(..., description="Comma-separated tickers, e.g. RELIANCE,TCS"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not requested:
        return {}

    resolved: dict[str, dict] = {}
    instruments = []
    for sym in requested:
        hit = hdfc_master.resolve(sym)
        if hit:
            resolved[sym] = hit
            instruments.append({"exchange": hit["exchange"], "token": hit["token"]})

    if not instruments:
        return {}

    access_token = _get_access_token(db)
    try:
        rows = hdfc_client.fetch_ltp(access_token, instruments)
    except HdfcApiError as exc:
        logger.error(f"HDFC fetch-ltp failed: {exc}")
        raise HTTPException(status_code=502, detail=f"HDFC market data unavailable: {exc}")

    # Match rows back to symbols by (exchange, token) — fetch-ltp doesn't echo
    # the symbol, only what we sent it.
    by_key = {(str(r.get("exchange")), str(r.get("token"))): r for r in rows}
    out: dict[str, dict] = {}
    for sym, hit in resolved.items():
        row = by_key.get((hit["exchange"], str(hit["token"])))
        if not row:
            continue
        ltp = row.get("ltp")
        prev_close = row.get("prev_close")
        change_pct = None
        if isinstance(ltp, (int, float)) and isinstance(prev_close, (int, float)) and prev_close:
            change_pct = round((ltp - prev_close) / prev_close * 100, 2)
        out[sym] = {"ltp": ltp, "prev_close": prev_close, "change_pct": change_pct}
    return out


@router.get("/coverage")
def get_coverage(user: User = Depends(get_current_user)):
    """How many symbols the compact equity master resolves — diagnostic."""
    return {"symbols": hdfc_master.coverage_count()}
