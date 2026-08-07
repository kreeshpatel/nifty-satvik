"""Tests for :mod:`nq.data.integrity` — the pre-run data gate.

Every "this is caught" assertion is paired with a "this does not false-trip" assertion. Per
``tests/test_adjustment_guard.py``: *a guard that only ever passes is indistinguishable from no
guard, and one that only ever fails gets disabled.*
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.data.integrity import (DROP_THRESHOLD, assert_min_universe, integrity_report,
                               scan_price_events, split_suspects, trades_spanning_events,
                               universe_counts)

IDX = pd.bdate_range("2024-01-01", periods=40)


def _frame(closes: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"Open": closes, "High": closes * 1.01, "Low": closes * 0.99,
                         "Close": closes, "Volume": 1e6}, index=IDX)


def _clean(price: float = 100.0) -> pd.DataFrame:
    return _frame(np.full(len(IDX), price))


def _with_split(factor: float = 4.0, at: int = 20) -> pd.DataFrame:
    """A 1:N split that was never adjusted: price divides by N and STAYS there."""
    c = np.full(len(IDX), 400.0)
    c[at:] = 400.0 / factor
    return _frame(c)


def _with_bad_tick(at: int = 20) -> pd.DataFrame:
    """A single erroneous print that recovers on the very next bar."""
    c = np.full(len(IDX), 400.0)
    c[at] = 100.0
    return _frame(c)


# --------------------------------------------------------------------------- detection
def test_unadjusted_split_is_flagged_with_its_factor():
    ev = scan_price_events({"SPLITCO": _with_split(4.0)}, demergers={})
    assert len(ev) == 1
    assert ev[0].kind == "split_suspect"
    assert ev[0].implied_factor == pytest.approx(4.0)
    assert ev[0].move == pytest.approx(-0.75)


def test_factor_roundness_separates_a_split_shape_from_a_crash_shape():
    """Reported, never used to classify — a real crash and a split are both flagged as suspects.

    A 1:4 split implies an exact 4.00; the real YESBANK 2020-03-06 collapse implied 2.28. The
    number travels with the event so a human can adjudicate against the exchange record.
    """
    split = scan_price_events({"S": _with_split(4.0)}, demergers={})[0]
    assert split.factor_roundness < 0.01

    crash = np.full(len(IDX), 100.0)
    crash[20:] = 100.0 / 2.28                    # arbitrary ratio, like a genuine collapse
    crashed = scan_price_events({"C": _frame(crash)}, demergers={})[0]
    assert crashed.factor_roundness > 0.2
    assert crashed.kind == "split_suspect", "still a suspect — roundness must not reclassify"


def test_a_clean_series_raises_nothing():
    """The paired negative: a guard that fires on everything is useless."""
    assert scan_price_events({"CLEAN": _clean()}, demergers={}) == []


def test_an_ordinary_crash_is_not_flagged():
    """-30% in a session is a market event, not a corporate action. Must not trip."""
    c = np.full(len(IDX), 100.0)
    c[20:] = 70.0
    assert scan_price_events({"CRASHCO": _frame(c)}, demergers={}) == []


def test_bad_tick_is_classified_separately_from_a_split():
    ev = scan_price_events({"TICKCO": _with_bad_tick()}, demergers={})
    assert [e.kind for e in ev] == ["bad_tick"]
    assert split_suspects({"TICKCO": _with_bad_tick()}, demergers={}) == []


def test_known_demerger_is_left_alone():
    """A value-leaving demerger is an honest discontinuity — the VEDL lesson."""
    day = str(IDX[20])[:10]
    ev = scan_price_events({"VEDL": _with_split(4.0)}, demergers={"VEDL": {day}})
    assert [e.kind for e in ev] == ["demerger"]
    assert split_suspects({"VEDL": _with_split(4.0)}, demergers={"VEDL": {day}}) == []


def test_demerger_reference_only_excuses_the_matching_date():
    """Registering a ticker must not blanket-excuse every drop it ever has."""
    ev = scan_price_events({"VEDL": _with_split(4.0)}, demergers={"VEDL": {"2099-01-01"}})
    assert [e.kind for e in ev] == ["split_suspect"]


def test_threshold_is_the_documented_minus_45_percent():
    assert DROP_THRESHOLD == -0.45
    just_under = np.full(len(IDX), 100.0)
    just_under[20:] = 56.0                       # -44% : below the bar, not an event
    assert scan_price_events({"X": _frame(just_under)}, demergers={}) == []
    just_over = just_under.copy()
    just_over[20:] = 54.0                        # -46% : an event
    assert len(scan_price_events({"X": _frame(just_over)}, demergers={})) == 1


# --------------------------------------------------------------------------- trade spanning
def _trade(entry: str, exit_: str, ticker: str = "SPLITCO", pnl: float = -1000.0, r: float = -2.0):
    return {"ticker": ticker, "entry_date": entry, "exit_date": exit_, "pnl": pnl, "r": r}


def test_trade_open_across_the_event_is_caught():
    ev = split_suspects({"SPLITCO": _with_split()}, demergers={})
    day = ev[0].date
    hit = trades_spanning_events([_trade(str(IDX[15])[:10], str(IDX[25])[:10])], ev)
    assert len(hit) == 1
    assert hit[0]["event_date"] == day


def test_trades_that_close_before_or_open_after_are_not_caught():
    """The paired negative — otherwise every trade in the name would be excluded."""
    ev = split_suspects({"SPLITCO": _with_split()}, demergers={})
    before = _trade(str(IDX[5])[:10], str(IDX[15])[:10])
    after = _trade(str(IDX[25])[:10], str(IDX[35])[:10])
    assert trades_spanning_events([before, after], ev) == []


def test_spanning_match_is_ticker_scoped():
    ev = split_suspects({"SPLITCO": _with_split()}, demergers={})
    other = _trade(str(IDX[15])[:10], str(IDX[25])[:10], ticker="SOMEONE_ELSE")
    assert trades_spanning_events([other], ev) == []


# --------------------------------------------------------------------------- universe floor
def _panel(n_names_by_year: dict[int, int]) -> pd.DataFrame:
    rows = []
    for year, n in n_names_by_year.items():
        for d in pd.bdate_range(f"{year}-01-01", f"{year}-03-31"):
            rows += [{"date": d, "ticker": f"T{i:03d}"} for i in range(n)]
    return pd.DataFrame(rows)


def test_thin_universe_raises():
    """The 2016 case: ~21 eligible names against ~490 elsewhere."""
    panel = _panel({2016: 21, 2017: 480})
    with pytest.raises(ValueError, match="universe too thin"):
        assert_min_universe(panel, floor=100)


def test_healthy_universe_passes_and_returns_counts():
    counts = assert_min_universe(_panel({2017: 480, 2018: 490}), floor=100)
    assert (counts >= 480).all()


def test_universe_counts_are_per_period_means():
    c = universe_counts(_panel({2017: 300}))
    assert len(c) == 1 and c.iloc[0] == pytest.approx(300.0)


# --------------------------------------------------------------------------- report
def test_report_is_red_when_a_trade_spans_a_suspect():
    ohlcv = {"SPLITCO": _with_split(), "CLEAN": _clean()}
    rep = integrity_report(ohlcv, trades=[_trade(str(IDX[15])[:10], str(IDX[25])[:10])])
    assert rep["overall"] == "RED"
    assert rep["trades_spanning_suspects"] == 1
    assert rep["pnl_in_spanning_trades"] == pytest.approx(-1000.0)
    assert rep["by_kind"]["split_suspect"] == 1


def test_report_is_warn_when_suspects_exist_but_no_trade_touches_them():
    rep = integrity_report({"SPLITCO": _with_split()}, trades=[])
    assert rep["overall"] == "WARN"
    assert rep["trades_spanning_suspects"] == 0


def test_report_is_ok_on_a_clean_universe():
    rep = integrity_report({"CLEAN": _clean()}, trades=[])
    assert rep["overall"] == "OK"
    assert rep["by_kind"] == {"demerger": 0, "bad_tick": 0, "split_suspect": 0}


def test_report_always_states_the_coverage_caveat():
    """INDETERMINATE is not OK — the 4-ticker reference limit must travel with the verdict."""
    rep = integrity_report({"CLEAN": _clean()}, trades=[])
    assert "4 tickers" in rep["coverage_caveat"]
    assert "INDETERMINATE" in rep["coverage_caveat"]


def test_report_is_json_serialisable():
    import json
    json.dumps(integrity_report({"SPLITCO": _with_split()}, trades=[]))
