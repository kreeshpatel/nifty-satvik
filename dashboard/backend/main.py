"""
NiftyQuant Dashboard — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load .env file for KITE_API_KEY, KITE_API_SECRET, etc.

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from ws_manager import WSManager
from routers import overview, positions, signals, backtest, trades, kite, yahoo_finance, admin, access_requests, landing_stats, nq_orders, watchlist, hdfc, hdfc_market_data
from config import INITIAL_CAPITAL
from github_data import fetch_github_json
from database import init_db, SessionLocal
from auth import get_current_user_from_ws_ticket, COOKIE_NAME
from jose import jwt as jose_jwt, JWTError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("niftyquant")


# ── Startup secret-presence check ─────────────────────
# Empty fallbacks on these env vars are catastrophic in production:
#  - JWT_SECRET=""  → any HS256 token signed with "" is accepted (auth bypass)
#  - ENCRYPTION_KEY="" → Fernet init crashes when decrypting Kite tokens
#  - DATABASE_URL=""  → app boots without a DB and fails at first query
#  - KITE_API_KEY/SECRET="" → Kite OAuth + market data silently 401
# We refuse to boot in production when any are missing. "Production" = any managed
# host: Render sets RENDER, Fly.io sets FLY_APP_NAME, or set IS_PRODUCTION=1 explicitly.
# In local dev (none set) we log warnings but allow boot.

# Mirrors auth.py.IS_PRODUCTION — keep the two in sync. Without this, a non-Render
# host (Fly.io) would boot in "dev" mode and silently skip required-secret enforcement
# (ephemeral JWT_SECRET = forgeable tokens) + secure-cookie flags.
_IS_PRODUCTION = bool(
    os.getenv("IS_PRODUCTION") or os.getenv("RENDER") or os.getenv("FLY_APP_NAME")
)

_REQUIRED_SECRETS = (
    "JWT_SECRET",
    "ENCRYPTION_KEY",
    "DATABASE_URL",
    "KITE_API_KEY",
    "KITE_API_SECRET",
)


def _assert_required_secrets() -> None:
    missing = [name for name in _REQUIRED_SECRETS if not os.getenv(name)]
    if not missing:
        return
    msg = f"Missing required environment variables: {', '.join(missing)}"
    if _IS_PRODUCTION:
        raise RuntimeError(
            f"{msg}. Refusing to start in production. "
            "Set these in the host's secrets (Fly.io: `fly secrets set ...`) before deploying."
        )
    logger.warning("%s. Allowed in dev (RENDER unset) — DO NOT deploy without these.", msg)


_assert_required_secrets()


# GITHUB_TOKEN is the de-facto datasource on the managed host: results/ is NOT
# baked into the Fly image (see deploy/.dockerignore), so github_data.py reads
# results/*.json from the repo via the GitHub Contents API. It is not a security
# secret (so we don't refuse to boot), but an unset OR INVALID token means every
# signals / positions / trades / equity endpoint silently falls back to empty —
# a "green" deploy that serves no data. Warn loudly so the failure mode is visible.
if not os.getenv("GITHUB_TOKEN"):
    logger.warning(
        "GITHUB_TOKEN unset — results/ data is served from the repo via the GitHub "
        "Contents API; without a valid token the dashboard returns EMPTY "
        "signals/positions/trades/equity. Set it in the host secrets."
    )


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="NiftyQuant Dashboard", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(
    status_code=429, content={"detail": "Too many requests. Please slow down."}
))
# SECURITY: SlowAPIMiddleware must be registered for the limiter's default_limits
# (60/min per IP) to actually apply. Without it the limiter is inert and auth
# endpoints (/auth/login, /auth/refresh) have NO brute-force protection despite
# the documented 60/min policy. NOTE: this turns on global 60/min/IP throttling —
# monitor for 429s on data-dense dashboard pages after deploy.
app.add_middleware(SlowAPIMiddleware)

# ── Initialize database on startup ────────────────────
@app.on_event("startup")
def startup():
    init_db()
    logger.info("Database tables initialized")


# ── CORS — restricted to known origins ────────────────

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "https://niftyquant.vercel.app",
]
extra_origin = os.environ.get("ALLOWED_ORIGIN", "")
if extra_origin:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origin.split(",") if o.strip()])

# Allow any Vercel deployment of this project (production, preview, branch URLs).
# Matches: niftyquant.vercel.app, niftyquant-git-*.vercel.app,
# niftyquant-*-kreeshpatels-projects.vercel.app, etc.
ALLOWED_ORIGIN_REGEX = r"https://([a-z0-9-]+\.)*vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    # Explicit allowlist (was "*"). Frontend only ever sends Content-Type
    # (JSON requests) — Authorization and X-Requested-With are kept as
    # defensive defaults for any future helper that adds them.
    # X-Service-Token is server-to-server (cron), bypasses CORS preflight,
    # so it is NOT listed here intentionally.
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# ── Security Headers Middleware ───────────────────────

# CSP for backend-served HTML (FastAPI /docs, /redoc, /). The SPA is hosted
# on Vercel — the *real* CSP for the dashboard is set in frontend/vercel.json.
# Running in Report-Only mode for one week so we can observe violations
# (especially Recharts inline-style violations) before promoting to enforcing.
_CSP_REPORT_ONLY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "  # FastAPI /docs needs inline scripts
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy-Report-Only"] = _CSP_REPORT_ONLY
    return response


# ── JWT Auth Middleware — protect all /api/* routes ───

PUBLIC_PATHS = {
    "/", "/health", "/api/health", "/docs", "/openapi.json", "/redoc",
    "/api/auth/login", "/api/auth/login/mfa", "/api/auth/refresh",
    "/api/auth/forgot-password", "/api/auth/reset-password",
    # Landing page endpoints (safe — no actionable trading data)
    "/api/access-requests",
    "/api/yahoo/index-sparklines",
    "/api/landing-stats",
    # Cron prune-exemption — protected by X-Service-Token at the endpoint,
    # not by user JWT. Rejecting at the middleware would short-circuit the
    # service-token check, so we let it through here and enforce in the
    # router.
    "/api/positions/nq/signal-ids",
}

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"


_ORIGIN_REGEX = re.compile(ALLOWED_ORIGIN_REGEX)


def _cors_headers(request: Request) -> dict:
    """Build CORS headers manually for short-circuited responses."""
    origin = request.headers.get("origin", "")
    if origin and (origin in ALLOWED_ORIGINS or _ORIGIN_REGEX.fullmatch(origin)):
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


def _middleware_extract_token(request: Request) -> str | None:
    """
    Pull the session JWT for the auth middleware. Bearer token first,
    legacy cookie fallback during the migration compat window. Mirrors
    auth.py::_extract_bearer_token + auth.py::get_current_user precedence.
    """
    auth_header = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
    if auth_header:
        scheme, _, raw_token = auth_header.partition(" ")
        if scheme.lower() == "bearer" and raw_token.strip():
            return raw_token.strip()
    # Legacy cookie fallback — remove after 2026-06-02
    return request.cookies.get(COOKIE_NAME)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public paths and OPTIONS (CORS preflight)
    if path in PUBLIC_PATHS or request.method == "OPTIONS" or not path.startswith("/api"):
        return await call_next(request)

    # Accept Authorization: Bearer header OR legacy nq_access cookie.
    # auth.py::get_current_user does the same precedence — the middleware
    # is here only as a fast-path 401 for unauthenticated requests, not as
    # the authoritative auth check (that's the dependency in each route).
    token = _middleware_extract_token(request)
    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"},
            headers=_cors_headers(request),
        )

    try:
        jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid session"},
            headers=_cors_headers(request),
        )

    return await call_next(request)


# ── Routers ───────────────────────────────────────────

from auth import router as auth_router
app.include_router(auth_router, prefix="/api")
app.include_router(overview.router, prefix="/api")
app.include_router(positions.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(kite.router, prefix="/api")
app.include_router(yahoo_finance.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(access_requests.router, prefix="/api")
app.include_router(landing_stats.router, prefix="/api")
app.include_router(nq_orders.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(hdfc.router, prefix="/api")
app.include_router(hdfc_market_data.router, prefix="/api")

ws_manager = WSManager()


def build_live_payload(is_admin: bool = False) -> dict:
    """Build the /ws periodic-update payload.

    Multi-user semantics (Sprint 1): paper portfolio is admin-only.
    Non-admin sockets get zeroed portfolio (they should use /kite/*
    endpoints for per-user brokerage state). Regime + timestamp are
    the same for everyone (market-wide signals).
    """
    portfolio = {"total_value": 0, "cash": 0,
                 "invested": 0, "total_return_pct": 0,
                 "drawdown_pct": 0, "n_positions": 0, "source": "none"}
    regime = {"regime": "UNKNOWN", "confidence": 0, "vix": 0, "breadth": 0, "nifty_rsi": 0}

    if is_admin:
        portfolio = {"total_value": INITIAL_CAPITAL, "cash": INITIAL_CAPITAL,
                     "invested": 0, "total_return_pct": 0,
                     "drawdown_pct": 0, "n_positions": 0, "source": "paper"}
        try:
            state = fetch_github_json("results/paper_portfolio_weekly.json")
            if state:
                pos = state.get("positions", {})
                invested = sum(p.get("current_value", 0) for p in pos.values())
                total = state.get("cash", INITIAL_CAPITAL) + invested
                peak = state.get("peak_value", total)
                portfolio = {
                    "total_value": round(total, 2),
                    "cash": round(state.get("cash", INITIAL_CAPITAL), 2),
                    "invested": round(invested, 2),
                    "total_return_pct": round((total / INITIAL_CAPITAL - 1) * 100, 2),
                    "drawdown_pct": round((total - peak) / max(peak, 1) * 100, 2),
                    "n_positions": len(pos),
                    "source": "paper",
                }
        except Exception:
            pass

    return {
        "type": "update",
        "timestamp": datetime.now().isoformat(),
        "portfolio": portfolio,
        "regime": regime,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for live data streaming.
    Requires a valid WS ticket (short-lived JWT) as query param.
    """
    # Authenticate via ticket
    ticket = ws.query_params.get("ticket")
    if not ticket:
        await ws.close(code=4001, reason="Missing authentication ticket")
        return

    db = SessionLocal()
    try:
        user = get_current_user_from_ws_ticket(ticket, db)
    finally:
        db.close()

    if not user:
        await ws.close(code=4001, reason="Invalid or expired ticket")
        return

    # Capture is_admin at connect time so periodic task doesn't hold
    # the DB session; role changes during a socket's lifetime are not
    # observed (acceptable — ticket TTL is short, reconnect picks up
    # the new role).
    is_admin = bool(getattr(user, "is_admin", False))

    await ws_manager.connect(ws)
    try:
        # Start periodic portfolio update task
        async def periodic_updates():
            while True:
                try:
                    data = build_live_payload(is_admin=is_admin)
                    await ws_manager.send_to(ws, json.dumps(data))
                except Exception:
                    break
                await asyncio.sleep(10)

        update_task = asyncio.create_task(periodic_updates())

        # Listen for client messages (subscribe/unsubscribe)
        while True:
            raw = await ws.receive_text()
            await ws_manager.handle_client_message(ws, raw)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        update_task.cancel()
        ws_manager.disconnect(ws)


@app.get("/")
def root():
    return {"status": "NiftyQuant API running", "version": "2.0.0", "docs": "/docs"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health_root():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
