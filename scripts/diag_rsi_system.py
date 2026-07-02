"""Faithful, thorough test of the Bhanushali RSI swing system (full transcript spec). Owner-set assumptions:
entry = RSI crosses back ABOVE 35 (prev<35, now>=35) on a green candle, in a weekly-44SMA-rising stock;
stop = just below the signal candle's low (faithful); targets 1:2 AND 1:3; 30-day max-hold cap; risk 2%,
20% notional/position cap. Mixed timeframe: 44-SMA on WEEKLY (trend), RSI(14) on DAILY (entry). Plus the
ch.6 divergence layer and the RSI+Bollinger / RSI+Volume combos. MEASUREMENT — reports numbers, no verdict.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

EPS, RISK, NOTIONAL_CAP, MAXPOS, COST, EQ0, MAXHOLD = 0.001, 0.02, 0.20, 10, 0.0025, 1_000_000.0, 30


def wilder_rsi(close: pd.Series, n: int = 14) -> np.ndarray:
    d = close.diff()
    up = d.clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = (-d).clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    return (100.0 - 100.0 / (1.0 + up / dn.replace(0.0, np.nan))).to_numpy()


def prep(ohlcv):
    out = {}
    for tkr, df in ohlcv.items():
        if len(df) < 300:
            continue
        w = df.resample("W-FRI").agg({"Close": "last"}).dropna()
        wsma = w["Close"].rolling(44).mean()
        wrise = (wsma > wsma.shift(4))                      # 44-week SMA rising over ~1 month
        trend = wrise.reindex(df.index, method="ffill").fillna(False).to_numpy().astype(bool)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        rsi = wilder_rsi(df["Close"])
        rsi_prev = np.concatenate([[np.nan], rsi[:-1]])
        green = c > o
        core = trend & (rsi_prev < 35) & (rsi >= 35) & green   # cross back above 35 on a green candle, in uptrend
        # daily Bollinger(20,2) lower-band touch, and high-volume-candle breakout, for the combos
        mid = df["Close"].rolling(20).mean(); sd = df["Close"].rolling(20).std()
        lower = (mid - 2 * sd).to_numpy()
        vol = df["Volume"].to_numpy(float); vma = df["Volume"].rolling(20).mean().to_numpy()
        hvc_breakout = trend & (c > o) & (vol > 1.5 * vma) & (c > np.concatenate([[np.nan], h[:-1]]))
        boll = trend & (l <= lower) & green
        out[tkr] = dict(dates=pd.to_datetime(df.index), o=o, h=h, l=l, c=c, rsi=rsi,
                        trend=trend, core=np.nan_to_num(core, nan=False).astype(bool),
                        boll=np.nan_to_num(boll, nan=False).astype(bool),
                        hvc=np.nan_to_num(hvc_breakout, nan=False).astype(bool))
    return out


def add_divergence(P, w=3):
    """Confirmed swing-low pivots (min over +/-w, known w days late) -> bullish & hidden divergence signals."""
    for s in P.values():
        c, rsi, trend = s["c"], s["rsi"], s["trend"]
        n = len(c)
        bull = np.zeros(n, bool); hidden = np.zeros(n, bool)
        piv = []  # (idx, close, rsi) confirmed pivot lows
        for i in range(w, n - w):
            if c[i] == c[i - w:i + w + 1].min():
                conf = i + w                              # confirmed w bars later (PIT)
                if piv:
                    pi, pc, pr = piv[-1]
                    if c[i] < pc and rsi[i] > pr:         # price lower low, RSI higher low
                        bull[conf] = True
                    if c[i] > pc and rsi[i] < pr and trend[conf]:  # higher low, RSI lower low, uptrend
                        hidden[conf] = True
                piv.append((i, c[i], rsi[i]))
        s["div_bull"] = bull; s["div_hidden"] = hidden
    return P


def entry_edge(P, key, fwds=(5, 10, 20)):
    rows = {k: [[], []] for k in fwds}; nsig = 0
    for s in P.values():
        c = s["c"]; setup = s[key]; nsig += int(setup.sum())
        for k in fwds:
            fwd = np.full(len(c), np.nan); fwd[:-k] = c[k:] / c[:-k] - 1.0
            m = np.isfinite(fwd)
            rows[k][0].append(fwd[m & setup]); rows[k][1].append(fwd[m])
    print(f"  {key:<12} signals={nsig}")
    for k in fwds:
        sr = np.concatenate(rows[k][0]); br = np.concatenate(rows[k][1])
        if len(sr) < 40:
            print(f"    {k}d: (too few: {len(sr)})"); continue
        print(f"    {k}d: signal {sr.mean()*100:+.2f}%  uni {br.mean()*100:+.2f}%  edge {(sr.mean()-br.mean())*100:+.3f}pp"
              f"  win {(sr>0).mean()*100:.0f}%/{(br>0).mean()*100:.0f}%")


def backtest(P, RR, start=None):
    all_dates = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    if start:
        all_dates = all_dates[all_dates >= pd.Timestamp(start)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    equity = cash = EQ0; open_pos = {}; eqc = []; R = []
    for d in all_dates:
        for tkr in list(open_pos):
            p = open_pos[tkr]; i = didx[tkr].get(d)
            if i is None:
                continue
            p["held"] += 1; ex = None
            if P[tkr]["l"][i] <= p["stop"]:
                ex = p["stop"]
            elif P[tkr]["h"][i] >= p["target"]:
                ex = p["target"]
            elif p["held"] >= MAXHOLD:
                ex = P[tkr]["c"][i]
            if ex is not None:
                cash += p["shares"] * ex * (1 - COST)
                R.append((ex - p["entry"]) / (p["entry"] - p["stop"])); del open_pos[tkr]
        if len(open_pos) < MAXPOS:
            for tkr, s in P.items():
                if tkr in open_pos:
                    continue
                i = didx[tkr].get(d)
                if i is None or i == 0 or not s["core"][i - 1]:
                    continue
                sh, sl = s["h"][i - 1], s["l"][i - 1]
                if s["h"][i] < sh:
                    continue
                entry = max(s["o"][i], sh); stop = sl * (1 - EPS)
                if entry <= stop:
                    continue
                shares = min(equity * RISK / (entry - stop), equity * NOTIONAL_CAP / entry)
                notion = shares * entry * (1 + COST)
                if notion > cash or shares <= 0:
                    continue
                cash -= notion
                open_pos[tkr] = dict(entry=entry, stop=stop, target=entry + RR * (entry - stop), shares=shares, held=0)
                if len(open_pos) >= MAXPOS:
                    break
        mtm = sum(p["shares"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["entry"]) for t, p in open_pos.items())
        equity = cash + mtm; eqc.append((d, equity))
    eq = pd.Series(dict(eqc)).sort_index(); ret = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    R = np.array(R)
    return dict(trades=len(R), wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                cagr=(eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1, sharpe=ret.mean() / ret.std() * np.sqrt(252) if ret.std() else float("nan"),
                dd=(eq / eq.cummax() - 1).min(), mult=eq.iloc[-1] / EQ0)


def main() -> int:
    P = add_divergence(prep(load_ohlcv_cache(OHLCV_CACHE)))
    print(f"names {len(P)}\n=== ENTRY-EDGE (forward return after signal vs universe) ===")
    for key in ("core", "div_bull", "div_hidden", "boll", "hvc"):
        entry_edge(P, key)
    print("\n=== CORE SYSTEM full backtest (weekly-44SMA + daily RSI cross-35, candle-low stop, 30d cap) ===")
    for RR in (2.0, 3.0):
        for tag, st in (("full 2019-26", None), ("2022-26", "2022-01-01")):
            m = backtest(P, RR, st)
            print(f"  RR 1:{int(RR)} {tag:<12} trades {m['trades']:>4} | win {m['wr']*100:>4.1f}% | expR {m['expR']:+.2f} "
                  f"| CAGR {m['cagr']*100:+6.1f}% | Sharpe {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}% | {m['mult']:.2f}x")
    print("\nvs baseline_v1 (63d momentum): Sharpe 0.667 / CAGR 15.5% / DD -46.3%. (measurement, no verdict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
