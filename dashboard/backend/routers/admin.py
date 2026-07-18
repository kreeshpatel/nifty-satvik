"""
Admin API — user management, audit logs, session control.
All routes require is_admin=True.
"""

import time
import logging
from datetime import datetime, timezone, timedelta
from netutil import client_ip
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db, User, KiteSession, AuditLog, RefreshToken
from auth import get_current_user

logger = logging.getLogger("admin")
router = APIRouter(prefix="/admin", tags=["admin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _cron_health_block(ch, now: datetime) -> dict:
    """Map results/cron_health.json into the AdminV2 hero-strip cron block,
    with a derived staleness flag. Pure (no DB / FastAPI), so it is unit-tested
    directly (T1-C).

    The cron writes cron_health.json with last_run_at / status /
    features_computed / signals_count / watchlist_count / macro_mode /
    macro_stale_days / ohlcv_stale_days / message. The previous panel read a
    'cron_health' key from signals_today.json that the cron never writes, so it
    was permanently UNKNOWN. `now` must be tz-aware UTC."""
    block = {"status": "UNKNOWN", "last_run": None, "expected_today": None}
    if not isinstance(ch, dict) or not ch:
        return block
    last_run = ch.get("last_run_at")
    age_minutes = None
    stale = False
    if last_run:
        try:
            lr = datetime.fromisoformat(str(last_run))
            if lr.tzinfo is None:
                lr = lr.replace(tzinfo=timezone.utc)
            age_minutes = int((now - lr).total_seconds() // 60)
            # The scanner runs every NSE trading day (~10:45 UTC). >30h without
            # a run is overdue. A Fri->Mon weekend gap (~72h) also reads stale,
            # which is correct: there has genuinely been no run since Friday.
            stale = age_minutes > 30 * 60
        except (ValueError, TypeError):
            pass
    return {
        "status": ch.get("status", "UNKNOWN"),
        "last_run": last_run,
        "expected_today": None,  # back-compat key; no real value
        "scan_time": last_run,
        "n_signals": ch.get("signals_count", 0),
        "watchlist_count": ch.get("watchlist_count", 0),
        "features_computed": ch.get("features_computed"),
        "macro_mode": ch.get("macro_mode"),
        "macro_stale_days": ch.get("macro_stale_days"),
        "ohlcv_stale_days": ch.get("ohlcv_stale_days"),
        "message": ch.get("message", ""),
        "age_minutes": age_minutes,
        "stale": stale,
    }


# ── User Management ──────────────────────────────────

@router.get("/users")
async def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """List all users with their status."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        kite = db.query(KiteSession).filter(KiteSession.user_id == u.id).first()
        result.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_active": u.last_active.isoformat() if u.last_active else None,
            "failed_login_attempts": u.failed_login_attempts,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
            "kite_connected": kite is not None and kite.expires_at > datetime.utcnow().timestamp(),
            "kite_user_id": kite.kite_user_id if kite else None,
        })
    return result


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Deactivate a user (prevents login, revokes sessions)."""
    from audit import log_event

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    # Revoke all their refresh tokens
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    # Remove Kite session
    db.query(KiteSession).filter(KiteSession.user_id == user_id).delete()
    db.commit()

    ip = client_ip(request)
    log_event(db, admin.id, "USER_DEACTIVATED", f"Deactivated user {user.email} (id={user_id})", ip)

    return {"status": "success", "message": f"User {user.email} deactivated"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Re-activate a deactivated user."""
    from audit import log_event

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    ip = client_ip(request)
    log_event(db, admin.id, "USER_ACTIVATED", f"Activated user {user.email} (id={user_id})", ip)

    return {"status": "success", "message": f"User {user.email} activated"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unlock a locked account (from failed login attempts)."""
    from audit import log_event

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    ip = client_ip(request)
    log_event(db, admin.id, "ACCOUNT_UNLOCKED", f"Unlocked user {user.email} (id={user_id})", ip)

    return {"status": "success", "message": f"User {user.email} unlocked"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reset a user's password. Returns the new temporary password."""
    from audit import log_event
    import secrets

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    temp_password = secrets.token_urlsafe(12)
    user.password_hash = pwd_context.hash(temp_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    ip = client_ip(request)
    log_event(db, admin.id, "PASSWORD_RESET", f"Reset password for {user.email} (id={user_id})", ip)

    return {"status": "success", "email": user.email, "temp_password": temp_password}


@router.post("/users/{user_id}/revoke-kite")
async def revoke_kite_session(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Revoke a user's Kite session."""
    from audit import log_event

    db.query(KiteSession).filter(KiteSession.user_id == user_id).delete()
    db.commit()

    ip = client_ip(request)
    log_event(db, admin.id, "KITE_REVOKED", f"Revoked Kite session for user_id={user_id}", ip)

    return {"status": "success"}


# ── Audit Logs ───────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=200),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get audit logs with optional filters."""
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "detail": log.detail,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


# ── Owner Kite Session Status & Refresh ──────────────

@router.get("/kite-status")
async def get_owner_kite_status(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get the owner's (admin's) Kite session status.
    This is the session that powers market data for ALL users.
    """
    # Find the owner (first admin user)
    owner = db.query(User).filter(User.is_admin == True).first()
    if not owner:
        return {"connected": False, "error": "No admin user found"}

    session = db.query(KiteSession).filter(KiteSession.user_id == owner.id).first()
    if not session:
        return {"connected": False, "kite_user_id": None, "expires_at": None}

    is_valid = time.time() < session.expires_at
    ist = timezone(timedelta(hours=5, minutes=30))
    expires_at_iso = datetime.fromtimestamp(session.expires_at, tz=ist).isoformat()

    return {
        "connected": is_valid,
        "kite_user_id": session.kite_user_id,
        "expires_at": session.expires_at,
        "expires_at_iso": expires_at_iso,
        "owner_email": owner.email,
    }


@router.post("/refresh-kite")
async def manual_refresh_kite(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Manually trigger an automatic refresh of the owner's Kite session.
    Uses the same logic as the daily cron job.
    """
    from audit import log_event

    try:
        # Import here so missing pyotp/env vars only fail when actually called
        from refresh_kite_session import refresh_admin_session
        result = refresh_admin_session()
    except Exception as e:
        logger.error(f"Manual Kite refresh failed: {e}")
        ip = client_ip(request)
        log_event(db, admin.id, "KITE_REFRESH_FAILED", str(e)[:500], ip)
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)[:200]}")

    ip = client_ip(request)
    log_event(db, admin.id, "KITE_MANUAL_REFRESH",
              f"Manually refreshed Kite session for {result.get('kite_user_id')}", ip)

    return {
        "status": "success",
        "kite_user_id": result.get("kite_user_id"),
        "expires_at": result.get("expires_at"),
    }


@router.get("/system-health")
async def get_system_health(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Aggregated dashboard for the AdminV2 page hero strip — single round-trip
    instead of firing 4 endpoints separately.

    Composes:
      - cron_health   — pulled from results/signals_today.json metadata
                        (status, last_run_today, expected_today, lag_minutes)
      - kite_owner    — same shape as /admin/kite-status
      - users         — counts (total, active, locked, suspended, kite_connected)
      - access        — pending access request count
      - errors_24h    — count of audit_logs entries with FAILED/ERROR action
                        within the last 24 hours
      - server_time   — backend's current UTC + IST time so the UI can
                        compute drift / show "as of" timestamp
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import or_, func

    # ── Cron health from cron_health.json (T1-C) ────────────
    # Reuses signals.py's _read_json_with_fallback (local file first, then
    # GitHub raw — Render's web service doesn't have results/ on disk since the
    # cron runs on a separate dyno). The cron writes a DEDICATED
    # results/cron_health.json; the old code read a "cron_health" key from
    # signals_today.json that never existed, so this panel was always UNKNOWN.
    cron_block = {"status": "UNKNOWN", "last_run": None, "expected_today": None}
    try:
        from routers.signals import _read_json_with_fallback, RESULTS_DIR
        ch = _read_json_with_fallback(
            RESULTS_DIR / "cron_health.json",
            "results/cron_health.json",
            {},
        )
        cron_block = _cron_health_block(ch, datetime.now(timezone.utc))
    except Exception as e:
        logger.warning(f"system-health: cron read failed: {e}")
        cron_block["error"] = str(e)[:140]

    # ── Owner Kite session ──────────────────────────────────
    owner = db.query(User).filter(User.is_admin == True).first()
    kite_block = {"connected": False, "kite_user_id": None, "expires_at": None}
    if owner:
        session = db.query(KiteSession).filter(KiteSession.user_id == owner.id).first()
        if session:
            is_valid = time.time() < session.expires_at
            ist = timezone(timedelta(hours=5, minutes=30))
            kite_block = {
                "connected":      is_valid,
                "kite_user_id":   session.kite_user_id,
                "expires_at":     session.expires_at,
                "expires_at_iso": datetime.fromtimestamp(session.expires_at, tz=ist).isoformat(),
                "owner_email":    owner.email,
            }

    # ── User counts ─────────────────────────────────────────
    users_block = {
        "total":           db.query(User).count(),
        "active":          db.query(User).filter(User.is_active == True).count(),
        "locked":          db.query(User).filter(User.locked_until > datetime.utcnow()).count(),
        "suspended":       db.query(User).filter(User.is_active == False).count(),
        "kite_connected":  db.query(KiteSession)
                              .filter(KiteSession.expires_at > time.time())
                              .count(),
    }

    # ── Access requests ─────────────────────────────────────
    try:
        from database import AccessRequest
        access_pending = (
            db.query(AccessRequest)
              .filter(AccessRequest.status == "pending")
              .count()
        )
    except Exception:
        access_pending = 0

    # ── Errors in last 24h (audit log) ──────────────────────
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    errors_24h = (
        db.query(AuditLog)
          .filter(AuditLog.timestamp >= cutoff_24h)
          .filter(or_(
              AuditLog.action.like("%FAILED%"),
              AuditLog.action.like("%ERROR%"),
              AuditLog.action.like("%REJECTED%"),
          ))
          .count()
    )

    return {
        "cron":         cron_block,
        "kite_owner":   kite_block,
        "users":        users_block,
        "access":       {"pending": access_pending},
        "errors_24h":   errors_24h,
        "server_time": {
            "utc":  datetime.utcnow().isoformat() + "Z",
            "ist":  datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
        },
    }
