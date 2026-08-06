"""M10 — the NSE holiday calendar is SOURCED, BOUNDED, and knows where it stops.

Three properties, each pinned because each failed silently before 2026-08-06:

1. **Sourced.** The 2026 block was hand-maintained and wrong in both directions — 10 holidays
   missing, 8 dates NSE does not list, 15 of them on weekdays. The specific dates that were
   wrong are pinned here so a regression is a test failure rather than a quiet re-drift.
2. **Bounded.** The set carries an explicit coverage window, and the bound is a real fact about
   NSE (it publishes one year at a time), not a guess.
3. **Loud past the bound.** The consumers that turn the calendar into a real-world commitment
   — the governance review date and the hash-chained forward-wall log — must not answer a
   question they cannot answer. One flags, one refuses; both are asserted.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    NSE_HOLIDAYS, NSE_HOLIDAYS_COVERED_FROM, NSE_HOLIDAYS_COVERED_THROUGH,
    CalendarCoverageError, assert_calendar_covers,
)

# Weekdays NSE's own holiday master says are TRADING days, which the old committed calendar
# listed as holidays. The three inside the pinned dataset carried 710 real positive-volume bars
# each that the cleaner was deleting; 2026-02-17 and 2026-03-30 were additionally confirmed
# present in the exchange's own bhavcopy (2,512 and 2,552 rows).
FORMERLY_SPURIOUS = [
    "2026-02-17", "2026-03-20", "2026-03-30", "2026-08-17",
    "2026-09-04", "2026-10-12", "2026-10-26", "2026-11-16",
]

# Weekday holidays NSE lists that the old calendar omitted. 2026-01-15 and 2026-03-26 were
# confirmed ABSENT from the exchange's bhavcopy.
FORMERLY_MISSING = [
    "2026-01-15", "2026-03-26", "2026-03-31",
    "2026-09-14", "2026-10-20", "2026-11-10", "2026-11-24",
]


class TestTheCalendarIsSourced:
    def test_the_spurious_holidays_are_gone(self):
        still_there = [d for d in FORMERLY_SPURIOUS if d in NSE_HOLIDAYS]
        assert not still_there, (
            f"{still_there} are TRADING days per NSE's holiday master. Listing them as holidays "
            f"makes the cleaner delete real bars — 710 per date in the pinned dataset.")

    def test_the_missing_holidays_are_present(self):
        absent = [d for d in FORMERLY_MISSING if d not in NSE_HOLIDAYS]
        assert not absent, f"{absent} are NSE holidays and must be in the calendar"

    def test_every_committed_date_parses_as_an_iso_date(self):
        for d in NSE_HOLIDAYS:
            date.fromisoformat(d)   # raises on anything malformed

    def test_the_regenerator_exists_and_does_not_write_config(self):
        """The calendar is a data input: the script emits a diff for a human, it never patches."""
        src = (ROOT / "scripts" / "build_nse_holidays.py").read_text(encoding="utf-8")
        assert "def fetch(" in src
        body = src.split('"""', 2)[-1]          # ignore the module docstring
        assert "write_text" not in body and "open(" not in body, (
            "build_nse_holidays.py must not write config.py — the diff is reviewed by a human")


class TestTheCoverageWindowIsHonest:
    def test_the_bounds_are_iso_and_ordered(self):
        assert (date.fromisoformat(NSE_HOLIDAYS_COVERED_FROM)
                < date.fromisoformat(NSE_HOLIDAYS_COVERED_THROUGH))

    def test_coverage_does_not_claim_more_than_the_calendar_holds(self):
        """THROUGH must not run past the last year the set actually carries dates for."""
        last_year = max(d[:4] for d in NSE_HOLIDAYS)
        assert NSE_HOLIDAYS_COVERED_THROUGH[:4] <= last_year

    def test_no_committed_date_falls_below_the_stated_lower_bound(self):
        assert min(NSE_HOLIDAYS) >= NSE_HOLIDAYS_COVERED_FROM


class TestItRefusesToGuess:
    def test_a_date_inside_coverage_passes(self):
        assert_calendar_covers("2026-10-01")
        assert_calendar_covers(date(2026, 12, 31))

    def test_a_date_past_coverage_raises(self):
        with pytest.raises(CalendarCoverageError):
            assert_calendar_covers(date(2027, 1, 1))

    def test_the_error_says_how_to_fix_it(self):
        with pytest.raises(CalendarCoverageError) as e:
            assert_calendar_covers("2027-04-01", what="a review date")
        msg = str(e.value)
        assert "build_nse_holidays.py" in msg and NSE_HOLIDAYS_COVERED_THROUGH in msg

    def test_the_lower_bound_is_deliberately_NOT_enforced(self):
        """Historical dates must pass: the backtest window predates the calendar entirely, and
        vendor placeholders there are caught by the cleaner's zero-volume filter instead."""
        assert_calendar_covers("2019-01-02")


class TestTheTwoCommitmentConsumers:
    def test_the_scorecard_flags_an_unverified_review_date(self):
        from bhanushali_review_scorecard import _is_verified
        assert _is_verified(date(2026, 10, 1)) is True
        assert _is_verified(date(2027, 1, 1)) is False, (
            "a review date past the published calendar is a weekends-only guess and must be "
            "flagged — the owner reads the governance cadence off this card")

    def test_the_wall_log_refuses_a_date_past_coverage(self, tmp_path):
        """Gap markers go into an append-only hash-chained log; a wrong one cannot be retracted."""
        from nq.paper.forward_wall_job import record_trading_day
        book = {"ret": 0.0, "equity": 1_000_000.0, "npos": 0}
        with pytest.raises(CalendarCoverageError):
            record_trading_day("2027-01-04", book, book, path=tmp_path / "wall.csv")

    def test_a_caller_supplying_its_own_holidays_is_exempt(self, tmp_path):
        """Passing `holidays` means the caller owns the coverage question — do not second-guess."""
        from nq.paper.forward_wall_job import record_trading_day
        book = {"ret": 0.0, "equity": 1_000_000.0, "npos": 0}
        record_trading_day("2027-01-04", book, book,
                           path=tmp_path / "wall.csv", holidays={"2027-01-01"})
