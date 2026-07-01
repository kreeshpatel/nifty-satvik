"""
Kite Connect API proxy — routes all Zerodha API calls through the backend
to avoid CORS issues and keep API secrets server-side.

Per-user Kite sessions stored in PostgreSQL with encrypted access tokens.
"""

import os
import json
import hashlib
import time
import logging
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crypto import encrypt as _crypto_encrypt, decrypt as _crypto_decrypt

from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db, User, KiteSession
from auth import get_current_user

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger("kite_proxy")

router = APIRouter(prefix="/kite", tags=["kite"])

# ── Config from environment ──────────────────────────
def _clean_credential(value: str) -> str:
    """Strip whitespace and stray angle brackets from a pasted credential.

    Kite api_key/secret are plain alphanumeric — they never contain '<' or '>'.
    Operators sometimes paste the placeholder form ``<your_key>`` (or a value with
    a trailing newline) into the host secret store; that corrupts the api_key the
    backend redeems with and surfaces as Kite's misleading "Token is invalid or
    has expired" (the redeemed api_key no longer matches the one the frontend
    minted the request_token under). Sanitising on read makes the paste error
    self-healing. (2026-06-26: this exact ``<…>`` bug broke live Kite OAuth.)
    """
    return value.strip().strip("<>").strip()


KITE_API_KEY = _clean_credential(os.getenv("KITE_API_KEY", ""))
KITE_API_SECRET = _clean_credential(os.getenv("KITE_API_SECRET", ""))
KITE_API_BASE = "https://api.kite.trade"
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# HTTP forward proxy URL for Kite traffic — when set, all Kite REST calls
# route through this proxy so api.kite.trade sees the proxy's static IP
# (which we whitelist on the Zerodha developer console).
#
# Required to satisfy SEBI's April-2024 retail-algo circular: every
# order-placement request must originate from a registered static IP, and
# Zerodha enforces strict per-IP uniqueness across all Kite Connect apps
# (so shared-IP proxy services like QuotaGuard Static Micro don't work —
# we need a dedicated IP, typically a small VPS).
#
# HTTPS traffic to api.kite.trade tunnels through the proxy via the standard
# CONNECT method — end-to-end TLS is preserved, the proxy only sees the
# destination host, never the request body. Format:
#   http://USER:PASS@HOST:PORT
#
# Unset / empty → calls go direct to api.kite.trade (fine for local dev or
# any env where SEBI compliance isn't required yet). See plan:
# also-when-i-click-snappy-beaver.md.
KITE_PROXY_URL = os.getenv("KITE_PROXY_URL", "")


def _kite_proxies():
    """Return a `proxies` dict for the `requests` library, or None if no proxy.

    Scoping: returned ONLY by the Kite REST call sites in this file so that
    Kite traffic is the only thing routed through the static-IP proxy.
    yfinance, GitHub, Anthropic, etc. continue to go direct — they don't
    need static IPs and routing them through would just add latency.
    """
    if not KITE_PROXY_URL:
        return None
    return {"http": KITE_PROXY_URL, "https": KITE_PROXY_URL}

# ── Instrument cache (shared, not user-specific) ─────
_instruments_cache = {
    "data": None,
    "fetched_at": 0,
}
INSTRUMENTS_CACHE_TTL = 86400  # 24 hours

# ── Interval whitelist ───────────────────────────────
VALID_INTERVALS = {"minute", "3minute", "5minute", "10minute", "15minute", "30minute", "60minute", "day"}


def compute_token_expiry() -> float:
    """
    Kite Connect tokens expire at 6 AM IST the next day.
    Returns the Unix timestamp when the current/new token will expire.
    """
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=5, minutes=30)))
    tomorrow_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now.hour >= 6:
        tomorrow_6am += _dt.timedelta(days=1)
    return tomorrow_6am.timestamp()


# ── Encryption Helpers ────────────────────────────────
# Thin wrappers that defer to the shared crypto module so key rotation
# (ENCRYPTION_KEYS_OLD) is centralized in one place.

def encrypt_token(token: str) -> str:
    return _crypto_encrypt(token)


