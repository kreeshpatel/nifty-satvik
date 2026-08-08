"""Cross-sectional signal primitives — pure, trailing-only, truncation-testable.

Signals are **pure functions of a price history**, separate from any engine. That separation is the
point: a signal can be truncation-tested on its own (``tests/test_signals_pit.py``), swapped without
touching execution, and reasoned about without reading a backtest loop.

Every function here reads only ``[..i]`` at bar ``i``, so deriving on a series truncated at date
``d`` gives byte-identical values at every date ``<= d``.

**The skip-a-month convention.** :func:`mom_12_1` deliberately excludes the most recent 21 sessions.
Jegadeesh-Titman established that short-term reversal contaminates the last month of a momentum
lookback, and that skipping it strengthens the effect. A momentum signal WITHOUT the skip is
measuring two opposing forces at once — which is why :func:`reversal_z` exists as its own signal
rather than as a negative-momentum special case.

Design note on smoothers: this module never calls :func:`nq.data.features.ema`, which is the frozen
v1 convention (alpha 2/(span+1), seeded at bar 0). Anything needing Wilder smoothing uses
:mod:`nq.data.indicators`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["mom_generic", "mom_12_1", "mom_6_1", "high_52w_proximity", "reversal_z",
           "turnover_value", "delivery_quality", "realised_vol", "cross_sectional_rank",
           "vol_adjusted_return", "nse_momentum_score", "clenow_score", "above_sma",
           "max_gap", "SKIP_DAYS", "YEAR_DAYS"]

YEAR_DAYS = 252
SKIP_DAYS = 21          # the "skip the most recent month" convention


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


# --------------------------------------------------------------------------- momentum
def mom_generic(close, lookback: int, skip: int = SKIP_DAYS) -> np.ndarray:
    """Formation return over ``lookback`` sessions ending ``skip`` sessions ago.

        mom(t) = close[t - skip] / close[t - skip - lookback] - 1

    Both reference points are at or before ``t``, so the value at bar ``t`` uses no future data.
    NaN until ``skip + lookback`` bars of history exist.
    """
    c = _arr(close)
    n = len(c)
    out = np.full(n, np.nan)
    need = skip + lookback
    if n <= need:
        return out
    end = c[need - skip:n - skip]          # close[t - skip]
    start = c[:n - need]                   # close[t - skip - lookback]
    with np.errstate(divide="ignore", invalid="ignore"):
        out[need:] = np.where(start > 0, end / start - 1.0, np.nan)
    return out


def mom_12_1(close) -> np.ndarray:
    """The canonical 12-1: twelve-month formation, skipping the most recent month."""
    return mom_generic(close, lookback=YEAR_DAYS - SKIP_DAYS, skip=SKIP_DAYS)


def mom_6_1(close) -> np.ndarray:
    """Six-month formation, skipping the most recent month (Sehgal-Jain report 6-6 > 12-12 in India)."""
    return mom_generic(close, lookback=126 - SKIP_DAYS, skip=SKIP_DAYS)


def high_52w_proximity(close, high, window: int = YEAR_DAYS) -> np.ndarray:
    """``close / max(high, window)`` in (0, 1] — George-Hwang 52-week-high nearness.

    1.0 means the bar closed at its own 52-week high. The anchoring mechanism is that traders treat
    the 52-week high as a reference point and under-react as price approaches it. Documented as a
    left-tail lever rather than a return lever, so it is scored on drawdown as well as return.
    """
    c, h = _arr(close), _arr(high)
    hi = pd.Series(h).rolling(window, min_periods=window).max().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(hi > 0, c / hi, np.nan)


# --------------------------------------------------------------------------- NSE / vol-adjusted
def vol_adjusted_return(close, lookback: int, vol_window: int = YEAR_DAYS,
                        skip: int = SKIP_DAYS) -> np.ndarray:
    """Formation return divided by annualised volatility — NSE's ``MR`` term.

        MR = (P[t-skip] / P[t-skip-lookback] - 1) / sigma_annualised(daily log returns, vol_window)

    **This is not a refinement, it is the signal.** A raw-return ranking loads on whatever is most
    volatile, so the "winners" are simply the names with the widest distributions. Dividing by sigma
    puts a quiet compounder and a violent midcap on the same axis. StockViz's India adaptation of
    Ammann-Moellenbeck-Schmid found the volatility adjustment **essential** — raw-return ranking
    failed outright in India — and the NSE momentum indices bake it into the formula.
    """
    c = _arr(close)
    raw = mom_generic(c, lookback=lookback, skip=skip)
    lr = pd.Series(np.concatenate([[np.nan], np.diff(np.log(np.where(c > 0, c, np.nan)))]))
    sig = (lr.rolling(vol_window, min_periods=max(vol_window // 2, 20)).std(ddof=1)
           * np.sqrt(YEAR_DAYS)).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.isfinite(sig) & (sig > 0), raw / sig, np.nan)


def nse_momentum_score(panel: pd.DataFrame, *, date_col: str = "date",
                       mr12_col: str = "mr12", mr6_col: str = "mr6",
                       out_col: str = "nms") -> pd.DataFrame:
    """NSE's Normalized Momentum Score, verbatim from the Methodology Document.

        Z12 = zscore(MR12) across the eligible universe on that date;  Z6 likewise
        WAZ = 0.5*Z12 + 0.5*Z6
        NMS = (1 + WAZ)          if WAZ >= 0
              (1 - WAZ)**-1      if WAZ  < 0

    Two design points worth naming. Blending **6- and 12-month** legs hedges the lookback choice
    rather than betting the book on one horizon. And the piecewise transform is deliberately
    **asymmetric**: it is linear above zero but compresses below it, so a badly-scoring name maps
    toward zero instead of going negative — which is what makes NMS usable directly as a weight
    multiplier without a sign problem.
    """
    out = panel.copy()
    g = out.groupby(date_col)
    for src, z in ((mr12_col, "_z12"), (mr6_col, "_z6")):
        mu, sd = g[src].transform("mean"), g[src].transform("std")
        out[z] = (out[src] - mu) / sd.where(sd > 0)
    waz = 0.5 * out["_z12"] + 0.5 * out["_z6"]
    out[out_col] = np.where(waz >= 0, 1.0 + waz, 1.0 / (1.0 - waz))
    out.loc[waz.isna(), out_col] = np.nan
    return out.drop(columns=["_z12", "_z6"])


def clenow_score(close, window: int = 90, periods: int = 250) -> np.ndarray:
    """Clenow's volatility-adjusted momentum: annualised exponential-regression slope x R^2.

        fit ln(price) on time over `window` bars
        annualised_slope = exp(slope)**periods - 1
        score            = annualised_slope * r_squared

    The R-squared term is the whole idea: it discounts a steep move that arrived as one gap in
    favour of the same move delivered smoothly. A ragged 60% and a clean 60% rank very differently.
    """
    c = _arr(close)
    n = len(c)
    out = np.full(n, np.nan)
    if n < window:
        return out
    x = np.arange(window, dtype=float)
    xc = x - x.mean()
    sxx = float((xc ** 2).sum())
    logc = np.log(np.where(c > 0, c, np.nan))
    for i in range(window - 1, n):
        y = logc[i - window + 1:i + 1]
        if not np.isfinite(y).all():
            continue
        yc = y - y.mean()
        slope = float((xc * yc).sum() / sxx)
        ss_tot = float((yc ** 2).sum())
        if ss_tot <= 0:
            continue
        resid = yc - slope * xc
        r2 = 1.0 - float((resid ** 2).sum()) / ss_tot
        out[i] = (np.exp(slope) ** periods - 1.0) * r2
    return out


def above_sma(close, window: int) -> np.ndarray:
    """Clenow disqualifier: True where close is above its own ``window``-day SMA."""
    c = _arr(close)
    sma = pd.Series(c).rolling(window, min_periods=window).mean().to_numpy()
    return np.where(np.isfinite(sma), c > sma, False)


def max_gap(close, window: int = 90) -> np.ndarray:
    """Largest absolute single-session move over the trailing ``window`` — Clenow's gap filter.

    A >15% gap says the price history contains an event (a result, a block, a corporate action)
    rather than a trend, and the regression score cannot tell the difference.
    """
    c = _arr(close)
    r = pd.Series(c).pct_change().abs()
    return r.rolling(window, min_periods=max(window // 2, 5)).max().to_numpy()


# --------------------------------------------------------------------------- reversal
def reversal_z(close, short: int = 5, window: int = 63) -> np.ndarray:
    """Standardised short-term move: how unusual is the last ``short``-day return for THIS name.

        r = close[t]/close[t-short] - 1
        z = (r - mean(r, window)) / std(r, window)

    Negative z = an unusually sharp drop. Self-normalising, so a volatile midcap and a quiet
    largecap are on the same scale — which is what makes it usable cross-sectionally.
    """
    c = _arr(close)
    n = len(c)
    r = np.full(n, np.nan)
    if n > short:
        with np.errstate(divide="ignore", invalid="ignore"):
            r[short:] = np.where(c[:-short] > 0, c[short:] / c[:-short] - 1.0, np.nan)
    s = pd.Series(r)
    mu = s.rolling(window, min_periods=window).mean()
    sd = s.rolling(window, min_periods=window).std(ddof=1)
    return ((s - mu) / sd.where(sd > 0)).to_numpy()


# --------------------------------------------------------------------------- liquidity / quality
def turnover_value(close, volume, window: int = 63) -> np.ndarray:
    """Trailing median rupee turnover — the liquidity/size axis and the ADV cost input."""
    return pd.Series(_arr(close) * _arr(volume)).rolling(
        window, min_periods=max(window // 2, 2)).median().to_numpy()


def delivery_quality(delivery_pct, window: int = 63) -> np.ndarray:
    """Trailing median delivery % — the anti-speculation proxy.

    The compendium's filter is monthly traded value / market cap: low means patient institutional
    ownership, high means speculative churn. Market cap is not in this repo's fundamentals store, so
    delivery percentage stands in — it isolates shares actually transferred from intraday churn, and
    arguably measures the same thing more directly. **Stated as a proxy, not the original filter.**
    """
    return pd.Series(_arr(delivery_pct)).rolling(
        window, min_periods=max(window // 2, 2)).median().to_numpy()


def realised_vol(close, window: int = 126, periods: int = YEAR_DAYS) -> np.ndarray:
    """Annualised trailing realised volatility — the Barroso-Santa-Clara scaling input."""
    r = pd.Series(_arr(close)).pct_change()
    return (r.rolling(window, min_periods=max(window // 2, 2)).std(ddof=1)
            * np.sqrt(periods)).to_numpy()


# --------------------------------------------------------------------------- cross-section
def cross_sectional_rank(panel: pd.DataFrame, col: str, *, date_col: str = "date",
                         out_col: str = "rank", higher_is_better: bool = True) -> pd.DataFrame:
    """Per-date percentile rank in (0, 1]; 1.0 = best. NaNs stay NaN and never rank.

    Mirrors :func:`nq.data.eligibility.cross_sectional_rank`'s convention so a panel is
    interchangeable between engines.
    """
    out = panel.copy()
    out[out_col] = (out.groupby(date_col)[col]
                    .rank(pct=True, ascending=higher_is_better, na_option="keep"))
    return out
