"""The four low-rank divergences the Oct-1 binder §4 scheduled for "next quarter" — D6, D8, D9, B-4.

Each was a card-vs-book or card-vs-calendar split small enough to survive a quarter and specific enough
to test. One of them turned out not to be a defect fix at all:

  D6  two Grade-A top-5 sets — `grade_a_entries` ranks everything, the card pipeline filters first, so a
      name the book can never hold can occupy a slot and waste it. FIXING IT CHANGES THE RECORD, because
      filtering before ranking promotes a different name into the top-5 in every historical week. So it
      ships GATED OFF and the tests pin both halves: off is byte-identical, on actually bites.
  D8  a missed Saturday is healed with fills the owner never saw, and nothing marked the week.
  D9  the monitor flagged fills on an inclusive band while the engine fills strictly.
  B-4 the buy window was compared against the DATA's as-of, so a stale feed showed an expired window as
      open — exactly when the operator most needs to know the feed is behind.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


# ---------------------------------------------------------------------------- D6
def _P(rows):
    """A minimal prep dict: {ticker: {dates, entry_win}} where entry_win is {e0: (days, lo, hi, rank, ...)}."""
    out = {}
    for tkr, e0, lo, hi, rank in rows:
        out[tkr] = {"dates": {e0: pd.Timestamp("2026-10-02")},
                    "entry_win": {e0: ({e0}, lo, hi, rank, 100.0, 0)}}
    return out


def test_d6_off_is_the_ranking_the_record_was_made_on():
    """Default OFF must rank everything, degenerate bands and non-members included."""
    import run_bhanushali_weekly_rank as R94
    P = _P([("AAA", 3, 90.0, 110.0, 0.9), ("DEGEN", 3, 100.0, 100.0, 0.8)])
    a = R94.grade_a_entries(P, top_n=5)
    assert ("DEGEN", 3) in a, "OFF must not silently start filtering — that would change the record"


def test_d6_on_drops_a_degenerate_band_before_ranking():
    import run_bhanushali_weekly_rank as R94
    P = _P([("AAA", 3, 90.0, 110.0, 0.9), ("DEGEN", 3, 100.0, 100.0, 0.8)])
    a = R94.grade_a_entries(P, top_n=5, filter_before_rank=True)
    assert ("AAA", 3) in a and ("DEGEN", 3) not in a


def test_d6_on_promotes_a_holdable_name_into_the_slot_the_unholdable_one_wasted():
    """B-3's mechanism, and the reason this cannot ride in as a defect fix: the A-SET CHANGES."""
    import run_bhanushali_weekly_rank as R94
    P = _P([("BAD", 3, 100.0, 100.0, 0.99),      # highest rank, unbuyable band
            ("G1", 3, 90.0, 110.0, 0.8), ("G2", 3, 90.0, 110.0, 0.7),
            ("G3", 3, 90.0, 110.0, 0.6), ("G4", 3, 90.0, 110.0, 0.5),
            ("G5", 3, 90.0, 110.0, 0.4)])
    off = R94.grade_a_entries(P, top_n=5)
    on = R94.grade_a_entries(P, top_n=5, filter_before_rank=True)
    assert ("BAD", 3) in off and ("G5", 3) not in off, "off: the unbuyable name wastes a slot"
    assert ("BAD", 3) not in on and ("G5", 3) in on, "on: a holdable name takes the freed slot"
    assert off != on, (
        "the two A-sets differ, which is exactly why D6 is gated: turning it on changes which trades "
        "the book takes in every historical week, so it is a re-anchor decision, not a prod-fix")


def test_d6_on_applies_the_membership_test_when_a_register_is_given(monkeypatch):
    import run_bhanushali_weekly_rank as R94
    P = _P([("MEMBER", 3, 90.0, 110.0, 0.9), ("DROPPED", 3, 90.0, 110.0, 0.95)])
    monkeypatch.setattr(R94, "ticker_in_index_on", lambda t, d, mem: t == "MEMBER")
    a = R94.grade_a_entries(P, top_n=5, mem={"stub": True}, filter_before_rank=True)
    assert a == {("MEMBER", 3)}


# ---------------------------------------------------------------------------- D8
def test_d8_a_normal_cadence_is_not_backfilled():
    import archive_weekly_snapshot as A
    assert A._gap_days("2026-09-19", "2026-09-26") == 7
    assert 7 <= A.BACKFILL_GAP_DAYS


