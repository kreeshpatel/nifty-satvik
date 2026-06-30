"""F4 gate (hermetic) — the validation layer: CPCV splits, block bootstrap, DSR, metrics.

These are the pure, decoupled validators that score any return series (the canonical CPCV run on
the corrected universe is a CLOUD job). The carried-governance gate is pinned here: the DSR reads
``cumulative_n_trials = 79`` from the committed n_trials.json, and deflation is monotone in the
trial count. The §11-KILL re-derivation gate (harness rejects a known-dead overlay) runs on the
cloud with the canonical dataset."""
from __future__ import annotations

import math

import numpy as np
import pytest

from nq.validation import (
    BootstrapResult,
    block_bootstrap_metric,
    bootstrap_delta,
    contiguous_blocks,
    cpcv_paths,
    cpcv_splits,
    cumulative_n_trials,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    n_backtest_paths,
    n_splits,
)
from nq.validation.metrics import cagr, calmar, max_drawdown, sharpe


# ── CPCV ────────────────────────────────────────────────────────────────────────────

def test_cpcv_split_counts_and_paths():
    assert n_splits(6, 2) == math.comb(6, 2) == 15
    assert n_backtest_paths(6, 2) == 15 * 2 // 6 == 5
    splits = cpcv_splits(60, n_groups=6, n_test_groups=2)
    assert len(splits) == 15
    paths = cpcv_paths(splits, 6)
    assert len(paths) == 5 and all(len(p) == 6 for p in paths)   # each path covers all 6 groups


def test_cpcv_purge_and_embargo_remove_adjacent_train():
    # one test block; horizon/embargo must drop the obs straddling the boundary
    splits = cpcv_splits(100, n_groups=10, n_test_groups=1, horizon=5, embargo=5)
    s = next(sp for sp in splits if sp.test_groups == (5,))   # test block = [50, 60)
    train = set(s.train_idx)
    assert set(range(50, 60)).isdisjoint(train)               # test obs never in train
    assert set(range(45, 50)).isdisjoint(train)               # purged: labels reaching into block
    assert set(range(60, 65)).isdisjoint(train)               # embargoed: obs right after block
    assert 44 in train and 65 in train                        # just outside the purge/embargo band


def test_cpcv_embargo_below_horizon_warns():
    with pytest.warns(UserWarning, match="embargo"):
        cpcv_splits(100, n_groups=10, n_test_groups=1, horizon=10, embargo=0)


def test_contiguous_blocks():
    assert contiguous_blocks([3, 4, 5, 8, 9]) == [(3, 5), (8, 9)]
    assert contiguous_blocks([]) == []


# ── DSR ─────────────────────────────────────────────────────────────────────────────

def test_dsr_reads_carried_n_trials():
    assert cumulative_n_trials() == 79          # the carried governance denominator


def test_dsr_monotonic_in_trials_and_bounds():
    # more trials -> a fixed Sharpe is less significant (lower DSR)
    args = dict(n_observations=2000, skewness=-0.3, kurtosis=5.0)
    dsr_1 = deflated_sharpe_ratio(0.12, n_trials=1, **args)
    dsr_79 = deflated_sharpe_ratio(0.12, n_trials=79, **args)
    assert 0.0 <= dsr_79 <= dsr_1 <= 1.0
    # expected max Sharpe rises with trials; 1 trial -> 0
    assert expected_max_sharpe(1) == 0.0
    assert expected_max_sharpe(79) > expected_max_sharpe(10) > 0.0


def test_dsr_degenerate_inputs_nan():
    assert math.isnan(deflated_sharpe_ratio(0.1, n_observations=1, n_trials=10))


# ── Block bootstrap ───────────────────────────────────────────────────────────────────

def _ar1(n, seed, phi=0.1, mu=0.0005, sd=0.012):
    rng = np.random.default_rng(seed)
    e = rng.normal(0, sd, n)
    r = np.empty(n)
    r[0] = mu + e[0]
    for i in range(1, n):
        r[i] = mu + phi * (r[i - 1] - mu) + e[i]
    return r


def test_block_bootstrap_ci_brackets_point_and_is_deterministic():
    r = _ar1(800, seed=1)
    res = block_bootstrap_metric(r, sharpe)
    assert isinstance(res, BootstrapResult)
    assert res.block_size == 63 and res.n_samples == 5000
    assert res.lower <= res.point <= res.upper
    # deterministic with the fixed default seed
    assert block_bootstrap_metric(r, sharpe).lower == res.lower


def test_block_bootstrap_rejects_bad_block():
    with pytest.raises(ValueError):
        block_bootstrap_metric(_ar1(50, 1), sharpe, block_size=100)


def test_bootstrap_delta_detects_a_real_edge():
    # arm A strictly dominates arm B by a constant daily increment -> ΔSharpe CI low > 0
    base = _ar1(1000, seed=2)
    a, b = base + 0.0015, base
    res = bootstrap_delta(a, b, sharpe, n_samples=2000)
    assert res.point > 0 and res.lower > 0


# ── Metrics ───────────────────────────────────────────────────────────────────────────

def test_metrics_known_values():
    # 504 equity points = 2 years (years = n/252); doubling -> CAGR = sqrt(2) - 1
    eq = np.geomspace(1.0, 2.0, 504)
    assert cagr(eq) == pytest.approx(math.sqrt(2.0) - 1.0, rel=1e-9)
    assert max_drawdown(eq) == pytest.approx(0.0, abs=1e-12)      # monotone -> no drawdown
    assert math.isnan(sharpe(np.zeros(20)))                      # zero dispersion -> NaN Sharpe
    assert sharpe(np.full(252, 0.001) + np.geomspace(1e-4, 2e-4, 252)) > 0   # real drift -> finite +ve
    # a curve with a dip has negative drawdown and finite calmar
    eq2 = np.array([100.0, 110, 99, 120, 130])
    assert max_drawdown(eq2) < 0 and np.isfinite(calmar(eq2))
