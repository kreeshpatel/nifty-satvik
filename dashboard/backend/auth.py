"""
NiftyQuant Authentication — JWT cookie-based auth with account lockout.
"""

import os
import secrets
import hashlib
import logging
import threading
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
import pyotp

from database import get_db, User, RefreshToken, PasswordResetToken
from crypto import encrypt as _crypto_encrypt, decrypt as _crypto_decrypt

logger = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Config ────────────────────────────────────────────

# SECURITY: never fall back to an empty string — jose accepts an empty-string
# HS256 secret, which makes every token forgeable (a full auth bypass) in any
# environment where JWT_SECRET is unset. If unset, generate a strong ephemeral
# secret (tokens won't survive a restart, which is the correct dev behaviour);
# production MUST set JWT_SECRET (enforced by _assert_required_secrets in main.py).
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)
if not os.getenv("JWT_SECRET"):
    logger.warning(
        "JWT_SECRET not set — using an ephemeral random secret. Tokens will not "
        "survive a restart; set JWT_SECRET in any real deployment."
    )
JWT_ALGORITHM = "HS256"
# Access token TTL — bumped from 15 minutes to 4 hours (2026-04-29).
# 15-min was tuned for multi-tenant SaaS with stolen-token blast-radius
# limits. With solo admin use it just produced ~96 refreshes/day for
# no defensible security gain (refresh token is the long-lived secret
# regardless), AND the every-12-min frontend refresh tick was racing
# transient backend hiccups into spurious logouts. AuthContext's
# proactive refresh interval should track this — see
# REFRESH_TICK_MINUTES in AuthContext.
ACCESS_TOKEN_EXPIRE_MINUTES = 240
REFRESH_TOKEN_EXPIRE_DAYS = 14
# Lockout policy is bypassed for admin users — see check in /auth/login.
# Solo-admin app shouldn't be able to lock itself out of its own tooling.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

COOKIE_NAME = "nq_access"
REFRESH_COOKIE_NAME = "nq_refresh"
# Production = any managed host (Render→RENDER, Fly.io→FLY_APP_NAME) or explicit
# IS_PRODUCTION=1. Gates Secure/SameSite cookie flags — MUST be true on Fly.io or
# auth cookies would be sent over plain HTTP. Mirrors main.py._IS_PRODUCTION.
IS_PRODUCTION = bool(
    os.getenv("IS_PRODUCTION") or os.getenv("RENDER") or os.getenv("FLY_APP_NAME")
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password strength ─────────────────────────────────
#
# Minimum bar for any user-chosen password (register, self-service reset,
# user-initiated change). Admin-generated temp passwords use
# secrets.token_urlsafe and bypass these checks (they're ~96 bits of
# entropy by construction).
#
# We keep the blocklist intentionally small + obvious — it's a guardrail
# against the worst defaults, not a HIBP-grade check. If we ever wire up
# the HIBP k-anonymity API (free, sends only 5-char SHA-1 prefix), this
# function is the single integration point.

_PW_MIN_LENGTH = 12

# Top obvious bad passwords. Lowercased for comparison.
_PW_BLOCKLIST = frozenset([
    "password", "password1", "password123", "passw0rd",
    "qwerty", "qwerty123", "qwertyuiop", "asdfghjkl",
    "12345678", "123456789", "1234567890", "0987654321",
    "letmein", "welcome", "welcome1", "welcome123",
    "admin", "administrator", "root", "user", "login",
    "iloveyou", "monkey", "dragon", "sunshine", "princess",
    "niftyquant", "niftyquant123", "trading", "trader",
    "zerodha", "kite", "stockmarket", "nifty500",
    "abc123", "abcdefgh", "trustno1", "letmein123",
    "changeme", "changeme123", "default", "secret",
    "passwordpassword", "12341234", "qwerty12345",
])


def validate_password_strength(password: str, *, email: str = "") -> None:
    """
    Raise HTTPException(400) if `password` doesn't meet our complexity bar.
    Returns None on success.
    """
    if not isinstance(password, str):
        raise HTTPException(status_code=400, detail="Password is required.")
    if len(password) < _PW_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {_PW_MIN_LENGTH} characters.",
        )
    if len(password) > 128:
        # Defensive: bcrypt truncates at 72 bytes; very long inputs are
        # almost certainly a paste error and slow the hash needlessly.
        raise HTTPException(
            status_code=400,
            detail="Password must be 128 characters or fewer.",
        )
    lowered = password.lower()
    if lowered in _PW_BLOCKLIST:
        raise HTTPException(
            status_code=400,
            detail="That password is on the common-password blocklist.",
        )
    # Reject passwords that are just the email's local part repeated, etc.
    if email:
        local = email.split("@", 1)[0].lower()
        if local and len(local) >= 4 and local in lowered:
            raise HTTPException(
                status_code=400,
                detail="Password cannot contain your email.",
            )
    # Require at least 3 of: lower, upper, digit, symbol — to nudge entropy
    # up without being a strict 4-class rule (NIST SP 800-63B discourages
    # rigid composition rules but a soft 3-of-4 is still useful).
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    classes = sum([has_lower, has_upper, has_digit, has_symbol])
    if classes < 3:
        raise HTTPException(
            status_code=400,
            detail="Password must include at least 3 of: lowercase, uppercase, digit, symbol.",
        )


