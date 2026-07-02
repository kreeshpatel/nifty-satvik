"""FAITHFUL backtest of Siddharth Bhanushali's two swing systems, exactly as he teaches them, with the two
fixes prior diag scripts lacked: (1) trade only PIT Nifty-500 index members (his curated watchlist + the
survivorship fix), (2) real NSE round-trip costs (config brokerage+STT+slippage, ~0.7% mid-cap), not a flat
0.25%. Baselines use his EXACT rules (candle-low stop, 3-10d hold, buy-above-high); a one-knob-at-a-time grid
shows where the exact spec sits vs the deviations that "worked". Window 2017-2026 (pre-2019 survivor-biased).

Engine A (RSI-35 system): WEEKLY 44-SMA rising (trend) + DAILY RSI(14)<35 then cross back >=35 on a green candle.
Engine B (44-SMA pullback): DAILY 44-SMA rising + price pulls back to the MA + green candle. No RSI.
Both: buy above the signal candle high, stop below its low, target 1:2 & 1:3, hold 3-10d, exit stop/target/time.
MEASUREMENT / analysis (no cfg change, no promotion).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import BROKERAGE_PCT, SLIPPAGE, STT_PCT  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

COST_LEG = BROKERAGE_PCT + STT_PCT + SLIPPAGE["MID_CAP"]   # per-leg fraction; round-trip ~= 2x (~0.70%)
BAND, RISK, NOTIONAL_CAP, MAXPOS, EQ0 = 0.02, 0.02, 0.20, 15, 1_000_000.0
START = "2017-01-01"


def wilder_rsi(close: pd.Series, n: int = 14) -> np.ndarray:
    d = close.diff()
    up = d.clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = (-d).clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    return (100.0 - 100.0 / (1.0 + up / dn.replace(0.0, np.nan))).to_numpy()


def _rose(sma: np.ndarray, k: int) -> np.ndarray:
    r = np.full(len(sma), False)
    r[k:] = sma[k:] > sma[:-k]
    return r & np.isfinite(sma)


def prep(ohlcv):
    """Per-ticker cached components (computed once); signals are combined cheaply per config."""
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < 300:
            continue
        idx = pd.to_datetime(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        n = len(c)
        # ATR(14)
        pc = np.concatenate([[np.nan], c[:-1]])
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        # daily RSI + daily 44-SMA
        rsi = wilder_rsi(df["Close"])
        rsi_prev = np.concatenate([[np.nan], rsi[:-1]])
        dsma = pd.Series(c).rolling(44).mean().to_numpy()
        # weekly 44-SMA rising -> mapped to daily (his mixed timeframe)
        w = df.resample("W-FRI").agg({"Close": "last"}).dropna()
        wsma = w["Close"].rolling(44).mean()
        w_lit = (wsma > wsma.shift(4))                                # rising over ~1 month
        w_sus = (wsma > wsma.shift(4)) & (wsma.shift(4) > wsma.shift(8))   # clearly/sustained rising
        wtrend_lit = w_lit.reindex(idx, method="ffill").fillna(False).to_numpy().astype(bool)
        wtrend_sus = w_sus.reindex(idx, method="ffill").fillna(False).to_numpy().astype(bool)
        # daily trend variants (engine B)
        slope66 = np.full(n, np.nan); slope66[66:] = dsma[66:] / dsma[:-66] - 1.0
        dtrend_lit = _rose(dsma, 10)                                  # daily 44-SMA rising over ~2 weeks
        dtrend_sus = _rose(dsma, 22) & _rose(dsma, 44) & _rose(dsma, 66) & (c > dsma) & (slope66 >= 0.08)
        near = (l <= dsma * (1 + BAND)) & (c >= dsma * (1 - BAND))    # pullback to the MA (support)
        green = c > o
        P[tkr] = dict(dates=idx, o=o, h=h, l=l, c=c, atr=atr, rsi=rsi, rsi_prev=rsi_prev,
                      green=green, near=np.nan_to_num(near, nan=False).astype(bool),
                      wtrend_lit=wtrend_lit, wtrend_sus=wtrend_sus,
                      dtrend_lit=np.nan_to_num(dtrend_lit, nan=False).astype(bool),
                      dtrend_sus=np.nan_to_num(dtrend_sus, nan=False).astype(bool))
    return P


def signal(s, engine, trend, rsi_thr):
    """Build the signal-candle boolean for one ticker under a config."""
    if engine == "A":                                                # RSI-35 system (weekly trend + daily RSI)
        tr = s["wtrend_sus"] if trend == "sustained" else s["wtrend_lit"]
        sig = tr & (s["rsi_prev"] < rsi_thr) & (s["rsi"] >= rsi_thr) & s["green"]
    else:                                                            # B: 44-SMA pullback (daily)
        tr = s["dtrend_sus"] if trend == "sustained" else s["dtrend_lit"]
        sig = tr & s["near"] & s["green"]
    return np.nan_to_num(sig, nan=False).astype(bool)


def backtest(P, membership, engine, *, trend="literal", rsi_thr=35, stop_mode="low", RR=2.0, maxhold=10):
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    sig = {t: signal(s, engine, trend, rsi_thr) for t, s in P.items()}
    eq = cash = EQ0; op = {}; curve = []; trades = []
    for d in dts:
        dd = d.date()
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            p["held"] += 1; ex = reason = None
            if P[t]["l"][i] <= p["stop"]:
                ex, reason = p["stop"], "stop"
            elif P[t]["h"][i] >= p["tp"]:
                ex, reason = p["tp"], "target"
            elif p["held"] >= maxhold:
                ex, reason = P[t]["c"][i], "time"
            if ex is not None:
                cash += p["sh"] * ex * (1 - COST_LEG)
                trades.append({"R": (ex - p["en"]) / (p["en"] - p["stop"]), "reason": reason})
                del op[t]
        if len(op) < MAXPOS:
            for t, s in P.items():
                if t in op:
                    continue
                i = didx[t].get(d)
                if i is None or i == 0 or not sig[t][i - 1]:
                    continue
                if membership is not None and not ticker_in_index_on(t, dd, membership):
                    continue                                         # PIT watchlist: index members only
                sh_, sl_, atr_ = s["h"][i - 1], s["l"][i - 1], s["atr"][i - 1]
                if s["h"][i] < sh_:                                  # never broke the signal-candle high
                    continue
                en = max(s["o"][i], sh_)
                if stop_mode == "low":
                    st = sl_ * (1 - 0.001)                           # faithful: just below the candle low
                elif stop_mode == "floor4":
                    st = min(sl_ * (1 - 0.001), en * (1 - 0.04))
                else:                                                # atr25
                    st = en - 2.5 * atr_ if atr_ > 0 else sl_ * (1 - 0.001)
                if en <= st:
                    continue
                sh = min(eq * RISK / (en - st), eq * NOTIONAL_CAP / en)
                notion = sh * en * (1 + COST_LEG)
                if notion > cash or sh <= 0:
                    continue
                cash -= notion
                op[t] = dict(en=en, stop=st, tp=en + RR * (en - st), sh=sh, held=0)
                if len(op) >= MAXPOS:
                    break
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm; curve.append((d, eq))
    e = pd.Series(dict(curve)).sort_index()
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    R = np.array([t["R"] for t in trades])
    reasons = pd.Series([t["reason"] for t in trades]).value_counts().to_dict() if len(trades) else {}
    return dict(curve=e, ret=r, trades=len(R), wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0, reasons=reasons)


def _row(tag, m):
    return (f"  {tag:<26} tr {m['trades']:>4} | win {m['wr']*100:>4.1f}% | expR {m['expR']:+.2f} "
            f"| CAGR {m['cagr']*100:+6.1f}% | Sh {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}% | {m['mult']:.2f}x")


def _subperiods(m):
    r = m["ret"]
    def sh(x):
        x = x.to_numpy(); return x.mean() / x.std() * np.sqrt(252) if len(x) > 5 and x.std() else float("nan")
    a = sh(r[r.index < "2019-01-01"]); b = sh(r[(r.index >= "2019-01-01") & (r.index < "2022-01-01")])
    c = sh(r[r.index >= "2022-01-01"])
    return f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}"


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    membership = load_membership()
    P = prep(ohlcv)
    print(f"names {len(P)} | PIT membership: {'ON' if membership else 'OFF'} | round-trip cost {COST_LEG*2*100:.2f}% "
          f"| window {START}..2026\n")
    for engine, label in (("A", "RSI-35 system (weekly-44SMA + daily RSI<35 cross-up)"),
                          ("B", "44-SMA pullback (daily)")):
        print(f"===== ENGINE {engine}: {label} =====")
        base = dict(trend="literal", rsi_thr=35, stop_mode="low", RR=2.0, maxhold=10)
        mb = backtest(P, membership, engine, **base)
        print("  -- FAITHFUL baseline (his exact rules: candle-low stop, 1:2, hold 10d) --")
        print(_row("faithful 1:2", mb)); print(_subperiods(mb))
        print(f"    exits: {mb['reasons']}")
        # one-knob-at-a-time grid
        grid = [("target 1:3", {**base, "RR": 3.0}),
                ("stop: 4% floor", {**base, "stop_mode": "floor4"}),
                ("stop: 2.5xATR", {**base, "stop_mode": "atr25"}),
                ("hold 20d", {**base, "maxhold": 20}),
                ("hold 40d", {**base, "maxhold": 40}),
                ("trend: sustained", {**base, "trend": "sustained"}),
                ("stop ATR + hold40 + 1:3", {**base, "stop_mode": "atr25", "maxhold": 40, "RR": 3.0})]
        if engine == "A":
            grid.append(("RSI thr 30", {**base, "rsi_thr": 30}))
        print("  -- sensitivity grid (one knob changed from faithful) --")
        for tag, kw in grid:
            print(_row(tag, backtest(P, membership, engine, **kw)))
        print()
    print("baseline_v1 (63d momentum, different strategy/horizon): Sharpe 0.667 / CAGR 15.5% / DD -46.3%")
    print("(measurement/analysis — no cfg change, no promotion. 2017-18* mildly survivor-biased.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
