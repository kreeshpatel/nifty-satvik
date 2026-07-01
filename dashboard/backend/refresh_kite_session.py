"""
Auto-refresh the owner's Kite Connect access token.

Runs as a Render cron job each weekday morning at ~6:15 AM IST (after Kite
tokens expire at 6:00 AM IST). Uses the owner's Zerodha credentials + TOTP
secret to programmatically log in, get a fresh request_token, exchange it
for an access_token, and store it (encrypted) in the kite_sessions table
for the admin user.

All connected users immediately have live market data — no manual login.

Required env vars:
  ZERODHA_USER_ID      — Zerodha login ID (e.g., AB1234)
  ZERODHA_PASSWORD     — Zerodha password
  ZERODHA_TOTP_SECRET  — TOTP secret (32-char base32 string from 2FA setup)
  KITE_API_KEY         — Kite Connect app API key
  KITE_API_SECRET      — Kite Connect app API secret
  ENCRYPTION_KEY       — Fernet key for encrypting tokens at rest
  DATABASE_URL         — PostgreSQL connection string
Optional:
  KITE_PROXY_URL       — http://USER:PASS@HOST:PORT forward proxy with the SEBI-whitelisted
                         static IP. Zerodha enforces static-IP login, so when this runs from a
                         non-whitelisted host (a GitHub-Actions runner, the Fly web dyno, a
                         laptop) it MUST tunnel the Zerodha login + token exchange through the
                         droplet's proxy or Zerodha will IP-block it. Unset = direct calls
                         (only works when already on the whitelisted IP, e.g. the droplet itself).

Run manually: python refresh_kite_session.py
"""

import os
import sys
import logging
from urllib.parse import urlparse, parse_qs

import requests
import pyotp
from dotenv import load_dotenv
from kiteconnect import KiteConnect

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("kite-refresh")


KITE_LOGIN_URL = "https://kite.zerodha.com/api/login"
KITE_TWOFA_URL = "https://kite.zerodha.com/api/twofa"
KITE_CONNECT_LOGIN_URL = "https://kite.zerodha.com/connect/login"


def _proxies():
    """`requests`-style proxies dict for the SEBI static-IP forward proxy, or None.

    Same env var + shape as routers/kite.py::_kite_proxies so a single KITE_PROXY_URL
    configures both the live REST path and this refresh. Zerodha's login/2FA/OAuth AND the
    token exchange must all egress from the whitelisted IP, so every network call below routes
    through it when set."""
    url = os.getenv("KITE_PROXY_URL", "").strip()
    if not url:
        return None
    return {"http": url, "https": url}


