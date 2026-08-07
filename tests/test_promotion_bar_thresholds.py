"""The promotion bar itself was unpinned. Under the 2026-08-08 amendment that is now load-bearing.

`adjudicate` is where PROMOTE / UNDERPOWERED / KILL is decided for every engine in the repo — it is
deliberately engine-agnostic, taking only `{equity_curve, trades, metrics}`, which is what lets the
momentum book, the swing book and the rebalance book reach the same bar. Its seven gates are ANDed,
fail-closed, and each carries a numeric threshold.

`tests/test_stage4_research.py` asserts that `gate_pass` is the AND of the gates and that a strictly
worse candidate fails. Both are true of a bar with every threshold set to zero. A mutation probe on
2026-08-08 confirmed it: `NOISE_FLOOR` 0.3 -> 0.0 and `dsr > 0.95` -> `dsr > 0.5` leave the suite
green.

Two reasons that matters more now than it did last week:

1. The owner ruled on 2026-08-08 that **no path may be killed without a run**. Every re-test that
   rule requires will be adjudicated here. A bar that drifts makes each of those verdicts wrong in a
   direction no reader can see from the output.
2. Dropping a gate is *easier* to do than loosening one, and strictly more dangerous — `all()` over
   six gates passes more often than over seven, and nothing in the output says a gate went missing.

So this file pins the gate NAMES (a set, exactly), the default thresholds, and the fact that each
gate is a real comparison rather than a constant. It does not pin the verdicts of any study.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from nq.runner.research import NOISE_FLOOR, adjudicate
from nq.validation import metrics

# The bar as it stood when baseline_v1 and every registry verdict were adjudicated. Changing any of
# these is a governance act — record it in research/config_CHANGELOG.md and update this test in the
# same commit, so the change is visible in the diff rather than in a silently different verdict.
EXPECTED_DEFAULTS = {
    "noise_floor": 0.3,
    "sub_start": "2022-01-01",
    "fold_since_year": 2019,
    "calmar_min": 0.05,
    "turnover_max_increase": 0.30,
    "n_eff_min": 20,
}

EXPECTED_GATES = {
    "dSharpe_meaningful",
    "dCalmar_ge_0.05",
    "subperiod_2022_positive",
    "fold_pass_ge_60pct",
    "turnover_le_30pct",
    "dsr_gt_0.95",
    "n_eff_ge_20",
}


def test_noise_floor_is_the_program_standard():
    assert NOISE_FLOOR == 0.3, (
        "NOISE_FLOOR is the minimum ΔSharpe point estimate the programme calls meaningful. "
        "Lowering it promotes on smaller effects; it is not an implementation detail."
    )


@pytest.mark.parametrize("name,expected", sorted(EXPECTED_DEFAULTS.items()))
def test_adjudicate_default_thresholds(name: str, expected):
    got = inspect.signature(adjudicate).parameters[name].default
    assert got == expected, f"adjudicate(..., {name}=) default is {got!r}, expected {expected!r}"


def _flat_backtest(daily_return: float, *, n: int = 300, calmar: float, turnover: float) -> dict:
    """A synthetic backtest with a known constant daily return. Constant returns give zero
    dispersion, so the bootstrap cannot manufacture a spurious ΔSharpe — the point here is the gate
    plumbing, not the statistics."""
    equity, e = [], 1_000_000.0
    for i in range(n):
        e *= (1.0 + daily_return)
        equity.append({"date": f"{2017 + i // 250}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                       "equity": e})
    return {
        "equity_curve": equity,
        "trades": [],
        "metrics": {"calmar": calmar, "turnover_per_year": turnover},
        "daily_returns": np.full(n, daily_return),
    }


def test_the_gate_set_is_exactly_these_seven():
    """A dropped gate loosens the bar without changing a single number in the output."""
    base = _flat_backtest(0.0004, calmar=0.5, turnover=1.0)
    cand = _flat_backtest(0.0005, calmar=0.6, turnover=1.1)
    res = adjudicate(base, cand, n_trials=2, n_samples=50, seed=1)
    got = set(res["gates"])
    assert got == EXPECTED_GATES, (
        f"gate set changed.\n  added:   {sorted(got - EXPECTED_GATES)}\n"
        f"  removed: {sorted(EXPECTED_GATES - got)}\n"
        f"Removing a gate makes `all(gates.values())` easier to satisfy and is invisible in the "
        f"verdict. Adding one is fine, but say so in the changelog."
    )
    assert res["gate_pass"] is all(res["gates"].values())


def test_the_verdict_vocabulary_is_the_three_the_programme_uses():
    base = _flat_backtest(0.0005, calmar=0.6, turnover=1.0)
    cand = _flat_backtest(0.0002, calmar=0.1, turnover=2.0)
    res = adjudicate(base, cand, n_trials=2, n_samples=50, seed=1)
    assert res["verdict"] in {"PROMOTE-CANDIDATE", "UNDERPOWERED", "KILL"}


def test_a_strictly_worse_candidate_cannot_promote():
    """Fail-closed, restated as a property rather than a fixture: worse on every axis must not
    pass, whatever the thresholds happen to be."""
    base = _flat_backtest(0.0006, calmar=0.8, turnover=1.0)
    cand = _flat_backtest(0.0001, calmar=0.05, turnover=3.0)
    res = adjudicate(base, cand, n_trials=2, n_samples=50, seed=1)
    assert res["gate_pass"] is False
    assert res["gates"]["dCalmar_ge_0.05"] is False
    assert res["gates"]["turnover_le_30pct"] is False


# ------------------------------------------------------------------ the validation annualiser
def test_validation_trading_days_is_252():
    """`nq.validation.metrics.TRADING_DAYS` is a SECOND annualiser, distinct from the
    golden-pinned `nq.engine.portfolio.TRADING_DAYS`. This one feeds `block_bootstrap_metric`,
    `_fold_pass`, `bootstrap_delta` and the `base_sharpe`/`candidate_sharpe` that `adjudicate`
    reports — i.e. every promote/kill number — and a 252 -> 260 change was verified silent across
    the whole suite. The function's own docstring calls a frequency mismatch 'the single
    highest-consequence error here'."""
    assert metrics.TRADING_DAYS == 252


def test_sharpe_scales_by_sqrt_periods():
    """Hand-derived: mean 0.001, population std 0.001 over an alternating series gives a daily
    ratio of 1.0, so the annualised value is exactly sqrt(periods)."""
    r = np.array([0.002, 0.0] * 200)
    assert metrics.sharpe(r) == pytest.approx(np.sqrt(252), rel=1e-9)
    assert metrics.sharpe(r, periods=52) == pytest.approx(np.sqrt(52), rel=1e-9)
    assert metrics.sharpe(r, periods=260) != pytest.approx(metrics.sharpe(r), rel=1e-6), (
        "the annualiser is not being applied — a frequency change produced the same Sharpe"
    )


def test_sharpe_is_nan_without_dispersion_not_zero():
    """Fail-closed at the statistic level: a flat series has no risk-adjusted return to report, and
    returning 0.0 would silently pass a `> noise_floor` comparison as False rather than as unknown."""
    assert np.isnan(metrics.sharpe(np.zeros(100)))
