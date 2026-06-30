"""Research-run harness — the canonical backtest + CPCV-over-time anti-overfit evaluation.

Three entry points, all over a ranked panel (``nq.engine.compose_ranked_panel``):

  * :func:`run_backtest` — frozen-cfg full-window backtest (the baseline_v0 reproduction entry).
  * :func:`cpcv_evaluate` — the CPCV path distribution of the frozen strategy. Because the cfg is
    FROZEN (no per-fold model training — the rule is fixed), each split just re-runs ``simulate``
    on its held-out date blocks; reconstructing the ``C(N,k)·k/N`` LdP paths gives a *distribution*
    of OOS outcomes that the Deflated Sharpe scores (robust to the single-path luck a lone
    walk-forward suffers).
  * :func:`paired_cpcv` — BASE vs CANDIDATE per-path ΔSharpe CI + DSR + a PROMOTE / UNDERPOWERED /
    KILL verdict. This is the §11-KILL re-derivation (a known-dead overlay must come back KILL) and
    the overlay-promotion significance test.

Data-source-agnostic (any OHLCV source → panel → here). The CANONICAL run executes on the cloud
(the local universe is a degenerate survivor subset → inadmissible headline); these functions are
hermetically unit-tested on a synthetic panel. Inference unit = **n_paths**, never the trade count
(a 63-day hold gives ~4 non-overlapping trades/stock/yr — trade count is a non-degeneracy floor).

Two scope notes:
  * **Frozen-cfg only.** Both arms here are *fixed* cfgs applied uniformly, so a group's OOS block
    returns are split-invariant and cached per group. A *re-derived-per-fold* overlay (Stage B
    cfg re-derivation) must NOT use this harness as-is — it would re-derive on each split's
    ``train_idx`` (which is why ``cpcv_splits`` carries the purge/embargo), and per-group caching
    would be invalid. For frozen overlays (sizing/exit/gate param changes) the cache is correct.
  * **``verdict`` is the CPCV-significance gate, not the full promotion bar.** It checks ΔSharpe
    CI-low>0 + point>noise_floor + DSR>0.95. The full 7-gate promotion bar (ΔCalmar, 2022-26
    sub-period, walk-forward fold-pass, turnover, mechanism — ``skills/overlay-testing``) is
    applied ON TOP by the human before any PROMOTE.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from statistics import mean, pstdev
from typing import Any

import numpy as np
import pandas as pd

from nq.engine.portfolio import simulate
from nq.validation.cpcv import CPCVSplit, cpcv_paths, cpcv_splits, make_groups
from nq.validation.dsr import cumulative_n_trials, deflated_sharpe_ratio
from nq.validation.metrics import TRADING_DAYS, cagr, equity_from_returns, sharpe

# Long-horizon CPCV defaults: 8 groups (NOT 10 — embargo=63 would erase a 10-group partition),
# k=2 → C(8,2)=28 splits / 7 paths; horizon=embargo=63 (the 63-day label) for full two-sided purge.
N_GROUPS = 8
N_TEST_GROUPS = 2
HORIZON = 63
EMBARGO = 63
NOISE_FLOOR = 0.3   # minimum meaningful ΔSharpe point estimate (program standard)
_Z = 1.959963984540054   # Φ⁻¹(0.975)


def _daily_returns(equity_curve: list[dict[str, Any]]) -> pd.Series:
    """Daily returns from a simulate() equity curve, indexed by date."""
    if not equity_curve:
        return pd.Series(dtype=float)
    s = pd.Series([e["equity"] for e in equity_curve],
                  index=pd.to_datetime([e["date"] for e in equity_curve]), dtype=float)
    return s.pct_change().dropna()


def run_backtest(
    panel: pd.DataFrame, cfg: Mapping[str, Any], *,
    start: str | None = None, end: str | None = None, initial_capital: float = 1_000_000.0,
) -> dict[str, Any]:
    """Frozen-cfg backtest over the full window — the baseline reproduction entry point."""
    return simulate(panel, cfg, start=start, end=end, initial_capital=initial_capital)


def _block_returns(
    panel: pd.DataFrame, cfg: Mapping[str, Any], splits: Sequence[CPCVSplit],
    group_spans: list[tuple[int, int]], dates: list[Any], initial_capital: float,
) -> dict[tuple[int, int], pd.Series]:
    """Run ``simulate`` once per (split, test-group) on that group's contiguous date block; return
    ``{(split_idx, group) -> daily-return Series}``. Each block is an independent OOS backtest of
    the frozen rule (fresh book per block)."""
    out: dict[tuple[int, int], pd.Series] = {}
    cache: dict[int, pd.Series] = {}   # group -> returns (cfg + block are identical across splits)
    for si, split in enumerate(splits):
        for g in split.test_groups:
            if g not in cache:
                s, e = group_spans[g]
                res = simulate(panel, cfg, start=str(dates[s]), end=str(dates[e - 1]),
                               initial_capital=initial_capital)
                cache[g] = _daily_returns(res["equity_curve"])
            out[(si, g)] = cache[g]
    return out


def _path_sharpes(
    rets: dict[tuple[int, int], pd.Series], paths: list[dict[int, int]], n_groups: int,
) -> tuple[list[float], list[float], list[pd.Series]]:
    """Per-path Sharpe, CAGR, and the stitched OOS return series (groups in time order)."""
    sh, cg, series = [], [], []
    for path in paths:
        pieces = [rets[(path[g], g)] for g in range(n_groups)
                  if path.get(g) is not None and len(rets.get((path[g], g), [])) > 0]
        if pieces:
            ser = pd.concat(pieces).sort_index()
            sh.append(sharpe(ser.to_numpy()))
            cg.append(cagr(equity_from_returns(ser.to_numpy())) * 100.0)
            series.append(ser)
        else:
            sh.append(0.0)
            cg.append(0.0)
    return sh, cg, series


def _emp_skew_kurt(series: list[pd.Series]) -> tuple[float, float]:
    """Population skewness + RAW (non-excess; normal→3.0) kurtosis of pooled daily returns — the
    DSR must not assume false normality."""
    present = [s for s in series if s is not None and len(s) > 0]
    if not present:
        return 0.0, 3.0
    a = pd.concat(present).to_numpy(dtype=float)
    if a.size < 8 or a.std() == 0:
        return 0.0, 3.0
    z = (a - a.mean()) / a.std()
    return float((z ** 3).mean()), float((z ** 4).mean())


def _ci(xs: list[float]) -> tuple[float, float, float]:
    """Normal CI (mean ± z·sd/√n) over the path values."""
    m = float(mean(xs)) if xs else 0.0
    sd = float(pstdev(xs)) if len(xs) > 1 else 0.0
    half = _Z * sd / math.sqrt(len(xs)) if xs else 0.0
    return m, m - half, m + half


def cpcv_evaluate(
    panel: pd.DataFrame, cfg: Mapping[str, Any], *,
    n_groups: int = N_GROUPS, n_test_groups: int = N_TEST_GROUPS,
    horizon: int = HORIZON, embargo: int = EMBARGO, initial_capital: float = 1_000_000.0,
    n_trials: int | None = None,
) -> dict[str, Any]:
    """CPCV path distribution of the frozen strategy + Deflated Sharpe. Returns the per-path Sharpe
    /CAGR, their means, and DSR (empirical skew/kurt, deflated at the carried cumulative n_trials)."""
    dates = sorted(pd.to_datetime(panel["date"]).dt.strftime("%Y-%m-%d").unique())
    n_obs = len(dates)
    splits = cpcv_splits(n_obs, n_groups=n_groups, n_test_groups=n_test_groups,
                         horizon=horizon, embargo=embargo)
    spans = make_groups(n_obs, n_groups)
    paths = cpcv_paths(splits, n_groups)
    rets = _block_returns(panel, cfg, splits, spans, dates, initial_capital)
    sh, cg, series = _path_sharpes(rets, paths, n_groups)
    nt = cumulative_n_trials() if n_trials is None else n_trials
    skew, kurt = _emp_skew_kurt(series)
    m_sh = float(mean(sh)) if sh else 0.0
    disp = float(pstdev(sh)) if len(sh) > 1 else 0.0
    dsr = deflated_sharpe_ratio(
        m_sh / math.sqrt(TRADING_DAYS), n_observations=len(paths) if paths else 0,
        skewness=skew, kurtosis=kurt, n_trials=nt,
        sharpe_variance=(disp ** 2 if disp > 0 else 1.0)) if paths else float("nan")
    return {
        "n_paths": len(paths), "n_splits": len(splits), "n_trials": nt,
        "path_sharpes": [round(x, 3) for x in sh], "path_cagrs": [round(x, 2) for x in cg],
        "mean_sharpe": round(m_sh, 3), "mean_cagr": round(float(mean(cg)) if cg else 0.0, 2),
        "dsr": dsr, "emp_skew": round(skew, 3), "emp_kurt": round(kurt, 3),
    }


def paired_cpcv(
    panel: pd.DataFrame, base_cfg: Mapping[str, Any], candidate_cfg: Mapping[str, Any], *,
    n_groups: int = N_GROUPS, n_test_groups: int = N_TEST_GROUPS,
    horizon: int = HORIZON, embargo: int = EMBARGO, initial_capital: float = 1_000_000.0,
    n_trials: int | None = None, noise_floor: float = NOISE_FLOOR,
) -> dict[str, Any]:
    """BASE vs CANDIDATE paired CPCV: per-path ΔSharpe (same splits/paths) → CI + DSR(candidate) →
    verdict. PROMOTE-CANDIDATE needs ΔSharpe CI-low > 0 AND point > noise_floor AND DSR > 0.95; a
    positive point with CI-low ≤ 0 is UNDERPOWERED (not a KILL); otherwise KILL. This is how a known
    §11-dead overlay is re-derived as killed."""
    dates = sorted(pd.to_datetime(panel["date"]).dt.strftime("%Y-%m-%d").unique())
    n_obs = len(dates)
    splits = cpcv_splits(n_obs, n_groups=n_groups, n_test_groups=n_test_groups,
                         horizon=horizon, embargo=embargo)
    spans = make_groups(n_obs, n_groups)
    paths = cpcv_paths(splits, n_groups)
    base = _path_sharpes(_block_returns(panel, base_cfg, splits, spans, dates, initial_capital),
                         paths, n_groups)
    cand = _path_sharpes(_block_returns(panel, candidate_cfg, splits, spans, dates, initial_capital),
                         paths, n_groups)
    npaths = len(paths)
    d_sharpe = _ci([cand[0][i] - base[0][i] for i in range(npaths)]) if npaths else (0.0, 0.0, 0.0)
    d_cagr = _ci([cand[1][i] - base[1][i] for i in range(npaths)]) if npaths else (0.0, 0.0, 0.0)
    nt = cumulative_n_trials() if n_trials is None else n_trials
    skew, kurt = _emp_skew_kurt(cand[2])
    c_mean = float(mean(cand[0])) if cand[0] else 0.0
    c_disp = float(pstdev(cand[0])) if len(cand[0]) > 1 else 0.0
    dsr = deflated_sharpe_ratio(
        c_mean / math.sqrt(TRADING_DAYS), n_observations=npaths, skewness=skew, kurtosis=kurt,
        n_trials=nt, sharpe_variance=(c_disp ** 2 if c_disp > 0 else 1.0)) if npaths else float("nan")
    clean = bool(d_sharpe[1] > 0 and d_sharpe[0] > noise_floor)
    dsr_ok = bool(np.isfinite(dsr) and dsr > 0.95)
    underpowered = bool(not (clean and dsr_ok) and d_sharpe[0] > 0 and d_sharpe[1] <= 0)
    verdict = ("PROMOTE-CANDIDATE" if (clean and dsr_ok)
               else "UNDERPOWERED" if underpowered else "KILL")
    return {
        "n_paths": npaths, "n_trials": nt,
        "base_sharpe": round(float(mean(base[0])) if base[0] else 0.0, 3),
        "candidate_sharpe": round(c_mean, 3),
        "dSharpe": round(d_sharpe[0], 3), "dSharpe_ci": [round(d_sharpe[1], 3), round(d_sharpe[2], 3)],
        "dCAGR": round(d_cagr[0], 2), "dCAGR_ci": [round(d_cagr[1], 2), round(d_cagr[2], 2)],
        "dsr_candidate": dsr, "emp_skew": round(skew, 3), "emp_kurt": round(kurt, 3),
        "verdict": verdict,
    }