# ── Pydantic Schemas ──────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool


# ── Token Utilities ───────────────────────────────────

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def auth_token_payload(access_token: str, refresh_token: str, user: User) -> dict:
    """
    Build the response body for /auth/login, /auth/login/mfa, /auth/refresh.

    Bearer-token auth: tokens are returned in the JSON body so the SPA can
    stash them in localStorage and attach as `Authorization: Bearer <token>`
    on every API call. This is browser/mode agnostic — no SameSite, no ITP,
    no third-party-cookie blocking, no CHIPS, no proxy quirks. Same auth
    behavior on Chrome desktop, Safari mobile, incognito, embedded WebView.

    Replaces the previous cookie-based flow which broke on mobile Safari +
    Chrome incognito after multiple iterations chasing the symptom. See
    plan: ~/.claude/plans/its-green-fluffy-manatee.md (2026-05-26).
    """
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
        },
    }


def clear_auth_cookies(response: Response):
    """
    Backward-compat: clears any legacy cookie-based session. Called on
    /auth/logout so users mid-migration get their old cookies cleaned up.
    Safe to remove once the 7-day compat window in `get_current_user` is
    closed.
    """
    response.delete_cookie(COOKIE_NAME, path="/", samesite="lax", secure=IS_PRODUCTION)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", samesite="lax", secure=IS_PRODUCTION)


# ── Current User Dependency ───────────────────────────

def _extract_bearer_token(request: Request) -> str | None:
    """Pull a bearer token from the Authorization header, if present."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Extract and validate JWT from `Authorization: Bearer <token>` header.

    Backward-compat window (~7 days from 2026-05-26): if no Authorization
    header is present, fall back to the legacy `nq_access` cookie so users
    already signed in via cookie keep working until their cookies expire.
    After 7 days the cookie fallback should be removed.
    """
    token = _extract_bearer_token(request)
    if not token:
        # Legacy cookie fallback — remove after 2026-06-02
        token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # SECURITY: reject special-purpose tokens (e.g. the short-lived
        # "mfa_pending" token issued after password but BEFORE the TOTP step).
        # Session access tokens carry no "purpose" claim; anything that does is
        # not a full session and must not authenticate a request — otherwise the
        # mfa_pending token works as a session token and MFA is fully bypassed.
        if payload.get("purpose"):
            raise HTTPException(status_code=401, detail="Invalid session")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid session")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # NOTE: previously did `user.last_active = datetime.utcnow(); db.commit()`
    # on every authenticated request. With even a handful of concurrent
    # requests on a single page (the stock detail view fires ~6 at once),
    # those writes serialised against each other on free-tier Postgres and
    # ballooned the auth check to 14-60 seconds per request. Removed
    # 2026-05-13 after a /stock/RELIANCE that was taking 90s of page-load
    # time was traced almost entirely to this write.
    #
    # last_active is still set on login (regular + MFA, lines ~314 and
    # ~714 below), so the admin user listing keeps a reasonable "last
    # seen" signal — it's now "last login" instead of "last request",
    # which is what every other auth system in the world does.

    return user