def decrypt_token(encrypted: str) -> str:
    return _crypto_decrypt(encrypted)


# ── Token Helpers ─────────────────────────────────────

def get_user_kite_token(user: User, db: Session) -> str:
    """Get the current user's decrypted Kite access token, or raise 401."""
    session = db.query(KiteSession).filter(KiteSession.user_id == user.id).first()
    if not session or time.time() > session.expires_at:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Kite. Please link your Kite account.",
        )
    return decrypt_token(session.access_token_encrypted)


def get_owner_kite_token(db: Session) -> str:
    """
    Get the admin/owner's Kite access token for shared market data.
    This powers quotes, LTP, historical data for ALL users.
    The owner (is_admin=True) connects Kite once; all users benefit.
    """
    from database import User as UserModel
    admin = db.query(UserModel).filter(UserModel.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=503, detail="Market data unavailable. Owner not configured.")
    session = db.query(KiteSession).filter(KiteSession.user_id == admin.id).first()
    if not session or time.time() > session.expires_at:
        raise HTTPException(
            status_code=503,
            detail="Market data unavailable. Owner's Kite session expired.",
        )
    return decrypt_token(session.access_token_encrypted)


# ── Kite API Helpers ──────────────────────────────────

def kite_headers(token: str) -> dict:
    return {
        "Authorization": f"token {KITE_API_KEY}:{token}",
        "Content-Type": "application/json",
    }


def _extract_kite_error(resp) -> str:
    """Pull Kite's actual error message + type out of the response body.

    Kite REST returns errors as:
        {"status": "error", "message": "<human-readable reason>",
         "error_type": "InputException" | "OrderException" | "TokenException" | ...}
    Without this extraction, every rejection (T2T market block, penny-stock
    policy, circuit-hit, margin shortfall, etc.) collapses into the same
    useless "Kite API request failed" — leaving users guessing why Zerodha
    refused the order.
    """
    try:
        data = resp.json()
        msg = data.get("message") or data.get("error_message")
        error_type = data.get("error_type")
        if msg and error_type:
            return f"{msg} ({error_type})"
        if msg:
            return msg
    except Exception:
        pass
    return f"Kite API request failed (HTTP {resp.status_code})"


