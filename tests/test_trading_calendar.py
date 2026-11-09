"""The one trading calendar: holiday Friday, Muhurat Sunday, Budget Saturday, IST/UTC boundary, run-out."""
from __future__ import annotations

import json
import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config  # noqa: E402
from nq.data import trading_calendar as C  # noqa: E402

D = date.fromisoformat


@pytest.fixture(autouse=True)
def _fresh_warning_state():
    C._warned.clear()
    yield
    C._warned.clear()


# ── (a) exchange holiday on a weekday ──────────────────────────────────────────────────────────────
def test_holiday_friday_is_not_a_regular_session_and_last_session_steps_back():
    # 2026-04-03 (Good Friday) is in NSE_HOLIDAYS
    assert "2026-04-03" in config.NSE_HOLIDAYS and D("2026-04-03").weekday() == 4
    assert not C.is_regular_session("2026-04-03") and not C.is_session("2026-04-03")
    assert C.last_session("2026-04-03", regular=True) == D("2026-04-02")
    assert C.last_session("2026-04-05") == D("2026-04-02")            # Sunday after, same answer
    assert C.next_session("2026-04-02", regular=True) == D("2026-04-06")
    # Mon, Wed, Thu (03-31 is also a listed holiday): 3 regular sessions, and the buy-window arithmetic skips the holiday
    assert len(C.sessions_between("2026-03-29", "2026-04-04", regular=True)) == 3
    assert C.add_sessions("2026-04-02", 1) == D("2026-04-06")


def test_buy_window_arithmetic_matches_the_old_helper_where_calendar_is_covered():
    from nq.strategy.long_horizon import _add_trading_days
    assert _add_trading_days(D("2026-04-02"), 2) == D("2026-04-07")
    assert _add_trading_days(D("2026-08-14"), 1) == D("2026-08-17")    # 08-15 holiday is a Saturday anyway


# ── (b) weekend special session ────────────────────────────────────────────────────────────────────
def test_muhurat_sunday_is_a_session_but_not_a_regular_one():
    assert C.is_session("2026-11-08") and not C.is_regular_session("2026-11-08")
    assert C.is_special_session("2026-11-08")
    assert C.last_session("2026-11-08") == D("2026-11-08")
    assert C.last_session("2026-11-08", regular=True) == D("2026-11-06")   # what the watched books reach
    # sessions strictly after Friday up to Sunday: 1 session, 0 regular ones
    assert len(C.sessions_between("2026-11-06", "2026-11-08")) == 1
    assert len(C.sessions_between("2026-11-06", "2026-11-08", regular=True)) == 0


def test_budget_saturday_and_observed_unknown_special_sessions():
    assert C.is_session("2025-02-01") and C.last_session("2025-02-01", regular=True) == D("2025-01-31")
    # a weekend the list does not know about is a session only when the data carries a bar for it
    assert not C.is_session("2026-12-19")
    assert C.is_session("2026-12-19", observed=["2026-12-19"])
    assert C.last_session("2026-12-20", observed=[D("2026-12-19")]) == D("2026-12-19")
    # Muhurat on a weekday that NSE lists as a holiday: a session, not a regular one
    assert C.is_session("2025-10-21") and not C.is_regular_session("2025-10-21")


def test_week_key_weekend_session_belongs_to_the_following_week():
    fri, sun, mon = "2026-11-06", "2026-11-08", "2026-11-09"
    assert C.week_key(sun) == C.week_key(mon) != C.week_key(fri)       # Muhurat Sunday -> next week
    assert C.week_key("2025-02-01") == C.week_key("2025-02-03")        # Budget Saturday -> next week
    # a weekend date that is NOT a session (the Saturday cron stamp) stays in the week that just closed
    assert C.week_key("2026-11-14") == C.week_key("2026-11-13")
    # and it agrees with the W-FRI resample the breadth-50 book uses
    import pandas as pd
    s = pd.Series(1.0, index=pd.to_datetime([fri, sun, mon, "2026-11-13"]))
    buckets = s.resample("W-FRI").count()
    assert list(buckets.values) == [1, 3]                              # sun+mon+fri(13th) in the next bucket


# ── (c) run late by a day ──────────────────────────────────────────────────────────────────────────
def test_late_run_still_resolves_the_last_session():
    # cron meant for Fri 2026-11-06 firing Sat/Sun/Mon late: last session is still well defined
    assert C.last_session("2026-11-07", regular=True) == D("2026-11-06")
    assert C.last_session("2026-11-09", regular=True) == D("2026-11-09")
    # the wall check counts one owed row on Monday after a Friday row, none on the Muhurat Sunday
    import assert_wall_advanced as W
    assert W.sessions_after("2026-11-06", "2026-11-08") == 0
    assert W.sessions_after("2026-11-06", "2026-11-09") == 1


def test_closed_flag_refuses_a_session_that_has_not_closed():
    ist = timezone(timedelta(hours=5, minutes=30))
    midday = datetime(2026, 11, 9, 11, 0, tzinfo=ist)
    after = datetime(2026, 11, 9, 16, 15, tzinfo=ist)
    assert C.last_session(midday, regular=True) == D("2026-11-09")
    assert C.last_session(midday, regular=True, closed=True) == D("2026-11-06")
    assert C.last_session(after, regular=True, closed=True) == D("2026-11-09")


