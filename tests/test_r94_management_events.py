"""The management-event stream: it must record what was DONE to a position, and change nothing.

Added 2026-09-27 (06_habit_ledger_spec.md §1.3). `curve` says what the book was worth, `position_log`
says what it held, and until now nothing said what happened to a position between entry and exit.
Partial bookings and stop ratchets were a declared hole in `collect_attribution_ledger.DECLARED_HOLES`;
0146 found the capital book had realised money five times while closing once, and could not say from any
artifact what those events were.

**This data cannot be backfilled.** A weekly position snapshot cannot be differentiated back into
events: the fraction and the fill price are gone by the next Saturday. That is why the stream lands now.

The same two properties as `position_log`, in the same order of importance:
  1. it changes NOTHING — asserted by differencing two runs of the same engine, and mutation-tested;
  2. it reconciles — a booked fraction must match the drop in `frac_left`, and a ratchet must only ever
     raise a stop.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# the live scaled exit, so the tranche path this stream exists to record is actually exercised
LIVE_SCALED = dict(scaled_exit=dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0,
                                   pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0))


@pytest.fixture(scope="module")
def runs():
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import synth_universe

    ohlcv, _index = synth_universe()
    prep = R94.prep_weekly_rank(ohlcv)

    def go(events):
        ledger: list = []
        out = R94.backtest(prep, None, ledger=ledger, ext_cap=0.20, max_risk_pct=0.10,
                           max_notional_pct=0.20, event_log=events, **LIVE_SCALED)
        return out, ledger

    off_out, off_led = go(None)
    ev: list = []
    on_out, on_led = go(ev)
    return {"off": (off_out, off_led), "on": (on_out, on_led), "events": ev}


def _blob(out: dict, ledger: list) -> str:
    return json.dumps({"out": out, "ledger": ledger}, sort_keys=True, default=str)


def test_the_event_log_changes_nothing(runs):
    """The property that matters on a live book. Observation only: rows go to a caller-owned list."""
    assert _blob(*runs["on"]) == _blob(*runs["off"]), (
        "the management-event stream altered the engine's output — that is a defect in the emitter, "
        "not a configuration choice")


def test_the_stream_actually_recorded_something(runs):
    """A guard that passes because nothing ran is the failure mode this file exists to avoid."""
    ev = runs["events"]
    assert ev, "no management events recorded — the fixture exercised no tranche, ratchet or trail"
    required = {"event_seq", "trade_id", "ticker", "entry_date", "event_date", "event_type",
                "price", "fraction", "stop_before", "stop_after", "frac_left_after",
                "shares_after", "reason_code"}
    assert required <= set(ev[0]), f"missing fields: {required - set(ev[0])}"


def test_every_event_identifies_its_trade(runs):
    """Without a trade_id the stream is a pile of prices. It is the spec's foreign key."""
    for e in runs["events"]:
        assert e["trade_id"] == f"{e['ticker']}:{e['entry_date']}"
        assert e["entry_date"] and e["entry_date"] <= e["event_date"], e


def test_the_sequence_is_dense_and_monotonic(runs):
    seqs = [e["event_seq"] for e in runs["events"]]
    assert seqs == sorted(seqs)
    assert seqs == list(range(1, len(seqs) + 1)), "event_seq must be a dense 1..n ordering"


def test_a_partial_booking_matches_the_fraction_it_removed(runs):
    """The reconciliation a weekly snapshot could not give: fraction booked vs frac_left consumed."""
    by_trade: dict[str, list] = {}
    for e in runs["events"]:
        by_trade.setdefault(e["trade_id"], []).append(e)
    checked = 0
    for _tid, evs in by_trade.items():
        books = [e for e in evs if e["event_type"] == "partial_book"]
        if not books:
            continue
        # frac_left starts at 1.0 and each booking removes its own `fraction`
        running = 1.0
        for e in books:
            running = max(running - e["fraction"], 0.0)
            assert e["frac_left_after"] == pytest.approx(running, abs=1e-6), e
            assert e["fraction"] > 0, e
            assert e["price"] > 0, e
            checked += 1
    assert checked, "fixture produced no partial bookings — this assertion would be vacuous"


def test_a_ratchet_only_ever_raises_a_stop(runs):
    """A ratchet that loosened a stop would be a live risk control moving the wrong way."""
    ratchets = [e for e in runs["events"] if e["event_type"] in ("stop_ratchet", "trail_update")]
    for e in ratchets:
        assert e["stop_after"] > e["stop_before"], e
    # and an event is only emitted when the level actually moved
    assert all(e["stop_before"] != e["stop_after"] for e in ratchets)


def test_only_the_documented_event_types_appear(runs):
    """`manual_override` is deliberately absent: the engine cannot know about an owner's deviation, and
    an empty column would read as 'no overrides happened'. It stays a declared hole."""
    seen = {e["event_type"] for e in runs["events"]}
    assert seen <= {"partial_book", "stop_ratchet", "trail_update", "halt"}, seen
    assert "manual_override" not in seen


def test_shares_never_increase_within_a_holding(runs):
    """There is no `add` path in this engine, so a rising share count would mean the emitter is wrong."""
    by_trade: dict[str, list] = {}
    for e in runs["events"]:
        by_trade.setdefault(e["trade_id"], []).append(e)
    for _tid, evs in by_trade.items():
        shares = [e["shares_after"] for e in evs]
        assert shares == sorted(shares, reverse=True), f"{_tid}: shares rose across events {shares}"
