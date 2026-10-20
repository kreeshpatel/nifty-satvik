"""The holiday calendar's expiry goes red a month early, and the engine warns instead of guessing silently."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check_calendar_coverage as K  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from config import NSE_HOLIDAYS_COVERED_THROUGH as THROUGH  # noqa: E402


def test_green_well_before_expiry_and_red_inside_the_window():
    from datetime import date, timedelta
    end = date.fromisoformat(THROUGH)
    assert K.main(["--today", str(end - timedelta(days=60))]) == 0
    assert K.main(["--today", str(end - timedelta(days=K.WARN_DAYS))]) == 1
    assert K.main(["--today", str(end + timedelta(days=1))]) == 1


def test_week_closed_at_warns_past_the_calendar_and_keeps_its_answer():
    import pandas as pd
    mon = pd.Timestamp(THROUGH) + pd.Timedelta(days=1)
    while mon.weekday() != 0:
        mon += pd.Timedelta(days=1)
    with pytest.warns(RuntimeWarning, match="holiday calendar ends"):
        assert R94.week_closed_at(mon) is False
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert R94.week_closed_at(mon + pd.Timedelta(days=4)) is True, "a Friday needs no calendar"


def test_the_check_runs_after_the_weekly_commit_and_is_read_only():
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")
    assert wf.index("check_calendar_coverage.py") > wf.index("- name: Commit weekly paper state")
