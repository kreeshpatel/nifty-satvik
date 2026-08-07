"""Value tests for :mod:`nq.data.indicators` — hand-computed expectations, no RNG.

The pivot cases here are the regression receipt for the 2026-08-06 double-shift defect: the old
``resample().shift(1).reindex(ffill)` implementation left the level TWO periods stale, so Q3 dates
received Q1's pivot. ``test_period_pivot_is_not_two_periods_stale`` fails loudly on that shape.

Following the repo's guard discipline: every "this is caught" assertion is paired with a "this does
not false-trip" assertion, because a guard that only ever passes is indistinguishable from no guard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.data import features
from nq.data.indicators import (atr, ema, fresh, macd, period_pivot, rma, sma, stochastic,
                                supertrend, wilder_rsi)


# --------------------------------------------------------------------------- fixtures
def _ramp(n_start: str = "2024-01-01", n_end: str = "2024-09-30"):
    """Deterministic monotone ramp: close = 100+i-1, high = 100+i, low = 95+i. No RNG, no clock."""
    idx = pd.bdate_range(n_start, n_end)
    h = np.arange(len(idx), dtype=float) + 100.0
    return idx, h, h - 5.0, h - 1.0


# --------------------------------------------------------------------------- rma / ema
def test_rma_seed_is_sma_and_warmup_is_nan():
    x = np.arange(1, 21, dtype=float)
    out = rma(x, 5)
    assert np.all(np.isnan(out[:4]))            # n-1 warm-up
    assert out[4] == pytest.approx(x[:5].mean())  # seed = SMA(first n) == 3.0
    # recursion: a_i = a_{i-1} + (x_i - a_{i-1})/n
    assert out[5] == pytest.approx(out[4] + (x[5] - out[4]) / 5)


def test_rma_is_not_the_frozen_v1_ema():
    """The two smoothing conventions must stay distinct.

    ``nq.data.features.ema`` is alpha=2/(span+1) seeded at bar 0; ``rma`` is alpha=1/n seeded at
    SMA(first n). Anyone 'simplifying' one into the other silently re-introduces the class of bug
    this module exists to prevent, so pin that they differ materially.
    """
    x = np.arange(1, 61, dtype=float)
    assert not np.allclose(rma(x, 14)[20:], features.ema(x, 14)[20:], rtol=1e-3)


def test_ema_matches_the_frozen_v1_ema():
    """This module's ``ema`` IS the Pine/v1 convention — pinned so MACD stays TV-comparable."""
    x = np.arange(1, 61, dtype=float)
    assert np.allclose(ema(x, 12), features.ema(x, 12))


def test_sma_is_trailing():
    x = np.arange(1, 11, dtype=float)
    out = sma(x, 3)
    assert np.all(np.isnan(out[:2]))
    assert out[2] == pytest.approx(2.0)
    assert out[9] == pytest.approx(9.0)


# --------------------------------------------------------------------------- atr / rsi
def test_atr_is_rma_of_true_range():
    _, h, l, c = _ramp()
    assert np.allclose(atr(h, l, c, 14), rma(features.true_range(h, l, c), 14), equal_nan=True)


def test_rsi_saturates_at_100_up_and_0_down():
    up = np.arange(1, 60, dtype=float)
    assert wilder_rsi(up, 14)[-1] == pytest.approx(100.0)
    assert wilder_rsi(up[::-1].copy(), 14)[-1] == pytest.approx(0.0)


def test_rsi_first_defined_bar_is_n():
    """Bar 0 has no change; the first Wilder-seeded value lands on bar n."""
    c = np.arange(1, 40, dtype=float)
    out = wilder_rsi(c, 14)
    assert np.all(np.isnan(out[:14]))
    assert np.isfinite(out[14])


def test_rsi_is_mirror_symmetric():
    """Reflecting the path about its mean flips every change, so RSI must become ``100 - RSI``.

    This is the real invariant, and it catches a gain/loss swap exactly. (A balanced sawtooth is
    NOT a clean 50 test: with strict alternation the smoothed gain and loss series are half a
    period out of phase, so the last bar reads ~52 depending on which way it moved last.)
    """
    _, _, _, c = _ramp()
    mirrored = 2.0 * c.mean() - c
    a, b = wilder_rsi(c, 14), wilder_rsi(mirrored, 14)
    ok = np.isfinite(a) & np.isfinite(b)
    np.testing.assert_allclose(b[ok], 100.0 - a[ok], atol=1e-9)


# --------------------------------------------------------------------------- supertrend
def test_supertrend_follows_a_clean_trend_and_sits_on_the_right_side():
    _, h, l, c = _ramp()
    line, up = supertrend(h, l, c, 10, 3.0)
    tail = slice(60, None)
    assert up[tail].all()                       # sustained uptrend
    assert np.all(line[tail] < c[tail])         # in an uptrend the line trails BELOW price
    down = supertrend(h[::-1].copy(), l[::-1].copy(), c[::-1].copy(), 10, 3.0)
    assert not down[1][tail].any()
    assert np.all(down[0][tail] > c[::-1][tail])  # in a downtrend it sits ABOVE


