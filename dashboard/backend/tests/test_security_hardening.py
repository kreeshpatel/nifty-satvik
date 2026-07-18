"""Security backlog (2026-07-18): real client IP behind Fly, email-alias normalization,
access-request dedupe. (The per-route rate limit + WS jti replay guard are covered by slowapi /
the existing auth tests.)"""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

import netutil
from netutil import normalize_email


class _Req:
    def __init__(self, headers=None, host="10.0.0.1"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": host})()


def test_client_ip_dev_ignores_forgeable_headers(monkeypatch) -> None:
    monkeypatch.setattr(netutil, "_IS_PRODUCTION", False)
    r = _Req(headers={"fly-client-ip": "6.6.6.6", "x-forwarded-for": "7.7.7.7"})
    assert netutil.client_ip(r) == "10.0.0.1"          # dev: socket peer only


def test_client_ip_production_trusts_fly_header(monkeypatch) -> None:
    monkeypatch.setattr(netutil, "_IS_PRODUCTION", True)
    assert netutil.client_ip(_Req(headers={"fly-client-ip": "1.2.3.4"})) == "1.2.3.4"
    assert netutil.client_ip(_Req(headers={"x-forwarded-for": "5.6.7.8, 9.9.9.9"})) == "5.6.7.8"
    assert netutil.client_ip(_Req()) == "10.0.0.1"     # no headers -> peer


def test_normalize_email_gmail_aliases() -> None:
    assert normalize_email("A.B+spam@Gmail.com") == "ab@gmail.com"
    assert normalize_email("a.b@googlemail.com") == "ab@gmail.com"
    assert normalize_email("First.Last+x@company.com") == "first.last@company.com"  # dots kept off-gmail
    assert normalize_email("  X@Y.COM ") == "x@y.com"


def test_access_request_alias_dedupe(client: TestClient) -> None:
    r1 = client.post("/api/access-requests", json={"name": "Alias Tester", "email": "alias.t@gmail.com"})
    assert r1.status_code == 200, r1.text
    rid = r1.json()["id"]
    # the +suffix / dotted alias of the same box is absorbed into the SAME pending request
    r2 = client.post("/api/access-requests", json={"name": "Alias Tester", "email": "aliast+again@gmail.com"})
    assert r2.status_code == 200 and r2.json()["id"] == rid


def test_approve_blocks_alias_duplicate_user(client: TestClient, make_user: Any, auth_cookies: Any,
                                             db_session: Any) -> None:
    admin = make_user(name="Root", is_admin=True)
    # existing user holds the canonical box
    u = make_user(name="Held")
    u.email = "inner.circle@gmail.com"
    db_session.commit()
    r = client.post("/api/access-requests", json={"name": "Dupe", "email": "innercircle+two@gmail.com"})
    rid = r.json()["id"]
    resp = client.post(f"/api/admin/access-requests/{rid}/approve",
                       json={"password": "Str0ng-Enough-Pass-2026"}, cookies=auth_cookies(admin))
    assert resp.status_code == 409 and "alias match" in resp.json()["detail"]
