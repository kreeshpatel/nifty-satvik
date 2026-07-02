"""WEEKLY RSI swing setup (TradingView-faithful), per owner spec. Resample daily->weekly (W-FRI, the bars
TradingView draws), Wilder RSI(14) on weekly close (= TradingView weekly RSI), 44-week SMA trend, RSI-35 entry
+ RSI-50 regime context. MEASUREMENT: forward weekly-return edge vs the universe (implementation-independent).
Several variants so we can iterate. No verdict — just the numbers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

RSI_N = 14


def wilder_rsi(close: pd.Series, n: int = RSI_N) -> np.ndarray:
    """TradingView RSI: Wilder's RMA smoothing (ewm alpha=1/n, adjust=False)."""
    d = close.diff()
    up = d.clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = (-d).clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    rs = up / dn.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).to_numpy()


def weekly(df: pd.DataFrame) -> pd.DataFrame:
    w = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min",
                                  "Close": "last", "Volume": "sum"}).dropna()
    return w


# each variant: name -> function(o,h,l,c,rsi,rsi_prev,sma,rising) -> boolean signal array
def _variants(o, h, l, c, rsi, rsi_prev, sma, rising):
    green = c > o
    rose_above50_recent = pd.Series(rsi > 50).rolling(8).max().to_numpy() > 0   # was in a >50 regime lately
    return {
        "A: 44wSMA-rise & RSI<35 uptick & green": rising & (rsi_prev < 35) & (rsi > rsi_prev) & green,
        "B: A + was-in->50-regime (cooled-off)":  rising & (rsi_prev < 35) & (rsi > rsi_prev) & green & rose_above50_recent,
        "C: 44wSMA-rise & RSI cross up thru 50":  rising & (rsi_prev < 50) & (rsi >= 50),
        "D: 44wSMA-rise & RSI>50 (regime only)":  rising & (rsi > 50),
    }


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    FWDS = (4, 8, 12)   # weeks
    agg = {}            # variant -> {fwd -> ([sig],[uni])}
    counts = {}
    for tkr, df in ohlcv.items():
        w = weekly(df)
        if len(w) < 44 + 12 + 5:
            continue
        c = w["Close"]
        o, h, l, cc = (w[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        rsi = wilder_rsi(c)
        rsi_prev = np.concatenate([[np.nan], rsi[:-1]])
        sma = c.rolling(44).mean().to_numpy()
        rising = np.full(len(cc), False)
        rising[8:] = sma[8:] > sma[:-8]            # 44w SMA rising over ~8 weeks
        rising &= np.isfinite(sma)
        vs = _variants(o, h, l, cc, rsi, rsi_prev, sma, rising)
        for name, setup in vs.items():
            setup = np.nan_to_num(setup, nan=False).astype(bool)
            counts[name] = counts.get(name, 0) + int(setup.sum())
            d = agg.setdefault(name, {k: [[], []] for k in FWDS})
            for k in FWDS:
                fwd = np.full(len(cc), np.nan)
                fwd[:-k] = cc[k:] / cc[:-k] - 1.0
                m = np.isfinite(fwd)
                d[k][0].append(fwd[m & setup])
                d[k][1].append(fwd[m])

    for name in agg:
        print(f"\n=== {name}   (signals: {counts[name]}) ===")
        print(f"{'horizon':<10}{'signal':>9}{'universe':>10}{'edge(pp)':>10}{'sigWin':>8}{'uniWin':>8}{'n':>8}")
        for k in FWDS:
            sr = np.concatenate(agg[name][k][0]); br = np.concatenate(agg[name][k][1])
            if len(sr) < 50:
                print(f"{k}w{'':<8}{'(too few)':>9}"); continue
            print(f"{k}w{'':<8}{sr.mean()*100:>+8.2f}%{br.mean()*100:>+9.2f}%{(sr.mean()-br.mean())*100:>+10.3f}"
                  f"{(sr>0).mean()*100:>7.0f}%{(br>0).mean()*100:>7.0f}%{len(sr):>8}")
    print("\n(measurement only — no verdict. edge in pp vs universe; ~0.25pp = round-trip cost floor.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
