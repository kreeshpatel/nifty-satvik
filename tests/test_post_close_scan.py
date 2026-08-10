"""The 16:30 reschedule must not manufacture a confirmation statistic.

Owner decision 2026-08-10 moved the shadow scan from 14:30 IST to 16:30 IST, weekdays. The 14:30
slot never worked — Actions drift of 49/131/132 minutes, two of three runs after the close, and a
confirmation log that never accrued a row.

The reschedule is honest but it creates one sharp edge. `_confirm` compares a prior scan's `forming`
list against that day's COMPLETED candle. If the prior scan itself ran post-close, its forming list
was DERIVED from that same completed candle, so confirmation is ~100% by tautology. The header of
run_intraday_scan.py used to say that survival rate is what "decides whether same-day entries are
ever proposed as a real trial" — so a manufactured 100% is not a cosmetic defect, it is a number
that could justify same-day buying.

These pin the exclusion, including for the legacy files that predate the `post_close` flag and which
the 2026-08 audit showed had already been firing after the close.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

IST = timezone(timedelta(hours=5, minutes=30))


def _scan():
    import run_intraday_scan
    return run_intraday_scan


def _at(h: int, m: int) -> datetime:
    return datetime(2026, 8, 10, h, m, tzinfo=IST)


# --------------------------------------------------------------------------- the clock
@pytest.mark.parametrize("h,m,expect", [
    (14, 30, False),   # the OLD slot — genuinely intraday
    (15, 29, False),   # one minute before the close
    (15, 30, True),    # the close itself
    (16, 30, True),    # the NEW slot
    (18, 42, True),    # the new slot after worst-measured drift (+132 min)
])
def test_post_close_is_read_off_the_clock(h, m, expect):
    assert _scan().is_post_close(_at(h, m)) is expect


def test_session_fraction_cannot_substitute_for_the_clock():
    """`session_fraction` clips at 1.0, so it cannot tell 15:30 from 23:00 — and would also read 1.0
    for a badly-drifted run that was *scheduled* intraday. That is why the flag is a clock read."""
    s = _scan()
    assert s.session_fraction(_at(15, 30)) == 1.0
    assert s.session_fraction(_at(23, 0)) == 1.0
    assert s.session_fraction(_at(16, 30)) == s.session_fraction(_at(20, 0))


# --------------------------------------------------------------------------- the exclusion
def _write(tmp: Path, date: str, forming, **kw) -> None:
    payload = {"ist": f"{date} 16:30", "forming": forming, "session_fraction": 1.0, **kw}
    (tmp / f"{date}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_a_post_close_prior_scan_is_excluded_from_the_confirmation_log(tmp_path, monkeypatch, capsys):
    s = _scan()
    monkeypatch.setattr(s, "OUTDIR", tmp_path)
    _write(tmp_path, "2026-08-07", [{"ticker": "ANY"}], post_close=True)

    s._confirm({}, __import__("pandas").Timestamp("2026-08-10"))

    assert not (tmp_path / "confirmation_log.csv").exists(), "a tautology must not be logged"
    assert "SKIPPED" in capsys.readouterr().out


def test_legacy_files_without_the_flag_are_inferred_from_a_saturated_fraction(tmp_path, monkeypatch,
                                                                             capsys):
    """The two 2026-08 runs that fired after the close predate `post_close` and carry
    session_fraction 1.0. They must be excluded too, or the log starts with tautological rows."""
    s = _scan()
    monkeypatch.setattr(s, "OUTDIR", tmp_path)
    _write(tmp_path, "2026-08-07", [{"ticker": "ANY"}])          # no post_close key at all
    s._confirm({}, __import__("pandas").Timestamp("2026-08-10"))
    assert not (tmp_path / "confirmation_log.csv").exists()
    assert "SKIPPED" in capsys.readouterr().out


def test_a_genuine_intraday_prior_scan_is_still_eligible(tmp_path, monkeypatch):
    """Guard the guard: the exclusion must not silently disable confirmation for every input, or a
    green suite would hide a scan that stopped measuring anything."""
    s = _scan()
    monkeypatch.setattr(s, "OUTDIR", tmp_path)
    (tmp_path / "2026-08-07.json").write_text(json.dumps(
        {"ist": "2026-08-07 14:30", "forming": [], "session_fraction": 0.83, "post_close": False}),
        encoding="utf-8")
    s._confirm({}, __import__("pandas").Timestamp("2026-08-10"))   # reaches the loop, finds nothing
    assert not (tmp_path / "confirmation_log.csv").exists()        # empty forming -> no rows, no skip


# --------------------------------------------------------------------------- the schedule itself
def test_the_workflow_is_scheduled_post_close_on_weekdays_only():
    wf = (ROOT / ".github" / "workflows" / "cron-intraday-scan.yml").read_text(encoding="utf-8")
    assert 'cron: "0 11 * * 1-5"' in wf, "16:30 IST == 11:00 UTC, Mon-Fri"
    assert "* * 6" not in wf and "* * 0" not in wf, "Saturday belongs to cron-bhanushali-scanner"


def test_saturday_still_belongs_to_the_weekly_scanner():
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")
    assert 'cron: "30 12 * * 6"' in wf, "Saturday 18:00 IST weekly-swing scanner, unchanged"
