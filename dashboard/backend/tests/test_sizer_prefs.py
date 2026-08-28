"""Tests for the per-user sizer prefs layer (routers/holdings.py).

Renamed from test_holdings.py on 2026-08-27, when the ephemeral "bought" mark
(GET/POST/DELETE /api/holdings) was removed in favour of the durable execution ledger. What
survives here is the half of that router that was never duplicated: the risk tiers and single-
position cap read from config.py, and the user's saved tier + capital.

The deleted tests covered the mark's own contract (post/get/delete, idempotent qty overwrite,
tenant isolation, erase-on-completion). They are not ported: they tested a store that no longer
exists, and the question they were really asking -- "does the app know you bought this" -- is
answered by dashboard/backend/tests/test_execution.py against the ledger.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("path", ["/api/me/sizing-prefs", "/api/sizer/config"])
def test_sizer_routes_require_auth(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


def test_removed_endpoints_are_gone(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    """Both removals are pinned, not just performed.

    An endpoint that quietly comes back is how the two-stores-for-one-fact problem returns: the
    frontend would happily write to /api/holdings again and the ledger would stop being the only
    answer to "did you buy this". /api/signals/watchlist is pinned for the opposite reason -- it
    should only return once something actually WRITES a watchlist file, and a route that answers
    with an empty list is indistinguishable from one that has nothing to say.
    """
    ck = auth_cookies(make_user(name="Gone"))
    # 404 on every verb, not 405: the path itself is unrouted, so there is no method set left to
    # be "not allowed" against.
    assert client.get("/api/holdings", cookies=ck).status_code == 404
    assert client.post("/api/holdings", json={"signal_id": "DELHIVERY__2026-05-29"},
                       cookies=ck).status_code == 404
    assert client.delete("/api/holdings/DELHIVERY__2026-05-29", cookies=ck).status_code == 404
    assert client.get("/api/signals/watchlist", cookies=ck).status_code == 404


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
