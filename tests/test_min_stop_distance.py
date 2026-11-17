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


# ── decomposition (2026-11-17): the stop level and the target distance, separated ──
# Sizing is NOT a channel: with 2% risk and the 10% stop cap, risk sizing always asks for >= 20% of
# equity, so max_notional_pct binds on essentially every position (median weight 0.200 on the real book).
def test_stop_only_moves_the_stop_and_leaves_every_target_where_live_had_it(world):
    _, base = _run(world)
    _, a = _run(world, min_stop_pct=0.08, min_stop_mode="stop_only")
    bq = {(r["tkr"], str(r["entry_date"])): r for r in base}
    moved = 0
    for r in a:
        b = bq[(r["tkr"], str(r["entry_date"]))]
        if (b["entry"] - b["stop0"]) / b["entry"] < 0.08 - 1e-9:
            assert (r["entry"] - r["stop0"]) / r["entry"] >= 0.08 - 1e-3   # the stop moved to the floor
            moved += 1
    assert moved > 0 and len(a) == len(base)


def test_risk_basis_only_leaves_the_stop_alone(world):
    _, base = _run(world)
    _, b = _run(world, min_stop_pct=0.08, min_stop_mode="risk_basis_only")
    bq = {(r["tkr"], str(r["entry_date"])): r for r in base}
    for r in b:
        o = bq.get((r["tkr"], str(r["entry_date"])))
        if o is not None:
            assert abs(r["stop0"] - o["stop0"]) < 1e-9


def test_the_two_modes_are_off_by_default(world):
    out_b, b_led = _run(world)
    for mode in ("stop_only", "risk_basis_only"):
        out, led = _run(world, min_stop_pct=0.0, min_stop_mode=mode)
        assert out["curve"].equals(out_b["curve"]) and led == b_led


def test_the_three_arms_are_distinct_where_the_fixture_can_show_it(world):
    """widen and risk_basis_only move every target, so they must move the curve. stop_only only matters when a
    trade's outcome actually depended on the stop level, which the synthetic fixture does not contain — there its
    curve may legitimately equal live, so this asserts only what the fixture can prove."""
    base = _run(world)[0]["curve"]
    curves = {m: _run(world, min_stop_pct=0.08, min_stop_mode=m)[0]["curve"]
              for m in ("widen", "stop_only", "risk_basis_only")}
    assert not curves["widen"].equals(base)
    assert not curves["risk_basis_only"].equals(base)
    assert not curves["stop_only"].equals(curves["widen"])
