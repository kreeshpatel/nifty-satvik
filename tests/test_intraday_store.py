"""Mechanics of the intraday bar store — pagination, merge, PIT, coverage.

Hermetic: the vendor call is injected, so nothing here touches a credential or a socket.

The properties that matter are the ones whose failure would be INVISIBLE. A pager that drops a day
produces a store that looks complete. A merge that keeps a duplicated boundary bar doubles one
candle's volume in a decade of data. A `bars_strictly_before` that uses `<=` is lookahead by one bar
— which is precisely the partial-candle error the 14:30 shadow scan spent a year not escaping.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from nq.data.intraday import (PAGE_DAYS, bars_strictly_before, coverage_report, date_pages,
                              overnight_gaps, split_seam_candidates,
                              fetch_symbol, merge_pages)


def _bars(start: str, n: int, freq: str = "15min", vol: int = 100) -> list[dict]:
    idx = pd.date_range(start, periods=n, freq=freq)
    return [{"date": t, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": vol}
            for t in idx]


# --------------------------------------------------------------------------- pagination
@pytest.mark.parametrize("interval", sorted(PAGE_DAYS))
def test_no_page_exceeds_the_vendor_limit(interval):
    pages = date_pages("2017-01-01", "2026-06-30", interval)
    for a, b in pages:
        assert (b - a).days + 1 <= PAGE_DAYS[interval], f"{interval} page {a}..{b} is over the limit"


@pytest.mark.parametrize("interval", sorted(PAGE_DAYS))
def test_pages_are_contiguous_and_cover_the_span_exactly(interval):
    s, e = dt.date(2017, 1, 1), dt.date(2026, 6, 30)
    pages = date_pages(s, e, interval)
    assert pages[0][0] == s and pages[-1][1] == e
    for (_, prev_end), (next_start, _) in zip(pages, pages[1:]):
        assert next_start == prev_end + dt.timedelta(days=1), "a gap or an overlap at a page seam"


def test_a_single_day_span_is_one_page():
    assert date_pages("2026-01-05", "2026-01-05", "15minute") == [(dt.date(2026, 1, 5),) * 2]


def test_page_count_matches_the_documented_limits():
    """15-minute at 200 days/request over ~9.5 years is the number the feasibility note costed."""
    n = len(date_pages("2017-01-01", "2026-06-30", "15minute"))
    assert n == 18, f"expected 18 pages, got {n}"


def test_unknown_interval_and_reversed_span_raise():
    with pytest.raises(ValueError, match="unknown interval"):
        date_pages("2026-01-01", "2026-02-01", "7minute")
    with pytest.raises(ValueError, match="precedes start"):
        date_pages("2026-02-01", "2026-01-01", "15minute")


# --------------------------------------------------------------------------- merge
def test_merge_deduplicates_a_repeated_boundary_bar():
    """A vendor that returns the seam bar on both pages must not double its volume."""
    a = pd.DataFrame(_bars("2026-01-01 09:15", 4))
    b = pd.DataFrame(_bars("2026-01-01 10:00", 4))          # 10:00 appears in both
    out = merge_pages([a, b])
    assert len(out) == 7
    assert out["date"].is_unique and out["date"].is_monotonic_increasing
    assert out["volume"].sum() == 700, "the duplicated bar was counted twice"


def test_merge_sorts_pages_arriving_out_of_order():
    a = pd.DataFrame(_bars("2026-01-02 09:15", 3))
    b = pd.DataFrame(_bars("2026-01-01 09:15", 3))
    out = merge_pages([b, a][::-1])
    assert out["date"].is_monotonic_increasing


def test_merge_of_nothing_is_an_empty_frame_not_none():
    out = merge_pages([None, pd.DataFrame()])
    assert isinstance(out, pd.DataFrame) and out.empty and "close" in out.columns


def test_merge_rejects_a_frame_missing_columns():
    with pytest.raises(ValueError, match="missing columns"):
        merge_pages([pd.DataFrame({"date": pd.date_range("2026-01-01", periods=2)})])


# --------------------------------------------------------------------------- fetch
def test_fetch_paginates_and_rejoins():
    seen: list[tuple] = []

    def historical(token, a, b, interval):
        seen.append((a, b))
        return _bars(f"{a} 09:15", 3, freq="D")

    out = fetch_symbol(historical, 123, "2017-01-01", "2018-06-30", "15minute")
    assert len(seen) == len(date_pages("2017-01-01", "2018-06-30", "15minute"))
    assert out["date"].is_monotonic_increasing and out["date"].is_unique


def test_fetch_raises_by_default_so_a_hole_is_never_silent():
    def historical(token, a, b, interval):
        raise RuntimeError("vendor 500")

    with pytest.raises(RuntimeError, match="vendor 500"):
        fetch_symbol(historical, 1, "2017-01-01", "2018-01-01", "15minute")


def test_fetch_can_skip_a_transient_failure_when_asked():
    calls = {"n": 0}

    def historical(token, a, b, interval):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("transient")
        return _bars(f"{a} 09:15", 2, freq="D")

    out = fetch_symbol(historical, 1, "2017-01-01", "2018-06-30", "15minute", on_error="skip")
    assert len(out) > 0 and calls["n"] > 2


# --------------------------------------------------------------------------- PIT
def test_bars_strictly_before_excludes_the_forming_bar():
    """Kite stamps a candle with its OPEN time, so the 14:30 bar is still forming at 14:30.
    Including it is lookahead by one bar."""
    bars = pd.DataFrame(_bars("2026-01-01 14:00", 4))       # 14:00, 14:15, 14:30, 14:45
    out = bars_strictly_before(bars, "2026-01-01 14:30")
    assert len(out) == 2
    assert out["date"].max() == pd.Timestamp("2026-01-01 14:15")


def test_bars_strictly_before_on_empty_is_empty():
    assert bars_strictly_before(pd.DataFrame(), "2026-01-01").empty


# --------------------------------------------------------------------------- coverage
def test_coverage_measures_linkage_years_and_the_delisted_tail():
    store = {
        "RELIANCE": pd.DataFrame(_bars("2019-06-03 09:15", 5)),
        "TCS": pd.DataFrame(_bars("2020-06-03 09:15", 3)),
        "DHFL": pd.DataFrame(_bars("2019-06-03 09:15", 2)),
        "JETAIRWAYS": pd.DataFrame(),                        # present but empty -> absent
    }
    rep = coverage_report(store, ["RELIANCE", "TCS", "DHFL", "JETAIRWAYS", "ALBK"], "15minute",
                          delisted=["DHFL", "JETAIRWAYS", "ALBK"])
    assert rep.n_requested == 5 and rep.n_present == 3
    assert rep.linkage_pct == 60.0
    assert rep.empty_symbols == ("ALBK", "JETAIRWAYS")
    assert rep.delisted_present == ("DHFL",)
    assert rep.delisted_pct == pytest.approx(33.33, abs=0.01)
    assert rep.by_year == {2019: 7, 2020: 3}


def test_coverage_reports_the_delisted_tail_even_though_ADR_0015_waived_the_probe():
    """The waiver is of the build GATE, not of the measurement. A store may be survivor-biased; it
    may not be SILENTLY survivor-biased, because then a result cannot state its own status."""
    rep = coverage_report({}, ["A"], "15minute", delisted=["DHFL", "ALBK"])
    assert rep.delisted_present == () and rep.delisted_pct == 0.0
    assert "delisted 0/2" in rep.summary()


def test_coverage_of_an_empty_request_does_not_divide_by_zero():
    rep = coverage_report({}, [], "day")
    assert rep.linkage_pct == 0.0 and rep.delisted_pct == 0.0 and rep.by_year == {}


# --------------------------------------------------------------------------- corporate actions
def _daily(closes: list[float], opens: list[float] | None = None, start="2026-01-01"):
    """One session per day, two intraday bars each, so overnight_gaps has a seam to find."""
    opens = opens or closes
    rows = []
    for i, (o, c) in enumerate(zip(opens, closes)):
        day = pd.Timestamp(start) + pd.Timedelta(days=i)
        rows.append({"date": day + pd.Timedelta(hours=9, minutes=15), "open": o, "high": max(o, c),
                     "low": min(o, c), "close": (o + c) / 2, "volume": 10})
        rows.append({"date": day + pd.Timedelta(hours=15), "open": (o + c) / 2, "high": max(o, c),
                     "low": min(o, c), "close": c, "volume": 10})
    return pd.DataFrame(rows)


def test_overnight_gaps_measure_the_seam_not_an_intraday_move():
    bars = _daily(closes=[100.0, 110.0], opens=[100.0, 105.0])
    g = overnight_gaps(bars)
    assert len(g) == 1
    assert g["prev_close"].iloc[0] == pytest.approx(100.0)
    assert g["open"].iloc[0] == pytest.approx(105.0)
    assert g["ratio"].iloc[0] == pytest.approx(1.05)


def test_a_one_for_two_split_is_flagged_as_a_candidate():
    """Kite serves AS-TRADED prices, so a 1:2 split opens at half the prior close with nothing
    marking it — a -50% 'return' no strategy earned."""
    bars = _daily(closes=[100.0, 50.0], opens=[100.0, 50.0])
    out = split_seam_candidates(bars)
    assert len(out) == 1 and out["nearest_ratio"].iloc[0] == pytest.approx(0.5)


def test_a_reverse_split_is_flagged_too():
    bars = _daily(closes=[100.0, 1000.0], opens=[100.0, 1000.0])
    out = split_seam_candidates(bars)
    assert len(out) == 1 and out["nearest_ratio"].iloc[0] == pytest.approx(10.0)


def test_ordinary_sessions_are_not_flagged():
    bars = _daily(closes=[100.0, 101.0, 99.5, 103.0], opens=[100.0, 100.5, 100.0, 99.0])
    assert split_seam_candidates(bars).empty


def test_the_tolerance_is_relative_and_bounded():
    """A -47% session is a catastrophe, not a 1:2 split. Rescaling it would delete a true loss."""
    near = _daily(closes=[100.0, 50.5], opens=[100.0, 50.5])      # ratio 0.505, within 2% of 0.5
    far = _daily(closes=[100.0, 53.0], opens=[100.0, 53.0])       # ratio 0.53, 6% off
    assert len(split_seam_candidates(near)) == 1
    assert split_seam_candidates(far).empty


def test_seam_detection_is_a_candidate_list_not_a_correction():
    """A demerger produces the same seam as a split and is NOT one — the value genuinely left the
    company. Nothing here may rewrite a price; adjudication lives in adjustment_guard.KNOWN_SEAMS."""
    bars = _daily(closes=[100.0, 50.0], opens=[100.0, 50.0])
    before = bars.copy()
    split_seam_candidates(bars)
    pd.testing.assert_frame_equal(bars, before)


@pytest.mark.parametrize("bars", [None, pd.DataFrame(), _daily(closes=[100.0])])
def test_gap_helpers_are_safe_on_degenerate_input(bars):
    assert overnight_gaps(bars).empty
    assert split_seam_candidates(bars).empty
