"""Value + PIT tests for :mod:`nq.signals`.

Two jobs. First, hand-computed expectations — a momentum signal that quietly drops the skip window,
or reads one bar too far forward, produces a plausible-looking number that is wrong, and only an
arithmetic pin catches it. Second, truncation invariance (same shape as ``tests/test_macro_pit.py``):
deriving on a truncated series must give byte-identical values at every date in common.

The guard-the-guard test at the end proves the truncation probe can actually fail, by feeding it a
deliberately leaky signal. A probe that passes everything is indistinguishable from no probe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.signals import (SKIP_DAYS, YEAR_DAYS, above_sma, clenow_score, cross_sectional_rank,
                        delivery_quality, high_52w_proximity, max_gap, mom_6_1, mom_12_1,
                        mom_generic, nse_momentum_score, realised_vol, reversal_z,
                        turnover_value, vol_adjusted_return)

N = 420
CUT = 300


def _ramp(n: int = N) -> np.ndarray:
    """close = 100, 101, 102, ... — every return is computable by hand."""
    return 100.0 + np.arange(n, dtype=float)


def _wiggle(n: int = N) -> np.ndarray:
    t = np.arange(n, dtype=float)
    return 100.0 * np.exp(0.0007 * t) * (1 + 0.05 * np.sin(2 * np.pi * t / 41.0))


# --------------------------------------------------------------------------- momentum values
def test_mom_generic_is_hand_computable():
    c = _ramp()
    out = mom_generic(c, lookback=100, skip=10)
    i = 300
    assert out[i] == pytest.approx(c[i - 10] / c[i - 10 - 100] - 1.0)


def test_mom_generic_warmup_is_nan():
    c = _ramp()
    out = mom_generic(c, lookback=100, skip=10)
    assert np.all(np.isnan(out[:110]))
    assert np.isfinite(out[110])


def test_mom_12_1_skips_exactly_one_month():
    """The skip is the whole point — a 12-1 that reads to t is a different, contaminated signal."""
    c = _wiggle()
    i = 400
    got = mom_12_1(c)[i]
    expected = c[i - SKIP_DAYS] / c[i - SKIP_DAYS - (YEAR_DAYS - SKIP_DAYS)] - 1.0
    assert got == pytest.approx(expected)
    # and it must NOT equal the no-skip version, or the convention silently vanished
    no_skip = c[i] / c[i - YEAR_DAYS] - 1.0
    assert got != pytest.approx(no_skip)


def test_mom_12_1_total_lookback_is_one_year():
    c = _ramp()
    out = mom_12_1(c)
    assert np.all(np.isnan(out[:YEAR_DAYS]))
    assert np.isfinite(out[YEAR_DAYS])


def test_mom_6_1_is_shorter_than_mom_12_1():
    c = _ramp()
    assert np.isfinite(mom_6_1(c)[126]) and np.isnan(mom_12_1(c)[126])


def test_momentum_is_positive_on_a_rising_series_and_negative_on_a_falling_one():
    c = _ramp()
    assert mom_12_1(c)[-1] > 0
    assert mom_12_1(c[::-1].copy())[-1] < 0


# --------------------------------------------------------------------------- 52-week high
def test_high_52w_is_one_at_a_new_high_and_below_one_otherwise():
    c = _ramp()
    prox = high_52w_proximity(c, c)          # close == high on a monotone ramp
    assert prox[-1] == pytest.approx(1.0)
    c2 = c.copy()
    c2[-1] = c[-1] * 0.80                    # close 20% below the running high
    prox2 = high_52w_proximity(c2, c)
    assert prox2[-1] == pytest.approx(0.80, rel=1e-6)


def test_high_52w_warmup_is_nan():
    c = _ramp()
    assert np.all(np.isnan(high_52w_proximity(c, c)[:YEAR_DAYS - 1]))


# --------------------------------------------------------------------------- reversal
def test_reversal_z_is_negative_after_a_sharp_drop():
    c = _wiggle().copy()
    c[350:] *= 0.80                          # a 20% gap down
    assert reversal_z(c)[352] < -1.0


def test_reversal_z_is_scale_free():
    """A name at Rs 50 and the same path at Rs 5000 must give identical z — that is what makes it
    comparable across the cross-section."""
    c = _wiggle()
    a, b = reversal_z(c), reversal_z(c * 100.0)
    ok = np.isfinite(a) & np.isfinite(b)
    np.testing.assert_allclose(a[ok], b[ok], rtol=1e-9)


def test_reversal_z_and_momentum_disagree_by_construction():
    """They measure opposite horizons; if they correlated strongly one of them is mis-specified."""
    c = _wiggle()
    m, z = mom_12_1(c), reversal_z(c)
    ok = np.isfinite(m) & np.isfinite(z)
    assert abs(np.corrcoef(m[ok], z[ok])[0, 1]) < 0.9


# --------------------------------------------------------------------------- liquidity / vol
def test_turnover_is_price_times_volume():
    c = np.full(50, 100.0)
    v = np.full(50, 1000.0)
    assert turnover_value(c, v, window=10)[-1] == pytest.approx(100_000.0)


def test_delivery_quality_is_a_trailing_median():
    d = np.concatenate([np.full(40, 20.0), np.full(40, 80.0)])
    out = delivery_quality(d, window=21)
    assert out[39] == pytest.approx(20.0)
    assert out[-1] == pytest.approx(80.0)


def test_realised_vol_rises_with_dispersion():
    calm = np.full(300, 100.0) + np.sin(np.arange(300)) * 0.1
    wild = np.full(300, 100.0) + np.sin(np.arange(300)) * 10.0
    assert realised_vol(wild)[-1] > realised_vol(calm)[-1]


# --------------------------------------------------------------------------- cross-section
def test_cross_sectional_rank_is_per_date_and_one_is_best():
    panel = pd.DataFrame({
        "date": ["2024-01-01"] * 4 + ["2024-01-02"] * 4,
        "ticker": list("ABCD") * 2,
        "sig": [1.0, 2.0, 3.0, 4.0, 40.0, 30.0, 20.0, 10.0]})
    out = cross_sectional_rank(panel, "sig")
    d1 = out[out["date"] == "2024-01-01"]
    assert d1.loc[d1["sig"].idxmax(), "rank"] == pytest.approx(1.0)
    d2 = out[out["date"] == "2024-01-02"]
    assert d2.loc[d2["sig"].idxmax(), "rank"] == pytest.approx(1.0)


def test_cross_sectional_rank_keeps_nan_out_of_the_ranking():
    panel = pd.DataFrame({"date": ["d"] * 3, "ticker": list("ABC"), "sig": [1.0, np.nan, 3.0]})
    out = cross_sectional_rank(panel, "sig")
    assert np.isnan(out.loc[1, "rank"])
    assert out.loc[2, "rank"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- NSE / vol-adjusted
def test_vol_adjustment_reorders_two_names_with_the_same_raw_return():
    """The reason the adjustment exists: identical raw return, different path smoothness.

    Raw ranking cannot separate these two. Dividing by sigma must prefer the quiet one — that is the
    whole finding behind 'raw-return ranking failed in India'.
    """
    n = 400
    t = np.arange(n, dtype=float)
    smooth = 100.0 * np.exp(0.001 * t)
    noisy = smooth * (1 + 0.08 * np.sin(t * 1.7))          # same trend, far more dispersion
    noisy[-1] = smooth[-1]                                  # force identical end price
    i = n - 1
    raw_s = mom_generic(smooth, YEAR_DAYS - SKIP_DAYS)[i]
    raw_n = mom_generic(noisy, YEAR_DAYS - SKIP_DAYS)[i]
    adj_s = vol_adjusted_return(smooth, YEAR_DAYS - SKIP_DAYS)[i]
    adj_n = vol_adjusted_return(noisy, YEAR_DAYS - SKIP_DAYS)[i]
    assert np.isfinite(adj_s) and np.isfinite(adj_n)
    assert adj_s > adj_n, "vol adjustment must favour the smoother path"
    assert abs(raw_s - raw_n) < abs(adj_s - adj_n), "adjustment must SEPARATE them more than raw"


def test_vol_adjusted_return_is_raw_over_sigma():
    c = _wiggle()
    i = 350
    lb = YEAR_DAYS - SKIP_DAYS
    lr = pd.Series(np.concatenate([[np.nan], np.diff(np.log(c))]))
    sig = lr.rolling(YEAR_DAYS, min_periods=126).std(ddof=1).to_numpy()[i] * np.sqrt(YEAR_DAYS)
    assert vol_adjusted_return(c, lb)[i] == pytest.approx(mom_generic(c, lb)[i] / sig)


def test_nse_nms_transform_is_asymmetric_and_positive():
    """NMS = 1+WAZ above zero, 1/(1-WAZ) below. Never negative — that is what lets it be a weight."""
    panel = pd.DataFrame({
        "date": ["d"] * 5, "ticker": list("ABCDE"),
        "mr12": [3.0, 2.0, 1.0, 0.0, -3.0], "mr6": [3.0, 2.0, 1.0, 0.0, -3.0]})
    out = nse_momentum_score(panel)
    assert (out["nms"].dropna() > 0).all(), "NMS must never go negative"
    assert out["nms"].iloc[0] > out["nms"].iloc[-1]
    worst, best = out["nms"].iloc[-1], out["nms"].iloc[0]
    assert worst < 1.0 < best, "the transform must straddle 1.0 at WAZ=0"


def test_nse_nms_blends_both_horizons():
    """A name strong on 12m but weak on 6m must land between the two pure cases."""
    panel = pd.DataFrame({
        "date": ["d"] * 3, "ticker": list("ABC"),
        "mr12": [2.0, 2.0, -2.0], "mr6": [2.0, -2.0, -2.0]})
    out = nse_momentum_score(panel)
    both, mixed, neither = out["nms"]
    assert both > mixed > neither


def test_nse_nms_is_per_date():
    panel = pd.DataFrame({
        "date": ["d1"] * 2 + ["d2"] * 2, "ticker": list("ABAB"),
        "mr12": [1.0, -1.0, 100.0, 98.0], "mr6": [1.0, -1.0, 100.0, 98.0]})
    out = nse_momentum_score(panel)
    # d2's absolute levels are huge but its SPREAD is small; z-scoring is per date, so both
    # dates produce the same pair of scores
    assert out["nms"].iloc[0] == pytest.approx(out["nms"].iloc[2])


# --------------------------------------------------------------------------- Clenow
def test_clenow_prefers_a_clean_trend_over_a_ragged_one_of_equal_size():
    """The R^2 term: same total move, delivered smoothly vs in one jump."""
    n = 200
    t = np.arange(n, dtype=float)
    clean = 100.0 * np.exp(0.002 * t)
    jumpy = np.full(n, 100.0)
    jumpy[n // 2:] = float(clean[-1])                      # one gap, same endpoint
    assert clenow_score(clean)[-1] > clenow_score(jumpy)[-1]


def test_clenow_is_negative_on_a_downtrend():
    t = np.arange(200, dtype=float)
    assert clenow_score(100.0 * np.exp(-0.002 * t))[-1] < 0


def test_clenow_warmup_is_nan():
    assert np.all(np.isnan(clenow_score(_wiggle(), window=90)[:89]))


def test_above_sma_and_max_gap_disqualifiers():
    c = _ramp()
    assert above_sma(c, 100)[-1]                            # a ramp is always above its own SMA
    assert not above_sma(c[::-1].copy(), 100)[-1]
    g = np.full(200, 100.0)
    g[150] = 130.0                                          # a +30% single-session gap
    assert max_gap(g, 90)[160] > 0.15
    assert max_gap(np.full(200, 100.0), 90)[-1] == pytest.approx(0.0)


# --------------------------------------------------------------------------- PIT
@pytest.mark.parametrize("fn", [
    mom_12_1,
    mom_6_1,
    reversal_z,
    lambda c: vol_adjusted_return(c, YEAR_DAYS - SKIP_DAYS),
    lambda c: clenow_score(c, window=90),
    lambda c: above_sma(c, 100).astype(float),
    lambda c: max_gap(c, 90),
])
def test_single_series_signals_are_trailing_only(fn):
    c = _wiggle()
    np.testing.assert_allclose(fn(c)[:CUT], fn(c[:CUT]), equal_nan=True, rtol=0, atol=0)


def test_two_series_signals_are_trailing_only():
    c = _wiggle()
    h = c * 1.01
    np.testing.assert_allclose(high_52w_proximity(c, h)[:CUT],
                               high_52w_proximity(c[:CUT], h[:CUT]), equal_nan=True, rtol=0, atol=0)
    v = np.full(N, 1000.0)
    np.testing.assert_allclose(turnover_value(c, v)[:CUT], turnover_value(c[:CUT], v[:CUT]),
                               equal_nan=True, rtol=0, atol=0)
    np.testing.assert_allclose(realised_vol(c)[:CUT], realised_vol(c[:CUT]),
                               equal_nan=True, rtol=0, atol=0)


def test_truncation_probe_can_actually_fail():
    """Guard the guard: a centred window must break the probe, or the probe proves nothing."""
    c = _wiggle()
    leaky = lambda x: pd.Series(x).rolling(21, center=True).mean().to_numpy()  # noqa: E731
    assert not np.allclose(leaky(c)[:CUT], leaky(c[:CUT]), equal_nan=True)
