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


def _subperiod_cagr(equity_curve: list[dict[str, Any]], start: str | None, end: str | None) -> float | None:
    """CAGR (%) over the [start, end] slice of an equity curve. None if the slice is too short."""
    sub_start = pd.to_datetime(start) if start else None
    sub_end = pd.to_datetime(end) if end else None
    pts = [(pd.to_datetime(e["date"]), float(e["equity"])) for e in equity_curve]
    sl = [(d, v) for d, v in pts
          if (sub_start is None or d >= sub_start) and (sub_end is None or d <= sub_end)]
    if len(sl) < 2 or sl[0][1] <= 0:
        return None
    yrs = (sl[-1][0] - sl[0][0]).days / 365.25
    return round(((sl[-1][1] / sl[0][1]) ** (1.0 / yrs) - 1.0) * 100.0, 3) if yrs > 0 else None


def _fold_pass(index: pd.Index, a: np.ndarray, b: np.ndarray, since_year: int) -> tuple[float, int]:
    """Walk-forward fold-pass: fraction of years (>= since_year, >=20 obs) where the candidate's
    Sharpe beats the base's, on the aligned daily returns. Returns (fraction, n_folds_counted)."""
    yr = pd.DatetimeIndex(index).year.to_numpy()
    wins = total = 0
    for y in sorted(set(int(v) for v in yr)):
        if y < since_year:
            continue
        m = yr == y
        if int(m.sum()) < 20:
            continue
        total += 1
        if sharpe(a[m]) > sharpe(b[m]):
            wins += 1
    return (wins / total if total else float("nan")), total


def _after_tax_cagr(bt: dict[str, Any], initial_capital: float, stcg: float = 0.20) -> float | None:
    """Approximate after-tax CAGR (%): per-calendar-year STCG (20%) on each year's NET realized
    gain (losses offset within the year). Approximate (calendar ≠ Apr-Mar FY; no path compounding
    of the tax drag) — a reported figure so the post-tax axis is never silently skipped."""
    trades = bt.get("trades", [])
    ec = bt.get("equity_curve", [])
    if not ec:
        return None
    by_yr: dict[int, float] = {}
    for t in trades:
        by_yr[int(str(t["exit_date"])[:4])] = by_yr.get(int(str(t["exit_date"])[:4]), 0.0) + float(t["pnl"])
    tax = sum(stcg * max(0.0, g) for g in by_yr.values())
    final = initial_capital + sum(float(t["pnl"]) for t in trades) - tax
    if final <= 0:
        return None
    yrs = (pd.to_datetime(ec[-1]["date"]) - pd.to_datetime(ec[0]["date"])).days / 365.25
    return round(((final / initial_capital) ** (1.0 / yrs) - 1.0) * 100.0, 3) if yrs > 0 else None


def evaluate_overlay(
    panel: pd.DataFrame, base_cfg: Mapping[str, Any], candidate_cfg: Mapping[str, Any], *,
    start: str | None = None, end: str | None = None, initial_capital: float = 1_000_000.0,
    n_trials: int | None = None, block_size: int = DEFAULT_BLOCK, n_samples: int = 5000,
    seed: int | None = 12345, noise_floor: float = NOISE_FLOOR,
    sub_start: str = "2022-01-01", fold_since_year: int = 2019,
    calmar_min: float = 0.05, turnover_max_increase: float = 0.30, n_eff_min: int = 20,
) -> dict[str, Any]:
    """BASE vs CANDIDATE through the **mechanized promotion bar**: the paired block bootstrap
    (ΔSharpe CI + DSR) PLUS the gates that used to be applied by hand — ΔCalmar, 2022-26 sub-period
    ΔCAGR, ≥2019 walk-forward fold-pass, turnover-Δ, and effective-sample size. ``gate_pass`` is the
    AND of all auto-computable gates and is **fail-closed** (an uncomputable gate cannot PROMOTE).
    PROMOTE-CANDIDATE iff every gate passes; a positive ΔSharpe with CI-low ≤ 0 is UNDERPOWERED;
    else KILL. (Mechanism-explainable-in-one-sentence stays a human gate; after-tax CAGR is reported.)
    """
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
    bm, cm = base_bt["metrics"], cand_bt["metrics"]

    # ── the mechanized gates (each fail-closed: None/NaN => False) ──────────────
    d_calmar = (cm.get("calmar", float("nan")) - bm.get("calmar", float("nan")))
    sub_b = _subperiod_cagr(base_bt["equity_curve"], sub_start, end)
    sub_c = _subperiod_cagr(cand_bt["equity_curve"], sub_start, end)
    d_sub = (round(sub_c - sub_b, 3) if (sub_b is not None and sub_c is not None) else None)
    fold_frac, n_folds = _fold_pass(common, a, b, fold_since_year)
    base_to, cand_to = bm.get("turnover_per_year"), cm.get("turnover_per_year")
    d_turn = (round((cand_to - base_to) / base_to, 4)
              if (base_to and base_to > 0 and cand_to is not None) else None)
    n_eff = int(block_returns(a).size)
    gates = {
        "dSharpe_meaningful": bool(delta.lower > 0 and delta.point > noise_floor),
        "dCalmar_ge_0.05": bool(np.isfinite(d_calmar) and d_calmar >= calmar_min),
        "subperiod_2022_positive": bool(d_sub is not None and d_sub > 0),
        "fold_pass_ge_60pct": bool(n_folds > 0 and fold_frac >= 0.60),
        "turnover_le_30pct": bool(d_turn is not None and d_turn <= turnover_max_increase),
        "dsr_gt_0.95": bool(np.isfinite(dsr) and dsr > 0.95),
        "n_eff_ge_20": bool(n_eff >= n_eff_min),
    }
    gate_pass = all(gates.values())
    underpowered = bool(not gate_pass and delta.point > 0 and delta.lower <= 0)
    verdict = "PROMOTE-CANDIDATE" if gate_pass else "UNDERPOWERED" if underpowered else "KILL"
    return {
        "n_obs": int(a.size), "n_eff_windows": n_eff, "n_trials": nt,
        "base_sharpe": round(float(sharpe(b)), 3), "candidate_sharpe": round(float(sharpe(a)), 3),
        "dSharpe": round(delta.point, 3), "dSharpe_ci": [round(delta.lower, 3), round(delta.upper, 3)],
        "dsr_candidate": dsr,
        "dCalmar": round(float(d_calmar), 4) if np.isfinite(d_calmar) else None,
        "subperiod_2022_dCAGR": d_sub, "fold_pass_frac": round(fold_frac, 3) if n_folds else None,
        "n_folds": n_folds, "turnover_delta": d_turn,
        "after_tax_cagr_base": _after_tax_cagr(base_bt, initial_capital),
        "after_tax_cagr_cand": _after_tax_cagr(cand_bt, initial_capital),
        "gates": gates, "gate_pass": gate_pass, "verdict": verdict,
    }
