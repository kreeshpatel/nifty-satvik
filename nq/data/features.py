"""Long-horizon per-stock features — trailing-only, no lookahead.

The clean rebuild carries ONLY the three columns the long-horizon strategy consumes (the v1
80-feature kitchen sink is deliberately gone):

  * ``sma200_slope_63`` — the **signal**: % change of the 200-day SMA over the last 63
    sessions, ``(sma200[i] / sma200[i-63] - 1) * 100``. Both points are <= ``i`` → backward-only.
  * ``atr_pct_63`` — 63-span ATR as a % of close (horizon-matched per-share risk for sizing).
  * ``adv_rupees_20d`` — 20-day average rupee turnover ``mean(volume[-20:]) * close`` (the
    liquidity sidecar driving the large+mid filter, the ADV position cap, and impact costs).

Every value at bar ``i`` uses only ``[..i]`` (trailing windows / ``.shift(+k)``), so the
truncation test is byte-stable (see ``skills/leakage-audit`` §1). The OHLCV is cleaned first
via :func:`nq.data.ohlcv.clean_ohlcv_for_features` (holidays + splits, **without** the demerger
reference — exactly the source feature path; the panel/simulator path cleans WITH the demerger
reference). Math ported verbatim from the validated source ``_compute_stock_features``.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from config import NSE_HOLIDAYS, get_sector

from .ohlcv import clean_ohlcv_for_features

# The long-horizon feature columns this module produces (besides close/sector/ticker).
LONG_HORIZON_FEATURE_COLS: tuple[str, ...] = ("sma200_slope_63", "atr_pct_63", "adv_rupees_20d")
SIGNAL = "sma200_slope_63"

_MIN_CLEANED_BARS = 60   # source guard: a name needs >= 60 cleaned bars to compute (data_store.py:343,350)
_MIN_FEATURE_ROWS = 50   # source keeps a name iff its post-warm-up feature frame has >= 50 rows

# Source-parity warm-up head-drop. The source `_compute_stock_features` ends with
# `feat_df.dropna(subset=<the v1 79-feature contract>)`; the longest-warm-up v1 column is the
# 52-week high/low (`rolling(min(252,n), min_periods=50)`), so the source feature frame always
# starts at bar 49 (verified empirically vs the source across n/seed). The clean LH-only rebuild
# carries none of those v1 columns, but it replicates this leading head-drop so the per-ticker
# ADV series fed to `restrict_to_large_mid`'s trailing rolling-median begins on the SAME bar —
# otherwise a short-history name's partial-window median (hence its large+mid keep mask) would
# diverge from baseline_v0 on its first ~1.5 months of signal-valid dates. This is a deliberate
# v1-compat alignment for Stage-3 reproduction, NOT an LH signal warm-up (the signal itself is
# NaN until bar 262). The carried golden (long-history large caps) is unaffected either way.
_V1_WARMUP_BARS = 49


def ema(arr: np.ndarray, span: int) -> np.ndarray:
    """Recursive EMA seeded at ``arr[0]`` (alpha = 2/(span+1)). No NaN warm-up — the smoother
    starts from bar 0, matching the source ATR computation exactly."""
    arr = np.asarray(arr, dtype=float)
    out = np.empty_like(arr, dtype=float)
    if len(arr) == 0:
        return out
    alpha = 2 / (span + 1)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def sma(arr: np.ndarray, window: int) -> np.ndarray:
    """Trailing simple moving average over ``[i-window+1, i]``; NaN before bar ``window-1``."""
    arr = np.asarray(arr, dtype=float)
    out = np.full_like(arr, np.nan, dtype=float)
    for i in range(window - 1, len(arr)):
        out[i] = arr[i - window + 1:i + 1].mean()
    return out


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Wilder true range, ``tr[0] = high[0]-low[0]``; thereafter
    ``max(H-L, |H-C_prev|, |L-C_prev|)``."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    return np.concatenate([[high[0] - low[0]], tr])


def compute_features(
    df: pd.DataFrame, ticker: str | None = None, *,
    holidays: set[str] | None = None, clean: bool = True,
) -> pd.DataFrame | None:
    """Compute the long-horizon features for one stock's OHLCV.

    ``df`` has title-cased ``Open/High/Low/Close/Volume`` on a ``DatetimeIndex``. When
    ``clean`` is True the frame is first run through :func:`clean_ohlcv_for_features`
    (holidays default to the carried ``NSE_HOLIDAYS``; no demerger reference, matching the
    source feature path). Returns a frame indexed by the cleaned dates with columns
    ``close, sma200_slope_63, atr_pct_63, adv_rupees_20d, sector, ticker`` — or ``None`` if
    fewer than 60 usable bars. The leading ``_V1_WARMUP_BARS`` (49) rows are head-dropped to
    match the source feature frame's start bar (see the constant). The signal column is still
    NaN until bar 262 (200d SMA + 63d slope); those pre-signal rows are retained (they feed the
    trailing ADV window) but are never selected by the ranker.
    """
    if df is None or len(df) < _MIN_CLEANED_BARS:
        return None
    if clean:
        hol = set(NSE_HOLIDAYS) if holidays is None else set(holidays)
        df, _ = clean_ohlcv_for_features(df, holidays=hol)
        if len(df) < _MIN_CLEANED_BARS:
            return None

    close = df["Close"].to_numpy(dtype=float)
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    volume = df["Volume"].to_numpy(dtype=float)

    # ── Signal: 200-day SMA slope over 63 sessions (backward-only ratio) ──
    sma200 = sma(close, 200)
    _sma200_s = pd.Series(sma200)
    sma200_slope_63 = ((_sma200_s / _sma200_s.shift(63) - 1.0) * 100).to_numpy()

    # ── Horizon-matched per-share risk: 63-span ATR as % of close ──
    tr = true_range(high, low, close)
    atr63 = ema(tr, 63)
    atr_pct_63 = atr63 / np.where(close == 0, 1, close) * 100

    # ── Liquidity sidecar: 20d average rupee turnover (point-in-time) ──
    vol_sma20 = sma(volume, 20)
    adv_rupees_20d = vol_sma20 * close

    feat_df = pd.DataFrame({
        "close": close,
        "sma200_slope_63": sma200_slope_63,
        "atr_pct_63": atr_pct_63,
        "adv_rupees_20d": adv_rupees_20d,
    }, index=df.index)
    feat_df["sector"] = get_sector(ticker) if ticker is not None else "Others"
    feat_df["ticker"] = ticker
    # Source-parity head-drop (see _V1_WARMUP_BARS): start on the same bar the source did.
    return feat_df.iloc[_V1_WARMUP_BARS:]


def compute_all_features(
    ohlcv: Mapping[str, pd.DataFrame], *, holidays: set[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Compute long-horizon features for every name in ``ohlcv``. Names with < 60 cleaned
    bars, fewer than 50 post-warm-up feature rows, or a compute error are skipped (matching
    the source's keep rule). Returns ``{ticker -> feature_df}``."""
    out: dict[str, pd.DataFrame] = {}
    for ticker, df in ohlcv.items():
        try:
            feat = compute_features(df, ticker, holidays=holidays)
        except Exception:
            continue
        if feat is not None and len(feat) >= _MIN_FEATURE_ROWS:
            out[ticker] = feat
    return out