def kite_get(path: str, token: str, params: dict = None, retries: int = 2):
    """Make authenticated GET request to Kite API with retry."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                f"{KITE_API_BASE}{path}",
                headers=kite_headers(token),
                params=params,
                proxies=_kite_proxies(),
                timeout=5,
            )
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data")
            raise HTTPException(status_code=resp.status_code, detail=_extract_kite_error(resp))
        except requests.exceptions.ConnectionError:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            raise HTTPException(status_code=502, detail="Cannot reach Kite API after retries")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Kite GET {path} error: {e}")
            if attempt < retries - 1:
                continue
            raise HTTPException(status_code=502, detail="Kite API request failed")


def kite_post(path: str, token: str, body: dict = None):
    """Make authenticated POST request to Kite API.

    No retry: POST is a mutation (e.g. place order) — retrying a transient
    failure risks a duplicate order. We only wrap network/parse errors into a
    clean 502 instead of letting ConnectionError/Timeout bubble up as an
    unhandled 500 (kite_get had this guard; post/put/delete did not).
    """
    try:
        resp = requests.post(
            f"{KITE_API_BASE}{path}",
            headers={
                "Authorization": f"token {KITE_API_KEY}:{token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=body,
            proxies=_kite_proxies(),
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data.get("data")
        raise HTTPException(status_code=resp.status_code, detail=_extract_kite_error(resp))
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Cannot reach Kite API")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kite POST {path} error: {e}")
        raise HTTPException(status_code=502, detail="Kite API request failed")


def kite_put(path: str, token: str, body: dict = None):
    """Make authenticated PUT request to Kite API. No retry (mutation)."""
    try:
        resp = requests.put(
            f"{KITE_API_BASE}{path}",
            headers={
                "Authorization": f"token {KITE_API_KEY}:{token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=body,
            proxies=_kite_proxies(),
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data.get("data")
        raise HTTPException(status_code=resp.status_code, detail=_extract_kite_error(resp))
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Cannot reach Kite API")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kite PUT {path} error: {e}")
        raise HTTPException(status_code=502, detail="Kite API request failed")


def kite_delete(path: str, token: str):
    """Make authenticated DELETE request to Kite API. No retry (mutation)."""
    try:
        resp = requests.delete(
            f"{KITE_API_BASE}{path}",
            headers=kite_headers(token),
            proxies=_kite_proxies(),
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data.get("data")
        raise HTTPException(status_code=resp.status_code, detail=_extract_kite_error(resp))
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Cannot reach Kite API")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kite DELETE {path} error: {e}")
        raise HTTPException(status_code=502, detail="Kite API request failed")


# ── Authentication ───────────────────────────────────

class TokenExchangeRequest(BaseModel):
    request_token: str


@router.post("/session/token")
async def exchange_token(
    req: TokenExchangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange request_token for access_token. Stores encrypted token per-user."""
    from audit import log_event

    if not KITE_API_KEY or not KITE_API_SECRET:
        raise HTTPException(status_code=500, detail="Kite API credentials not configured on server")

    checksum = hashlib.sha256(
        f"{KITE_API_KEY}{req.request_token}{KITE_API_SECRET}".encode()
    ).hexdigest()

    try:
        resp = requests.post(
            f"{KITE_API_BASE}/session/token",
            data={
                "api_key": KITE_API_KEY,
                "request_token": req.request_token,
                "checksum": checksum,
            },
            proxies=_kite_proxies(),
            timeout=15,
        )
        data = resp.json()
    except requests.exceptions.ConnectionError:
        logger.error("Connection to Kite API failed during token exchange")
        raise HTTPException(status_code=502, detail="Cannot reach Kite API. Please try again.")
    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=502, detail="Token exchange failed. Please try again.")

    if data.get("status") != "success":
        logger.error(
            "Kite token exchange rejected: http=%s error_type=%s message=%s",
            resp.status_code, data.get("error_type"), data.get("message"),
        )
        raise HTTPException(status_code=400, detail="Token exchange failed")

    session_data = data["data"]
    expires_at = compute_token_expiry()

    # Upsert per-user Kite session with encrypted token
    existing = db.query(KiteSession).filter(KiteSession.user_id == user.id).first()
    encrypted = encrypt_token(session_data["access_token"])

    if existing:
        existing.kite_user_id = session_data.get("user_id")
        existing.access_token_encrypted = encrypted
        existing.expires_at = expires_at
    else:
        db.add(KiteSession(
            user_id=user.id,
            kite_user_id=session_data.get("user_id"),
            access_token_encrypted=encrypted,
            expires_at=expires_at,
        ))
    db.commit()

    ip = request.client.host if request.client else "unknown"
    log_event(db, user.id, "KITE_CONNECTED", f"Kite user: {session_data.get('user_id')}", ip)

    return {
        "status": "success",
        "user_id": session_data.get("user_id"),
        "user_name": session_data.get("user_name"),
    }


@router.get("/session/status")
async def session_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check if the current user has a valid Kite session."""
    session = db.query(KiteSession).filter(KiteSession.user_id == user.id).first()
    is_valid = session is not None and time.time() < session.expires_at
    return {
        "connected": is_valid,
        "user_id": session.kite_user_id if is_valid else None,
    }


@router.post("/session/logout")
async def kite_logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear the user's Kite session."""
    from audit import log_event

    session = db.query(KiteSession).filter(KiteSession.user_id == user.id).first()
    kite_uid = session.kite_user_id if session else None
    if session:
        db.delete(session)
        db.commit()

    ip = request.client.host if request.client else "unknown"
    log_event(db, user.id, "KITE_DISCONNECTED", f"Kite user: {kite_uid}", ip)

    return {"status": "success"}


# ── Portfolio Data ───────────────────────────────────

@router.get("/holdings")
async def get_holdings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_user_kite_token(user, db)
    return kite_get("/portfolio/holdings", token)


