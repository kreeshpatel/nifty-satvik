"""PIT / leakage guard for :mod:`nq.data.indicators` — the truncation invariance proof.

Same shape as ``tests/test_macro_pit.py``: deriving on a series truncated at date ``d`` must give
byte-identical values at every date ``<= d`` as deriving on the full series. Any forward-looking op
(centered window, full-sample normalisation, ``bfill``, ``shift(-k)``, or a period aggregate read
before its period closes) breaks this.

This matters most for the two stateful indicators. :func:`supertrend` carries band state forward
bar-by-bar, and :func:`period_pivot` aggregates over calendar periods — the exact place a
"use the current period's own high/low" mistake would hide, which is a genuine lookahead rather
than the (conservative) staleness bug fixed on 2026-08-06.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.data.indicators import (atr, ema, macd, period_pivot, rma, sma, stochastic, supertrend,
                                wilder_rsi)


def _series(n: int = 420):
    """Deterministic wiggly path — trend x sine x sawtooth. No RNG so failures are reproducible."""
    idx = pd.bdate_range("2023-01-02", periods=n)
    t = np.arange(n, dtype=float)
    c = 100.0 * np.exp(0.0006 * t) * (1.0 + 0.06 * np.sin(2 * np.pi * t / 47.0))
    h = c * (1.0 + 0.011 + 0.004 * np.cos(t / 5.0))
    l = c * (1.0 - 0.011 - 0.004 * np.sin(t / 7.0))
    return idx, h, l, c


CUT = 300   # truncate here; everything at or before this bar must be unchanged


@pytest.mark.parametrize("fn,kwargs", [
    (rma, {"n": 14}),
    (ema, {"span": 12}),
    (sma, {"window": 20}),
])
def test_single_series_smoothers_are_trailing_only(fn, kwargs):
    _, _, _, c = _series()
    full, trunc = fn(c, **kwargs), fn(c[:CUT], **kwargs)
    np.testing.assert_allclose(full[:CUT], trunc, equal_nan=True, rtol=0, atol=0)


def test_wilder_rsi_is_trailing_only():
    _, _, _, c = _series()
    np.testing.assert_allclose(wilder_rsi(c, 14)[:CUT], wilder_rsi(c[:CUT], 14),
                               equal_nan=True, rtol=0, atol=0)


def test_atr_is_trailing_only():
    _, h, l, c = _series()
    np.testing.assert_allclose(atr(h, l, c, 14)[:CUT], atr(h[:CUT], l[:CUT], c[:CUT], 14),
                               equal_nan=True, rtol=0, atol=0)


def test_supertrend_is_trailing_only():
    """Stateful band ratchet — truncating the future must not perturb any past bar."""
    _, h, l, c = _series()
    f_line, f_up = supertrend(h, l, c, 10, 3.0)
    t_line, t_up = supertrend(h[:CUT], l[:CUT], c[:CUT], 10, 3.0)
    np.testing.assert_allclose(f_line[:CUT], t_line, equal_nan=True, rtol=0, atol=0)
    np.testing.assert_array_equal(f_up[:CUT], t_up)


def test_macd_is_trailing_only():
    _, _, _, c = _series()
    for a, b in zip(macd(c), macd(c[:CUT])):
        np.testing.assert_allclose(a[:CUT], b, equal_nan=True, rtol=0, atol=0)


def test_stochastic_is_trailing_only():
    _, h, l, c = _series()
    for a, b in zip(stochastic(h, l, c, 14, 3), stochastic(h[:CUT], l[:CUT], c[:CUT], 14, 3)):
        np.testing.assert_allclose(a[:CUT], b, equal_nan=True, rtol=0, atol=0)


@pytest.mark.parametrize("freq", ["D", "W", "M", "Q"])
@pytest.mark.parametrize("level", ["P", "R1", "S1"])
def test_period_pivot_is_trailing_only(freq, level):
    """A pivot that read its OWN period's high/low would change when the future is removed."""
    idx, h, l, c = _series()
    full = period_pivot(idx, h, l, c, freq=freq, level=level)
    trunc = period_pivot(idx[:CUT], h[:CUT], l[:CUT], c[:CUT], freq=freq, level=level)
    np.testing.assert_allclose(full[:CUT], trunc, equal_nan=True, rtol=0, atol=0)


def test_period_pivot_truncation_probe_would_catch_a_same_period_read():
    """Guard-the-guard: prove the probe above can actually fail.

    A deliberately leaky pivot (this period's own aggregate, no shift) must break truncation
    invariance on the cut date — otherwise the passing tests prove nothing.
    """
    idx, h, l, c = _series()

    def leaky(index, high, low, close):
        per = pd.DatetimeIndex(index).to_period("Q")
        g = pd.DataFrame({"h": high, "l": low, "c": close}, index=index).groupby(per).agg(
            {"h": "max", "l": "min", "c": "last"})
        p = (g["h"] + g["l"] + g["c"]) / 3.0          # NO .shift(1) -> reads its own period
        return pd.Series(per.map(p), index=index).to_numpy(dtype=float)

    full = leaky(idx, h, l, c)
    trunc = leaky(idx[:CUT], h[:CUT], l[:CUT], c[:CUT])
    assert not np.allclose(full[:CUT], trunc, equal_nan=True), \
        "the truncation probe cannot detect lookahead — the guard is inert"
