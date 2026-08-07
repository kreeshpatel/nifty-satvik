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


def cagr(equity: np.ndarray, *, periods: int = TRADING_DAYS, years: float | None = None) -> float:
    """Compound annual growth rate of an equity curve. **``years`` is required** — see below.

    DIVERGENCE, recorded deliberately (2026-08-07, ADR-0014). ``nq.engine.portfolio.compute_metrics``
    now annualises by **calendar time** via ``elapsed_years``, because the panels supply ~247.5
    sessions per calendar year rather than 252 and the shorter denominator inflated every published
    CAGR by ~0.44pp. This function was NOT changed to match, for two reasons:

    1. It is the site ``DEFINITIONS_REGISTER.md`` §6 names as canonical for the bar-year convention,
       and §6 is an open DOOR whose resolution is routed to the owner's review binder. Silently
       flipping a convention that a governance register catalogues would defeat the register.
    2. Nothing published reads it. Every external caller of this module imports ``sharpe`` or
       ``sortino``; ``cagr`` is reached only by :func:`calmar`, :func:`summary` and their own tests.

    ``years`` IS REQUIRED, and that is the point. This function cannot annualise by calendar time
    even if it wanted to — it receives a bare array with no dates — so the convention is necessarily
    the caller's decision. Leaving it as a silent default is the one option ruled out: a future
    session reaching for the module named *canonical* would get bar-years without being told, which
    is exactly how the same book came to carry two published CAGRs (§6). Passing ``years`` makes the
    choice deliberate; omitting it raises with the two readings named.

    For a headline CAGR call :func:`nq.engine.portfolio.compute_metrics`, which has the dates and
    uses calendar time.
    """
    eq = np.asarray(equity, dtype=float)
    if years is None:
        raise ValueError(
            "nq.validation.metrics.cagr requires an explicit `years`: this function has no dates, "
            "so it cannot choose a year-denominator for you. Bar-years -> years=len(equity)/252 "
            "(the DEFINITIONS_REGISTER §6 convention for this module); calendar years -> "
            "years=(last-first).days/365.25 (ADR-0014, what the engine uses). They differ by ~0.44pp "
            "on this programme's panels. For a headline number call "
            "nq.engine.portfolio.compute_metrics instead.")
    if years <= 0 or eq.size == 0 or eq[0] <= 0:
        return float("nan")
    return float((eq[-1] / eq[0]) ** (1.0 / years) - 1.0)


def calmar(equity: np.ndarray, *, periods: int = TRADING_DAYS) -> float:
    """CAGR / |max drawdown| — return per unit of worst-case pain, on **bar-years**.

    States the convention explicitly rather than inheriting a default, per §6/ADR-0014. Like
    :func:`cagr` it has no dates available, so bar-years is the only denominator it can compute.
    """
    c = cagr(equity, periods=periods, years=np.asarray(equity).size / periods)
    dd = max_drawdown(equity)
    return float(c / abs(dd)) if dd != 0 and np.isfinite(c) and np.isfinite(dd) else float("nan")


def equity_from_returns(returns: np.ndarray, *, initial: float = 1.0) -> np.ndarray:
    """Compound a daily-return series into an equity curve (prepends the initial level)."""
    r = np.asarray(returns, dtype=float)
    return initial * np.cumprod(np.concatenate([[1.0], 1.0 + r]))


def summary(returns: np.ndarray, *, periods: int = TRADING_DAYS) -> dict[str, float]:
    """Headline metrics for a daily-return series (Sharpe, Sortino, CAGR, maxDD, Calmar).

    Its ``cagr`` is on **bar-years**, stated explicitly (§6/ADR-0014). A return series carries no
    dates, so calendar annualisation is not available here; do not quote this ``cagr`` against an
    engine CAGR without converting.
    """
    eq = equity_from_returns(returns)
    return {
        "sharpe": sharpe(returns, periods=periods),
        "sortino": sortino(returns, periods=periods),
        "cagr": cagr(eq, periods=periods, years=eq.size / periods),
        "max_drawdown": max_drawdown(eq),
        "calmar": calmar(eq, periods=periods),
    }
