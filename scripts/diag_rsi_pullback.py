"""How we calculate + measure the RSI checklist (Bhanushali ch.6): weekly-44MA-uptrend + daily RSI<35 uptick
+ bullish candle. MEASUREMENT (implementation-independent entry-edge: forward return after a signal vs the
universe) — the honest, cheap test of whether the ENTRY has edge, before any exit/sizing choices.

The two computations the owner asked about, made explicit:
  RSI(14) — Wilder's smoothing (the standard). rsi = 100 - 100/(1+RS), RS = avg_gain/avg_loss over 14 bars.
  44-week-MA uptrend — 44 weeks ~= 220 trading days; 'rising' = SMA220[t] > SMA220[t-50] (~10 weeks up).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

RSI_N, TREND_N, TREND_RISE, OS = 14, 220, 50, 35.0


def wilder_rsi(close: pd.Series, n: int = RSI_N) -> np.ndarray:
    """Wilder's RSI(n) — the calculation, spelled out."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False).mean()   # Wilder smoothing
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).to_numpy()


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    sig_fwd = {5: [], 10: [], 20: []}
    base_fwd = {5: [], 10: [], 20: []}
    n_sig = 0
    for tkr, df in ohlcv.items():
        if len(df) < TREND_N + TREND_RISE + 5:
            continue
        o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
        close = df["Close"]
        rsi = wilder_rsi(close)
        sma = close.rolling(TREND_N).mean().to_numpy()
        rising = np.full(len(c), False)
        rising[TREND_RISE:] = sma[TREND_RISE:] > sma[:-TREND_RISE]      # 44-week MA uptrend
        # signal on day t: uptrend, yesterday oversold (RSI<35), today RSI ticks up, today green candle
        rsi_prev = np.concatenate([[np.nan], rsi[:-1]])
        setup = rising & (rsi_prev < OS) & (rsi > rsi_prev) & (c > o) & np.isfinite(sma)
        n_sig += int(np.nansum(setup))
        for FWD in (5, 10, 20):
            fwd = np.full(len(c), np.nan)
            fwd[:-FWD] = c[FWD:] / c[:-FWD] - 1.0
            m = np.isfinite(fwd)
            sig_fwd[FWD].append(fwd[m & setup])
            base_fwd[FWD].append(fwd[m])

    print(f"RSI checklist signals: {n_sig} (rising-220SMA & RSI<35 uptick & green candle)\n")
    print(f"{'horizon':<9}{'signal':>9}{'universe':>10}{'edge(pp)':>10}{'sig_win':>9}{'uni_win':>9}{'n':>9}")
    print("-" * 65)
    for FWD in (5, 10, 20):
        sr = np.concatenate(sig_fwd[FWD]); br = np.concatenate(base_fwd[FWD])
        edge = (sr.mean() - br.mean()) * 100
        print(f"{FWD}d{'':<7}{sr.mean()*100:>+8.2f}%{br.mean()*100:>+9.2f}%{edge:>+10.3f}"
              f"{(sr>0).mean()*100:>8.0f}%{(br>0).mean()*100:>8.0f}%{len(sr):>9}")
    print("\nRead: edge >> ~0.25pp round-trip cost = worth a full backtest; edge <= cost = dead like 0079/0020.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
