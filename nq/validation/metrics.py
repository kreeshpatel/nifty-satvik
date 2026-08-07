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
    engine). NaN when the series has no dispersion.

    **Risk-free rate is ZERO** — this is a raw-return Sharpe, not an excess-return Sharpe. With an
    Indian rf of ~6–7% that OVERSTATES risk-adjusted excess return in LEVEL terms. It cancels in any
    ΔSharpe comparison (how this programme almost always uses it) but NOT in an absolute threshold;
    the one absolute gate is ``KILL_SHARPE`` in ``scripts/bhanushali_review_scorecard.py``.
    ``periods`` must match the series frequency (252 daily / 52 weekly / 12 monthly) — mixing them
    is the single highest-consequence error here. See ``DEFINITIONS_REGISTER.md`` §8."""
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
    """Compound annual growth rate of an equity curve, on **trading-bar years** (``n / periods``).

    DIVERGENCE, recorded deliberately (2026-08-07, ADR-0014). ``nq.engine.portfolio.compute_metrics``
    now annualises by **calendar time** via ``elapsed_years``, because the panels supply ~247.5
    sessions per calendar year rather than 252 and the shorter denominator inflated every published
    CAGR by ~0.44pp. This function was NOT changed to match, for two reasons:

    1. It is the site ``DEFINITIONS_REGISTER.md`` §6 names as canonical for the bar-year convention,
       and §6 is an open DOOR whose resolution is routed to the owner's review binder. Silently
       flipping a convention that a governance register catalogues would defeat the register.
    2. Nothing published reads it. Every external caller of this module imports ``sharpe`` or
       ``sortino``; ``cagr`` is reached only by :func:`calmar`, :func:`summary` and their own tests.

    So the divergence is dormant rather than harmless. **Do not use this for a headline CAGR** — call
    ``compute_metrics``, or pass an explicit calendar-derived ``periods``. If §6 is ever closed in
    favour of calendar years, this is the second site to change.
    """
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
