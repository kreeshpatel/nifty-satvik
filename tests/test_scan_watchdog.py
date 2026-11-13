"""Watchdog decision logic (scripts/scan_watchdog.py). Pure: no clock, network or repo reads."""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scan_watchdog as w  # noqa: E402

UTC = timezone.utc
HOL = {"2026-11-06"}                         # synthetic Friday holiday: Thursday 11-05 closes that week


def dt(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def run(now, gen, runs=(), active=False, hol=frozenset(), special=None):
    return w.decide(now=dt(now), generated_at=gen, holidays=set(hol),
                    dispatch_run_times=[dt(r) for r in runs], scanner_active=active,
                    special={} if special is None else special)


def test_normal_saturday_unpublished_dispatches():
    d = run("2026-11-14T03:30", "2026-11-06")
    assert (d.action, d.target_session) == ("dispatch", "2026-11-13")


def test_normal_week_published_is_noop():
    assert run("2026-11-16T03:30", "2026-11-13").action == "noop"


def test_holiday_friday_target_is_thursday():
    d = run("2026-11-07T03:30", "2026-10-30", hol=HOL)
    assert (d.action, d.target_session) == ("dispatch", "2026-11-05")
    assert run("2026-11-07T03:30", "2026-11-05", hol=HOL).action == "noop"


def test_muhurat_sunday_bar_is_the_week_close():
    sp = {"2026-11-08": "Muhurat"}
    # Sunday 03:30: session not yet held -> previous week is the target
    assert run("2026-11-08T03:30", "2026-10-30", special=sp).target_session == "2026-10-30"
    # Sunday 12:00 UTC: Muhurat bars not settled yet -> still the previous week
    assert run("2026-11-08T12:00", "2026-11-06", special=sp).target_session == "2026-10-30"
    # Monday: week closed with the Sunday bar; a scan that stopped at Friday is NOT enough
    d = run("2026-11-09T03:30", "2026-11-06", special=sp)
    assert (d.action, d.target_session) == ("dispatch", "2026-11-08")
    assert run("2026-11-09T03:30", "2026-11-08", special=sp).action == "noop"


def test_weekend_is_not_a_session_without_special():
    assert not w.is_session(date(2026, 11, 8), set(), {})
    assert w.is_session(date(2026, 11, 8), set(), {"2026-11-08": "x"})


def test_attempt_cap_reached_skips():
    d = run("2026-11-16T03:30", "2026-11-06", runs=["2026-11-14T04:00", "2026-11-15T04:00"])
    assert d.action == "skip" and d.attempts == 2 and "cap" in d.reason


def test_dispatches_before_target_close_do_not_count():
    d = run("2026-11-16T03:30", "2026-11-06", runs=["2026-11-10T04:00", "2026-11-14T04:00"])
    assert d.action == "dispatch" and d.attempts == 1


def test_active_scanner_run_blocks_dispatch():
    assert run("2026-11-16T03:30", "2026-11-06", active=True).action == "skip"


def test_missing_envelope_counts_as_unpublished():
    assert run("2026-11-16T03:30", None).action == "dispatch"


def test_friday_before_close_targets_prior_week():
    d = run("2026-11-13T09:00", "2026-11-06")
    assert (d.action, d.target_session) == ("noop", "2026-11-06")
