"""The missed-exit pass — the daily "you were supposed to be out of this" recommendation.

**Why this exists.** The live book's stop is a WEEKLY-CLOSE stop executed at the next session's
open. That means the sell instruction has a shelf life of exactly one weekend: the moment the
Saturday recompute books the trade, the card leaves `signals_today_weekly.json`, and a reader who
did not sell at the Monday open is left holding a position that has vanished from the only surface
meant to instruct it. The longer the miss, the less the product said about it — precisely backwards.

`build_missed_exits` closes that by re-pricing every already-booked exit every weekday. These tests
pin the three properties that make it safe to act on:

  * it reads the RECORD's exit price and date; it never re-decides an exit,
  * it stays SILENT rather than quoting a drift it cannot compute (the stale-bar guard),
  * a sell that is due but whose open has not happened yet is NOT a miss.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_bhanushali_monitor import (  # noqa: E402
    build_missed_exits, build_missed_exits_report, build_monitor)

TODAY = pd.Timestamp("2026-08-25")


def _frame(dates: list[str], price: float, last: float | None = None) -> pd.DataFrame:
    """A daily OHLCV frame flat at `price`, with the final bar optionally moved to `last`."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    closes = [price] * len(idx)
    if last is not None:
        closes[-1] = last
    return pd.DataFrame({"Open": closes, "High": closes, "Low": closes, "Close": closes}, index=idx)


def _booked(**kw) -> dict:
    row = {"ticker": "GLENMARK", "signal_date": "2026-07-13", "status": "HIT_STOP",
           "entry": 2285.9, "close_price": 2218.0, "close_date": "2026-07-27",
           "exit_reason": "stop", "r_multiple": -0.93}
    row.update(kw)
    return row


# ── the booked record ─────────────────────────────────────────────────────────

def test_a_booked_stop_the_reader_still_holds_becomes_a_missed_exit():
    ohlcv = {"GLENMARK": _frame(["2026-07-27", "2026-08-24"], 2218.0, last=2000.0)}
    rows = build_missed_exits({}, [_booked()], ohlcv, today=TODAY)
    assert len(rows) == 1
    r = rows[0]
    assert r["ticker"] == "GLENMARK" and r["signal_id"] == "GLENMARK__2026-07-13"
    assert r["severity"] == "high"                    # a stop is the risk line, never merely "action"
    assert r["due_date"] == "2026-07-27"
    assert r["due_price"] == 2218.0                   # THE RECORD'S price, not a recomputed one
    assert r["last_close"] == 2000.0
    assert r["drift_pct"] == pytest.approx(-9.83, abs=0.01)
    assert r["source"] == "booked"
    assert "sell the remainder at market at the next open" in r["do"].lower()


def test_recovery_since_the_exit_is_reported_as_readily_as_a_loss():
    """A rule that only speaks when it flatters the model is not a rule. Drift is stated both ways."""
    ohlcv = {"GLENMARK": _frame(["2026-07-27", "2026-08-24"], 2218.0, last=2440.0)}
    (r,) = build_missed_exits({}, [_booked()], ohlcv, today=TODAY)
    assert r["drift_pct"] > 0
    assert "+10.0%" in r["do"]


def test_a_still_open_trade_is_not_a_missed_exit():
    ohlcv = {"IKS": _frame(["2026-08-24"], 1791.6)}
    active = {"ticker": "IKS", "signal_date": "2026-08-18", "status": "ACTIVE", "entry": 1830.2}
    assert build_missed_exits({}, [active], ohlcv, today=TODAY) == []


def test_an_exit_older_than_the_lookback_is_dropped():
    old = _booked(close_date="2026-01-05")
    ohlcv = {"GLENMARK": _frame(["2026-01-05", "2026-08-24"], 2218.0, last=2000.0)}
    assert build_missed_exits({}, [old], ohlcv, today=TODAY) == []


# ── the stale-bar guard ───────────────────────────────────────────────────────

def test_a_bar_older_than_the_exit_produces_silence_not_a_wrong_number():
    """The cold-cache case. If today's bar PREDATES the sell, "where it is now" is a price from
    before the sell — a confident number pointing the wrong way. Say nothing instead."""
    ohlcv = {"GLENMARK": _frame(["2026-06-29"], 2186.6)}       # cache ends before the 2026-07-27 exit
    assert build_missed_exits({}, [_booked()], ohlcv, today=TODAY) == []


def test_a_ticker_with_no_bars_at_all_is_skipped_not_crashed():
    assert build_missed_exits({}, [_booked()], {}, today=TODAY) == []


# ── the issued-but-unbooked card ──────────────────────────────────────────────

def _envelope(gen: str) -> dict:
    return {"generated_at": gen, "signals": [{
        "ticker": "CCL", "signal_date": "2026-07-06", "actionability": "EXIT_REQUIRED",
        "status": "HIT_STOP", "entry": 1200.0, "stop": 1116.2, "target": 1400.0,
        "bought_date": "2026-07-06", "current_price": 1099.0,
    }]}


