"""The public raw URL as a fallback, so one expired secret cannot take the product's data to zero.

**Why this exists.** `results/` is listed in `.dockerignore`, so it is absent from the deployed
image — the "fall back to the local file" that both fetchers documented does not exist in
production. Until 2026-08-29 a single expired, revoked or rate-limited `GITHUB_TOKEN` therefore
took every signal, position and monitor read to **zero**, not to something stale, and the only
symptom would have been empty pages.

The repo is public. A secret has no business being load-bearing on a public read.

These tests pin the two properties that make the fallback worth having: it engages on *both*
failure shapes (no token at all, and a token the API rejects), and it is never silent — a
fallback nobody can see is how you discover months later that the primary has been dead all along.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest


def _resp(status: int, text: str = ""):
    return SimpleNamespace(status_code=status, text=text)


# ── routers/signals.py ────────────────────────────────────────────────────────

@pytest.fixture()
def sig(monkeypatch):
    from routers import signals as m
    m._GITHUB_CACHE.clear()
    return m


def test_no_token_reads_over_the_public_url(sig, monkeypatch, caplog):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return _resp(200, '{"ok": true}')

    monkeypatch.setattr(sig.requests, "get", fake_get)
    with caplog.at_level(logging.WARNING):
        assert sig._fetch_github_raw("results/x.json") == {"ok": True}

    assert calls and calls[0].startswith(sig.GITHUB_RAW), f"did not use the raw URL: {calls}"
    assert any("no GITHUB_TOKEN" in r.getMessage() for r in caplog.records), "fell back silently"


def test_a_rejected_token_falls_back_rather_than_serving_nothing(sig, monkeypatch, caplog):
    """The real-world case: the token expires. Before this, the answer was None — and with
    results/ absent from the image, None means the product shows nothing at all."""
    monkeypatch.setenv("GITHUB_TOKEN", "expired-token")
    seen = []

    def fake_get(url, **kw):
        seen.append(url)
        if url.startswith(sig.GITHUB_API_CONTENTS):
            return _resp(401)
        return _resp(200, '{"recovered": 1}')

    monkeypatch.setattr(sig.requests, "get", fake_get)
    with caplog.at_level(logging.WARNING):
        assert sig._fetch_github_raw("results/y.json") == {"recovered": 1}

    assert len(seen) == 2 and seen[1].startswith(sig.GITHUB_RAW)
    assert any("Check GITHUB_TOKEN" in r.getMessage() for r in caplog.records), (
        "a dead token must be visible in the log, not merely worked around"
    )


def test_both_paths_failing_still_returns_none_for_the_caller(sig, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setattr(sig.requests, "get", lambda url, **kw: _resp(500))
    assert sig._fetch_github_raw("results/z.json") is None


def test_a_healthy_token_never_touches_the_raw_url(sig, monkeypatch):
    """The authenticated path stays primary — it carries the 5,000/hour limit against 60."""
    monkeypatch.setenv("GITHUB_TOKEN", "good")
    seen = []

    def fake_get(url, **kw):
        seen.append(url)
        return _resp(200, '{"v": 1}')

    monkeypatch.setattr(sig.requests, "get", fake_get)
    assert sig._fetch_github_raw("results/a.json") == {"v": 1}
    assert len(seen) == 1 and seen[0].startswith(sig.GITHUB_API_CONTENTS)


# ── github_data.py ────────────────────────────────────────────────────────────

def test_github_data_falls_back_on_a_rejected_token(monkeypatch, caplog):
    import github_data as g

    monkeypatch.setenv("GITHUB_TOKEN", "expired")
    seen = []

    def fake_get(url, **kw):
        seen.append(url)
        return _resp(403) if url.startswith(g.GITHUB_API_CONTENTS) else _resp(200, "payload")

    monkeypatch.setattr(g.requests, "get", fake_get)
    with caplog.at_level(logging.WARNING):
        assert g._fetch_remote("results/p.json") == "payload"
    assert len(seen) == 2 and seen[1].startswith(g.GITHUB_RAW)
    assert any("Check GITHUB_TOKEN" in r.getMessage() for r in caplog.records)


def test_github_data_no_token_uses_the_public_url(monkeypatch):
    import github_data as g

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(g.requests, "get", lambda url, **kw: _resp(200, "public"))
    assert g._fetch_remote("results/q.json") == "public"
