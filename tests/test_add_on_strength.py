"""Cfg-gated `scaled_exit.add_at_r` / `add_frac` (2026-11-13 explore): one add on strength.

Contract: absent key = byte-identical; when on, an add fires only after a Friday close at or above
+add_at_r R, at most once per trade, and never pushes a position past the live per-name notional cap.
Hermetic: the synthetic fixture the R94 golden master uses.
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
    return R94, P, dict(start=START_FIX, a_grade=R94.grade_a_entries(P), **LIVE_DISCIPLINE), LIVE_EXIT


def _run(world, **se):
    R94, P, kw, live_exit = world
    led, ev, plog = [], [], []
    exit_cfg = {**live_exit, "scaled_exit": {**live_exit["scaled_exit"], **se}}
    out = R94.backtest(P, None, ledger=led, event_log=ev, position_log=plog, **kw, **exit_cfg)
    return out, led, ev, plog


def test_absent_key_is_byte_identical(world):
    a, la, _, _ = _run(world)
    b, lb, _, _ = _run(world, add_at_r=0.0)
    assert a["curve"].equals(b["curve"]) and la == lb


def test_adds_fire_at_most_once_per_trade_and_change_the_book(world):
    base, _, _, _ = _run(world)
    out, _, ev, _ = _run(world, add_at_r=1.0, add_frac=0.5)
    adds = [e for e in ev if e["event_type"] == "add"]
    assert adds, "the fixture should contain at least one trade that closes a week above +1R"
    per_trade = pd.Series([e["trade_id"] for e in adds]).value_counts()
    assert per_trade.max() == 1
    assert not out["curve"].equals(base["curve"])


def test_an_add_never_breaks_the_notional_cap(world):
    _, _, ev, plog = _run(world, add_at_r=1.0, add_frac=0.5)
    pl = pd.DataFrame(plog)
    adds = {(e["ticker"], e["event_date"]) for e in ev if e["event_type"] == "add"}
    pl["day"] = pd.to_datetime(pl["date"]).dt.strftime("%Y-%m-%d")
    on_add = pl[[(t, d) in adds for t, d in zip(pl.tkr, pl.day)]]
    # cap is 20% of the PRIOR close's equity at the add price; allow for that day's move
    assert (on_add.notional / on_add.equity).max() <= 0.20 * 1.25
