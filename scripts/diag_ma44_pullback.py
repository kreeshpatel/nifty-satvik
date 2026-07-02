"""Daily 44-SMA pullback video (distinct from the RSI one) — with the owner's fix: the trend filter must be a
VISIBLE, SUSTAINED uptrend in the 44-SMA, not a marginal uptick. Tests weak vs medium vs strong trend
definitions side by side to show the effect. Setup: rising 44-SMA -> price pulls back to the MA (support) ->
green candle -> buy above its high, stop below its low, target 1:2/1:3, hold<=30d, exit stop/target/time only.
MEASUREMENT, no verdict.

Trend definitions (daily 44-SMA):
  WEAK   : SMA[t] > SMA[t-5]                      (my old flawed filter -- a marginal up-value)
  MEDIUM : SMA[t] > SMA[t-44]                     (rose over a full 44d period)
  STRONG : rose on 1/2/3-month horizons (22/44/66) AND price above the MA AND >=8% MA-slope over 66d
           (a clearly rising, sustained uptrend -- the curated-watchlist stock he describes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

BAND, EPS, RISK, NOTIONAL_CAP, MAXPOS, COST, EQ0, MAXHOLD = 0.02, 0.001, 0.02, 0.20, 10, 0.0025, 1_000_000.0, 30


def prep(ohlcv):
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < 150:
            continue
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        sma = pd.Series(c).rolling(44).mean().to_numpy()
        prev_c = np.concatenate([[np.nan], c[:-1]])
        tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
        atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        n = len(c)

        def rose(k):
            r = np.full(n, False)
            r[k:] = sma[k:] > sma[:-k]
            return r & np.isfinite(sma)
        weak = rose(5)
        med = rose(44)
        slope66 = np.full(n, np.nan); slope66[66:] = sma[66:] / sma[:-66] - 1.0
        strong = rose(22) & rose(44) & rose(66) & (c > sma) & (slope66 >= 0.08)
        near = (l <= sma * (1 + BAND)) & (c >= sma * (1 - BAND))   # pulled back to the MA (support)
        green = c > o
        vol = df["Volume"].to_numpy(float)
        vspike = vol > 1.5 * pd.Series(vol).rolling(20).mean().to_numpy()   # HVC: volume >1.5x its 20d avg
        sig = {}
        for name, tr in (("weak", weak), ("medium", med), ("strong", strong)):
            sig[name] = np.nan_to_num(tr & near & green, nan=False).astype(bool)
        sig["strong_vol"] = np.nan_to_num(strong & near & green & vspike, nan=False).astype(bool)  # + volume conf
        P[tkr] = dict(dates=pd.to_datetime(df.index), o=o, h=h, l=l, c=c, atr=atr,
                      **{f"sig_{k}": v for k, v in sig.items()})
    return P


def entry_edge(P, key, fwds=(5, 10, 20)):
    rows = {k: [[], []] for k in fwds}; nsig = 0
    for s in P.values():
        c = s["c"]; setup = s[key]; nsig += int(setup.sum())
        for k in fwds:
            fwd = np.full(len(c), np.nan); fwd[:-k] = c[k:] / c[:-k] - 1.0
            m = np.isfinite(fwd); rows[k][0].append(fwd[m & setup]); rows[k][1].append(fwd[m])
    print(f"  {key.replace('sig_',''):<8} signals={nsig}")
    for k in fwds:
        sr = np.concatenate(rows[k][0]); br = np.concatenate(rows[k][1])
        if len(sr) < 40:
            print(f"    {k}d: (too few: {len(sr)})"); continue
        print(f"    {k:>2}d: signal {sr.mean()*100:+.2f}%  uni {br.mean()*100:+.2f}%  "
              f"edge {(sr.mean()-br.mean())*100:+.3f}pp  win {(sr>0).mean()*100:.0f}%/{(br>0).mean()*100:.0f}%")


def backtest(P, sigkey, RR, start=None, stop_mode="tight", maxhold=MAXHOLD, exit_mode="target"):
    """stop_mode: tight(candle low) / floor4(>=4% away) / atr25(entry-2.5*ATR).
    exit_mode: target(stop or 1:RR target or time) / drift(stop or hold `maxhold` days then close)."""
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    if start:
        dts = dts[dts >= pd.Timestamp(start)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = EQ0; op = {}; curve = []; R = []
    for d in dts:
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            p["held"] += 1; ex = None
            if P[t]["l"][i] <= p["stop"]:
                ex = p["stop"]
            elif exit_mode == "target" and P[t]["h"][i] >= p["tp"]:
                ex = p["tp"]
            elif p["held"] >= maxhold:
                ex = P[t]["c"][i]
            if ex is not None:
                cash += p["sh"] * ex * (1 - COST); R.append((ex - p["en"]) / (p["en"] - p["stop"])); del op[t]
        if len(op) < MAXPOS:
            for t, s in P.items():
                if t in op:
                    continue
                i = didx[t].get(d)
                if i is None or i == 0 or not s[sigkey][i - 1]:
                    continue
                sh_, sl_, atr_ = s["h"][i - 1], s["l"][i - 1], s["atr"][i - 1]
                if s["h"][i] < sh_:
                    continue
                en = max(s["o"][i], sh_)
                if stop_mode == "tight":
                    st = sl_ * (1 - EPS)
                elif stop_mode == "floor4":
                    st = min(sl_ * (1 - EPS), en * (1 - 0.04))
                else:  # atr25
                    st = en - 2.5 * atr_ if atr_ > 0 else sl_ * (1 - EPS)
                if en <= st:
                    continue
                sh = min(eq * RISK / (en - st), eq * NOTIONAL_CAP / en); notion = sh * en * (1 + COST)
                if notion > cash or sh <= 0:
                    continue
                cash -= notion; op[t] = dict(en=en, stop=st, tp=en + RR * (en - st), sh=sh, held=0)
                if len(op) >= MAXPOS:
                    break
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm; curve.append((d, eq))
    e = pd.Series(dict(curve)).sort_index(); ret = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25; R = np.array(R)
    return dict(trades=len(R), wr=(R > 0).mean() if len(R) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=ret.mean() / ret.std() * np.sqrt(252) if ret.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0, curve=e)


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    print(f"names {len(P)}\n=== ENTRY-EDGE by trend-filter strength (+ volume confirmation) ===")
    for k in ("sig_weak", "sig_medium", "sig_strong", "sig_strong_vol"):
        entry_edge(P, k)
    print("\n=== PHASE 1: does VOLUME confirmation add to the strong-filter pullback? (ATR2.5 1:3/40d) ===")
    for tag, st in (("2019-26", None), ("2022-26", "2022-01-01")):
        for sk in ("sig_strong", "sig_strong_vol"):
            m = backtest(P, sk, RR=3.0, start=st, stop_mode="atr25", maxhold=40, exit_mode="target")
            print(f"  {tag:<9} {sk.replace('sig_',''):<11} trades {m['trades']:>4} | win {m['wr']*100:>4.1f}% "
                  f"| CAGR {m['cagr']*100:+6.1f}% | Sharpe {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}% | {m['mult']:.2f}x")
    print("\n=== STRONG filter x STOP/EXIT (harvest the 20d drift without noise shake-out) ===")
    configs = [
        ("tight 1:2 30d", dict(stop_mode="tight", RR=2.0, maxhold=30, exit_mode="target")),
        ("floor4 1:2 30d", dict(stop_mode="floor4", RR=2.0, maxhold=30, exit_mode="target")),
        ("atr2.5 1:2 30d", dict(stop_mode="atr25", RR=2.0, maxhold=30, exit_mode="target")),
        ("atr2.5 1:3 40d", dict(stop_mode="atr25", RR=3.0, maxhold=40, exit_mode="target")),
        ("atr2.5 drift-20d", dict(stop_mode="atr25", RR=2.0, maxhold=20, exit_mode="drift")),
        ("atr2.5 drift-40d", dict(stop_mode="atr25", RR=2.0, maxhold=40, exit_mode="drift")),
    ]
    for tag, st in (("2019-26", None), ("2022-26", "2022-01-01")):
        print(f"  -- {tag} --")
        for name, kw in configs:
            m = backtest(P, "sig_strong", start=st, **kw)
            print(f"    {name:<18} trades {m['trades']:>4} | win {m['wr']*100:>4.1f}% | CAGR {m['cagr']*100:+6.1f}% "
                  f"| Sharpe {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}% | {m['mult']:.2f}x")
    print("\nvs baseline_v1: Sharpe 0.667 / CAGR 15.5% / DD -46.3%. (measurement, no verdict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
