"""No weekly exit is decided on a week that has not closed — and a holiday-shortened week has.

THE DEFECT (2026-09-15). The engine groups bars by ISO week and treats each group's last bar as the
weekly close. A run made on a Tuesday therefore used Tuesday's close as the weekly close, and the
2026-09-15 manual scan published six "Weekly close below the stop — SELL at Monday's open" cards from
it (ASTERDM 741.25 against a 745.05 stop, LTF 296.80 against 297.50, ...). Signals already refused a
partial week; exits never did.

THE FIX. `prep_weekly_rank(complete_weeks_only=True)` (the cron's LIVE_PREP) drops the open week's last
bar from the weekly-close set. "Open" is holiday-aware (`week_closed_at`): a Thursday before a Friday
exchange holiday closes its week — 2026-10-02 is one, and the Saturday 2026-10-03 scan will have data
ending on Thursday 10-01. A plain weekday rule would have deferred that week's stop exits by a week.

The tests inject a stop breach into a real held trade of the hermetic R94 golden fixture, on a Tuesday
and on the Friday of the same week, and check the queued exit both ways.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from build_r94_golden_fixture import START_FIX, synth_universe  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP  # noqa: E402

from config import NSE_HOLIDAYS, NSE_HOLIDAYS_COVERED_THROUGH  # noqa: E402


# --------------------------------------------------------------------------- the calendar test
@pytest.mark.parametrize("day, closed, why", [
    ("2026-09-11", True, "a Friday closes its week"),
    ("2026-09-15", False, "the Tuesday of the incident: three sessions remain"),
    ("2026-09-17", False, "an ordinary Thursday: Friday still trades"),
    ("2026-10-01", True, "Thursday before the Gandhi Jayanti Friday holiday"),
    ("2026-04-02", True, "Thursday before Good Friday"),
    ("2026-09-30", False, "Wednesday before it: Thursday 10-01 still trades"),
])
def test_week_closed_at(day, closed, why):
    assert R94.week_closed_at(day) is closed, why


def test_the_holiday_cases_above_are_real_calendar_entries():
    """If the calendar is regenerated and these move, the parametrised cases stop proving anything."""
    assert {"2026-10-02", "2026-04-03"} <= NSE_HOLIDAYS
    assert "2026-10-01" not in NSE_HOLIDAYS and "2026-09-18" not in NSE_HOLIDAYS


def test_past_the_calendar_only_friday_closes_a_week():
    """Holidays past the published year are unknown; guessing would act on a partial bar."""
    thursday = pd.Timestamp(NSE_HOLIDAYS_COVERED_THROUGH) + pd.offsets.Week(weekday=3)
    assert R94.week_closed_at(thursday) is False
    assert R94.week_closed_at(thursday + pd.Timedelta(days=1)) is True
    assert R94.week_closed_at("2019-04-18") is False      # before coverage: Good Friday 2019 unknown here


# --------------------------------------------------------------------------- the engine
@pytest.fixture(scope="module")
def fixture():
    ohlcv, index = synth_universe()
    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)
    led: list = []
    R94.backtest(P, None, ledger=led, start=START_FIX, return_state=True, uncapped=True,
                 **LIVE_DISCIPLINE, **LIVE_EXIT)
    trade = next(r for r in led if r["tkr"] == "INDIG" and str(r["entry_date"])[:10] == "2017-12-18")
    return ohlcv, index, trade


def _breach_on(ohlcv, index, trade, day, **prep_kw):
    """Cut the panel at `day` and put INDIG's close there 10% under its initial stop."""
    day = pd.Timestamp(day)
    cut = {t: df[df.index <= day].copy() for t, df in ohlcv.items()}
    df = cut["INDIG"]
    assert df.index[-1] == day, f"INDIG has no bar on {day.date()}"
    px = float(trade["stop0"]) * 0.90
    df.loc[day, ["Close", "Low"]] = px
    df.loc[day, "Open"] = min(float(df.loc[day, "Open"]), float(df.loc[day, "High"]))
    P = R94.prep_weekly_rank(cut, index_provider=lambda _t: index, **prep_kw)
    out = R94.backtest(P, None, ledger=[], start=START_FIX, return_state=True, uncapped=True,
                       **LIVE_DISCIPLINE, **LIVE_EXIT)
    pos = out["open_positions"].get("INDIG")
    assert pos is not None and str(pos["rec"]["entry_date"])[:10] == "2017-12-18", \
        "the trade must still be held on the cut date for this test to prove anything"
    return P, pos


def _hold_week(trade):
    """A Tuesday and the Friday of the same week, strictly inside the hold."""
    tue = pd.Timestamp(trade["entry_date"]) + pd.Timedelta(weeks=3) + pd.Timedelta(days=1)
    assert tue.weekday() == 1 and tue + pd.Timedelta(days=3) < pd.Timestamp(trade["exit_date"])
    return tue, tue + pd.Timedelta(days=3)


def test_the_defect_a_tuesday_close_queues_a_stop_exit_without_the_guard(fixture):
    ohlcv, index, trade = fixture
    tue, _ = _hold_week(trade)
    _, pos = _breach_on(ohlcv, index, trade, tue)
    assert pos["pending"] is not None and pos["pending"][0] == "full" and pos["pending"][1].startswith("stop"), \
        f"expected the old behaviour to queue a stop exit on a Tuesday, got {pos['pending']}"


def test_with_the_live_prep_a_tuesday_close_decides_nothing(fixture):
    ohlcv, index, trade = fixture
    tue, _ = _hold_week(trade)
    P, pos = _breach_on(ohlcv, index, trade, tue, **LIVE_PREP)
    assert pos["pending"] is None, f"a partial week queued an exit: {pos['pending']}"
    assert len(P["INDIG"]["dates"]) - 1 not in P["INDIG"]["weekend"]


def test_with_the_live_prep_the_friday_close_still_stops_it_out(fixture):
    """The guard must not swallow a real weekly close."""
    ohlcv, index, trade = fixture
    _, fri = _hold_week(trade)
    _, pos = _breach_on(ohlcv, index, trade, fri, **LIVE_PREP)
    assert pos["pending"] is not None and pos["pending"][1].startswith("stop"), pos["pending"]


def test_a_suspended_names_last_week_is_closed_by_the_market_not_by_its_own_bars(fixture):
    """SUSPX stops printing mid-week in 2020. The panel has moved on, so that week closed."""
    ohlcv, index, _ = fixture
    # as_of on a Tuesday, so the panel IS inside an open week — otherwise the guard never engages and
    # this passes for the wrong reason.
    assert not R94.week_closed_at("2021-12-28")
    cut = {t: df[df.index <= "2021-12-28"] for t, df in ohlcv.items()}
    P = R94.prep_weekly_rank(cut, index_provider=lambda _t: index, **LIVE_PREP)
    live = next(t for t in P if t != "SUSPX")
    assert len(P[live]["dates"]) - 1 not in P[live]["weekend"], "guard did not engage on the open week"
    s = P["SUSPX"]
    assert pd.Timestamp(s["dates"][-1]).weekday() < 4, "fixture changed: SUSPX no longer ends mid-week"
    assert len(s["dates"]) - 1 in s["weekend"]


def test_the_live_cron_uses_the_guard():
    assert LIVE_PREP.get("complete_weeks_only") is True
