"""Deflated Sharpe Ratio (DSR) — the multiple-testing / data-mining penalty.

Bailey & López de Prado (2014). Every hypothesis tested on the same history raises the bar a real
edge must clear; the DSR deflates the observed Sharpe by the expected MAXIMUM Sharpe from
``n_trials`` independent trials (and adjusts for non-normal returns). ``DSR >= 0.95`` = beats the
N-trial max at 5% significance.

The family-wise trial count is **carried**, not guessed: :func:`cumulative_n_trials` reads
``diagnostics/research/n_trials.json`` (the arm-level denominator — grows per trial). Passing a
per-run count overstates significance — every DSR that informs a PROMOTE/KILL decision must deflate
at the cumulative count.

This module also provides the single-strategy certification statistics (Bailey & López de Prado
2012): :func:`probabilistic_sharpe_ratio` (is the Sharpe > a benchmark at all?) and
:func:`min_track_record_length` (how long a record is needed to certify it?). All three take a
PER-PERIOD Sharpe over the EFFECTIVE (non-overlapping) sample — for this overlapping 63-day-hold
book that is the per-window Sharpe over ~n_days/63 windows, NOT the raw daily count.
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
    """The carried POST-RESET family-wise trial count (``cumulative_n_trials`` in n_trials.json).

    Every DSR that informs a promotion/kill decision MUST deflate at a carried count, never a
    per-run guess. But see :func:`lifetime_n_trials` — on 2026-08-07 this counter was reset 138 → 0
    by owner decision, and a DSR deflated at the post-reset count is measuring a search that is
    smaller than the one which actually happened. Report both.
    """
    p = path or N_TRIALS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return int(data["cumulative_n_trials"])


def lifetime_n_trials(path: Path | None = None) -> int:
    """Every trial ever run on this data, INCLUDING those before the 2026-08-07 counter reset.

    This is the statistically defensible denominator, and the reason is the whole point of the DSR:
    it deflates by the expected maximum Sharpe across the search that was actually performed. The
    138 trials happened. They were run on the same 2017-2026 daily Indian equity history that every
    number since is measured on, so they raised the bar whether or not a JSON field records them.
    Resetting the counter lowered a gate; it added no information and un-ran no trial.

    The reset was a deliberate owner decision with a stated rationale — the carried 138 had made the
    bar effectively unpassable — and it is honoured: :func:`cumulative_n_trials` still returns the
    post-reset family count, which is the right denominator for "how much has THIS family of work
    searched". Reporting both ends the ambiguity instead of re-arguing it every readout.

    Falls back to the post-reset count when no reset is recorded (a fresh programme, where the two
    are the same number by construction).
    """
    p = path or N_TRIALS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    prior = int(data.get("_reset", {}).get("prior_cumulative", 0))
    return prior + int(data["cumulative_n_trials"])


def probabilistic_sharpe_ratio(
    sharpe_observed: float, n_observations: float, *,
    skewness: float = 0.0, kurtosis: float = 3.0, benchmark: float = 0.0,
) -> float:
    """PSR (Bailey & López de Prado 2012): probability in [0, 1] that the TRUE per-period Sharpe
    exceeds ``benchmark``, given ``n_observations`` EFFECTIVE (non-overlapping) periods, adjusted
    for skew/(raw)kurtosis. ``sharpe_observed`` is PER-PERIOD (e.g. the per-window Sharpe, NOT
    annualized). PSR ≥ 0.95 ⇒ the Sharpe is statistically above ``benchmark`` at 5%."""
    if n_observations <= 1:
        return float("nan")
    denom = 1.0 - skewness * sharpe_observed + ((kurtosis - 1.0) / 4.0) * sharpe_observed ** 2
    if denom <= 0.0:
        return float("nan")
    z = (sharpe_observed - benchmark) * math.sqrt(n_observations - 1) / math.sqrt(denom)
    return float(norm.cdf(z))


def min_track_record_length(
    sharpe_observed: float, *, skewness: float = 0.0, kurtosis: float = 3.0,
    benchmark: float = 0.0, confidence: float = 0.95,
) -> float:
    """Minimum Track Record Length (Bailey & López de Prado 2012): the number of EFFECTIVE
    (non-overlapping) periods needed for :func:`probabilistic_sharpe_ratio` to reach ``confidence``.
    ``inf`` when the per-period Sharpe ≤ ``benchmark`` (never certifiable). Same per-period Sharpe
    convention as PSR — divide the result by periods-per-year to read it in years."""
    if sharpe_observed <= benchmark:
        return float("inf")
    denom = 1.0 - skewness * sharpe_observed + ((kurtosis - 1.0) / 4.0) * sharpe_observed ** 2
    return 1.0 + denom * (norm.ppf(confidence) / (sharpe_observed - benchmark)) ** 2


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