# ── WS-ticket replay protection ──────────────────────
#
# Each /auth/ws-ticket issues a JWT with a unique `jti`. We accept each jti
# at most once on the /ws endpoint, then drop it after 60s (>2x ticket TTL).
# Single-process only — if we ever scale Render to >1 worker this needs Redis.

_WS_JTI_TTL_SECONDS = 60
_ws_consumed_jtis: dict[str, datetime] = {}
_ws_jti_lock = threading.Lock()


def _consume_ws_jti(jti: str) -> bool:
    """Return True if jti is fresh (first use); False if it's a replay."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=_WS_JTI_TTL_SECONDS)
    with _ws_jti_lock:
        # Drop expired entries opportunistically.
        for k in [k for k, v in _ws_consumed_jtis.items() if v < cutoff]:
            del _ws_consumed_jtis[k]
        if jti in _ws_consumed_jtis:
            return False
        _ws_consumed_jtis[jti] = now
    return True


def get_current_user_from_ws_ticket(ticket: str, db: Session) -> User:
    """Validate a short-lived WS ticket. Single-use per jti."""
    try:
        payload = jwt.decode(ticket, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        jti = payload.get("jti")
    except (JWTError, KeyError, ValueError):
        return None
    if not jti or not _consume_ws_jti(jti):
        return None
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()


# ── Routes ────────────────────────────────────────────

@router.post("/login")
async def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    from audit import log_event

    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    ip = request.client.host if request.client else "unknown"

    if not user:
        log_event(db, None, "LOGIN_FAILED", f"Unknown email: {body.email}", ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check lockout — but skip for admin users. A solo-admin app
    # locking itself out of its own console is friction with no upside
    # (no other tenants to protect from a brute-force fan-out). When
    # multi-user usage is real we can flip this back on for non-admins.
    if not user.is_admin and user.locked_until and datetime.utcnow() < user.locked_until:
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=423,
            detail=f"Account locked. Try again in {remaining} minutes.",
        )
    # Defensive cleanup: if admin has a stale locked_until from before
    # this exemption shipped, clear it so audits stay accurate.
    if user.is_admin and user.locked_until:
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()

    # Verify password
    if not pwd_context.verify(body.password, user.password_hash):
        user.failed_login_attempts += 1
        # Same admin-exemption: track failed attempts but don't trip
        # the lockout state. Useful audit trail without operational
        # self-DoS risk.
        if not user.is_admin and user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            db.commit()
            log_event(db, user.id, "ACCOUNT_LOCKED", f"Locked after {MAX_FAILED_ATTEMPTS} failed attempts", ip)
            raise HTTPException(
                status_code=423,
                detail=f"Account locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts.",
            )
        db.commit()
        log_event(db, user.id, "LOGIN_FAILED", f"Wrong password (attempt {user.failed_login_attempts})", ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Success — reset lockout counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_active = datetime.utcnow()
    db.commit()

    # Anomaly: first login from this IP for a user that's logged in before.
    # Useful signal even without an alerting channel — shows up in /admin
    # audit-log view, and a future SMTP integration can fire on this action.
    from database import AuditLog
    prior_total = db.query(AuditLog).filter(
        AuditLog.user_id == user.id,
        AuditLog.action.in_(("LOGIN_SUCCESS", "LOGIN_FROM_NEW_IP")),
    ).count()
    if prior_total > 0:
        seen_ip = db.query(AuditLog.id).filter(
            AuditLog.user_id == user.id,
            AuditLog.action.in_(("LOGIN_SUCCESS", "LOGIN_FROM_NEW_IP")),
            AuditLog.ip_address == ip,
        ).first()
        if seen_ip is None:
            log_event(db, user.id, "LOGIN_FROM_NEW_IP", f"first login from {ip}", ip)

    # If MFA is enabled, return a short-lived pending token instead of
    # session cookies. The frontend prompts for the TOTP code and POSTs
    # to /auth/login/mfa to complete the login.
    if user.mfa_enabled:
        log_event(db, user.id, "LOGIN_PASSWORD_OK_MFA_PENDING", None, ip)
        return JSONResponse(content={
            "mfa_required": True,
            "mfa_pending_token": _create_mfa_pending_token(user.id),
        })

    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token_raw = create_refresh_token()

    # Store refresh token hash in DB
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_raw),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(db_token)
    db.commit()

    log_event(db, user.id, "LOGIN_SUCCESS", None, ip)

    return auth_token_payload(access_token, refresh_token_raw, user)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/logout")
async def logout(
    request: Request,
    body: LogoutRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    Revoke the user's refresh token on logout.

    Bearer-token flow: client sends `{refresh_token}` in body. Backward-compat
    fallback: if body is absent or refresh_token is missing, read the legacy
    `nq_refresh` cookie. After the compat window closes (2026-06-02), drop
    the cookie fallback.
    """
    from audit import log_event

    # Identify the user from the access token (header or legacy cookie) for
    # audit logging. Don't fail logout if the access token is invalid — the
    # whole point of logout is to handle expired/stale sessions.
    token = _extract_bearer_token(request) or request.cookies.get(COOKIE_NAME)
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = int(payload["sub"])
        except (JWTError, KeyError, ValueError):
            pass

    # Refresh token: body first, then legacy cookie fallback.
    refresh_token = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        # Mark refresh token as revoked (don't delete — needed so a post-logout
        # replay of the same token is caught by the reuse detector in /refresh).
        db.query(RefreshToken).filter(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        ).update({RefreshToken.revoked_at: datetime.utcnow()})
        db.commit()

    ip = request.client.host if request.client else "unknown"
    if user_id:
        log_event(db, user_id, "LOGOUT", None, ip)

    resp = JSONResponse(content={"status": "success"})
    # Clear any legacy cookies so users mid-migration get a clean slate.
    clear_auth_cookies(resp)
    return resp


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/refresh")
async def refresh(
    request: Request,
    body: RefreshRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.

    Bearer-token flow: client sends `{refresh_token}` in body. Backward-compat
    fallback: if body is missing the refresh_token field, read the legacy
    `nq_refresh` cookie. Returns the new {access_token, refresh_token, user}
    pair in body.

    Implements OWASP refresh-token-rotation with reuse detection:
      - active token  → rotate (revoke old, mint new linked via parent_token_hash)
      - revoked token replayed → token theft suspected → revoke entire chain
        for the user (forces re-login on every device)
      - unknown token → normal 401
    """
    from audit import log_event

    refresh_token_raw = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token_raw:
        raise HTTPException(status_code=401, detail="No refresh token")

    ip = request.client.host if request.client else "unknown"
    token_hash = hash_token(refresh_token_raw)

    # Look up regardless of revoked_at / expires_at — we need to distinguish
    # "never existed" (cookie tampered / stale) from "existed but already used".
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Reuse detection: token was already rotated or explicitly revoked.
    # A legitimate client always rotates forward — replay of an old token
    # means either an attacker stole the token or the user restored from
    # a stale browser snapshot. Either way, safe-fail by killing the chain.
    if db_token.revoked_at is not None:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == db_token.user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({RefreshToken.revoked_at: datetime.utcnow()})
        db.commit()
        log_event(
            db, db_token.user_id, "REFRESH_TOKEN_REUSE",
            "Revoked refresh token replayed — all sessions invalidated", ip,
        )
        # Clear legacy cookies (if any) on the way out so the client is
        # forced to /login. With bearer-token flow the frontend's 401
        # handler clears localStorage and bounces to /login regardless.
        response = JSONResponse(
            status_code=401,
            content={"detail": "Session compromised — please log in again"},
        )
        clear_auth_cookies(response)
        return response

    if db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == db_token.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Normal rotation: revoke the old token (don't delete), mint new linked
    # via parent_token_hash so a future replay of *this* token is detectable.
    db_token.revoked_at = datetime.utcnow()
    new_access = create_access_token(user.id)
    new_refresh_raw = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_raw),
        parent_token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()

    return auth_token_payload(new_access, new_refresh_raw, user)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}


@router.get("/ws-ticket")
async def ws_ticket(user: User = Depends(get_current_user)):
    """
    Issue a short-lived single-use ticket for WebSocket authentication.
    Each ticket carries a random jti; the /ws endpoint rejects replays.
    """
    expire = datetime.utcnow() + timedelta(seconds=30)
    jti = uuid.uuid4().hex
    ticket = jwt.encode(
        {"sub": str(user.id), "exp": expire, "jti": jti},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"ticket": ticket}


# ── Password reset (self-service) ─────────────────────

PASSWORD_RESET_TTL_MINUTES = 30
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://niftyquant.vercel.app")


# ── MFA (TOTP) helpers ────────────────────────────────
#
# Encryption is delegated to the shared `crypto` module so the MFA secret
# and Kite tokens share one key-rotation surface (ENCRYPTION_KEY +
# ENCRYPTION_KEYS_OLD). An empty key only matters when MFA is actually
# used — crypto.encrypt/decrypt raise HTTPException(500) with a clear
# "Server-side encryption not configured." instead of failing silently.

MFA_PENDING_TTL_SECONDS = 300  # 5 min between password-step and code-step
_MFA_ISSUER = "NiftyQuant"


def _encrypt_mfa_secret(secret: str) -> str:
    return _crypto_encrypt(secret)


def _decrypt_mfa_secret(encrypted: str) -> str:
    return _crypto_decrypt(encrypted)


def _create_mfa_pending_token(user_id: int) -> str:
    """JWT issued after password-step, exchanged for full session via /auth/login/mfa."""
    expire = datetime.utcnow() + timedelta(seconds=MFA_PENDING_TTL_SECONDS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "purpose": "mfa_pending"},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def _decode_mfa_pending_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("purpose") != "mfa_pending":
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def _verify_totp_code(secret: str, code: str) -> bool:
    """Validates a 6-digit TOTP. Allows ±1 step (30s) clock drift."""
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def _send_password_reset_email(email: str, reset_url: str) -> None:
    """
    Send a password-reset email. Falls back to logging the URL when no
    transactional-email service is configured (current state). When SMTP/
    SES/Resend is wired up later, swap this implementation only.

    Logging the URL is not a security regression in our current setup
    because Render server logs are admin-only, and the alternative would
    be silently dropping the request — which is worse UX. The audit log
    captures the request itself with the user_id + IP regardless.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        logger.warning(
            "Password reset requested for %s but no SMTP_HOST configured. "
            "Reset URL (admin must DM to user manually): %s",
            email, reset_url,
        )
        return
    # Stub for future SMTP integration — intentionally not implemented now.
    # When wiring this up, use smtplib.SMTP_SSL with SMTP_HOST/PORT/USER/
    # PASSWORD env vars and a from-address of FROM_EMAIL.
    logger.warning(
        "SMTP_HOST is set but the email-send path isn't implemented yet. "
        "Falling back to log-only for %s — URL: %s", email, reset_url,
    )


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Request a password-reset link.

    Always returns 200 with a generic message — never confirm whether the
    email is registered (prevents user-enumeration). The actual work
    (token issue + email send) is conditional on the email existing.
    """
    from audit import log_event

    email = body.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    user = db.query(User).filter(User.email == email, User.is_active == True).first()

    if user:
        # Invalidate any prior unused tokens for this user.
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: datetime.utcnow()})

        raw_token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
        ))
        db.commit()

        reset_url = f"{FRONTEND_URL}/reset-password?token={raw_token}"
        _send_password_reset_email(user.email, reset_url)
        log_event(db, user.id, "PASSWORD_RESET_REQUESTED", None, ip)
    else:
        # Still log the attempt so brute-force-by-email shows up in audit.
        log_event(db, None, "PASSWORD_RESET_REQUESTED_UNKNOWN", f"email={email}", ip)

    return {"status": "ok", "message": "If that email is registered, we’ve sent a reset link."}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Consume a single-use reset token and set a new password."""
    from audit import log_event

    ip = request.client.host if request.client else "unknown"
    token_hash = hash_token(body.token)

    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
    ).first()

    # Generic error in all failure cases — don't leak whether token existed.
    if (
        not db_token
        or db_token.used_at is not None
        or db_token.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = db.query(User).filter(
        User.id == db_token.user_id, User.is_active == True
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    validate_password_strength(body.new_password, email=user.email)

    user.password_hash = pwd_context.hash(body.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db_token.used_at = datetime.utcnow()

    # Defensive: revoke all active refresh tokens — if an attacker triggered
    # the reset, the legitimate user's existing sessions stay alive otherwise.
    # Actually: opposite. The legitimate user is the one resetting, so we
    # want to invalidate any session already in flight (e.g. an attacker
    # who just stole the cookie). Belt-and-braces: revoke every active row.
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: datetime.utcnow()})

    db.commit()
    log_event(db, user.id, "PASSWORD_RESET_COMPLETED", None, ip)
    return {"status": "ok", "message": "Password updated. You can now sign in."}


# ── MFA (TOTP) endpoints ──────────────────────────────


class MfaLoginRequest(BaseModel):
    mfa_pending_token: str
    code: str


@router.post("/login/mfa")
async def login_mfa(
    body: MfaLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Second step of MFA login — exchange pending-token + TOTP code for a session."""
    from audit import log_event

    ip = request.client.host if request.client else "unknown"
    user_id = _decode_mfa_pending_token(body.mfa_pending_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token. Please sign in again.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user or not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise HTTPException(status_code=401, detail="MFA not configured.")

    secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)
    if not _verify_totp_code(secret, body.code):
        log_event(db, user.id, "MFA_FAILED", None, ip)
        raise HTTPException(status_code=401, detail="Invalid authentication code.")

    user.last_active = datetime.utcnow()
    access_token = create_access_token(user.id)
    refresh_token_raw = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_raw),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    log_event(db, user.id, "LOGIN_SUCCESS", "via MFA", ip)

    return auth_token_payload(access_token, refresh_token_raw, user)


@router.post("/mfa/setup")
async def mfa_setup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Begin TOTP enrollment.

    Generates a fresh secret, stores it encrypted (but mfa_enabled stays
    False), and returns the otpauth:// URI for the frontend to render as
    a QR code. The user must complete /auth/mfa/verify with a working
    code to actually flip mfa_enabled = true.
    """
    if user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA is already enabled. Disable it first to re-enroll.")

    secret = pyotp.random_base32()
    user.mfa_secret_encrypted = _encrypt_mfa_secret(secret)
    db.commit()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name=_MFA_ISSUER,
    )
    return {"otpauth_uri": uri, "secret": secret}


class MfaCodeRequest(BaseModel):
    code: str


@router.post("/mfa/verify")
async def mfa_verify(
    body: MfaCodeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a code from the user's authenticator and flip mfa_enabled = true."""
    from audit import log_event

    if user.mfa_enabled:
        return {"status": "ok", "already_enabled": True}
    if not user.mfa_secret_encrypted:
        raise HTTPException(status_code=400, detail="Run /auth/mfa/setup first.")

    secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)
    if not _verify_totp_code(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid authentication code.")

    user.mfa_enabled = True
    db.commit()
    ip = request.client.host if request.client else "unknown"
    log_event(db, user.id, "MFA_ENABLED", None, ip)
    return {"status": "ok"}


class MfaDisableRequest(BaseModel):
    password: str


@router.post("/mfa/disable")
async def mfa_disable(
    body: MfaDisableRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable MFA. Re-prompt for password as a sanity check before unwiring."""
    from audit import log_event

    if not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    db.commit()
    ip = request.client.host if request.client else "unknown"
    log_event(db, user.id, "MFA_DISABLED", None, ip)
    return {"status": "ok"}


@router.get("/mfa/status")
async def mfa_status(user: User = Depends(get_current_user)):
    return {"enabled": bool(user.mfa_enabled)}


@router.post("/register")
async def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db), admin: User = Depends(get_current_user)):
    """Create a new user. Only admins can register new users."""
    from audit import log_event

    if not admin.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create users")

    email = body.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Reject weak passwords at the boundary, before we even hash.
    validate_password_strength(body.password, email=email)

    user = User(
        email=email,
        password_hash=pwd_context.hash(body.password),
        name=body.name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ip = request.client.host if request.client else "unknown"
    log_event(db, admin.id, "ACCOUNT_CREATED", f"Created user {email} (id={user.id})", ip)

    return {"id": user.id, "email": user.email, "name": user.name}
