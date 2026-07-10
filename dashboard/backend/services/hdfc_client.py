"""
hdfc_client.py — raw HTTP wrapper for HDFC Securities' InvestRight Open API.

MARKET DATA ONLY. This module never places, modifies, or cancels an order and
never reads holdings/positions/funds — those stay on Kite (see routers/kite.py).
Scope, per owner decision (2026-07): swap only the live-quote (LTP) source.

Auth flow (per InvestRight docs, "Fetch Access Token via API" — the headless
variant, no browser redirect):
    1. GET  /oapi/v1/login                          -> tokenId
    2. POST /oapi/v1/login/validate                  -> twofa question(s)
    3. POST /oapi/v1/twofa/validate    (OTP answer)   -> requestToken (unauthorised)
    4. GET  /oapi/v1/authorise         (consent)      -> requestToken (authorised)
    5. POST /oapi/v1/access-token                     -> accessToken

HDFC's 2FA is answered with a real OTP sent to the account holder's registered
email/mobile — no TOTP/authenticator-app option is documented, so steps 2-5
cannot run unattended. An admin completes them via /api/admin/hdfc/login/*
(routers/hdfc.py); the resulting accessToken is the single shared market-data
credential for the whole app (mirrors Kite's "owner token" pattern in kite.py,
but via a manual admin action instead of a cron — see HdfcMarketDataSession).
"""
from __future__ import annotations

import os

import requests

HDFC_API_BASE = "https://developer.hdfcsec.com/oapi/v1"
HDFC_API_KEY = os.getenv("HDFC_API_KEY", "").strip()
HDFC_API_SECRET = os.getenv("HDFC_API_SECRET", "").strip()

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


class HdfcApiError(RuntimeError):
    """Raised on any non-2xx response or unexpected payload shape from HDFC."""


def _require_key() -> str:
    if not HDFC_API_KEY:
        raise HdfcApiError("HDFC_API_KEY is not configured on this service.")
    return HDFC_API_KEY


def _headers(access_token: str | None = None) -> dict:
    h = {"User-Agent": _USER_AGENT}
    if access_token:
        h["Authorization"] = access_token
    return h


def _call(method: str, path: str, *, params: dict | None = None,
           json_body: dict | None = None, access_token: str | None = None) -> dict:
    url = f"{HDFC_API_BASE}{path}"
    try:
        resp = requests.request(
            method, url, params=params, json=json_body,
            headers=_headers(access_token), timeout=15,
        )
    except requests.RequestException as exc:
        raise HdfcApiError(f"HDFC request failed ({method} {path}): {exc}") from exc
    if resp.status_code >= 400:
        raise HdfcApiError(f"HDFC {method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise HdfcApiError(f"HDFC {method} {path} returned non-JSON body") from exc


# ── Step 1: Token ID ────────────────────────────────────────────────────
def get_token_id() -> str:
    api_key = _require_key()
    data = _call("GET", "/login", params={"api_key": api_key})
    token_id = data.get("tokenId")
    if not token_id:
        raise HdfcApiError(f"No tokenId in response: {data}")
    return token_id


# ── Step 2: Login (username/password) — returns the 2FA question(s) ─────
def login_validate(token_id: str, username: str, password: str) -> dict:
    api_key = _require_key()
    return _call(
        "POST", "/login/validate",
        params={"api_key": api_key, "token_id": token_id},
        json_body={"username": username, "password": password},
    )


def resend_2fa(token_id: str) -> dict:
    api_key = _require_key()
    return _call("GET", "/twofa/resend", params={"api_key": api_key, "token_id": token_id})


# ── Step 3: Validate the OTP ─────────────────────────────────────────────
def validate_2fa(token_id: str, answer: str) -> dict:
    api_key = _require_key()
    return _call(
        "POST", "/twofa/validate",
        params={"api_key": api_key, "token_id": token_id},
        json_body={"answer": answer},
    )


# ── Step 4: Authorise (accept T&C, get the final request token) ─────────
def authorise(token_id: str, request_token: str, consent: bool = True) -> dict:
    api_key = _require_key()
    return _call(
        "GET", "/authorise",
        params={
            "api_key": api_key, "token_id": token_id,
            "consent": "True" if consent else "False",
            "request_token": request_token,
        },
    )


# ── Step 5: Exchange the request token for the access token ─────────────
def fetch_access_token(request_token: str) -> str:
    api_key = _require_key()
    if not HDFC_API_SECRET:
        raise HdfcApiError("HDFC_API_SECRET is not configured on this service.")
    # The documented sample sends apiSecret only in the JSON body — and that
    # sample's own JSON has a trailing comma (invalid JSON), a sign this one
    # endpoint's docs are unreliable. Every OTHER authenticated call in this
    # API (e.g. fetch-ltp) takes its credential as a raw `Authorization`
    # header, not just a body field, so send api_secret both ways here too —
    # a 401 "authorization not provided" means the header was the missing part.
    data = _call(
        "POST", "/access-token",
        params={"api_key": api_key, "request_token": request_token},
        json_body={"apiSecret": HDFC_API_SECRET},
        access_token=HDFC_API_SECRET,
    )
    token = data.get("accessToken")
    if not token:
        raise HdfcApiError(f"No accessToken in response: {data}")
    return token


# ── Market data: LTP snapshot ────────────────────────────────────────────
def fetch_ltp(access_token: str, instruments: list[dict]) -> list[dict]:
    """
    instruments: [{"exchange": "NSE", "token": "21840"}, ...]
    Returns the raw `data` list: [{"prev_close": .., "ltp": .., "exchange": .., "token": ..}, ...]
    NOTE: the documented method is PUT (not the more usual POST-for-a-query) —
    verified against the InvestRight "Fetch LTP" spec, not a typo.
    """
    api_key = _require_key()
    data = _call(
        "PUT", "/fetch-ltp",
        params={"api_key": api_key},
        json_body={"data": instruments},
        access_token=access_token,
    )
    return data.get("data", [])
