"""Strategy Lab ensemble — seeded determinism, paired draws, the no-op pair, the CUT assertion.

Runs the REAL engine on the hermetic synthetic fixture (closed-form paths, no network, no live cache) with a
tiny ``n`` so it is fast. The fixture spans 2015-2021, so the default 2019 window and `REPORT_FROM` apply.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.lab import ensemble as E  # noqa: E402
from nq.lab import runs as L  # noqa: E402

N = 3


@pytest.fixture(scope="module")
def ctx():
    from build_r94_golden_fixture import synth_universe
    ohlcv, _ = synth_universe()
    mem = {t: [(pd.Timestamp("2000-01-01").date(), pd.Timestamp("2100-01-01").date())] for t in ohlcv}
    return E.prepare_context(ohlcv, mem=mem, demerger_rows=[])


@pytest.fixture(scope="module")
def live(ctx):
    return E.replay_ensemble(None, n=N, seed=7, context=ctx)


def test_seed_determinism(ctx, live):
    again = E.replay_ensemble(None, n=N, seed=7, context=ctx)
    pd.testing.assert_frame_equal(live["paths"], again["paths"])
    pd.testing.assert_frame_equal(live["draws"], again["draws"])
    other = E.draw_perturbations(N, 8)
    assert not other["cost_delta"].equals(live["draws"]["cost_delta"])


def test_the_ensemble_actually_trades_and_perturbs(live):
    p = live["paths"]
    assert (p["trades"] > 0).all(), "fixture produced no trades; every assertion here would be vacuous"
    assert p["cost_delta"].abs().max() > 0 and p["start"].nunique() >= 1
    assert np.isfinite(p["sharpe"]).all()
    assert set(live["summary"]) >= {"sharpe", "cagr", "maxdd", "trades"}
    s = live["summary"]["sharpe"]
    assert s["p5"] <= s["median"] <= s["p95"]


def test_draws_are_config_independent_so_pairs_share_them(ctx, live):
    other = E.replay_ensemble({"ext_cap": None}, n=N, seed=7, context=ctx)
    pd.testing.assert_frame_equal(live["draws"], other["draws"])
    cmp_ = E.compare_ensembles(live, other)
    assert cmp_["n_paired"] == N
    assert list(cmp_["paths"].columns[:2]) == ["path", "d_sharpe"]
    with pytest.raises(ValueError, match="drawn identically"):
        E.compare_ensembles(live, E.replay_ensemble(None, n=N, seed=8, context=ctx))


def test_a_noop_pair_has_zero_differences(ctx, live):
    twin = E.replay_ensemble(dict(L.DEFAULT_CONFIG), n=N, seed=7, context=ctx)
    c = E.compare_ensembles(live, twin)
    for col in ("d_sharpe", "d_cagr", "d_maxdd", "d_trades"):
        assert (c["paths"][col] == 0).all(), col
    assert c["summary"]["sharpe"]["median"] == 0 and c["summary"]["sharpe"]["p5"] == 0
    assert c["share_better"] == 0.0 and c["robust"] is False


def test_cost_jitter_changes_the_book_and_restores_the_engine(ctx):
    R94 = L._engine()[0]
    orig = R94._cost_leg
    base = E.run_path(None, ctx, cost_delta=0.0)
    hi = E.run_path(None, ctx, cost_delta=0.0010)
    assert R94._cost_leg is orig, "cost jitter leaked out of its context manager"
    assert hi["cagr"] != base["cagr"]
    again = E.run_path(None, ctx, cost_delta=0.0)
    assert again == base, "an unperturbed run must be reproducible after a jittered one"


def test_start_draws_stay_in_the_first_20_trading_days_and_ties_are_refused():
    d = E.draw_perturbations(50, 1)
    days = {str(x.date()) for x in pd.bdate_range("2019-01-01", periods=20)}
    assert set(d["start"]) <= days and len(set(d["start"])) > 1
    assert d["cost_delta"].abs().max() <= 0.0010
    assert (E.draw_perturbations(5, 1, ("start",))["cost_delta"] == 0).all()
    with pytest.raises(ValueError, match="total order"):
        E.draw_perturbations(5, 1, ("cost", "ties"))


def test_the_cut_is_asserted():
    from build_r94_golden_fixture import synth_universe
    ohlcv, _ = synth_universe()
    t = next(iter(ohlcv))
    tail = ohlcv[t].iloc[[-1] * 5].copy()
    tail.index = pd.bdate_range("2024-07-01", periods=5)           # bars inside the SEALED slice
    ohlcv = {**ohlcv, t: pd.concat([ohlcv[t], tail])}
    mem = {k: [(pd.Timestamp("2000-01-01").date(), pd.Timestamp("2100-01-01").date())] for k in ohlcv}
    c = E.prepare_context(ohlcv, mem=mem, demerger_rows=[])
    assert pd.Timestamp(c.last_bar) <= pd.Timestamp(L.CUT), "post-CUT bars were not cut"
    assert max(pd.Timestamp(s["dates"][-1]) for s in c.P.values()) <= pd.Timestamp(L.CUT)
    c.last_bar = pd.Timestamp("2024-07-05")                         # a context that somehow carries sealed data
    with pytest.raises(L.CutViolation):
        E.replay_ensemble(None, n=1, context=c)