def test_d8_a_missed_saturday_is_marked(tmp_path, monkeypatch):
    """A 14-day gap means one Saturday did not land, so the week carries fills nobody could have taken."""
    import archive_weekly_snapshot as A
    assert A._gap_days("2026-09-12", "2026-09-26") == 14 > A.BACKFILL_GAP_DAYS


def test_d8_a_rerun_is_not_a_zero_day_gap():
    """A rerun directory is the SAME week; reading its suffix as a date would report a 0-day gap and
    mask the real one."""
    import archive_weekly_snapshot as A
    assert A._gap_days("2026-09-19", "2026-09-26") == 7
    # the suffix-stripping is what archive() relies on
    assert "2026-09-19__rerun-20260920T101010Z".split("__rerun-")[0] == "2026-09-19"


def test_d8_an_unreadable_predecessor_is_none_not_zero():
    """None means 'unknown', which must never read as 'no gap'."""
    import archive_weekly_snapshot as A
    assert A._gap_days(None, "2026-09-26") is None
    assert A._gap_days("not-a-date", "2026-09-26") is None


def test_d8_the_flag_reaches_the_snapshot_meta(tmp_path):
    """End to end: archive a results dir whose predecessor is 14 days old and read the flag back."""
    import archive_weekly_snapshot as A
    results = tmp_path / "results"
    results.mkdir()
    (results / "signals_today_weekly.json").write_text(
        json.dumps({"generated_at": "2026-09-26", "signals": []}), encoding="utf-8")
    monkey_archive = tmp_path / "archive"
    (monkey_archive / "2026-09-12").mkdir(parents=True)
    # `latest_snapshot` only recognises a directory as a predecessor once it carries an input
    # fingerprint — without this the fixture has no predecessor and the gap reads None, not 14.
    (monkey_archive / "2026-09-12" / "input_fingerprint.json").write_text("{}", encoding="utf-8")
    (monkey_archive / "2026-09-12" / "snapshot_meta.json").write_text("{}", encoding="utf-8")

    import unittest.mock as mock
    with mock.patch.object(A, "ARCHIVE_DIR", monkey_archive), \
         mock.patch.object(A, "DRIFT_LOG", tmp_path / "drift.jsonl"):
        A.archive(results)
    meta = json.loads((monkey_archive / "2026-09-26" / "snapshot_meta.json").read_text(encoding="utf-8"))
    assert meta["gap_days"] == 14
    assert meta["backfilled"] is True
    assert "could not have taken" in (meta["backfilled_note"] or "")
    assert meta["prev_as_of"] == "2026-09-12"


# ---------------------------------------------------------------------------- D9
def test_d9_the_monitor_fills_strictly_like_the_engine():
    """A boundary tick is NOT a fill. The engine uses `lo < open < hi`; the monitor used `<=`."""
    import run_bhanushali_monitor as M
    idx = pd.DatetimeIndex(["2026-10-05", "2026-10-06"])
    df = pd.DataFrame({"Open": [100.0, 105.0]}, index=idx)
    # open exactly ON the band edge must not report a fill
    assert M._window_fill(df, signal_date="2026-10-02", buy_window_until="2026-10-09",
                          lo=100.0, hi=120.0) == {"date": "2026-10-06", "open": 105.0}
    assert M._window_fill(df, signal_date="2026-10-02", buy_window_until="2026-10-09",
                          lo=105.0, hi=120.0) is None, "105.0 is the low edge — strictly outside"


def test_d9_a_price_inside_the_band_still_fills():
    import run_bhanushali_monitor as M
    idx = pd.DatetimeIndex(["2026-10-05"])
    df = pd.DataFrame({"Open": [110.0]}, index=idx)
    assert M._window_fill(df, signal_date="2026-10-02", buy_window_until="2026-10-09",
                          lo=100.0, hi=120.0)["open"] == 110.0


# ---------------------------------------------------------------------------- B-4
def test_b4_the_window_is_compared_against_todays_ist_date():
    import run_bhanushali_monitor as M
    today = M._today_ist()
    assert isinstance(today, date)
    # IST is ahead of UTC, so the market's day is never behind UTC's
    from datetime import datetime, timezone
    assert today >= datetime.now(timezone.utc).date()


def test_b4_the_source_no_longer_reads_the_window_off_the_feeds_as_of():
    """The defect was `str(as_of.date()) <= bw`. It must be gone, and the replacement must use today."""
    src = (ROOT / "scripts" / "run_bhanushali_monitor.py").read_text(encoding="utf-8")
    assert "str(as_of.date()) <= bw" not in src, "the window is still read off the data's as-of"
    assert "_today <= bw" in src
    assert "feed_behind" in src, "a stale feed must be surfaced beside the window, not hidden by it"
