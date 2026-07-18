"""Client-IP + email-identity helpers (security backlog, 2026-07-18).

client_ip(request)
    Behind Fly's proxy, `request.client.host` is the PROXY address — every user shares one
    rate-limit bucket and every audit row records the same useless IP. Fly injects the real
    client address in the `Fly-Client-IP` header (single value, set by the edge, not
    client-forgeable through Fly). We trust that header ONLY when actually running on a managed
    host (same production detection as auth/main); in local dev a client could send the header
    themselves, so we ignore it there and use the socket peer.

normalize_email(email)
    Canonical identity form for de-duplication: lowercase + trimmed, and for Gmail/Googlemail
    the dots and +suffix in the local part are stripped (a.b+c@gmail.com == ab@gmail.com to
    Google). Used for DUPLICATE CHECKS (access requests, admin-created accounts) so one person
    can't hold N accounts via aliases — the display/login email keeps the user's original form.
"""
import os

from fastapi import Request

_IS_PRODUCTION = bool(
    os.getenv("IS_PRODUCTION") or os.getenv("RENDER") or os.getenv("FLY_APP_NAME")
)

_GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def client_ip(request: Request) -> str:
    """The real client IP: Fly's edge header in production, the socket peer otherwise."""
    if _IS_PRODUCTION:
        fly = (request.headers.get("fly-client-ip") or "").strip()
        if fly:
            return fly
        # X-Forwarded-For fallback (first hop = original client on Fly/Render)
        xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if xff:
            return xff
    return request.client.host if request.client else "unknown"


def normalize_email(email: str) -> str:
    """Canonical form for duplicate/identity checks. Never used to rewrite what the user typed."""
    e = (email or "").strip().lower()
    if "@" not in e:
        return e
    local, _, domain = e.partition("@")
    if domain in _GMAIL_DOMAINS:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    else:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"
