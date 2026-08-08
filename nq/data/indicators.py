"""TradingView-parity technical indicators — trailing-only, pure, deterministic.

One source of truth for the indicator primitives that the swing/signal research needs, so the
throwaway ``scripts/diag_*.py`` explorers stop each re-deriving their own (and their own bugs).
Same motivation as :mod:`nq.data.weekly`, which exists because ~10 scripts each re-derived weekly
candles and drifted.

Everything here is **trailing-only**: the value at bar ``i`` reads only ``[..i]``. That makes the
truncation test byte-stable (``tests/test_indicators_pit.py``) — deriving on a series truncated at
date ``d`` must give identical values at every date ``<= d``.

.. warning::
   **Do NOT use :func:`nq.data.features.ema` to build an RSI or ATR that must match TradingView.**
   That function is ``alpha = 2/(span+1)`` seeded at bar 0 with no warm-up — deliberately frozen for
   source parity with the v1 long-horizon feature path. Wilder's smoothing (what TradingView's
   ``ta.rsi`` / ``ta.atr`` / Supertrend actually use) is ``alpha = 1/n`` seeded with ``SMA(first n)``.
   For a 14-period input the two differ by roughly 2x in effective span. Use :func:`rma` here.

The two EMA conventions in this repo, stated once:

===============================  ============================  ==========================
                                 ``nq.data.features.ema``      :func:`rma` (this module)
===============================  ============================  ==========================
alpha                            ``2/(span+1)``                ``1/n``
seed                             ``arr[0]``, no warm-up        ``SMA(arr[:n])``
NaN warm-up                      none                          ``n-1`` bars
matches                          the frozen v1 ATR             Pine ``ta.rma``
===============================  ============================  ==========================

:func:`ema` in this module is the *Pine* ``ta.ema`` convention (``alpha = 2/(span+1)`` seeded at the
first value) and is used only for MACD, where that is what TradingView does.

Public API
----------
``rma`` ``ema`` ``sma`` ``atr`` ``wilder_rsi`` ``supertrend`` ``period_pivot`` ``macd``
``stochastic`` ``fresh``
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .features import true_range

__all__ = ["rma", "ema", "sma", "atr", "wilder_rsi", "supertrend", "period_pivot", "macd",
           "stochastic", "fresh", "PIVOT_LEVELS"]

PIVOT_LEVELS: tuple[str, ...] = ("P", "R1", "R2", "S1", "S2")


# --------------------------------------------------------------------------- smoothers
def rma(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing — Pine ``ta.rma``. Seed ``SMA(x[:n])``, then ``a_i = a_{i-1} + (x_i - a_{i-1})/n``.

    NaN for the first ``n-1`` bars. This is the smoother behind ``ta.atr``, ``ta.rsi`` and
    Supertrend; it is NOT :func:`nq.data.features.ema` (see the module warning).
    """
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, np.nan, dtype=float)
    if len(x) < n or n < 1:
        return out
    s = pd.Series(x)
    tail = s.iloc[n - 1:].copy()
    tail.iloc[0] = s.iloc[:n].mean()
    out[n - 1:] = tail.ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    return out


def ema(x: np.ndarray, span: int) -> np.ndarray:
    """Pine ``ta.ema``: ``alpha = 2/(span+1)``, seeded at the first value, no NaN warm-up.

    Mathematically identical to :func:`nq.data.features.ema` (kept separate so this module has no
    reverse dependency on the frozen v1 feature path). Used here only for MACD.
    """
    return pd.Series(np.asarray(x, dtype=float)).ewm(span=span, adjust=False).mean().to_numpy()


def sma(x: np.ndarray, window: int) -> np.ndarray:
    """Trailing simple moving average; NaN before bar ``window-1``."""
    return pd.Series(np.asarray(x, dtype=float)).rolling(window).mean().to_numpy()


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> np.ndarray:
    """Wilder ATR — ``rma(true_range, n)``, matching Pine ``ta.atr``.

    Reuses :func:`nq.data.features.true_range` (``tr[0] = high[0]-low[0]``, thereafter
    ``max(H-L, |H-C_prev|, |L-C_prev|)``), which is the same convention as Pine ``ta.tr``.
    """
    return rma(true_range(high, low, close), n)


