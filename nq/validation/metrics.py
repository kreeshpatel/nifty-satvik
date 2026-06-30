"""Risk/return metrics on a return or equity series — the clean, decoupled validators.

The same definitions the engine's ``compute_metrics`` uses, factored out as pure functions over a
daily-return array so the validation layer (bootstrap CI, CPCV path distribution) can score any
return series without the engine. Annualization uses ``TRADING_DAYS = 252``.
"""
from __future__ import annotations

import numpy as np

TRADING_DAYS = 252


def _returns(x: np.ndarray) -> np.ndarray:
    r = np.asarray(x, dtype=float)
    return r[np.isfinite(r)]


def sharpe(returns: np.ndarray, *, periods: int = TRADING_DAYS) -> float:
    """Annualized Sharpe: ``mean / std × √periods`` (population-free std, ddof=0 — matching the
    engine). NaN when the series has no dispersion."""
    r = _returns(returns)
    sd = r.std()
    return float(r.mean() / sd * np.sqrt(periods)) if sd > 0 else float("nan")


def sortino(returns: np.ndarray, *, periods: int = TRADING_DAYS) -> float:
    """Annualized Sortino: ``mean / downside_std × √periods`` (downside = negative returns)."""
    r = _returns(returns)
    downside = r[r < 0]
    sd = downside.std()
    return float(r.mean() / sd * np.sqrt(periods)) if downside.size and sd > 0 else float("nan")


def max_drawdown(equity: np.ndarray) -> float:
    """Worst peak-to-trough fraction of an equity curve (<= 0)."""
    eq = np.asarray(equity, dtype=float)
    if eq.size == 0:
        return float("nan")
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def cagr(equity: np.ndarray, *, periods: int = TRADING_DAYS) -> float:
    """Compound annual growth rate of an equity curve."""
    eq = np.asarray(equity, dtype=float)
    n = eq.size
    years = n / periods
    if years <= 0 or eq[0] <= 0:
        return float("nan")
    return float((eq[-1] / eq[0]) ** (1.0 / years) - 1.0)


def calmar(equity: np.ndarray, *, periods: int = TRADING_DAYS) -> float:
    """CAGR / |max drawdown| — return per unit of worst-case pain."""
    c = cagr(equity, periods=periods)
    dd = max_drawdown(equity)
    return float(c / abs(dd)) if dd != 0 and np.isfinite(c) and np.isfinite(dd) else float("nan")


def equity_from_returns(returns: np.ndarray, *, initial: float = 1.0) -> np.ndarray:
    """Compound a daily-return series into an equity curve (prepends the initial level)."""
    r = np.asarray(returns, dtype=float)
    return initial * np.cumprod(np.concatenate([[1.0], 1.0 + r]))


def summary(returns: np.ndarray, *, periods: int = TRADING_DAYS) -> dict[str, float]:
    """Headline metrics for a daily-return series (Sharpe, Sortino, CAGR, maxDD, Calmar)."""
    eq = equity_from_returns(returns)
    return {
        "sharpe": sharpe(returns, periods=periods),
        "sortino": sortino(returns, periods=periods),
        "cagr": cagr(eq, periods=periods),
        "max_drawdown": max_drawdown(eq),
        "calmar": calmar(eq, periods=periods),
    }
