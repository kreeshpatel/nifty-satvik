"""The Strategy Lab's replay must be the live cron's book, key for key and trade for trade.

Research scripts drifted from the cron (mem=None -> Sharpe 1.67 vs live 1.03). Two guards:
  * static: ``engine_kwargs(DEFAULT_CONFIG)`` equals the union of the cron's LIVE_* blocks;
  * dynamic: on the hermetic fixture, with a PIT membership that is actually exercised, the cron's
    kwargs and the lab's kwargs produce identical ledgers and NAV.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import run_bhanushali_cron as C  # noqa: E402
from nq.lab import runs as L  # noqa: E402

NON_ENGINE = {"start", "uncapped"}     # reporting window / mode, not part of the LIVE_* blocks


def _cron_union() -> dict:
    return {**C.LIVE_DISCIPLINE, **C.LIVE_EXIT, **C.LIVE_STALENESS}


def test_lab_default_engine_kwargs_equal_the_cron_live_blocks_key_by_key():
    lab = {k: v for k, v in L.engine_kwargs(L.DEFAULT_CONFIG).items() if k not in NON_ENGINE}
    live = _cron_union()
    assert set(lab) == set(live), f"key drift: lab-only {set(lab) - set(live)}, cron-only {set(live) - set(lab)}"
    for k in live:
        assert lab[k] == live[k], f"{k}: lab {lab[k]!r} != cron {live[k]!r}"
    assert L.DEFAULT_CONFIG["pit_membership"] is True and L.DEFAULT_CONFIG["grade_gate"] is True
    assert L.engine_kwargs(L.DEFAULT_CONFIG)["uncapped"] is False


def test_base_exit_drops_only_the_exit_block():
    base = L.engine_kwargs({"exit": "base"})
    assert "scaled_exit" not in base and base["ext_cap"] == C.LIVE_DISCIPLINE["ext_cap"]


@pytest.fixture(scope="module")
def fixture_books():
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import synth_universe
    ohlcv, _ = synth_universe()
    P = R94.prep_weekly_rank(ohlcv, **C.LIVE_PREP)
    mem = {t: [(date(2000, 1, 1), date(2100, 1, 1))] for t in ohlcv}     # every name, whole period

    def run(kw: dict):
        led: list = []
        out = R94.backtest(P, mem, ledger=led, a_grade=R94.grade_a_entries(P), **kw)
        nav = pd.Series(out["curve"], dtype=float)
        return pd.DataFrame(led), nav

    cron_kw = dict(start=L.DEFAULT_CONFIG["start"], **C.LIVE_DISCIPLINE, **C.LIVE_EXIT, **C.LIVE_STALENESS)
    return run(cron_kw), run(L.engine_kwargs(L.DEFAULT_CONFIG))


def test_replay_kwargs_reproduce_the_cron_book_on_the_fixture(fixture_books):
    (led_c, nav_c), (led_l, nav_l) = fixture_books
    assert len(led_c) > 0 and len(nav_c) > 0, "fixture produced no trades; the parity assertion is vacuous"
    pd.testing.assert_frame_equal(led_c, led_l)
    pd.testing.assert_series_equal(nav_c, nav_l)
