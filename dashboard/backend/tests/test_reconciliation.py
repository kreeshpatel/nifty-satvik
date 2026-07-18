"""Stage-4b: reconciliation — model plan minus user ledger => per-user action items.

Covers the spec contract (docs/EXECUTION_CAPTURE_SPEC.md §5):
  * a model exit flag on a name the user still holds surfaces a SELL_DUE at the P-cadence severity,
  * a fully-closed model trade the user still holds surfaces a STALE_HOLD,
  * an actionable model buy the user hasn't recorded surfaces an UNTAKEN_BUY (informational),
  * items are DERIVED — recording the missing sell RESOLVES the SELL_DUE on the next read (no extra
    bookkeeping), which is what a capture popup relies on.
"""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services import execution_ledger as ledger
from services import reconciliation as recon

HELD = "LTFOODS__2026-07-01"        # user holds this; model flags a runner exit
CLOSED = "USHAMART__2026-06-01"     # user holds this; model has closed it
BUYABLE = "MARICO__2026-07-17"      # model has an open buy the user hasn't taken


def _positions(remaining_held=100, remaining_closed=50):
    return [
        {"signal_id": HELD, "ticker": "LTFOODS", "remaining_qty": remaining_held},
        {"signal_id": CLOSED, "ticker": "USHAMART", "remaining_qty": remaining_closed},
    ]


def _model():
    envelope = {"generated_at": "2026-07-18", "signals": [
        {"ticker": "LTFOODS", "signal_date": "2026-07-01", "actionability": "HOLD", "status": "ACTIVE"},
        {"ticker": "USHAMART", "signal_date": "2026-06-01", "actionability": "EXIT_REQUIRED", "status": "HIT_TARGET"},
        {"ticker": "MARICO", "signal_date": "2026-07-17", "actionability": "BUY_OPEN", "status": "FRESH"},
    ]}
    monitor = {"as_of": "2026-07-17", "flags": [
        {"ticker": "LTFOODS", "event": "RUNNER_BELOW_SMA", "severity": "warn"},
        {"ticker": "USHAMART", "event": "STOP_BREACH", "severity": "high"},
    ]}
    return envelope, monitor


def test_action_items_cover_the_three_cases() -> None:
    envelope, monitor = _model()
    idx = recon.build_model_index(envelope, monitor)
    items = recon.build_action_items(_positions(), idx)
    by_type = {it["type"] for it in items}
    assert {"SELL_DUE", "STALE_HOLD", "UNTAKEN_BUY"} <= by_type

    sell_due = next(it for it in items if it["type"] == "SELL_DUE" and it["ticker"] == "LTFOODS")
    assert sell_due["event"] == "RUNNER_BELOW_SMA" and sell_due["severity"] == "warn"
    stale = next(it for it in items if it["type"] == "STALE_HOLD")
    assert stale["ticker"] == "USHAMART" and stale["remaining_qty"] == 50
    buy = next(it for it in items if it["type"] == "UNTAKEN_BUY")
    assert buy["ticker"] == "MARICO" and buy["severity"] == "info"

    # most-urgent first (high before warn/info)
    assert items[0]["severity"] == "high"


def test_recording_the_sell_resolves_the_sell_due() -> None:
    envelope, monitor = _model()
    idx = recon.build_model_index(envelope, monitor)
    # held with 100 -> SELL_DUE present
    before = recon.build_action_items(_positions(remaining_held=100), idx)
    assert any(it["type"] == "SELL_DUE" and it["ticker"] == "LTFOODS" for it in before)
    # user records the full sell -> remaining 0 -> the item is gone on the next derive
    after = recon.build_action_items(_positions(remaining_held=0), idx)
    assert not any(it["type"] == "SELL_DUE" and it["ticker"] == "LTFOODS" for it in after)


def test_no_open_when_ledger_matches_model() -> None:
    # user holds nothing the model wants exited, and has taken the buy → no SELL_DUE/STALE_HOLD
    envelope = {"signals": [{"ticker": "MARICO", "signal_date": "2026-07-17",
                             "actionability": "BUY_OPEN", "status": "FRESH"}]}
    idx = recon.build_model_index(envelope, {})
    positions = [{"signal_id": "MARICO__2026-07-17", "ticker": "MARICO", "remaining_qty": 40}]
    items = recon.build_action_items(positions, idx)
    assert items == []                    # they hold the buy the model opened; nothing outstanding


# ── endpoint ──────────────────────────────────────────

def test_reconciliation_endpoint(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Recon")
    ck = auth_cookies(u)
    # empty ledger + whatever model state is on disk → endpoint responds with the contract shape
    r = client.get("/api/execution/reconciliation", cookies=ck)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"as_of", "n_open", "n_positions", "action_items"}
    assert isinstance(body["action_items"], list)


def test_reconciliation_requires_auth(client: TestClient) -> None:
    assert client.get("/api/execution/reconciliation").status_code == 401