def wilder_rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    """Pine ``ta.rsi``: ``100 - 100/(1 + rma(gain,n)/rma(loss,n))``.

    Bar 0 is NaN (no prior close, so no change), and the first defined value lands on bar ``n``.
    Degenerate windows follow Pine: all-gain (``loss == 0``) -> 100, all-loss -> 0.
    """
    close = np.asarray(close, dtype=float)
    out = np.full(close.shape, np.nan, dtype=float)
    if len(close) <= n:
        return out
    d = np.diff(close)                              # d[k] = close[k+1] - close[k]; no NaN
    up, dn = rma(np.clip(d, 0.0, None), n), rma(np.clip(-d, 0.0, None), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = up / np.where(dn == 0.0, np.nan, dn)
        val = 100.0 - 100.0 / (1.0 + rs)
    defined = np.isfinite(up) & np.isfinite(dn)
    val[defined & (dn == 0.0)] = 100.0              # all-gain window
    val[defined & (up == 0.0) & (dn > 0.0)] = 0.0   # all-loss window
    out[1:] = val
    return out


# --------------------------------------------------------------------------- supertrend
def supertrend(high: np.ndarray, low: np.ndarray, close: np.ndarray,
               atr_len: int = 10, factor: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """TradingView Supertrend — returns ``(line, is_uptrend)``.

    Verbatim from TradingView's published formulation
    (support/solutions/43000634738)::

        hl2        = (high + low) / 2
        basicUpper = hl2 + factor * ta.atr(atr_len)
        basicLower = hl2 - factor * ta.atr(atr_len)
        upperBand  = basicUpper < prevUpper or prevClose > prevUpper ? basicUpper : prevUpper
        lowerBand  = basicLower > prevLower or prevClose < prevLower ? basicLower : prevLower
        dir        = prevST == prevUpper ? (close > upperBand ? UP : DOWN)
                                         : (close < lowerBand ? DOWN : UP)
        superTrend = dir == UP ? lowerBand : upperBand

    The bands **ratchet** (only tighten toward price) until price closes through, then flip. The
    first bar with a defined ATR seeds DOWN, matching TV's "until the ATR value is calculated"
    branch. Defaults are TradingView's (ATR Length 10, Factor 3).

    Sequential by construction — the band state at bar ``i`` depends on bar ``i-1`` — so it cannot
    be vectorised without changing the result.
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    n = len(close)
    a = atr(high, low, close, atr_len)
    hl2 = (high + low) / 2.0
    basic_up, basic_dn = hl2 + factor * a, hl2 - factor * a

    line = np.full(n, np.nan, dtype=float)
    up_trend = np.zeros(n, dtype=bool)
    prev_upper = prev_lower = prev_line = np.nan
    for i in range(n):
        if not np.isfinite(basic_up[i]):
            continue
        if not np.isfinite(prev_upper):             # first bar with an ATR: TV seeds DOWN
            prev_upper, prev_lower = basic_up[i], basic_dn[i]
            up_trend[i] = False
            line[i] = prev_line = prev_upper
            continue
        pc = close[i - 1]
        upper = basic_up[i] if (basic_up[i] < prev_upper or pc > prev_upper) else prev_upper
        lower = basic_dn[i] if (basic_dn[i] > prev_lower or pc < prev_lower) else prev_lower
        up = (close[i] > upper) if prev_line == prev_upper else not (close[i] < lower)
        up_trend[i] = up
        line[i] = lower if up else upper
        prev_upper, prev_lower, prev_line = upper, lower, line[i]
    return line, up_trend


# --------------------------------------------------------------------------- pivots
def period_pivot(index: pd.DatetimeIndex, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 *, freq: str = "M", level: str = "P") -> np.ndarray:
    """Traditional pivot of the **prior completed period**, held flat across the current one.

    ``freq`` is a pandas *period* alias — ``"D"`` (prior trading day), ``"W"``, ``"M"``, ``"Q"``,
    ``"Y"``. ``level`` is one of :data:`PIVOT_LEVELS`::

        P  = (H + L + C) / 3
        R1 = 2P - L      S1 = 2P - H
        R2 = P + (H - L) S2 = P - (H - L)

    H/L/C are aggregated from the **daily** bars of the prior period — TradingView's "Use
    daily-based values" behaviour.

    .. note::
       **Bug receipt (fixed 2026-08-06).** The prior implementation was
       ``resample(freq).shift(1).reindex(index, method="ffill")``, which *double-shifts*: period-END
       labels sort AFTER the dates they should govern, so the ffill reindex picks up the previous
       label whose value is already shifted. The level in force was therefore **two periods stale**
       for the whole period (and NaN for the first one) — verified on a synthetic quarter, where Q3
       dates received Q1's pivot instead of Q2's. Conservative (older data, no lookahead) but not
       the rule. Mapping each date to its OWN period and reading that period's shifted value is the
       fix, and ``tests/test_indicators.py`` pins hand-computed values so it cannot regress.
    """
    if level not in PIVOT_LEVELS:
        raise ValueError(f"level must be one of {PIVOT_LEVELS}, got {level!r}")
    index = pd.DatetimeIndex(index)
    per = index.to_period(freq)
    g = pd.DataFrame({"h": np.asarray(high, dtype=float),
                      "l": np.asarray(low, dtype=float),
                      "c": np.asarray(close, dtype=float)},
                     index=index).groupby(per).agg({"h": "max", "l": "min", "c": "last"})
    p = (g["h"] + g["l"] + g["c"]) / 3.0
    val = {"P": p,
           "R1": 2 * p - g["l"], "S1": 2 * p - g["h"],
           "R2": p + (g["h"] - g["l"]), "S2": p - (g["h"] - g["l"])}[level]
    return pd.Series(per.map(val.shift(1)), index=index).to_numpy(dtype=float)


# --------------------------------------------------------------------------- oscillators
def macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
         ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pine ``ta.macd`` — returns ``(macd_line, signal_line, histogram)``."""
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def stochastic(high: np.ndarray, low: np.ndarray, close: np.ndarray, k: int = 14, d: int = 3
               ) -> tuple[np.ndarray, np.ndarray]:
    """Pine ``ta.stoch`` — returns ``(%K, %D)`` where ``%D = SMA(%K, d)``.

    ``%K = 100 * (close - LL(k)) / (HH(k) - LL(k))``; NaN on a zero-range window.
    """
    high, low, close = (np.asarray(v, dtype=float) for v in (high, low, close))
    hh = pd.Series(high).rolling(k).max().to_numpy()
    ll = pd.Series(low).rolling(k).min().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        pk = 100.0 * (close - ll) / np.where(hh - ll > 0, hh - ll, np.nan)
    return pk, sma(pk, d)


# --------------------------------------------------------------------------- helpers
def fresh(flag: np.ndarray) -> np.ndarray:
    """Rising edge of a boolean array — True where ``flag`` is True and was False on the prior bar.

    Turns a *state* ("the condition holds") into an *event* ("the condition just became true"),
    which is what an entry trigger needs. Bar 0 is a rising edge iff ``flag[0]``.
    """
    b = np.asarray(flag, dtype=bool)
    return b & ~np.concatenate([[False], b[:-1]])
