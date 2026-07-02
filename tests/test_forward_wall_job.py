"""Forward-wall daily-JOB tests — the acceptance criteria for the WIRING (forward/prereg.md §1, §3).

The chain proves the log can't lie about the past; these prove the job writes the right row: a
double-run is refused, a missed trading day becomes a gap marker, and the drift exposure multiplier
is derived from logged history and recorded (not recomputable-away by a later data revision).
"""
from __future__ import annotations

import pandas as pd
import pytest

from nq.paper.forward_wall import IntegrityError, read_verified
from nq.paper.forward_wall_job import record_trading_day


def _m(ret: float, eq: float = 1_000_000.0, npos: int = 15) -> dict:
    return {"ret": ret, "equity": eq, "npos": npos}


def test_double_run_refused(tmp_path):
    log = tmp_path / "wall.csv"
    record_trading_day("2026-07-06", _m(0.01), _m(0.01), path=log, holidays=[])   # Monday
    with pytest.raises(IntegrityError):
        record_trading_day("2026-07-06", _m(0.01), _m(0.01), path=log, holidays=[])


def test_missed_day_becomes_gap_marker(tmp_path):
    log = tmp_path / "wall.csv"
    record_trading_day("2026-07-06", _m(0.01), _m(0.01), path=log, holidays=[])   # Mon
    record_trading_day("2026-07-09", _m(0.02), _m(0.02), path=log, holidays=[])   # Thu -> Tue,Wed gap
    rows = read_verified(log)
    assert [r["status"] for r in rows] == ["ok", "gap", "gap", "ok"]
    assert [r["date"] for r in rows[1:3]] == ["2026-07-07", "2026-07-08"]
    assert rows[1]["base_ret"] == "" and rows[1]["drift_mult"] == ""   # gap carries no observation


def test_drift_mult_default_full_exposure_short_history(tmp_path):
    log = tmp_path / "wall.csv"
    record_trading_day("2026-07-06", _m(0.013), _m(1.013e6), path=log, holidays=[])
    r = read_verified(log)[-1]
    assert r["drift_mult"] == "1.0000"                      # <63d history -> full exposure
    assert abs(float(r["drift_ret"]) - 0.013) < 1e-9        # drift_ret == base_ret * 1.0


def _run_n(log, rets):
    days = pd.bdate_range("2026-01-01", periods=len(rets))
    for d, ret in zip(days, rets):
        record_trading_day(d.date().isoformat(), _m(ret), _m(ret), path=log, holidays=[])


def test_drift_degrosses_when_trailing_63d_negative(tmp_path):
    log = tmp_path / "wall.csv"
    _run_n(log, [-0.005] * 63)                              # 63 logged negative days
    record_trading_day(pd.bdate_range("2026-01-01", periods=64)[-1].date().isoformat(),
                       _m(0.02), _m(0.02), path=log, holidays=[])
    r = read_verified(log)[-1]
    assert r["drift_mult"] == "0.5000"                      # trailing-63d base return < 0 -> de-gross
    assert abs(float(r["drift_ret"]) - 0.02 * 0.5) < 1e-9   # multiplier ACTUALLY applied to the return


def test_drift_full_exposure_when_trailing_63d_positive(tmp_path):
    log = tmp_path / "wall.csv"
    _run_n(log, [0.004] * 63)                               # 63 logged positive days
    record_trading_day(pd.bdate_range("2026-01-01", periods=64)[-1].date().isoformat(),
                       _m(0.02), _m(0.02), path=log, holidays=[])
    r = read_verified(log)[-1]
    assert r["drift_mult"] == "1.0000"
