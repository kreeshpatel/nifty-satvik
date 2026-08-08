"""Tests for :mod:`nq.validation.pbo` and :mod:`nq.validation.montecarlo`.

Both tools exist to say "this looks less certain than you think", so the load-bearing tests are the
ones that pin their behaviour at the two extremes: pure noise must produce PBO near 0.5, and a
genuinely dominant configuration must produce PBO near 0. A PBO implementation that returns a
comfortable number on random data is worse than not having one.
"""
from __future__ import annotations

import numpy as np
import pytest

from nq.validation.montecarlo import (MonteCarloResult, acf, resample_equity_curve,
                                      resample_trades, suggest_block_days, trade_returns)
from nq.validation.pbo import cscv_pbo, sharpe_of

SEED = 20260807


# --------------------------------------------------------------------------- PBO
def test_pure_noise_gives_pbo_near_a_coin_flip():
    """THE calibration test. If every config is noise, the in-sample winner is random OOS."""
    rng = np.random.default_rng(SEED)
    M = rng.normal(0, 0.01, size=(1000, 12))
    res = cscv_pbo(M, n_blocks=10)
    assert 0.35 < res.pbo < 0.65, f"noise should sit near 0.5, got {res.pbo}"
    assert not res.selection_is_informative or res.pbo < 0.5


def test_a_genuinely_dominant_config_gives_low_pbo():
    """The paired positive — a real edge must be detected, or the test above proves nothing."""
    rng = np.random.default_rng(SEED)
    M = rng.normal(0, 0.01, size=(1000, 8))
    M[:, 3] += 0.004                                  # one column with a persistent real edge
    res = cscv_pbo(M, n_blocks=10)
    assert res.pbo < 0.10
    assert res.selection_is_informative
    assert max(res.winner_counts, key=res.winner_counts.get) == 3