def test_an_issued_sell_whose_open_has_passed_is_a_miss_priced_at_that_open():
    ohlcv = {"CCL": _frame(["2026-08-17", "2026-08-24"], 1099.0, last=1050.0)}
    (r,) = build_missed_exits(_envelope("2026-08-15"), [], ohlcv, today=TODAY)
    assert r["source"] == "issued"
    assert r["due_date"] == "2026-08-17"        # the first session at/after the deciding close
    assert r["due_price"] == 1099.0             # that session's OPEN — the engine's execution price
    # entry+stop are both on the card here, so R is reported at the exit AND now.
    assert r["r_at_exit"] == pytest.approx(-1.21, abs=0.01)
    assert r["r_now"] == pytest.approx(-1.79, abs=0.01)


def test_a_sell_due_at_todays_open_is_this_weeks_instruction_not_a_miss():
    ohlcv = {"CCL": _frame(["2026-08-24"], 1099.0)}
    assert build_missed_exits(_envelope("2026-08-22"), [], ohlcv, today=TODAY) == []


def test_the_booked_record_wins_over_the_issued_card_for_the_same_position():
    """Both sources can describe one exit. The booked price is what the record actually used."""
    env = _envelope("2026-08-15")
    hist = [_booked(ticker="CCL", signal_date="2026-07-06", close_price=1090.0,
                    close_date="2026-08-17", entry=1200.0)]
    ohlcv = {"CCL": _frame(["2026-08-17", "2026-08-24"], 1099.0, last=1050.0)}
    (r,) = build_missed_exits(env, hist, ohlcv, today=TODAY)
    assert r["source"] == "booked" and r["due_price"] == 1090.0


# ── wiring into the monitor's published output ────────────────────────────────

def test_build_monitor_publishes_missed_exits_and_flags_them():
    env = {"generated_at": "2026-08-22", "signals": [{
        "ticker": "GLENMARK", "signal_date": "2026-07-13", "status": "ACTIVE",
        "entry": 2285.9, "stop": 2100.0, "target": 2600.0, "bought_date": "2026-07-13",
        "current_price": 2000.0,
    }]}
    ohlcv = {"GLENMARK": _frame(["2026-07-27", "2026-08-24"], 2218.0, last=2000.0)}
    out = build_monitor(env, ohlcv, history=[_booked()])
    assert out["n_missed_exits"] == 1
    assert out["missed_exits"][0]["ticker"] == "GLENMARK"
    assert any(f["event"] == "MISSED_EXIT" and f["severity"] == "high" for f in out["flags"])


def test_build_monitor_without_history_is_unchanged():
    """The parameter is optional, so nothing that calls the old two-arg form can break."""
    env = {"generated_at": "2026-08-22", "signals": [{
        "ticker": "GLENMARK", "signal_date": "2026-07-13", "status": "ACTIVE",
        "entry": 2285.9, "stop": 2100.0, "target": 2600.0, "bought_date": "2026-07-13",
    }]}
    out = build_monitor(env, {"GLENMARK": _frame(["2026-08-24"], 2400.0)})
    assert out["n_missed_exits"] == 0 and out["missed_exits"] == []
    assert not any(f["event"] == "MISSED_EXIT" for f in out["flags"])


# ── the suppression counter ───────────────────────────────────────────────────
# The guard above is what makes this feature safe; it is also what can silence it. A cron whose
# download failed leaves the same empty `missed_exits` as a reader who is perfectly on-plan, and
# nothing distinguished the two. These pin that they are now different numbers.

def test_a_suppressed_exit_is_counted_not_merely_dropped():
    ohlcv = {"GLENMARK": _frame(["2026-06-29"], 2186.6)}       # cache ends before the exit
    rep = build_missed_exits_report({}, [_booked()], ohlcv, today=TODAY)
    assert rep["rows"] == []                                    # still silent on the page — correct
    (u,) = rep["unpriceable"]                                   # but never silent on the run
    assert u["ticker"] == "GLENMARK" and u["due_date"] == "2026-07-27"
    assert "predates the exit" in u["why"]                      # names the fix, not just the fault


def test_a_ticker_with_no_bars_names_that_as_the_cause():
    (u,) = build_missed_exits_report({}, [_booked()], {}, today=TODAY)["unpriceable"]
    assert u["why"] == "no daily bars cached for this ticker"


def test_a_priced_exit_is_not_also_reported_as_suppressed():
    ohlcv = {"GLENMARK": _frame(["2026-07-27", "2026-08-24"], 2218.0, last=2000.0)}
    rep = build_missed_exits_report({}, [_booked()], ohlcv, today=TODAY)
    assert len(rep["rows"]) == 1 and rep["unpriceable"] == []


def test_an_exit_outside_the_lookback_is_not_a_suppression():
    """Deliberately dropped is not the same as could-not-look — only the latter is an alarm."""
    ohlcv = {"GLENMARK": _frame(["2026-01-05"], 2218.0)}
    rep = build_missed_exits_report({}, [_booked(close_date="2026-01-05")], ohlcv, today=TODAY)
    assert rep["rows"] == [] and rep["unpriceable"] == []


def test_build_monitor_publishes_the_suppression_count_beside_the_exit_count():
    env = {"generated_at": "2026-08-22", "signals": []}
    out = build_monitor(env, {"GLENMARK": _frame(["2026-06-29"], 2186.6)}, history=[_booked()])
    assert out["n_missed_exits"] == 0                # the page correctly shows nothing …
    assert out["n_missed_unpriceable"] == 1          # … and the run says why that zero is not proof
    assert out["missed_unpriceable"][0]["ticker"] == "GLENMARK"
