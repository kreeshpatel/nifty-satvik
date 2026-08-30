"""A wall that RAN is not a wall that logged.

`cron-forward-wall` already goes red when a contracted artifact is MISSING. It could not see the
other failure: every artifact present, unchanged, and a commit announcing a daily log that was never
written. Five scheduled runs (2026-08-24 .. 2026-08-28) finished green while
`results/forward_wall.csv` still ended at 2026-08-21, because `run_paper_cron` took the `min_bars`
default on a 15-day top-up and the OHLCV cache never moved.

That cause is fixed and is now checked at every call site by `check_ohlcv_topup_contract.py`. These
tests cover the second control: whatever the cause, a wall that stops must stop the job.

Hermetic — the wall CSV is written to tmp_path; nothing reads the repo's own wall.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import assert_wall_advanced as W  # noqa: E402

HEADER = "date,status,base_ret,base_nav,base_n,veto_ret,veto_nav,veto_n,drift_ret,drift_nav,drift_n,chain,hash\n"


def _wall(tmp_path: Path, *dates: str) -> Path:
    body = "".join(f"{d},ok,0.0,1000000.0,10,0.0,1000000.0,10,0.0,1000000.0,10,1.0000,deadbeef\n"
                   for d in dates)
    (tmp_path / "forward_wall.csv").write_text(HEADER + body, encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------------- the incident
def test_the_five_session_hole_would_now_stop_the_job(tmp_path):
    """The exact shape of what shipped: wall at 2026-08-21, checked on 2026-08-28."""
    with pytest.raises(W.WallStalledError, match="WALL DID NOT ADVANCE"):
        W.check(_wall(tmp_path, "2026-08-20", "2026-08-21"), "2026-08-28")


def test_the_message_names_where_to_look(tmp_path):
    """A guard that fires without naming the suspect costs the next reader the day it cost this one."""
    with pytest.raises(W.WallStalledError) as e:
        W.check(_wall(tmp_path, "2026-08-21"), "2026-08-28")
    msg = str(e.value)
    assert "5 NSE session(s)" in msg
    assert "min_bars" in msg and "check_ohlcv_topup_contract.py" in msg
    assert "ff_india_factors.parquet" in msg          # the other real cause, from wall_cron's guard
    assert "Do NOT publish" in msg


# --------------------------------------------------------------------------- what must NOT fire
def test_a_same_day_rerun_is_legitimate(tmp_path):
    """No session has closed since the last row, so there is nothing to advance to."""
    assert "nothing to advance to" in W.check(_wall(tmp_path, "2026-08-28"), "2026-08-28")


def test_the_weekend_does_not_stall_the_wall(tmp_path):
    """Friday's row checked on Sunday. Two calendar days, zero sessions — a red here would fire
    every weekend and be muted within a month, which is worse than no guard at all."""
    assert "nothing to advance to" in W.check(_wall(tmp_path, "2026-08-28"), "2026-08-30")


def test_a_holiday_is_not_a_stall(tmp_path):
    """Counting business days alone would call a published NSE holiday a missed session."""
    hol = sorted(h for h in W.NSE_HOLIDAYS if "2026-" in h)
    assert hol, "no 2026 NSE holidays in config — this test can no longer prove anything"
    import pandas as pd
    d = pd.Timestamp(hol[0])
    prev = (d - pd.Timedelta(days=1)).date().isoformat()
    assert W.sessions_after(prev, hol[0]) == 0, f"{hol[0]} is a holiday and must not count"


def test_a_cold_start_has_nothing_to_compare(tmp_path):
    assert "cold start" in W.check(tmp_path, "2026-08-28")


def test_allow_stale_is_an_explicit_door_not_a_default(tmp_path):
    wall = _wall(tmp_path, "2026-08-21")
    with pytest.raises(W.WallStalledError):
        W.check(wall, "2026-08-28")
    assert "STALE, allowed" in W.check(wall, "2026-08-28", allow_stale=True)


# --------------------------------------------------------------------------- parsing
def test_the_header_row_is_not_read_as_a_date(tmp_path):
    """`forward_wall.csv` carries a header. Treating it as a row would compare 'date' to a date."""
    (tmp_path / "forward_wall.csv").write_text(HEADER, encoding="utf-8")
    assert "cold start" in W.check(tmp_path, "2026-08-28")


def test_it_reads_the_last_row_not_the_first(tmp_path):
    assert "no NSE session has closed" in W.check(
        _wall(tmp_path, "2026-07-01", "2026-08-14", "2026-08-28"), "2026-08-28")


def test_a_gap_marker_row_still_counts_as_a_logged_session(tmp_path):
    """The wall writes `gap` markers for missed trading days. A gap is a RECORD of a missing
    session, not a missing record — the chain moved, so the job did its job."""
    (tmp_path / "forward_wall.csv").write_text(
        HEADER + "2026-08-27,gap,,,,,,,,,,1.0000,deadbeef\n", encoding="utf-8")
    assert "nothing to advance to" in W.check(tmp_path, "2026-08-27")


# --------------------------------------------------------------------------- the calendar bound
def test_it_refuses_past_the_published_calendar(tmp_path):
    """`sessions_after` counts business days minus published holidays. Past the calendar's coverage
    that count is a guess, and this file exists to stop guesses reaching a pre-registered record."""
    from config import CalendarCoverageError, NSE_HOLIDAYS_COVERED_THROUGH
    import pandas as pd
    beyond = (pd.Timestamp(NSE_HOLIDAYS_COVERED_THROUGH) + pd.Timedelta(days=1)).date().isoformat()
    with pytest.raises(CalendarCoverageError):
        W.check(_wall(tmp_path, "2026-08-21"), beyond)