def get_request_token() -> str:
    """
    Programmatically log into Zerodha to get a fresh request_token.
    Uses the same internal API that kite.zerodha.com web app uses.
    """
    user_id = os.getenv("ZERODHA_USER_ID", "").strip()
    password = os.getenv("ZERODHA_PASSWORD", "").strip()
    totp_secret = os.getenv("ZERODHA_TOTP_SECRET", "").strip().replace(" ", "")
    api_key = os.getenv("KITE_API_KEY", "").strip().strip("<>").strip()

    if not all([user_id, password, totp_secret, api_key]):
        raise RuntimeError(
            "Missing required env vars: ZERODHA_USER_ID, ZERODHA_PASSWORD, "
            "ZERODHA_TOTP_SECRET, KITE_API_KEY"
        )

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    })
    # Tunnel the whole Zerodha login through the static-IP proxy when configured — every
    # request on this session (login, 2FA, OAuth redirect walk) inherits session.proxies.
    proxies = _proxies()
    if proxies:
        session.proxies.update(proxies)
        logger.info("  (routing Zerodha login through KITE_PROXY_URL static-IP proxy)")

    # Step 1: Login with username + password → get request_id
    logger.info("Step 1: POST /api/login")
    r = session.post(KITE_LOGIN_URL, data={"user_id": user_id, "password": password}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: HTTP {r.status_code} — {r.text[:200]}")
    login_data = r.json()
    if login_data.get("status") != "success":
        raise RuntimeError(f"Login failed: {login_data.get('message', 'unknown error')}")
    request_id = login_data["data"]["request_id"]
    logger.info(f"  ✓ request_id received")

    # Step 2: Submit TOTP 2FA
    logger.info("Step 2: POST /api/twofa")
    totp_code = pyotp.TOTP(totp_secret).now()
    r = session.post(KITE_TWOFA_URL, data={
        "user_id": user_id,
        "request_id": request_id,
        "twofa_value": totp_code,
        "twofa_type": "totp",
        "skip_session": "",
    }, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"2FA failed: HTTP {r.status_code} — {r.text[:200]}")
    twofa_data = r.json()
    if twofa_data.get("status") != "success":
        raise RuntimeError(f"2FA failed: {twofa_data.get('message', 'unknown error')}")
    logger.info(f"  ✓ 2FA accepted")

    # Step 3: Hit the OAuth endpoint with the authenticated session.
    # Zerodha will issue a redirect to your registered redirect URL with ?request_token=XXX.
    # We don't follow the redirect (the redirect URL is your Vercel app, unreachable from cron)
    # — we just extract request_token from the Location header.
    logger.info("Step 3: GET /connect/login (extract request_token from redirect)")
    try:
        r = session.get(
            KITE_CONNECT_LOGIN_URL,
            params={"api_key": api_key, "v": "3"},
            allow_redirects=False,
            timeout=15,
        )
    except Exception as e:
        raise RuntimeError(f"OAuth redirect failed: {e}")

    request_token = None

    # Walk redirect chain manually
    current = r
    for _ in range(10):
        location = current.headers.get("Location", "")
        if not location:
            break
        parsed = urlparse(location)
        qs = parse_qs(parsed.query)
        if "request_token" in qs:
            request_token = qs["request_token"][0]
            break
        # Follow internal Zerodha redirects only
        if parsed.netloc and "zerodha.com" not in parsed.netloc:
            # External redirect (your Vercel URL) — extract token from it directly
            if "request_token" in qs:
                request_token = qs["request_token"][0]
            break
        next_url = location if parsed.netloc else f"https://kite.zerodha.com{location}"
        current = session.get(next_url, allow_redirects=False, timeout=15)

    if not request_token:
        raise RuntimeError(
            "Could not extract request_token from redirect chain. "
            "Check that your Kite Connect app's redirect URL is set correctly."
        )

    logger.info(f"  ✓ request_token extracted")
    return request_token


def refresh_admin_session() -> dict:
    """
    Main entry point: log in, exchange token, save to DB.
    Returns: {"status": "success", "kite_user_id": str, "expires_at": float}
    """
    api_key = os.getenv("KITE_API_KEY", "").strip().strip("<>").strip()
    api_secret = os.getenv("KITE_API_SECRET", "").strip().strip("<>").strip()

    # Lazy imports — these touch the DB which needs DATABASE_URL
    from database import SessionLocal, User, KiteSession
    from routers.kite import encrypt_token, compute_token_expiry

    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured")

    # Step 1-3: Get fresh request_token
    request_token = get_request_token()

    # Step 4: Exchange request_token for access_token — also through the static-IP proxy,
    # since generate_session hits api.kite.trade which is subject to the same IP rule.
    logger.info("Step 4: Exchanging request_token for access_token")
    kite = KiteConnect(api_key=api_key, proxies=_proxies())
    session_data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = session_data["access_token"]
    kite_user_id = session_data.get("user_id")
    logger.info(f"  ✓ access_token received for Kite user {kite_user_id}")

    # Step 5: Save to admin's kite_sessions row
    logger.info("Step 5: Saving encrypted token to database")
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.is_admin == True).first()
        if not admin:
            raise RuntimeError(
                "No admin user found in database. "
                "Run create_admin.py first to create an admin account."
            )

        encrypted = encrypt_token(access_token)
        expires_at = compute_token_expiry()

        existing = db.query(KiteSession).filter(KiteSession.user_id == admin.id).first()
        if existing:
            existing.kite_user_id = kite_user_id
            existing.access_token_encrypted = encrypted
            existing.expires_at = expires_at
        else:
            db.add(KiteSession(
                user_id=admin.id,
                kite_user_id=kite_user_id,
                access_token_encrypted=encrypted,
                expires_at=expires_at,
            ))
        db.commit()

        # Audit log entry
        try:
            from audit import log_event
            log_event(db, admin.id, "KITE_AUTO_REFRESHED",
                      f"Auto-refreshed Kite session for {kite_user_id}", "cron")
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        # Daily owner NAV snapshot — fills the equity curve even on days the
        # dashboard is NOT opened. services/nav_history.py notes a cron "can't
        # snapshot user NAV" because per-user Kite sessions can't be refreshed
        # server-side — but the ADMIN session is exactly what we just refreshed
        # above, so the live snapshot path works here. Reuses the SAME holdings/
        # margins helpers + snapshot_nav the dashboard uses, so the row format is
        # identical (idempotent per (user, date)). Best-effort — never blocks the
        # refresh. Runs at 6:15 AM IST so it records the prior trading day's
        # closing NAV as one daily equity-curve point.
        try:
            from routers.positions import _safe_kite_holdings, _safe_kite_margins
            from services.nav_history import snapshot_nav
            _hold = _safe_kite_holdings(admin, db)
            if _hold:
                _marg = _safe_kite_margins(admin, db)
                snapshot_nav(admin.id, db, margins=_marg, holdings=_hold)
                logger.info("  ✓ Owner NAV snapshot written (daily equity-curve fill)")
            else:
                logger.info("  (no holdings returned — NAV snapshot skipped this run)")
        except Exception as e:
            logger.warning(f"NAV snapshot skipped (non-fatal): {e}")

        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        expiry_str = datetime.fromtimestamp(expires_at, tz=ist).strftime("%Y-%m-%d %H:%M:%S IST")
        logger.info(f"  ✓ Kite session refreshed for admin {admin.email}")
        logger.info(f"  ✓ Expires at {expiry_str}")

        return {
            "status": "success",
            "kite_user_id": kite_user_id,
            "expires_at": expires_at,
            "admin_email": admin.email,
        }
    finally:
        db.close()


if __name__ == "__main__":
    try:
        result = refresh_admin_session()
        print(f"\n✅ SUCCESS: {result}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        sys.exit(1)
