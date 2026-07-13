"""Tests for the per-user sizer prefs + ephemeral holdings layer (routers/holdings.py).

Covers: auth guard, tenant isolation, POST→GET→DELETE contract, idempotent qty overwrite,
sizing-prefs round-trip, sizer config, signal_id validation, and erase-on-completion (the
holding is deleted once the model marks the signal closed).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

SIG_A = "DELHIVERY__2026-05-29"
SIG_B = "TITAGARH__2026-05-29"


# ── auth guard ────────────────────────────────────────

@pytest.mark.parametrize("path", ["/api/holdings", "/api/me/sizing-prefs", "/api/sizer/config"])
def test_holdings_routes_require_auth(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


# ── sizer config + prefs ──────────────────────────────

def test_sizer_config_shape(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Cfg")
    r = client.get("/api/sizer/config", cookies=auth_cookies(u))
    assert r.status_code == 200
    body = r.json()
    assert body["tiers"] == {"medium": 0.02, "high": 0.03}
    assert body["position_cap_pct"] == 0.20


def test_sizing_prefs_default_and_update(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Prefs")
    ck = auth_cookies(u)
    assert client.get("/api/me/sizing-prefs", cookies=ck).json() == {"risk_tier": "medium", "default_capital": None}

    r = client.put("/api/me/sizing-prefs", json={"risk_tier": "high", "default_capital": 2000000}, cookies=ck)
    assert r.status_code == 200 and r.json() == {"risk_tier": "high", "default_capital": 2000000.0}
    # Persisted across a fresh GET
    assert client.get("/api/me/sizing-prefs", cookies=ck).json()["risk_tier"] == "high"


def test_sizing_prefs_rejects_bad_tier(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="BadTier")
    r = client.put("/api/me/sizing-prefs", json={"risk_tier": "reckless"}, cookies=auth_cookies(u))
    assert r.status_code == 422


# ── holdings contract ─────────────────────────────────

def test_mark_get_delete_roundtrip(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Round")
    ck = auth_cookies(u)

    r = client.post("/api/holdings", json={"signal_id": SIG_A, "ticker": "DELHIVERY",
                                           "entry": 510.95, "stop": 486.0, "qty": 1600,
                                           "risk_tier_at_buy": "high"}, cookies=ck)
    assert r.status_code == 201 and r.json()["qty"] == 1600

    got = client.get("/api/holdings", cookies=ck).json()["holdings"]
    assert len(got) == 1 and got[0]["signal_id"] == SIG_A and got[0]["risk_tier_at_buy"] == "high"

    assert client.delete(f"/api/holdings/{SIG_A}", cookies=ck).status_code == 204
    assert client.get("/api/holdings", cookies=ck).json()["holdings"] == []
    assert client.delete(f"/api/holdings/{SIG_A}", cookies=ck).status_code == 404


def test_repost_overwrites_qty(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Overwrite")
    ck = auth_cookies(u)
    client.post("/api/holdings", json={"signal_id": SIG_A, "qty": 100}, cookies=ck)
    client.post("/api/holdings", json={"signal_id": SIG_A, "qty": 250}, cookies=ck)
    got = client.get("/api/holdings", cookies=ck).json()["holdings"]
    assert len(got) == 1 and got[0]["qty"] == 250  # overwrite, not a second row


def test_mark_only_qty_null(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="MarkOnly")
    ck = auth_cookies(u)
    r = client.post("/api/holdings", json={"signal_id": SIG_A}, cookies=ck)  # no qty
    assert r.status_code == 201 and r.json()["qty"] is None
    assert r.json()["ticker"] == "DELHIVERY"  # derived from signal_id


def test_invalid_signal_id_rejected(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="BadId")
    r = client.post("/api/holdings", json={"signal_id": "not-a-valid-id"}, cookies=auth_cookies(u))
    assert r.status_code == 422


# ── tenant isolation ──────────────────────────────────

def test_holdings_isolated_between_users(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    a, b = make_user(name="A"), make_user(name="B")
    client.post("/api/holdings", json={"signal_id": SIG_A, "qty": 10}, cookies=auth_cookies(a))
    # B sees nothing of A's
    assert client.get("/api/holdings", cookies=auth_cookies(b)).json()["holdings"] == []
    # B cannot delete A's
    assert client.delete(f"/api/holdings/{SIG_A}", cookies=auth_cookies(b)).status_code == 404
    # A still holds it
    assert len(client.get("/api/holdings", cookies=auth_cookies(a)).json()["holdings"]) == 1


# ── erase-on-completion ───────────────────────────────

def test_completed_holding_erased_on_read(
    client: TestClient, make_user: Any, auth_cookies: Any, monkeypatch: Any
) -> None:
    u = make_user(name="Erase")
    ck = auth_cookies(u)
    client.post("/api/holdings", json={"signal_id": SIG_A, "qty": 10}, cookies=ck)  # closed later
    client.post("/api/holdings", json={"signal_id": SIG_B, "qty": 20}, cookies=ck)  # stays open

    import routers.holdings as h
    monkeypatch.setattr(h, "signal_lifecycle_state",
                        lambda sid, tkr: "closed" if sid == SIG_A else "open")

    got = client.get("/api/holdings", cookies=ck).json()["holdings"]
    assert [r["signal_id"] for r in got] == [SIG_B]  # SIG_A pruned

    # And it is actually GONE from the DB, not just filtered — a second read (now un-mocked,
    # 'unknown' for a fresh buy) must not resurrect it.
    monkeypatch.setattr(h, "signal_lifecycle_state", lambda sid, tkr: "unknown")
    got2 = client.get("/api/holdings", cookies=ck).json()["holdings"]
    assert [r["signal_id"] for r in got2] == [SIG_B]
