"""Cfg-gated minimum stop distance (2026-11-13 explore): min_stop_pct / min_stop_atr20 with skip or widen.

Contract: both 0 = byte-identical; skip only removes fills; widen never leaves a stop tighter than the floor.
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
    return R94, P, dict(start=START_FIX, a_grade=R94.grade_a_entries(P), **LIVE_DISCIPLINE, **LIVE_EXIT)


def _run(world, **kw):
    R94, P, base = world
    led: list = []
    out = R94.backtest(P, None, ledger=led, uncapped=True, **base, **kw)
    return out, led


def test_off_is_byte_identical(world):
    a, la = _run(world)
    b, lb = _run(world, min_stop_pct=0.0, min_stop_atr20=0.0, min_stop_mode="widen")
    assert a["curve"].equals(b["curve"]) and la == lb


def test_skip_only_removes_trades(world):
    _, base = _run(world)
    _, sk = _run(world, min_stop_pct=0.08)
    keys = {(r["tkr"], str(r["entry_date"])) for r in base}
    assert len(sk) <= len(base)
    assert all((r["tkr"], str(r["entry_date"])) in keys for r in sk)
    assert all((r["entry"] - r["stop0"]) / r["entry"] >= 0.08 - 1e-6 for r in sk)


def test_widen_respects_the_floor(world):
    _, wd = _run(world, min_stop_pct=0.08, min_stop_mode="widen")
    assert wd and all((r["entry"] - r["stop0"]) / r["entry"] >= 0.08 - 1e-3 for r in wd)   # ledger rounds entry and stop to 2 dp
