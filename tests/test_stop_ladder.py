"""Cfg-gated `scaled_exit.lockin_ladder` (2026-11-03): several stop-raise steps on the live scaled exit.

Contract: absent key = byte-identical; a one-step ladder equals the existing single ratchet
(`lockin_mfe` / `lockin_at`) exactly; a two-step ladder can only raise stops relative to its first step.
Hermetic: the synthetic fixture the R94 golden master uses.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(scope="module")
def world():
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import START_FIX, synth_universe
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT
    ohlcv, index = synth_universe()
    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)
    return R94, P, dict(start=START_FIX, a_grade=R94.grade_a_entries(P), **LIVE_DISCIPLINE), LIVE_EXIT


def _run(world, **se):
    R94, P, kw, live_exit = world
    led: list = []
    exit_cfg = {**live_exit, "scaled_exit": {**live_exit["scaled_exit"], **se}}
    out = R94.backtest(P, None, ledger=led, **kw, **exit_cfg)
    return (round(float(out["curve"].iloc[-1]), 6),
            [(r["tkr"], str(r["entry_date"]), str(r["exit_date"]), round(float(r["R"]), 6)) for r in led])


def test_absent_and_empty_ladder_are_byte_identical(world):
    assert _run(world) == _run(world, lockin_ladder=())


def test_one_step_ladder_equals_single_ratchet(world):
    assert _run(world, lockin_ladder=((1.0, 0.0),)) == _run(world, lockin_mfe=1.0, lockin_at=0.0)


def test_ladder_changes_something(world):
    assert _run(world, lockin_ladder=((1.0, 0.0), (2.0, 1.0))) != _run(world)


# ratchet_peak (2026-11-13): arm the ratchets from the week's full high, not week-end-session highs
def test_ratchet_peak_absent_or_default_is_byte_identical(world):
    base = _run(world, lockin_mfe=1.0, lockin_at=0.0)
    assert base == _run(world, lockin_mfe=1.0, lockin_at=0.0, ratchet_peak="week_end")


def test_ratchet_peak_alone_changes_nothing(world):
    """With no ratchet configured the peak definition is never read."""
    assert _run(world, ratchet_peak="week_high") == _run(world)


def test_week_high_peak_arms_at_least_as_often(world):
    """The week's high is >= its last session's high, so the ratchet fires at least as often (by event count)."""
    R94, P, kw, live_exit = world

    def fired(**se):
        ev: list = []
        R94.backtest(P, None, ledger=[], event_log=ev, **kw,
                     **{**live_exit, "scaled_exit": {**live_exit["scaled_exit"], **se}})
        return sum(1 for e in ev if e.get("event_type") == "stop_ratchet")

    assert fired(lockin_mfe=1.0, lockin_at=0.0, ratchet_peak="week_high") >= fired(lockin_mfe=1.0, lockin_at=0.0) > 0
