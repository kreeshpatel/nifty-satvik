"""RSI variant sweep (MEASUREMENT, exploratory — no verdict). Reports the implementation-independent entry
edge (forward return after signal vs the universe) for several RSI formulations, incl. the RSI-50 regime
filter and an RSI>50 momentum trigger. Same 3-step recipe: compute indicator -> boolean signal (PIT) ->
forward-return edge vs universe. Keep-testing mode: numbers only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from scripts.diag_rsi_pullback import wilder_rsi  # noqa: E402

TREND_N, TREND_RISE = 220, 50


def weekly_rsi_daily(df: pd.DataFrame) -> np.ndarray:
    """Weekly Wilder RSI(14) forward-filled onto the daily index (higher-timeframe regime)."""
    wk = df["Close"].resample("W-FRI").last().dropna()
    if len(wk) < 20:
        return np.full(len(df), np.nan)
    wr = pd.Series(wilder_rsi(wk), index=wk.index)
    return wr.reindex(df.index, method="ffill").to_numpy()


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    # each variant: name -> function(o,c,rsi,wrsi,sma_rising,n_rows) -> boolean signal array
    def v_os35(o, c, rsi, wr, up):   # oversold<35 dip + green + 220-uptrend
        rp = np.r_[np.nan, rsi[:-1]]
        return up & (rp < 35) & (rsi > rp) & (c > o)
    def v_os35_r50(o, c, rsi, wr, up):   # + weekly RSI>50 healthy regime
        rp = np.r_[np.nan, rsi[:-1]]
        return up & (rp < 35) & (rsi > rp) & (c > o) & (wr > 50)
    def v_os30(o, c, rsi, wr, up):
        rp = np.r_[np.nan, rsi[:-1]]
        return up & (rp < 30) & (rsi > rp) & (c > o)
    def v_os40(o, c, rsi, wr, up):
        rp = np.r_[np.nan, rsi[:-1]]
        return up & (rp < 40) & (rsi > rp) & (c > o)
    def v_cross50(o, c, rsi, wr, up):    # MOMENTUM: RSI crosses UP through 50 in uptrend (not oversold)
        rp = np.r_[np.nan, rsi[:-1]]
        return up & (rp < 50) & (rsi >= 50) & (c > o)
    def v_diverg(o, c, rsi, wr, up):     # bullish divergence proxy: price lower / RSI higher over 14d
        L = 14
        cL = np.r_[np.full(L, np.nan), c[:-L]]
        rL = np.r_[np.full(L, np.nan), rsi[:-L]]
        return up & (c < cL) & (rsi > rL) & (c > o)
    variants = {"os<35 (base)": v_os35, "os<35 +wkRSI>50": v_os35_r50, "os<30": v_os30,
                "os<40": v_os40, "RSI cross>50 (momentum)": v_cross50, "bull divergence": v_diverg}

    acc = {k: {10: ([], []), 20: ([], [])} for k in variants}
    for tkr, df in ohlcv.items():
        if len(df) < TREND_N + TREND_RISE + 25:
            continue
        o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
        rsi = wilder_rsi(df["Close"])
        wr = weekly_rsi_daily(df)
        sma = df["Close"].rolling(TREND_N).mean().to_numpy()
        up = np.full(len(c), False)
        up[TREND_RISE:] = sma[TREND_RISE:] > sma[:-TREND_RISE]
        up &= np.isfinite(sma)
        for name, fn in variants.items():
            sset_ = fn(o, c, rsi, wr, up)
            for FWD in (10, 20):
                fwd = np.full(len(c), np.nan); fwd[:-FWD] = c[FWD:] / c[:-FWD] - 1.0
                m = np.isfinite(fwd)
                acc[name][FWD][0].append(fwd[m & sig_bool(sset_)])
                acc[name][FWD][1].append(fwd[m])

    print(f"{'variant':<26}{'10d edge':>10}{'10d n':>9}{'20d edge':>10}{'20d win':>9}")
    print("-" * 66)
    for name in variants:
        s10 = np.concatenate(acc[name][10][0]); b10 = np.concatenate(acc[name][10][1])
        s20 = np.concatenate(acc[name][20][0]); b20 = np.concatenate(acc[name][20][1])
        e10 = (s10.mean() - b10.mean()) * 100
        e20 = (s20.mean() - b20.mean()) * 100
        print(f"{name:<26}{e10:>+9.3f}{len(s10):>9}{e20:>+9.3f}{(s20 > 0).mean()*100:>8.0f}%")
    print("\n(edge in pp vs universe; cost bar ~0.25pp round-trip. numbers only — no verdict.)")
    return 0


def sig_bool(x):
    return np.asarray(x, dtype=bool)


if __name__ == "__main__":
    raise SystemExit(main())
