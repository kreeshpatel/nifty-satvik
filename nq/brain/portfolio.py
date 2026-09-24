"""Portfolio risk decomposition — how much of this book is one bet, and how much is the market.

Layer 5 of the Brain. Pure functions: no network, no clock, no model calls. The diagnostic that feeds
prices and holdings in is `scripts/diag_portfolio_risk.py`; the definitions live in
`diagnostics/research/portfolio_risk/SPEC.md`, committed before any result existed.

WHY THESE MEASURES

Finding 0141 showed the book's +2R hit rate is about what same-day stocks with the same volatility and
stop distance give. That moves the question from the target to exposure: if the names move together and
with the index, six seats are not six bets, and a drawdown that arrives with the index was never
diversifiable. :func:`market_model` prices the index part; :func:`average_pairwise_correlation`,
:func:`effective_bets` and :func:`diversification_ratio` price the together-ness.

WHAT THESE CANNOT DO

They describe exposure. They do not authorise a de-gross, a hedge or a seat-count change: the one
de-gross measured on this book inverted (0095, ΔSharpe −0.398), and concentration is load-bearing here
(`FINDING_more_slots`: 4–5 seats 1.21 Sharpe against 10 seats 0.81). A low effective-bet count is a
description, not a defect.
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd

Floats = npt.NDArray[np.float64]


# --------------------------------------------------------------------------- returns and the market
def daily_returns(nav: pd.Series) -> pd.Series:
    """Simple daily returns of an equity curve, dropping the first (undefined) point."""
    s = pd.Series(nav, dtype=float).sort_index()
    return s.pct_change().dropna()


def beta_of(market: Floats, book: Floats) -> float:
    """OLS slope of book on market, on plain arrays (no dates, so a bootstrap can resample freely)."""
    x = np.asarray(market, dtype=float)
    y = np.asarray(book, dtype=float)
    vx = float(np.var(x, ddof=1)) if x.size > 1 else 0.0
    return float(np.cov(x, y, ddof=1)[0, 1] / vx) if vx > 0 else float("nan")


def market_model(book: pd.Series, market: pd.Series) -> dict[str, float]:
    """OLS of book returns on market returns over their common dates.

    Returns beta, alpha per day, R², the common-sample size, and the split of the book's mean daily
    return into the market part (beta x mean market) and the residual (alpha).
    """
    both = pd.concat([pd.Series(book, dtype=float), pd.Series(market, dtype=float)], axis=1,
                     join="inner").dropna()
    both.columns = ["book", "mkt"]
    n = len(both)
    if n < 3:
        return {"n": float(n), "beta": float("nan"), "alpha_daily": float("nan"), "r2": float("nan")}
    x = both["mkt"].to_numpy(float)
    y = both["book"].to_numpy(float)
    beta = beta_of(x, y)
    alpha = float(y.mean() - beta * x.mean())
    resid = y - (alpha + beta * x)
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = float(1.0 - np.sum(resid ** 2) / sst) if sst > 0 else float("nan")
    return {"n": float(n), "beta": beta, "alpha_daily": alpha, "r2": r2,
            "mean_book_daily": float(y.mean()), "mean_market_daily": float(x.mean()),
            "market_part_daily": beta * float(x.mean())}


def drawdown_regime(index_close: pd.Series, *, threshold: float = 0.10, lookback: int = 252) -> pd.Series:
    """True on sessions where the index sits `threshold` or more below its trailing `lookback` high."""
    s = pd.Series(index_close, dtype=float).sort_index()
    peak = s.rolling(lookback, min_periods=20).max()
    return (s / peak - 1.0) <= -abs(threshold)


# --------------------------------------------------------------------------- togetherness
def average_pairwise_correlation(returns: pd.DataFrame) -> float:
    """Mean off-diagonal correlation of the columns. NaN when fewer than two usable columns."""
    r = returns.dropna(axis=1, how="all")
    if r.shape[1] < 2:
        return float("nan")
    c = r.corr()
    m = c.to_numpy(float)
    iu = np.triu_indices_from(m, k=1)
    vals = m[iu]
    vals = vals[np.isfinite(vals)]
    return float(vals.mean()) if vals.size else float("nan")


def effective_bets(n_names: int, rho: float) -> float:
    """`N / (1 + (N − 1)·rho)` — the equal-weight effective number of independent bets.

    rho = 0 gives N; rho = 1 gives 1. Negative rho can exceed N, which is real (offsetting positions),
    so it is not clipped.
    """
    if n_names <= 0:
        return float("nan")
    denom = 1.0 + (n_names - 1) * float(rho)
    return float(n_names) / denom if denom > 0 else float("inf")


def diversification_ratio(weights: Sequence[float], cov: npt.NDArray[np.float64]) -> float:
    """`(Σ w_i σ_i) / σ_portfolio`. 1.0 means the names move as one; √N means independent and equal."""
    w = np.asarray(weights, dtype=float)
    c = np.asarray(cov, dtype=float)
    sig = np.sqrt(np.diag(c))
    port_var = float(w @ c @ w)
    if port_var <= 0:
        return float("nan")
    return float((w @ sig) / np.sqrt(port_var))


def variance_shares(weights: Sequence[float], cov: npt.NDArray[np.float64]) -> pd.DataFrame:
    """Each holding's share of portfolio variance, split into its own term and its covariance terms.

    The shares are the risk-contribution decomposition `w_i (Σw)_i / (w'Σw)`, which sums to 1 exactly.
    """
    w = np.asarray(weights, dtype=float)
    c = np.asarray(cov, dtype=float)
    port_var = float(w @ c @ w)
    if port_var <= 0:
        return pd.DataFrame(columns=["share", "own", "cov"])
    total = c @ w
    share = w * total / port_var
    own = (w ** 2) * np.diag(c) / port_var
    return pd.DataFrame({"share": share, "own": own, "cov": share - own})


def top_eigenvalue_share(returns: pd.DataFrame) -> float:
    """The largest eigenvalue's share of the correlation matrix's trace — one number for "one bet"."""
    r = returns.dropna(axis=1, how="all")
    if r.shape[1] < 2:
        return float("nan")
    c = r.corr().to_numpy(float)
    if not np.isfinite(c).all():
        return float("nan")
    ev = np.linalg.eigvalsh(c)
    return float(ev.max() / ev.sum()) if ev.sum() > 0 else float("nan")


# --------------------------------------------------------------------------- trade-side descriptions
def sample_skew(x: Sequence[float]) -> float:
    """Population skewness (the same convention as the DSR path in `nq.runner.research`)."""
    a = np.asarray(list(x), dtype=float)
    a = a[np.isfinite(a)]
    if a.size < 3:
        return float("nan")
    sd = a.std(ddof=0)
    return float(np.mean((a - a.mean()) ** 3) / sd ** 3) if sd > 0 else float("nan")


def exit_reason_stats(trades: pd.DataFrame, *, reason_col: str = "reason", r_col: str = "R") -> pd.DataFrame:
    """Per exit reason: n, mean/median R, skew, and total R in R units (SPEC measure 7).

    `share_of_total_R` is only defined when the book's total R is POSITIVE. With a negative total the
    ratio inverts sign and a losing family reads as a positive contribution: the live book's stop family
    (sum −16.32R of a −17.27R total) printed **+94.5%**. Found by the red-team read, 2026-09-24. Report
    `sum_R` in R units; the share is NaN whenever it cannot be read as a contribution.
    """
    cols = ["n", "mean_R", "median_R", "skew_R", "sum_R", "share_of_total_R"]
    d = pd.DataFrame(trades)[[reason_col, r_col]].dropna()
    if d.empty:
        return pd.DataFrame(columns=cols)
    total = float(d[r_col].sum())
    out = d.groupby(reason_col)[r_col].agg(n="size", mean_R="mean", median_R="median", sum_R="sum")
    out["skew_R"] = d.groupby(reason_col)[r_col].apply(sample_skew)
    out["share_of_total_R"] = (out["sum_R"] / total) if total > 0 else np.nan
    return out[cols].sort_values("sum_R")


def cluster_bootstrap_mean(values: Sequence[float], clusters: Sequence[str], *, n_boot: int = 2000,
                           seed: int = 20260924) -> tuple[float, float, float]:
    """(mean, lo95, hi95) resampling whole clusters (tickers) — the SPEC's uncertainty for trade stats.

    Trades of one name share its path, so resampling trades independently understates the spread.
    """
    v = np.asarray(list(values), dtype=float)
    c = np.asarray(list(clusters))
    ok = np.isfinite(v)
    v, c = v[ok], c[ok]
    if v.size == 0:
        return float("nan"), float("nan"), float("nan")
    point = float(v.mean())
    keys, inv = np.unique(c, return_inverse=True)
    groups = [np.flatnonzero(inv == g) for g in range(len(keys))]
    if len(groups) < 2:
        return point, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        out[i] = v[np.concatenate([groups[g] for g in pick])].mean()
    lo, hi = np.percentile(out, [2.5, 97.5])
    return point, float(lo), float(hi)


# --------------------------------------------------------------------------- uncertainty
def block_bootstrap_paired(x: Sequence[float], y: Sequence[float],
                           stat: Callable[[Floats, Floats], float], *, block: int = 63,
                           n_boot: int = 2000, seed: int = 20260924) -> tuple[float, float, float]:
    """(point, lo95, hi95) for a two-series statistic — beta, correlation — resampling whole blocks.

    Both series are resampled at the SAME block positions, so the pairing survives. Written after a
    bootstrap that resampled dated Series produced duplicate dates and crashed the join: a bootstrap
    belongs on arrays, where a repeated observation is ordinary.
    """
    a = np.asarray(list(x), dtype=float)
    b = np.asarray(list(y), dtype=float)
    if a.size != b.size:
        raise ValueError("paired bootstrap needs two series of the same length")
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    point = stat(a, b) if a.size > 2 else float("nan")
    if a.size < block or a.size < 3:
        return point, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(a.size / block))
    out = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, a.size - block + 1, n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:a.size]
        out[i] = stat(a[idx], b[idx])
    lo, hi = np.percentile(out[np.isfinite(out)], [2.5, 97.5])
    return point, float(lo), float(hi)


def block_bootstrap_ci(series: Sequence[float], stat: Callable[[Floats], float], *, block: int = 63,
                       n_boot: int = 2000, seed: int = 20260924) -> tuple[float, float, float]:
    """(point, lo95, hi95) for a statistic of a serially dependent series, resampling whole blocks."""
    a = np.asarray(list(series), dtype=float)
    a = a[np.isfinite(a)]
    if a.size < block or a.size < 3:
        return (stat(a) if a.size else float("nan")), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(a.size / block))
    starts_max = a.size - block
    out = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, starts_max + 1, n_blocks)
        sample = np.concatenate([a[s:s + block] for s in starts])[:a.size]
        out[i] = stat(sample)
    lo, hi = np.percentile(out, [2.5, 97.5])
    return float(stat(a)), float(lo), float(hi)
