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
from nq.validation.dsr import (cumulative_n_trials, deflated_sharpe_ratio,
                               min_track_record_length, probabilistic_sharpe_ratio)
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


def block_returns(rets: np.ndarray, block: int = DEFAULT_BLOCK) -> np.ndarray:
    """Non-overlapping compounded ``block``-day returns — the autocorrelation-robust significance
    basis, consistent with the block bootstrap's 63-day block. The book holds ~one 63-day cycle, so
    daily returns are autocorrelated; the per-window series has ~``len/block`` EFFECTIVELY-
    independent observations whose std already embeds the within-cycle correlation. Drops the final
    partial block."""
    r = np.asarray(rets, dtype=float)
    n = r.size - (r.size % block)
    if n < block:
        return np.empty(0, dtype=float)
    return np.prod(1.0 + r[:n].reshape(-1, block), axis=1) - 1.0


def _window_sig(rets: np.ndarray) -> tuple[float, int, float, float] | None:
    """(per-window Sharpe, n_windows, skew, kurt) on non-overlapping 63-day blocks — the basis all
    single-strategy significance stats (DSR / PSR / MinTRL) share. None if too few windows."""
    blk = block_returns(rets)
    sd = blk.std(ddof=0) if blk.size else 0.0
    if blk.size < 4 or sd == 0:
        return None
    skew, kurt = _skew_kurt(blk)
    return float(blk.mean() / sd), int(blk.size), skew, kurt


def _dsr_from_bootstrap(rets: np.ndarray, n_trials: int, sharpe_ci: tuple[float, float] | None) -> float:
    """DSR of a single strategy's Sharpe, deflated at ``n_trials``, on the PER-WINDOW basis
    (:func:`_window_sig`) — overlapping 63-day-hold returns carry only ~n_days/63 independent
    observations, so the raw daily count would overstate significance. The cross-trial SR variance
    (for the expected-max benchmark) is the bootstrap-CI sd converted to per-window units
    (sd_annual / √(252/63)); this is the documented within-arm proxy (a P1 refinement remains)."""
    sig = _window_sig(rets)
    if sig is None or sharpe_ci is None:
        return float("nan")
    sr_w, n_w, skew, kurt = sig
    sd_ann = max((sharpe_ci[1] - sharpe_ci[0]) / (2.0 * _Z95), 1e-9)
    var_w = (sd_ann / math.sqrt(TRADING_DAYS / DEFAULT_BLOCK)) ** 2
    return deflated_sharpe_ratio(sr_w, n_observations=n_w, skewness=skew, kurtosis=kurt,
                                 n_trials=n_trials, sharpe_variance=var_w)


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
    # single-strategy certification on the per-window basis: is the Sharpe > 0 at all (PSR), and how
    # long a record would it take to certify (MinTRL) — answers "are 9 years even enough?"
    sig = _window_sig(rets)
    psr = min_trl_years = None
    n_eff = int(sig[1]) if sig else 0
    if sig is not None:
        sr_w, n_w, skew, kurt = sig
        psr = round(probabilistic_sharpe_ratio(sr_w, n_w, skewness=skew, kurtosis=kurt), 4)
        mtrl = min_track_record_length(sr_w, skewness=skew, kurtosis=kurt)
        min_trl_years = (round(mtrl * DEFAULT_BLOCK / TRADING_DAYS, 2) if math.isfinite(mtrl) else None)
    return {
        "metrics": bt["metrics"], "n_obs": int(rets.size), "n_eff_windows": n_eff, "n_trials": nt,
        "sharpe_point": round(ci.point, 3) if ci else None,
        "sharpe_ci": [round(ci.lower, 3), round(ci.upper, 3)] if ci else None,
        "dsr": _dsr_from_bootstrap(rets, nt, ci_tuple),
        "psr": psr, "min_trl_years": min_trl_years,
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
