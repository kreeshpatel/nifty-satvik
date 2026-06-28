"""Stage-1 gate — long-horizon feature math: formula correctness + the no-lookahead proof.

The headline gate is :func:`test_no_lookahead_truncation` — the definitive probe from
``skills/leakage-audit`` §1: a feature at bar ``i`` must use only ``[..i]``, so truncating the
future cannot change a past value. Plus scale-invariance to corporate-action back-adjustment
(why retroactive split adjustment is safe for these ratio features).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.data.features import (
    LONG_HORIZON_FEATURE_COLS,
    compute_features,
    ema,
    sma,
    true_range,
)


def _synth_ohlcv(n: int, *, seed: int = 0, with_split_at: int | None = None) -> pd.DataFrame:
    """Deterministic positive OHLCV random walk (no >50% moves → cleaning is a no-op). If
    ``with_split_at`` is set, halve every price from that bar onward (a 1:2 forward split:
    an unadjusted ~-50%+ drop the cleaner back-adjusts)."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.012, size=n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    if with_split_at is not None:
        for arr in (close, high, low, open_):
            arr[with_split_at:] *= 0.4   # clear >50% drop → split back-adjust
        volume[with_split_at:] /= 0.4
    idx = pd.bdate_range("2015-01-01", periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close,
                         "Volume": volume}, index=idx)


def test_sma_trailing_and_warmup():
    arr = np.arange(1.0, 8.0)   # 1..7
    out = sma(arr, 3)
    assert np.isnan(out[0]) and np.isnan(out[1])
    np.testing.assert_allclose(out[2:], [2, 3, 4, 5, 6])


def test_ema_seed_and_recursion():
    arr = np.array([10.0, 12.0, 14.0])
    out = ema(arr, span=3)            # alpha = 2/4 = 0.5, seeded at arr[0]
    assert out[0] == 10.0
    assert out[1] == pytest.approx(0.5 * 12 + 0.5 * 10)
    assert out[2] == pytest.approx(0.5 * 14 + 0.5 * out[1])


def test_true_range_formula():
    high = np.array([10.0, 11.0, 12.0])
    low = np.array([9.0, 9.5, 10.0])
    close = np.array([9.5, 10.5, 11.0])
    tr = true_range(high, low, close)
    assert tr[0] == pytest.approx(10.0 - 9.0)                      # first bar: H-L
    assert tr[1] == pytest.approx(max(11 - 9.5, abs(11 - 9.5), abs(9.5 - 9.5)))
    assert tr[2] == pytest.approx(max(12 - 10, abs(12 - 10.5), abs(10 - 10.5)))


def test_feature_frame_starts_at_source_warmup_bar():
    """Source parity: the feature frame head-drops the v1 warm-up so it starts on the SAME bar
    the source did (bar 49 = the 52-week-extremes min_periods=50 boundary). This keeps the
    per-ticker ADV series aligned with the source for restrict_to_large_mid (see
    nq/data/features.py::_V1_WARMUP_BARS)."""
    df = _synth_ohlcv(350, seed=11)
    feat = compute_features(df, "X", clean=False)
    assert feat.index[0] == df.index[49]
    assert len(feat) == 350 - 49


def test_sma200_slope_63_matches_independent_recompute():
    df = _synth_ohlcv(400, seed=1)
    feat = compute_features(df, "X", clean=False)
    close = df["Close"].to_numpy(float)
    s200 = pd.Series(sma(close, 200))
    expected = pd.Series(((s200 / s200.shift(63) - 1.0) * 100).to_numpy(), index=df.index)
    np.testing.assert_allclose(feat["sma200_slope_63"].to_numpy(),
                               expected.loc[feat.index].to_numpy(), equal_nan=True)
    # signal is NaN until bar 199+63 = 262, non-NaN thereafter
    cut = df.index[262]
    assert feat.loc[feat.index < cut, "sma200_slope_63"].isna().all()
    assert feat.loc[feat.index >= cut, "sma200_slope_63"].notna().all()


def test_atr_pct_63_matches_independent_recompute():
    df = _synth_ohlcv(300, seed=2)
    feat = compute_features(df, "X", clean=False)
    h, lo, c = (df[col].to_numpy(float) for col in ("High", "Low", "Close"))
    expected = pd.Series(ema(true_range(h, lo, c), 63) / np.where(c == 0, 1, c) * 100, index=df.index)
    np.testing.assert_allclose(feat["atr_pct_63"].to_numpy(),
                               expected.loc[feat.index].to_numpy(), equal_nan=True)


def test_adv_rupees_20d_matches_independent_recompute():
    df = _synth_ohlcv(120, seed=3)
    feat = compute_features(df, "X", clean=False)
    c, v = df["Close"].to_numpy(float), df["Volume"].to_numpy(float)
    expected = pd.Series(sma(v, 20) * c, index=df.index)
    np.testing.assert_allclose(feat["adv_rupees_20d"].to_numpy(),
                               expected.loc[feat.index].to_numpy(), equal_nan=True)


def test_no_lookahead_truncation():
    """THE gate: dropping all bars after date d must not change any feature value at a bar
    <= d. Run on several cut points for all three LH features (clean=False isolates the
    feature math from the inherently-retroactive split back-adjustment). Both the full and the
    truncated frames head-drop the same warm-up, so they are compared on the dates they share."""
    df = _synth_ohlcv(420, seed=7)
    full = compute_features(df, "X", clean=False)
    for cut in (262, 280, 330, 400, 418):
        trunc = compute_features(df.iloc[: cut + 1], "X", clean=False)
        a = full.loc[trunc.index]   # the shared date range [bar 49 .. bar cut]
        for col in LONG_HORIZON_FEATURE_COLS:
            assert np.array_equal(a[col].to_numpy(), trunc[col].to_numpy(), equal_nan=True), (
                f"lookahead in {col}: truncating after bar {cut} changed a past value")


def test_features_scale_invariant_to_backadjust():
    """A future split back-adjusts past raw prices, but the LH features are scale-free ratios
    (slope of an SMA, ATR/close, and vol*close with volume inversely scaled), so pre-split
    feature values are unchanged. This is why retroactive CA adjustment is safe."""
    n = 330
    base = _synth_ohlcv(n, seed=5)
    split = _synth_ohlcv(n, seed=5, with_split_at=300)   # same path, then a 1:2 split at 300
    fb = compute_features(base, "X", clean=True, holidays=set())
    fs = compute_features(split, "X", clean=True, holidays=set())
    common = fb.index[fb.index < base.index[300]]        # pre-split dates
    for col in LONG_HORIZON_FEATURE_COLS:
        np.testing.assert_allclose(fb.loc[common, col].to_numpy(), fs.loc[common, col].to_numpy(),
                                   rtol=1e-9, atol=1e-6, equal_nan=True)
