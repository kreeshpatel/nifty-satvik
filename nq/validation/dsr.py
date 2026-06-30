"""Deflated Sharpe Ratio (DSR) — the multiple-testing / data-mining penalty.

Bailey & López de Prado (2014). Every hypothesis tested on the same history raises the bar a real
edge must clear; the DSR deflates the observed Sharpe by the expected MAXIMUM Sharpe from
``n_trials`` independent trials (and adjusts for non-normal returns). ``DSR >= 0.95`` = beats the
N-trial max at 5% significance.

The family-wise trial count is **carried**, not guessed: :func:`cumulative_n_trials` reads
``diagnostics/research/n_trials.json`` (=79, the arm-level denominator). Passing a per-run count
overstates significance — every DSR that informs a PROMOTE/KILL decision must deflate at the
cumulative count. Ported verbatim from the validated source ``src/validation/overfitting.py``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from scipy.stats import norm

from config import BASE_DIR

EULER_MASCHERONI = 0.5772156649015329
N_TRIALS_PATH = BASE_DIR / "diagnostics" / "research" / "n_trials.json"


def cumulative_n_trials(path: Path | None = None) -> int:
    """The carried family-wise trial count (``cumulative_n_trials`` in n_trials.json, = 79). Every
    DSR that informs a promotion/kill decision MUST deflate at this count, not a per-run guess."""
    p = path or N_TRIALS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return int(data["cumulative_n_trials"])


def expected_max_sharpe(n_trials: int, sharpe_variance: float = 1.0) -> float:
    """Expected maximum Sharpe from ``n_trials`` independent strategies (Bailey & López de Prado
    2014, eq. 6, extreme-value approximation). ``n_trials <= 1`` → 0."""
    if n_trials <= 1:
        return 0.0
    e = math.exp(1.0)
    g = EULER_MASCHERONI
    term = (1.0 - g) * norm.ppf(1.0 - 1.0 / n_trials) + g * norm.ppf(1.0 - 1.0 / (n_trials * e))
    return float(math.sqrt(sharpe_variance) * term)


def deflated_sharpe_ratio(
    sharpe_observed: float, n_observations: int, *,
    skewness: float = 0.0, kurtosis: float = 3.0,
    n_trials: int = 1, sharpe_variance: float = 1.0,
) -> float:
    """Deflated Sharpe Ratio — probability in [0, 1] that the observed (per-period) Sharpe exceeds
    the expected max from ``n_trials`` trials, adjusted for skew/(raw)kurtosis.

    ``sharpe_observed`` must be PER-PERIOD (de-annualize an annual SR: ``sr / √periods``).
    ``kurtosis`` is RAW (normal = 3; if you have excess kurtosis pass ``excess + 3``). Returns NaN
    for degenerate inputs (T ≤ 1, or a non-positive denominator under pathological inputs).
    """
    if n_observations <= 1:
        return float("nan")
    sr_0 = expected_max_sharpe(n_trials, sharpe_variance)
    denom_squared = (
        1.0 - skewness * sharpe_observed + ((kurtosis - 1.0) / 4.0) * sharpe_observed ** 2)
    if denom_squared <= 0.0:
        return float("nan")
    z = (sharpe_observed - sr_0) * math.sqrt(n_observations - 1) / math.sqrt(denom_squared)
    return float(norm.cdf(z))
