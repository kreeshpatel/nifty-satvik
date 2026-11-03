"""Cfg-gated fill lever `entry_size_scale_by_week` on the live weekly engine (2026-11-02).

Scales the size of NEW entries by the ISO (year, week) of the fill date. Contract:
  * None (default) and an empty mapping are byte-identical to the unscaled run;
  * a scale of 0.0 for every week fills nothing (the freed cash stays in cash);
  * a scale of 0.5 halves the entry size of the first fill (shares), exits untouched;
  * only `.get(key, default)` is called, so a state-reading Mapping-like object works.
Runs on the hermetic synthetic fixture the R94 golden master uses.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
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
    a = R94.grade_a_entries(P)
    kw = dict(start=START_FIX, a_grade=a, **LIVE_DISCIPLINE, **LIVE_EXIT)
    return R94, P, kw


def _run(world, **extra):
    R94, P, kw = world
    led: list = []
    out = R94.backtest(P, None, ledger=led, **kw, **extra)
    return out, led


def _key(out, led):
    return (round(float(out["curve"].iloc[-1]), 6), [(r["tkr"], str(r["entry_date"]), r.get("R")) for r in led])


class _Const:
    def __init__(self, v):
        self.v = v

    def get(self, key, default=1.0):
        return self.v


def test_none_and_empty_are_byte_identical(world):
    base = _key(*_run(world))
    assert base[1], "fixture must produce trades for this test to mean anything"
    assert _key(*_run(world, entry_size_scale_by_week=None)) == base
    assert _key(*_run(world, entry_size_scale_by_week={})) == base


def test_zero_scale_fills_nothing(world):
    out, led = _run(world, entry_size_scale_by_week=_Const(0.0))
    assert led == []
    assert float(out["curve"].iloc[-1]) == pytest.approx(float(out["curve"].iloc[0]))


def test_half_scale_halves_first_entry(world):
    R94, P, kw = world
    full: list = []
    half: list = []
    R94.backtest(P, None, ledger=[], position_log=full, **kw)
    R94.backtest(P, None, ledger=[], position_log=half, entry_size_scale_by_week=_Const(0.5), **kw)
    fd = pd.DataFrame(full).sort_values(["date", "tkr"])
    f = fd.groupby("tkr").first()
    h = pd.DataFrame(half).sort_values("date").groupby("tkr").first()
    t0 = fd.iloc[0]["tkr"]          # the earliest fill: sizing equity is still the start capital in both runs
    assert t0 in h.index
    assert h.loc[t0, "shares"] == pytest.approx(0.5 * f.loc[t0, "shares"], rel=1e-6)