def test_an_anti_predictive_family_gives_high_pbo():
    """Alternating-sign edges: the in-sample winner is SYSTEMATICALLY the OOS loser."""
    n, k = 800, 6
    t = np.arange(n)
    M = np.zeros((n, k))
    for j in range(k):
        flip = np.where((t // 100) % 2 == (j % 2), 1.0, -1.0)
        M[:, j] = flip * 0.004
    res = cscv_pbo(M, n_blocks=8)
    assert res.pbo > 0.6, f"anti-predictive family should exceed 0.5, got {res.pbo}"


def test_pbo_reports_its_own_shape():
    rng = np.random.default_rng(SEED)
    res = cscv_pbo(rng.normal(0, 0.01, size=(600, 5)), n_blocks=8)
    assert res.n_configs == 5 and res.n_periods == 600
    assert res.n_splits == 70                          # C(8,4)
    assert len(res.oos_ranks) == res.n_splits
    assert all(0.0 < w < 1.0 for w in res.oos_ranks)


def test_pbo_rejects_a_single_configuration():
    """PBO is about CHOOSING between configs — one column is a category error, not an edge case."""
    with pytest.raises(ValueError, match="at least 2"):
        cscv_pbo(np.random.default_rng(SEED).normal(size=(500, 1)))


def test_pbo_rejects_odd_or_tiny_block_counts_and_short_samples():
    M = np.random.default_rng(SEED).normal(size=(500, 4))
    with pytest.raises(ValueError, match="even"):
        cscv_pbo(M, n_blocks=7)
    with pytest.raises(ValueError, match="periods"):
        cscv_pbo(M[:10], n_blocks=8)


def test_sharpe_of_is_degenerate_safe():
    assert sharpe_of(np.array([])) == 0.0
    assert sharpe_of(np.full(100, 0.01)) == 0.0        # zero variance must not win by accident


# --------------------------------------------------------------------------- Monte Carlo
def _trades(rets):
    return [{"return_pct": float(r) * 100.0} for r in rets]


def test_block_resampling_finds_deeper_drawdowns_than_iid_when_losses_cluster():
    """The reason block is the default: shuffling breaks clustering and flatters the drawdown."""
    rets = np.concatenate([np.full(60, 0.02), np.full(20, -0.06), np.full(60, 0.02)])
    iid = resample_trades(_trades(rets), scheme="iid", n_paths=800, seed=SEED)
    blk = resample_trades(_trades(rets), scheme="block", block=10, n_paths=800, seed=SEED)
    assert blk.dd_p99 < iid.dd_p99, "block must expose the clustered loss run that iid destroys"


def test_observed_drawdown_is_located_in_the_distribution():
    rng = np.random.default_rng(SEED)
    rets = rng.normal(0.004, 0.03, size=300)
    res = resample_trades(_trades(rets), n_paths=600, seed=SEED)
    assert 0.0 <= res.dd_observed_pctile <= 1.0
    assert res.dd_worst <= res.dd_p99 <= res.dd_p95 <= res.dd_median <= 0.0
    assert isinstance(res.observed_was_lucky, bool)


def test_terminal_wealth_spread_is_reported():
    rng = np.random.default_rng(SEED)
    res = resample_trades(_trades(rng.normal(0.004, 0.03, size=400)), n_paths=600, seed=SEED)
    assert res.terminal_p05 < res.terminal_median < res.terminal_p95
    assert 0.0 <= res.prob_loss <= 1.0


def test_a_losing_book_reports_high_prob_loss():
    res = resample_trades(_trades(np.full(120, -0.01)), n_paths=400, seed=SEED)
    assert res.prob_loss == pytest.approx(1.0)


def test_weight_scales_drawdown():
    """`weight` is the per-name notional; getting it wrong rescales every number, so it is explicit."""
    rng = np.random.default_rng(SEED)
    t = _trades(rng.normal(0.0, 0.03, size=300))
    small = resample_trades(t, weight=0.05, n_paths=400, seed=SEED)
    big = resample_trades(t, weight=0.20, n_paths=400, seed=SEED)
    assert big.dd_median < small.dd_median


def test_resampling_is_deterministic_under_a_fixed_seed():
    rng = np.random.default_rng(SEED)
    t = _trades(rng.normal(0.003, 0.02, size=250))
    a = resample_trades(t, n_paths=300, seed=42)
    b = resample_trades(t, n_paths=300, seed=42)
    assert a.dd_p99 == b.dd_p99 and a.terminal_median == b.terminal_median


def test_too_few_trades_raises_rather_than_returning_a_confident_number():
    with pytest.raises(ValueError, match=">= 20 trades"):
        resample_trades(_trades(np.full(5, 0.01)))


def test_bad_scheme_raises():
    with pytest.raises(ValueError, match="iid.*block"):
        resample_trades(_trades(np.full(50, 0.01)), scheme="bootstrap")


def test_trade_returns_reads_the_engine_contract():
    trades = [{"return_pct": 5.0}, {"return_pct": -2.5}]
    np.testing.assert_allclose(trade_returns(trades), [0.05, -0.025])


# --------------------------------------------------------------------------- equity-curve bootstrap
def _curve(rets):
    eq = np.cumprod(1.0 + np.asarray(rets, dtype=float)) * 1_000_000.0
    return [{"date": f"d{i}", "equity": float(v)} for i, v in enumerate(eq)]


def test_block_is_read_off_the_data_not_guessed():
    """Clustered volatility must produce a LONGER block than iid noise."""
    rng = np.random.default_rng(SEED)
    iid = rng.normal(0, 0.01, 1500)
    clustered = iid.copy()
    for lo in range(200, 1400, 300):                    # sustained high-vol regimes
        clustered[lo:lo + 120] *= 5.0
    assert suggest_block_days(clustered) >= suggest_block_days(iid)


def test_block_never_goes_below_a_month():
    """A floor exists because a sub-month block cannot represent a multi-month drawdown."""
    rng = np.random.default_rng(SEED)
    assert suggest_block_days(rng.normal(0, 0.01, 1000)) >= 21


def test_equity_bootstrap_captures_a_clustered_drawdown_that_trade_shuffling_misses():
    """THE fix. A long adverse run must land inside the resampled distribution, not outside it.

    The trade-sequence bootstrap on pre-reg 0001 put the observed drawdown at the 0th percentile of
    5,000 paths — the signature of a block shorter than the dependence horizon.
    """
    rng = np.random.default_rng(SEED)
    rets = rng.normal(0.0006, 0.012, 1200)
    rets[500:640] = -0.004                              # a sustained 140-session bleed
    res = resample_equity_curve(_curve(rets), n_paths=600, seed=SEED)
    assert res.scheme == "equity_block"
    assert res.block >= 21
    assert res.dd_observed_pctile > 0.0, \
        "observed drawdown still outside the whole distribution — block is too short"


def test_equity_bootstrap_orders_its_percentiles():
    rng = np.random.default_rng(SEED)
    res = resample_equity_curve(_curve(rng.normal(0.0005, 0.012, 900)), n_paths=500, seed=SEED)
    assert res.dd_worst <= res.dd_p99 <= res.dd_p95 <= res.dd_median <= 0.0
    assert res.terminal_p05 < res.terminal_median < res.terminal_p95


def test_equity_bootstrap_needs_enough_sessions():
    with pytest.raises(ValueError, match=">= 60 sessions"):
        resample_equity_curve(_curve(np.full(30, 0.001)))


def test_acf_detects_persistence_and_ignores_noise():
    rng = np.random.default_rng(SEED)
    persistent = np.cumsum(rng.normal(0, 1, 500))       # random walk: high ACF at lag 1
    assert acf(persistent, 5)[0] > 0.8
    assert abs(acf(rng.normal(0, 1, 2000), 5)[0]) < 0.1


def test_result_is_a_frozen_dataclass():
    rng = np.random.default_rng(SEED)
    res = resample_trades(_trades(rng.normal(0.003, 0.02, size=200)), n_paths=200, seed=SEED)
    assert isinstance(res, MonteCarloResult)
    with pytest.raises(Exception):
        res.pbo = 1.0                                  # type: ignore[misc]