def test_supertrend_band_ratchets_within_a_trend():
    """The defining property: within an uptrend the line only tightens toward price."""
    _, h, l, c = _ramp()
    line, up = supertrend(h, l, c, 10, 3.0)
    seg = line[60:]
    assert np.all(np.diff(seg) >= -1e-9), "uptrend line must be non-decreasing (ratchet)"


def test_supertrend_flips_on_a_reversal():
    """Guard-the-guard: a fixture that never flips would not prove the flip logic runs."""
    idx = pd.bdate_range("2024-01-01", periods=300)
    ramp = np.concatenate([np.arange(150, dtype=float), 150 - np.arange(150, dtype=float)])
    c = 100.0 + ramp
    _, up = supertrend(c + 1.0, c - 1.0, c, 10, 3.0)
    assert up[100] and not up[-1], "expected an up->down flip across the reversal"
    assert len(idx) == 300


# --------------------------------------------------------------------------- pivots
def test_period_pivot_quarterly_hand_computed():
    """Q1 H/L/C = 164/95/163 -> P = 140.667 ; Q2 = 229/160/228 -> P = 205.667."""
    idx, h, l, c = _ramp()
    p = pd.Series(period_pivot(idx, h, l, c, freq="Q", level="P"), index=idx)
    assert p.loc["2024-05-15"] == pytest.approx(140.6666667)   # Q2 uses Q1
    assert p.loc["2024-08-15"] == pytest.approx(205.6666667)   # Q3 uses Q2
    r1 = pd.Series(period_pivot(idx, h, l, c, freq="Q", level="R1"), index=idx)
    assert r1.loc["2024-05-15"] == pytest.approx(2 * 140.6666667 - 95.0)
    assert r1.loc["2024-08-15"] == pytest.approx(2 * 205.6666667 - 160.0)


def test_period_pivot_is_not_two_periods_stale():
    """REGRESSION (2026-08-06). The double-shift bug gave Q3 dates Q1's pivot."""
    idx, h, l, c = _ramp()
    p = pd.Series(period_pivot(idx, h, l, c, freq="Q", level="P"), index=idx)
    q1, q2 = 140.6666667, 205.6666667
    assert p.loc["2024-08-15"] != pytest.approx(q1), "two-periods-stale bug has regressed"
    assert p.loc["2024-08-15"] == pytest.approx(q2)
    assert np.isfinite(p.loc["2024-05-15"]), "Q2 must be defined, not NaN"


def test_period_pivot_is_flat_within_a_period_and_nan_in_the_first():
    idx, h, l, c = _ramp()
    p = pd.Series(period_pivot(idx, h, l, c, freq="Q", level="P"), index=idx)
    assert p.loc["2024-04-01":"2024-06-28"].nunique() == 1
    assert p.loc["2024-07-01":"2024-09-30"].nunique() == 1
    assert p.loc["2024-01-02":"2024-03-28"].isna().all()   # no prior quarter exists


def test_period_pivot_daily_uses_the_prior_trading_day():
    idx, h, l, c = _ramp()
    p = period_pivot(idx, h, l, c, freq="D", level="P")
    expected = (h[10] + l[10] + c[10]) / 3.0     # bar 11 reads bar 10
    assert p[11] == pytest.approx(expected)
    assert np.isnan(p[0])


def test_period_pivot_monthly_steps_once_per_month():
    idx, h, l, c = _ramp()
    p = pd.Series(period_pivot(idx, h, l, c, freq="M", level="P"), index=idx)
    steps = p.resample("MS").first().dropna()
    assert steps.is_monotonic_increasing and len(steps) >= 7


def test_period_pivot_rejects_an_unknown_level():
    idx, h, l, c = _ramp()
    with pytest.raises(ValueError):
        period_pivot(idx, h, l, c, freq="M", level="R9")


# --------------------------------------------------------------------------- oscillators
def test_macd_line_is_fast_minus_slow_and_hist_closes():
    _, _, _, c = _ramp()
    line, sig, hist = macd(c)
    assert np.allclose(line, ema(c, 12) - ema(c, 26))
    assert np.allclose(hist, line - sig, equal_nan=True)


def test_stochastic_pins_at_the_extremes():
    _, h, l, c = _ramp()
    pk, pd_ = stochastic(h, l, c, 14, 3)
    assert pk[-1] == pytest.approx(100.0 * (c[-1] - l[-14]) / (h[-1] - l[-14]))
    assert np.isfinite(pd_[-1])
    down_pk, _ = stochastic(h[::-1].copy(), l[::-1].copy(), c[::-1].copy(), 14, 3)
    assert down_pk[-1] < 50.0


# --------------------------------------------------------------------------- helpers
def test_fresh_is_a_rising_edge():
    b = np.array([False, True, True, False, True], dtype=bool)
    assert list(fresh(b)) == [False, True, False, False, True]
    assert list(fresh(np.array([True, True]))) == [True, False]   # bar 0 counts as an edge
