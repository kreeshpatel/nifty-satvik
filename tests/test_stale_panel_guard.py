"""A job that RAN is not a job that produced new data.

On 2026-08-10 the weekly cron succeeded, committed, and published `generated_at: 2026-07-31` for the
ninth day running. Every control was green: the adjustment guard, the output contract, the
scheduler-health card (age_days 8.89 against overdue_after_days 9), and the commit itself. None of
them could see it, because each verifies that a STEP RAN, and the step did run — on unchanged input.

This is the missing control. It asserts the panel MOVED.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402

TODAY = str(pd.Timestamp.today().date())


# --------------------------------------------------------------------------- the guard
def test_the_2026_08_10_incident_would_now_raise():
    """The exact shape of the failure: same date out, six sessions elapsed."""
    with pytest.raises(C.StaleDataError, match="PANEL DID NOT ADVANCE"):
        C._assert_data_advanced("2026-07-31", "2026-07-31")


def test_the_message_names_the_actual_suspect():
    """A guard that fires without naming where to look costs the next reader the same day it cost
    this one."""
    with pytest.raises(C.StaleDataError) as e:
        C._assert_data_advanced("2026-07-31", "2026-07-31")
    msg = str(e.value)
    assert "min_bars" in msg and "download_ohlcv" in msg
    assert "Do NOT publish" in msg


def test_an_advancing_panel_passes():
    C._assert_data_advanced("2026-07-31", "2026-08-07")


def test_a_same_day_rerun_is_legitimate_and_does_not_raise():
    """No session has elapsed, so there is nothing to advance to. Re-running must stay safe."""
    C._assert_data_advanced(TODAY, TODAY)


def test_a_cold_checkout_with_no_prior_artifact_does_not_raise():
    C._assert_data_advanced(None, "2026-08-07")


def test_allow_stale_is_an_explicit_escape_for_offline_replay():
    C._assert_data_advanced("2026-07-31", "2026-07-31", allow_stale=True)


def test_a_regression_is_caught_too():
    """Going BACKWARDS is at least as bad as standing still."""
    with pytest.raises(C.StaleDataError):
        C._assert_data_advanced("2026-08-07", "2026-07-31")


# --------------------------------------------------------------------------- session counting
def test_sessions_after_skips_weekends():
    # 2026-08-07 is a Friday; 08-08/09 are the weekend, so Monday 08-10 is the only session.
    assert C._sessions_after("2026-08-07", "2026-08-10") == 1
    assert C._sessions_after("2026-08-07", "2026-08-09") == 0


def test_sessions_after_skips_nse_holidays():
    from config import NSE_HOLIDAYS
    hol = sorted(h for h in NSE_HOLIDAYS if "2026-" in h)
    assert hol, "no 2026 holidays in the calendar to test against"
    h = pd.Timestamp(hol[0])
    if h.weekday() < 5:                                   # only meaningful on a weekday holiday
        prev = (h - pd.Timedelta(days=1)).date().isoformat()
        assert C._sessions_after(prev, h.date().isoformat()) == 0


def test_sessions_after_is_zero_for_a_non_advancing_window():
    assert C._sessions_after("2026-08-10", "2026-08-10") == 0
    assert C._sessions_after("2026-08-10", "2026-08-01") == 0


# --------------------------------------------------------------------------- the prior read
def test_previous_generated_at_reads_the_published_envelope(tmp_path):
    (tmp_path / "signals_today_weekly.json").write_text(
        json.dumps({"generated_at": "2026-07-31"}), encoding="utf-8")
    assert C._previous_generated_at(tmp_path) == "2026-07-31"


@pytest.mark.parametrize("body", [None, "not json", "{}"])
def test_previous_generated_at_is_none_on_anything_unusable(tmp_path, body):
    if body is not None:
        (tmp_path / "signals_today_weekly.json").write_text(body, encoding="utf-8")
    assert C._previous_generated_at(tmp_path) is None


def test_the_guard_is_wired_into_the_run():
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert "_assert_data_advanced(_previous_generated_at(sd), generated_at" in src, \
        "the guard exists but nothing calls it"
