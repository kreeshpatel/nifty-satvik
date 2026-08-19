"""The parallel terminal frontend (frontend2/) is served same-origin at /terminal.

Serving it from the API origin is what makes the nq_access cookie + /api work with no CORS. These
pin that the mount is wired, serves the page and its assets, redirects the no-slash path, and never
shadows an /api route.
"""
from __future__ import annotations


def test_terminal_index_is_served(client):
    r = client.get("/terminal/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Nifty Satvik Terminal" in r.text


def test_terminal_static_assets_served(client):
    for asset in ("styles.css", "app.js", "config.js"):
        r = client.get(f"/terminal/{asset}")
        assert r.status_code == 200, f"/terminal/{asset} -> {r.status_code}"


def test_terminal_noslash_redirects_to_slash(client):
    r = client.get("/terminal", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers.get("location") == "/terminal/"


def test_mount_does_not_shadow_api(client):
    assert client.get("/api/health").status_code == 200
