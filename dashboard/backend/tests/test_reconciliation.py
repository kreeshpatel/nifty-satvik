"""Stage-4b: reconciliation — model plan minus user ledger => per-user action items.

Covers the spec contract (docs/EXECUTION_CAPTURE_SPEC.md §5):
  * a model exit flag on a name the user still holds surfaces a SELL_DUE at the P-cadence severity,
  * a fully-closed model trade the user still holds surfaces a STALE_HOLD,
  * an exit the model has ALREADY BOOKED, on a name the user still holds, surfaces a MISSED_EXIT
    carrying the exit's date/price and the drift since — and supersedes the weaker duplicates,
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


# ── MISSED_EXIT — the "you didn't get out at your stop" line ─────────────────

MISSED = "GESHIP__2026-07-27"       # the model booked this exit; the user still holds the shares


def _monitor_with_missed(**over):
    row = {
        "ticker": "GESHIP", "signal_id": MISSED, "signal_date": "2026-07-27", "reason": "stop",
        "severity": "high", "cause": "the weekly close broke its stop", "due_date": "2026-08-10",
        "due_price": 1000.0, "last_close": 910.0, "drift_pct": -9.0, "r_at_exit": -1.46,
        "as_of": "2026-08-25", "source": "booked",
        "do": "The model sold GESHIP on 2026-08-10 at Rs 1,000.00 — the weekly close broke its stop. "
              "If you did not sell, you are holding a position the record is flat on: sell the "
              "remainder at market at the next open. It is still at Rs 910.00 (-9.0% vs the model's exit).",
    }
    row.update(over)
    return {"as_of": "2026-08-25", "flags": [], "missed_exits": [row]}


def test_a_booked_exit_the_user_still_holds_surfaces_a_missed_exit_with_its_numbers():
    """"You are off-plan" without a number is not an instruction — the item must carry the cost."""
    idx = recon.build_model_index({"signals": []}, _monitor_with_missed())
    items = recon.build_action_items(
        [{"signal_id": MISSED, "ticker": "GESHIP", "remaining_qty": 30}], idx)
    (it,) = [i for i in items if i["type"] == "MISSED_EXIT"]
    assert it["severity"] == "high" and it["remaining_qty"] == 30
    assert it["due_date"] == "2026-08-10" and it["due_price"] == 1000.0
    assert it["last_close"] == 910.0 and it["drift_pct"] == -9.0
    assert it["r_at_exit"] == -1.46
    assert "at the next open" in it["message"]


def test_recording_the_sell_clears_the_missed_exit():
    """Derived, not stored — the same property every other item on this surface relies on."""
    idx = recon.build_model_index({"signals": []}, _monitor_with_missed())
    held = recon.build_action_items([{"signal_id": MISSED, "ticker": "GESHIP", "remaining_qty": 30}], idx)
    assert any(i["type"] == "MISSED_EXIT" for i in held)
    sold = recon.build_action_items([{"signal_id": MISSED, "ticker": "GESHIP", "remaining_qty": 0}], idx)
    assert not any(i["type"] == "MISSED_EXIT" for i in sold)


def test_a_missed_exit_nobody_holds_raises_nothing():
    """The monitor re-prices every booked exit for everyone; only a HOLDER is off-plan."""
    idx = recon.build_model_index({"signals": []}, _monitor_with_missed())
    assert recon.build_action_items([], idx) == []


def test_missed_exit_supersedes_the_weaker_duplicates_for_the_same_position():
    """One missed sell must never render as three lines saying the same thing with less evidence."""
    envelope = {"signals": [{"ticker": "GESHIP", "signal_date": "2026-07-27",
                             "actionability": "EXIT_REQUIRED", "status": "HIT_STOP"}]}
    monitor = _monitor_with_missed()
    monitor["flags"] = [{"ticker": "GESHIP", "event": "STOP_BREACH", "severity": "high"}]
    idx = recon.build_model_index(envelope, monitor)
    items = recon.build_action_items(
        [{"signal_id": MISSED, "ticker": "GESHIP", "remaining_qty": 30}], idx)
    types = [i["type"] for i in items]
    assert types == ["MISSED_EXIT"], types


def test_a_missed_exit_matches_on_ticker_when_the_ledger_keys_a_different_episode():
    """The point of the item is that the model is FLAT on the name — a stale signal_id must not hide it."""
    idx = recon.build_model_index({"signals": []}, _monitor_with_missed())
    items = recon.build_action_items(
        [{"signal_id": "GESHIP__2026-05-04", "ticker": "GESHIP", "remaining_qty": 12}], idx)
    (it,) = [i for i in items if i["type"] == "MISSED_EXIT"]
    assert it["signal_id"] == "GESHIP__2026-05-04"      # the LEDGER's id — that is what a sell records against
    assert it["ticker"] == "GESHIP"


def test_the_most_recent_exit_wins_per_ticker():
    """An older episode's miss must not shadow the one the reader is actually carrying."""
    mon = _monitor_with_missed()
    mon["missed_exits"].append({**mon["missed_exits"][0], "signal_id": "GESHIP__2026-05-04",
                                "due_date": "2026-05-18", "due_price": 800.0})
    idx = recon.build_model_index({"signals": []}, mon)
    assert idx["missed_by_ticker"]["GESHIP"]["due_date"] == "2026-08-10"


def test_a_monitor_without_missed_exits_behaves_exactly_as_before():
    """Backward compatibility: the key is absent from every monitor file written before today."""
    envelope, monitor = _model()
    idx = recon.build_model_index(envelope, monitor)
    items = recon.build_action_items(_positions(), idx)
    assert not any(i["type"] == "MISSED_EXIT" for i in items)
    assert {"SELL_DUE", "STALE_HOLD", "UNTAKEN_BUY"} <= {i["type"] for i in items}


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
