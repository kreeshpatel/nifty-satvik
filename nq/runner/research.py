"""Research-run harness — baseline reproduction + OOS-robustness + overlay significance.

Methodology note (learned from the first cloud run): the long-horizon strategy is a **frozen rule**
(rank by sma200_slope_63 — no per-fold model training). CPCV's path *distribution* comes from
per-fold training variation, so on a frozen rule every CPCV path collapses to the same stitched
series (degenerate). The correct OOS-robustness tool for a frozen rule is the **overlapping block
bootstrap** on the realised equity curve (block = 63 = one cycle; backtest-rigor §E2 cites the
baseline Sharpe CI). CPCV (``nq.validation.cpcv``) is retained for *re-derived / trained* arms —
i.e. Stage B's per-fold cfg re-derivation — where the per-fold variation is real.

Entry points (data-source-agnostic, over a ranked panel):
  * :func:`run_backtest`     — frozen-cfg full-window backtest (baseline reproduction).
  * :func:`evaluate`         — backtest + block-bootstrap Sharpe CI + Deflated Sharpe (the frozen
                               baseline's OOS-robustness read).
  * :func:`evaluate_overlay` — BASE vs CANDIDATE paired block-bootstrap ΔSharpe CI + DSR(candidate)
                               → PROMOTE-CANDIDATE / UNDERPOWERED / KILL (the significance gate;
                               the full 7-gate promotion bar is applied on top per overlay-testing).

The CANONICAL numbers come from the cloud run on the corrected universe (the local universe is a
degenerate survivor subset → inadmissible). These functions are hermetically unit-tested on a
synthetic panel.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from nq.engine.portfolio import simulate
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta
from nq.validation.dsr import cumulative_n_trials, deflated_sharpe_ratio
from nq.validation.metrics import TRADING_DAYS, sharpe

NOISE_FLOOR = 0.3   # minimum meaningful ΔSharpe point estimate (program standard)


def _daily_returns(equity_curve: list[dict[str, Any]]) -> pd.Series:
    """Daily returns from a simulate() equity curve, indexed by date."""
    if not equity_curve:
        return pd.Series(dtype=float)
    s = pd.Series([e["equity"] for e in equity_curve],
                  index=pd.to_datetime([e["date"] for e in equity_curve]), dtype=float)
    return s.pct_change().dropna()


def _skew_kurt(arr: np.ndarray) -> tuple[float, float]:
    """Population skewness + RAW (non-excess; normal→3.0) kurtosis — the DSR must not assume
    false normality."""
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    if a.size < 8 or a.std() == 0:
        return 0.0, 3.0
    z = (a - a.mean()) / a.std()
    return float((z ** 3).mean()), float((z ** 4).mean())


def run_backtest(
    panel: pd.DataFrame, cfg: Mapping[str, Any], *,
    start: str | None = None, end: str | None = None, initial_capital: float = 1_000_000.0,
) -> dict[str, Any]:
    """Frozen-cfg backtest over the full window — the baseline reproduction entry point."""
    return simulate(panel, cfg, start=start, end=end, initial_capital=initial_capital)


_Z95 = 1.959963984540054   # Φ⁻¹(0.975)


def effective_n(n_obs: int, block: int = DEFAULT_BLOCK) -> float:
    """Effective independent sample size of the OVERLAPPING equity-return series.

    The book holds ~one 63-day cycle, so daily equity returns are autocorrelated over ``block``
    days; the number of effectively-independent observations is ~``n_obs / block`` (the same
    63-day block the bootstrap treats as exchangeable), NOT the raw daily count. The DSR z-stat
    scales by √(n−1), so feeding the daily count (~2300) instead of the effective count (~30-40)
    badly OVERSTATES significance. Floored at 2."""
    return max(2.0, n_obs / float(block))


def _dsr_from_bootstrap(rets: np.ndarray, n_trials: int, sharpe_ci: tuple[float, float] | None) -> float:
    """DSR of a single equity-return series' Sharpe, deflated at ``n_trials``. All in PER-PERIOD
    units: SR = annualized/√252, and the cross-trial SR variance is estimated from the block-
    bootstrap Sharpe CI (sd_annual ≈ (hi−lo)/2z → var_pp = (sd_annual/√252)²). The candidate
    Sharpe's own SE uses the EFFECTIVE sample size (:func:`effective_n`), not the raw daily count
    — overlapping 63-day-hold returns carry far fewer than ``rets.size`` independent observations."""
    if rets.size <= 1:
        return float("nan")
    ann = sharpe(rets)
    if not np.isfinite(ann) or sharpe_ci is None:
        return float("nan")
    sd_ann = max((sharpe_ci[1] - sharpe_ci[0]) / (2.0 * _Z95), 1e-9)
    var_pp = (sd_ann / math.sqrt(TRADING_DAYS)) ** 2
    skew, kurt = _skew_kurt(rets)
    return deflated_sharpe_ratio(ann / math.sqrt(TRADING_DAYS), n_observations=effective_n(rets.size),
                                 skewness=skew, kurtosis=kurt, n_trials=n_trials,
                                 sharpe_variance=var_pp)


def evaluate(
    panel: pd.DataFrame, cfg: Mapping[str, Any], *,
    start: str | None = None, end: str | None = None, initial_capital: float = 1_000_000.0,
    n_trials: int | None = None, block_size: int = DEFAULT_BLOCK, n_samples: int = 5000,
    seed: int | None = 12345,
) -> dict[str, Any]:
    """Frozen-baseline OOS robustness: backtest metrics + block-bootstrap Sharpe CI + Deflated
    Sharpe. ``sharpe_ci`` is the [5th, 95th] percentile band of the annualized Sharpe under the
    63-day block bootstrap (None if too few return observations)."""
    bt = run_backtest(panel, cfg, start=start, end=end, initial_capital=initial_capital)
    rets = _daily_returns(bt["equity_curve"]).to_numpy(dtype=float)
    nt = cumulative_n_trials() if n_trials is None else n_trials
    ci = (block_bootstrap_metric(rets, sharpe, block_size=block_size, n_samples=n_samples, seed=seed)
          if rets.size > block_size else None)
    ci_tuple = (ci.lower, ci.upper) if ci else None
    return {
        "metrics": bt["metrics"], "n_obs": int(rets.size), "n_trials": nt,
        "sharpe_point": round(ci.point, 3) if ci else None,
        "sharpe_ci": [round(ci.lower, 3), round(ci.upper, 3)] if ci else None,
        "dsr": _dsr_from_bootstrap(rets, nt, ci_tuple),
    }


def evaluate_overlay(
    panel: pd.DataFrame, base_cfg: Mapping[str, Any], candidate_cfg: Mapping[str, Any], *,
    start: str | None = None, end: str | None = None, initial_capital: float = 1_000_000.0,
    n_trials: int | None = None, block_size: int = DEFAULT_BLOCK, n_samples: int = 5000,
    seed: int | None = 12345, noise_floor: float = NOISE_FLOOR,
) -> dict[str, Any]:
    """BASE vs CANDIDATE significance via the **paired block bootstrap** on the two equity-return
    series (date-aligned, same resampled blocks each draw) → ΔSharpe CI + DSR(candidate) → verdict.
    PROMOTE-CANDIDATE needs ΔSharpe CI-low > 0 AND point > noise_floor AND DSR > 0.95; a positive
    point with CI-low ≤ 0 is UNDERPOWERED; otherwise KILL. (The full 7-gate promotion bar —
    ΔCalmar, 2022-26 sub-period, fold-pass, turnover, mechanism — is applied on top per
    overlay-testing.)"""
    base_bt = run_backtest(panel, base_cfg, start=start, end=end, initial_capital=initial_capital)
    cand_bt = run_backtest(panel, candidate_cfg, start=start, end=end, initial_capital=initial_capital)
    base_r = _daily_returns(base_bt["equity_curve"])
    cand_r = _daily_returns(cand_bt["equity_curve"])
    common = base_r.index.intersection(cand_r.index)
    a = cand_r.loc[common].to_numpy(dtype=float)   # candidate
    b = base_r.loc[common].to_numpy(dtype=float)   # base
    nt = cumulative_n_trials() if n_trials is None else n_trials
    if a.size <= block_size:
        return {"verdict": "UNDERPOWERED", "reason": "too few aligned observations",
                "n_obs": int(a.size), "n_trials": nt}
    delta = bootstrap_delta(a, b, sharpe, block_size=block_size, n_samples=n_samples, seed=seed)
    cand_ci = block_bootstrap_metric(a, sharpe, block_size=block_size, n_samples=n_samples, seed=seed)
    dsr = _dsr_from_bootstrap(a, nt, (cand_ci.lower, cand_ci.upper))
    clean = bool(delta.lower > 0 and delta.point > noise_floor)
    dsr_ok = bool(np.isfinite(dsr) and dsr > 0.95)
    underpowered = bool(not (clean and dsr_ok) and delta.point > 0 and delta.lower <= 0)
    verdict = ("PROMOTE-CANDIDATE" if (clean and dsr_ok)
               else "UNDERPOWERED" if underpowered else "KILL")
    return {
        "n_obs": int(a.size), "n_trials": nt,
        "base_sharpe": round(float(sharpe(b)), 3), "candidate_sharpe": round(float(sharpe(a)), 3),
        "dSharpe": round(delta.point, 3), "dSharpe_ci": [round(delta.lower, 3), round(delta.upper, 3)],
        "dsr_candidate": dsr, "verdict": verdict,
    }