@router.get("/positions")
async def get_positions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_user_kite_token(user, db)
    return kite_get("/portfolio/positions", token)


@router.get("/margins")
async def get_margins(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_user_kite_token(user, db)
    return kite_get("/user/margins", token)


# ── Orders ───────────────────────────────────────────

@router.get("/orders")
async def get_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_user_kite_token(user, db)
    return kite_get("/orders", token)


@router.get("/trades")
async def get_trades(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_user_kite_token(user, db)
    return kite_get("/trades", token)


class PlaceOrderRequest(BaseModel):
    exchange: str = "NSE"
    tradingsymbol: str
    transaction_type: str  # BUY or SELL
    quantity: int
    product: str = "CNC"  # CNC, MIS, NRML
    order_type: str = "MARKET"  # MARKET, LIMIT, SL, SL-M
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    validity: str = "DAY"  # DAY, IOC
    disclosed_quantity: Optional[int] = None
    tag: Optional[str] = "NQ"


@router.post("/orders/{variety}")
@limiter.limit("10/minute")
async def place_order(
    variety: str,
    order: PlaceOrderRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place an order. variety: regular, amo, co, iceberg"""
    from audit import log_event

    token = get_user_kite_token(user, db)

    body = {
        "exchange": order.exchange,
        "tradingsymbol": order.tradingsymbol,
        "transaction_type": order.transaction_type,
        "quantity": str(order.quantity),
        "product": order.product,
        "order_type": order.order_type,
        "validity": order.validity,
    }
    if order.price is not None:
        body["price"] = str(order.price)
    if order.trigger_price is not None:
        body["trigger_price"] = str(order.trigger_price)
    if order.disclosed_quantity is not None:
        body["disclosed_quantity"] = str(order.disclosed_quantity)
    if order.tag:
        body["tag"] = order.tag

    result = kite_post(f"/orders/{variety}", token, body)

    ip = request.client.host if request.client else "unknown"
    log_event(
        db, user.id, "ORDER_PLACED",
        f"{order.transaction_type} {order.quantity} {order.tradingsymbol} @ {order.order_type} ({variety})",
        ip,
    )

    return result


class ModifyOrderRequest(BaseModel):
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    order_type: Optional[str] = None
    validity: Optional[str] = None
    disclosed_quantity: Optional[int] = None


@router.put("/orders/{variety}/{order_id}")
async def modify_order(
    variety: str,
    order_id: str,
    order: ModifyOrderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Modify a pending order."""
    token = get_user_kite_token(user, db)

    body = {}
    if order.quantity is not None:
        body["quantity"] = str(order.quantity)
    if order.price is not None:
        body["price"] = str(order.price)
    if order.trigger_price is not None:
        body["trigger_price"] = str(order.trigger_price)
    if order.order_type is not None:
        body["order_type"] = order.order_type
    if order.validity is not None:
        body["validity"] = order.validity
    if order.disclosed_quantity is not None:
        body["disclosed_quantity"] = str(order.disclosed_quantity)

    return kite_put(f"/orders/{variety}/{order_id}", token, body)


@router.delete("/orders/{variety}/{order_id}")
async def cancel_order(
    variety: str,
    order_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a pending order."""
    from audit import log_event

    token = get_user_kite_token(user, db)
    result = kite_delete(f"/orders/{variety}/{order_id}", token)

    ip = request.client.host if request.client else "unknown"
    log_event(db, user.id, "ORDER_CANCELLED", f"Order {order_id} ({variety})", ip)

    return result


@router.get("/orders/{order_id}/trades")
async def get_order_trades(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get trades for a specific order."""
    token = get_user_kite_token(user, db)
    return kite_get(f"/orders/{order_id}/trades", token)


# ── Instruments ──────────────────────────────────────

@router.get("/instruments")
async def get_instruments(
    exchange: str = "NSE",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get instrument list (cached for 24 hours). Uses owner's Kite session."""
    now = time.time()

    if _instruments_cache["data"] and (now - _instruments_cache["fetched_at"]) < INSTRUMENTS_CACHE_TTL:
        return _instruments_cache["data"]

    token = get_owner_kite_token(db)
    resp = requests.get(
        f"{KITE_API_BASE}/instruments/{exchange}",
        headers={"Authorization": f"token {KITE_API_KEY}:{token}"},
        proxies=_kite_proxies(),
        timeout=30,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch instruments")

    # Parse CSV response into JSON
    lines = resp.text.strip().split("\n")
    headers_row = lines[0].split(",")
    instruments = []
    for line in lines[1:]:
        values = line.split(",")
        if len(values) >= len(headers_row):
            inst = dict(zip(headers_row, values))
            instruments.append({
                "instrument_token": int(inst.get("instrument_token", 0)),
                "exchange_token": int(inst.get("exchange_token", 0)),
                "tradingsymbol": inst.get("tradingsymbol", ""),
                "name": inst.get("name", ""),
                "exchange": inst.get("exchange", exchange),
                "segment": inst.get("segment", ""),
                "instrument_type": inst.get("instrument_type", ""),
                "lot_size": int(inst.get("lot_size", 1)),
                "tick_size": float(inst.get("tick_size", 0.05)),
            })

    _instruments_cache["data"] = instruments
    _instruments_cache["fetched_at"] = now

    return instruments


# ── Quotes (current prices) ──────────────────────────

# In-memory quote cache: { instruments_key: (timestamp, data) }
_quote_cache: dict[str, tuple[float, dict]] = {}
_QUOTE_CACHE_TTL = 1.0  # seconds — avoids duplicate Kite round trips


@router.get("/quote")
@limiter.limit("60/minute")
async def get_quotes(
    instruments: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current quotes. Uses owner's Kite session (paid Market Data)."""
    cache_key = instruments
    now = time.time()
    cached = _quote_cache.get(cache_key)
    if cached and (now - cached[0]) < _QUOTE_CACHE_TTL:
        return cached[1]

    token = get_owner_kite_token(db)
    data = kite_get("/quote", token, params={"i": instruments.split(",")})
    _quote_cache[cache_key] = (now, data)
    return data


@router.get("/quote/ltp")
async def get_ltp(
    instruments: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get last traded prices. Uses owner's Kite session (paid Market Data)."""
    token = get_owner_kite_token(db)
    return kite_get("/quote/ltp", token, params={"i": instruments.split(",")})


@router.get("/ltp-via-history")
async def get_ltp_via_history(
    tokens: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get latest prices using historical API (free tier).
    Uses owner's Kite session — available to all logged-in users.
    """
    import datetime
    token = get_owner_kite_token(db)
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    results = {}
    for inst_token in tokens.split(","):
        inst_token = inst_token.strip()
        if not inst_token:
            continue
        try:
            data = kite_get(
                f"/instruments/historical/{inst_token}/day",
                token,
                params={"from": start, "to": end},
            )
            candles = data.get("candles", []) if isinstance(data, dict) else data
            if candles and len(candles) > 0:
                last = candles[-1]
                results[inst_token] = {
                    "last_price": last[4],
                    "open": last[1],
                    "high": last[2],
                    "low": last[3],
                    "close": last[4],
                    "volume": last[5] if len(last) > 5 else 0,
                    "date": last[0],
                }
        except Exception as e:
            logger.warning(f"Failed to get history for {inst_token}: {e}")
            continue

    return results


# ── Historical Data ──────────────────────────────────

@router.get("/historical/{instrument_token}/{interval}")
async def get_historical(
    instrument_token: int,
    interval: str,
    start: str,
    end: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get historical OHLCV data. interval: minute, 5minute, 15minute, 30minute, 60minute, day"""
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval. Must be one of: {', '.join(sorted(VALID_INTERVALS))}",
        )

    # Validate date format
    import datetime
    for date_str, label in [(start, "start"), (end, "end")]:
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid {label} date. Use YYYY-MM-DD format.")

    token = get_owner_kite_token(db)
    return kite_get(
        f"/instruments/historical/{instrument_token}/{interval}",
        token,
        params={"from": start, "to": end},
    )
