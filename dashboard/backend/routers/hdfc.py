"""
HDFC Securities market-data session — admin-only login flow.

MARKET DATA ONLY. This router never places orders and never reads
holdings/positions/funds — Kite remains the broker for all of that
(routers/kite.py, KiteSession). This exists solely to obtain and hold the one
shared access token that will power live quotes (see services/hdfc_client.py
for why this can't be an unattended cron like Kite's: HDFC's 2FA is a real OTP
sent to the account holder, not a TOTP secret).

Flow (matches services/hdfc_client.py's 5 auth steps, collapsed into 2 calls
an admin makes from the UI):
    POST /api/admin/hdfc/login/start   {username, password}
        -> {token_id, twofa_questions}
    POST /api/admin/hdfc/login/verify  {token_id, otp}
        -> validates OTP, authorises, fetches + stores the access token
    GET  /api/admin/hdfc/status
        -> whether a session exists and when it was obtained
"""
from __future__ import annotations
from netutil import client_ip

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, HdfcMarketDataSession, User
from routers.admin import require_admin
from services import hdfc_client
from services.hdfc_client import HdfcApiError
import crypto

logger = logging.getLogger("hdfc")

router = APIRouter(prefix="/admin/hdfc", tags=["hdfc-admin"])


class LoginStartRequest(BaseModel):
    username: str
    password: str


class LoginVerifyRequest(BaseModel):
    token_id: str
    otp: str


@router.post("/login/start")
def hdfc_login_start(
    req: LoginStartRequest,
    admin: User = Depends(require_admin),
):
    """Step 1-2: get a tokenId, submit credentials, return the 2FA question(s).
    Nothing is persisted here — token_id is short-lived state HDFC tracks
    server-side; the client just carries it to /login/verify."""
    try:
        token_id = hdfc_client.get_token_id()
        result = hdfc_client.login_validate(token_id, req.username, req.password)
    except HdfcApiError as exc:
        logger.error(f"HDFC login/start failed: {exc}")
        raise HTTPException(status_code=502, detail=f"HDFC login failed: {exc}")

    return {
        "token_id": token_id,
        "twofa_questions": (result.get("twofa") or {}).get("questions", []),
        "two_fa_enabled": result.get("twoFAEnabled", True),
    }


@router.post("/login/verify")
def hdfc_login_verify(
    req: LoginVerifyRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Step 3-5: validate the OTP, authorise, exchange for an access token,
    and store it (encrypted) as the single shared market-data session."""
    from audit import log_event

    try:
        twofa_result = hdfc_client.validate_2fa(req.token_id, req.otp)
        request_token = twofa_result.get("requestToken")
        if not request_token:
            raise HdfcApiError(f"No requestToken after 2FA validation: {twofa_result}")

        auth_result = hdfc_client.authorise(req.token_id, request_token, consent=True)
        final_request_token = auth_result.get("requestToken", request_token)

        access_token = hdfc_client.fetch_access_token(final_request_token)
    except HdfcApiError as exc:
        logger.error(f"HDFC login/verify failed: {exc}")
        ip = client_ip(request)
        log_event(db, admin.id, "HDFC_LOGIN_FAILED", str(exc)[:500], ip)
        raise HTTPException(status_code=502, detail=f"HDFC login failed: {exc}")

    encrypted = crypto.encrypt(access_token)
    session = db.query(HdfcMarketDataSession).order_by(HdfcMarketDataSession.id).first()
    if session:
        session.access_token_encrypted = encrypted
        session.obtained_at = datetime.utcnow()
        session.connected_by_user_id = admin.id
    else:
        session = HdfcMarketDataSession(
            access_token_encrypted=encrypted,
            connected_by_user_id=admin.id,
        )
        db.add(session)
    db.commit()

    ip = client_ip(request)
    log_event(db, admin.id, "HDFC_LOGIN_SUCCESS", "HDFC market-data session connected", ip)

    return {"connected": True, "obtained_at": session.obtained_at.isoformat()}


@router.get("/status")
def hdfc_status(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    session = db.query(HdfcMarketDataSession).order_by(HdfcMarketDataSession.id).first()
    if not session:
        return {"connected": False}
    return {
        "connected": True,
        "obtained_at": session.obtained_at.isoformat() if session.obtained_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }


class TestLtpRequest(BaseModel):
    # e.g. [{"exchange": "NSE", "token": "21840"}] — manual probe until the
    # symbol->token (security master) lookup is wired up. Not used by any
    # user-facing feature yet.
    instruments: list[dict]


@router.post("/test-ltp")
def hdfc_test_ltp(
    req: TestLtpRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually probe fetch-ltp with known {exchange, token} pairs. Exists so we
    can validate the connection + response shape before any symbol lookup exists.
    Not wired into the live app — admin-only diagnostic."""
    session = db.query(HdfcMarketDataSession).order_by(HdfcMarketDataSession.id).first()
    if not session:
        raise HTTPException(status_code=400, detail="No HDFC session — connect via /login/start first.")
    access_token = crypto.decrypt(session.access_token_encrypted)
    try:
        data = hdfc_client.fetch_ltp(access_token, req.instruments)
    except HdfcApiError as exc:
        raise HTTPException(status_code=502, detail=f"HDFC fetch-ltp failed: {exc}")
    return {"data": data}