# ── IST / UTC boundary ─────────────────────────────────────────────────────────────────────────────
def test_utc_evening_is_already_tomorrow_in_ist():
    # Friday 2026-11-06 20:00 UTC == Saturday 2026-11-07 01:30 IST
    t = datetime(2026, 11, 6, 20, 0, tzinfo=timezone.utc)
    assert C.to_date(t) == D("2026-11-07")
    assert C.last_session(t, regular=True) == D("2026-11-06")
    # Sunday 20:00 UTC == Monday 01:30 IST: IST Monday, but its session has not closed
    t2 = datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)
    assert C.to_date(t2) == D("2026-11-09")
    assert C.last_session(t2, regular=True, closed=True) == D("2026-11-06")
    # naive values are already-IST calendar dates and are not shifted
    assert C.to_date(datetime(2026, 11, 6, 23, 0)) == D("2026-11-06")


def test_dashboard_cron_status_uses_the_ist_day():
    src = (ROOT / "dashboard/backend/routers/signals.py").read_text(encoding="utf-8")
    assert "now_utc + timedelta(hours=5, minutes=30)" in src


# ── (d) calendar run-out ───────────────────────────────────────────────────────────────────────────
def test_calendar_runout_falls_back_to_weekdays_warns_once_and_never_raises():
    first = D(config.NSE_HOLIDAYS_COVERED_THROUGH) + timedelta(days=1)
    while first.weekday() >= 5:
        first += timedelta(days=1)
    assert not C.is_covered(first)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert C.is_regular_session(first)                       # weekday fallback, not a crash
        assert not C.is_regular_session(first + timedelta(days=(5 - first.weekday())))   # Saturday
        assert C.last_session(first + timedelta(days=2), regular=True)
        assert len(C.sessions_between(first, first + timedelta(days=7), regular=True)) == 5
        assert C.add_sessions(first, 3) == first + timedelta(days=3 if first.weekday() <= 1 else 5)
        assert C.week_key(first)
    assert len([x for x in w if issubclass(x.category, RuntimeWarning)]) == 1     # once per process
    # data-observed weekend sessions still count past the run-out
    sat = first + timedelta(days=(5 - first.weekday()))
    assert C.is_session(sat, observed=[sat])


def test_monkeypatched_short_calendar_is_honoured(monkeypatch):
    monkeypatch.setattr(config, "NSE_HOLIDAYS", set(config.NSE_HOLIDAYS) | {"2026-11-10"})
    assert not C.is_regular_session("2026-11-10")


def test_wall_staleness_check_degrades_past_the_calendar(tmp_path, capsys):
    import assert_wall_advanced as W
    hdr = "date,status,base_ret,base_nav,base_n,veto_ret,veto_nav,veto_n,drift_ret,drift_nav,drift_n,chain,hash\n"
    first = D(config.NSE_HOLIDAYS_COVERED_THROUGH) + timedelta(days=1)
    while first.weekday() >= 5:
        first += timedelta(days=1)
    prev = first - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    (tmp_path / "forward_wall.csv").write_text(
        hdr + f"{prev},ok,0.0,1000000.0,10,0.0,1000000.0,10,0.0,1000000.0,10,1.0000,deadbeef\n", encoding="utf-8")
    assert "nothing to advance to" in W.check(tmp_path, str(first))
    assert "calendar ends" in capsys.readouterr().out


# ── the 2026-11-08 incident, end to end ────────────────────────────────────────────────────────────
def _write_logger_fixture(root: Path, scan_asof: str, logged: str) -> None:
    (root / "brain").mkdir(parents=True, exist_ok=True)
    (root / "signals_today_weekly.json").write_text(json.dumps({"generated_at": scan_asof}), encoding="utf-8")
    for name in ("blend_hybrid_paper.json", "breadth50_forward.json"):
        (root / name).write_text(json.dumps({"asof": logged, "n_points": 5}), encoding="utf-8")
    (root / "signal_quality_forward.csv").write_text("a\n1\n", encoding="utf-8")


def test_check_weekly_loggers_accepts_the_last_regular_session_when_scan_is_muhurat(tmp_path, monkeypatch):
    import check_weekly_loggers as L
    monkeypatch.setattr(L, "RESULTS", tmp_path)
    monkeypatch.setattr(L, "AS_OF_COLUMN_LOGGERS", {})
    _write_logger_fixture(tmp_path, scan_asof="2026-11-08", logged="2026-11-06")
    assert L.check() == []                                           # was: red on the 2026-11-08 incident


def test_check_weekly_loggers_still_catches_a_genuinely_stale_logger(tmp_path, monkeypatch):
    import check_weekly_loggers as L
    monkeypatch.setattr(L, "RESULTS", tmp_path)
    monkeypatch.setattr(L, "AS_OF_COLUMN_LOGGERS", {})
    _write_logger_fixture(tmp_path, scan_asof="2026-11-08", logged="2026-10-30")
    assert len(L.check()) == 2 and "last regular session 2026-11-06" in L.check()[0]
    _write_logger_fixture(tmp_path, scan_asof="2026-11-06", logged="2026-11-05")   # ordinary week, a day behind
    assert len(L.check()) == 2


def test_blend_drops_special_sessions_before_intersecting():
    import pandas as pd
    idx = pd.to_datetime(["2026-11-05", "2026-11-06", "2026-11-08", "2026-11-09"])
    keep = [d for d in idx if C.is_regular_session(d)]
    assert [str(d.date()) for d in keep] == ["2026-11-05", "2026-11-06", "2026-11-09"]
