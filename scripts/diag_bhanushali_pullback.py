"""Exploration (MEASUREMENT, standalone candidate — NOT a baseline_v1 overlay): the Siddharth Bhanushali
6-step swing setup, systematized. Rising-44-SMA pullback + green-candle trigger, wide stop, R:R target,
3-10 day hold, exit ONLY on stop/target/time (never a red day — the owner's "2-3% is noise" point, so the
stop is floored at 4%). Short-horizon by construction → a different strategy from the 63d base; reported
standalone, honestly, with the short-horizon caveat.

Systematized discretionary rules (fixed, pre-declared):
  trend   : SMA44 rising over the last TREND_LOOKBACK days
  pullback: the day's low touches within BAND of SMA44 AND closes back above it (support held)
  trigger : that day is a green candle (close>open); enter next day if it breaks the green candle's high
  entry   : max(next open, green-candle high)   stop: min(green-candle low, entry*(1-STOP_FLOOR))
  target  : entry + RR*(entry-stop)             exit: stop / target / MAXHOLD days (no red-day exits)
  book    : 1% risk/trade, <=MAXPOS concurrent, round-trip cost, daily mark-to-market equity.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

SMA_LEN, TREND_LOOKBACK, BAND = 44, 10, 0.03
RR, STOP_FLOOR, MAXHOLD = 2.0, 0.04, 10
MAXPOS, RISK, COST, EQ0 = 15, 0.01, 0.0025, 1_000_000.0


def build_signals(ohlcv):
    """Per ticker: arrays + the (entry-eligible on d) signal from d-1's green pullback candle."""
    sig = {}
    for tkr, df in ohlcv.items():
        if len(df) < SMA_LEN + TREND_LOOKBACK + 5:
            continue
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        sma = pd.Series(c).rolling(SMA_LEN).mean().to_numpy()
        rising = np.full(len(c), False)
        rising[TREND_LOOKBACK:] = sma[TREND_LOOKBACK:] > sma[:-TREND_LOOKBACK]
        near = (l <= sma * (1 + BAND)) & (c >= sma)          # pulled back to support, closed above
        green = c > o
        setup = rising & near & green & np.isfinite(sma)     # green pullback candle on day t
        sig[tkr] = {"dates": pd.to_datetime(df.index), "o": o, "h": h, "l": l, "c": c, "setup": setup}
    return sig


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    sig = build_signals(ohlcv)
    all_dates = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in sig.values()])))
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in sig.items()}
    print(f"names {len(sig)} | dates {all_dates[0].date()}..{all_dates[-1].date()} ({len(all_dates)})", flush=True)

    equity = EQ0
    cash = EQ0
    open_pos = {}          # tkr -> dict(entry, stop, target, shares, held)
    eq_curve = []
    trades = []            # closed-trade R multiples + pnl
    for d in all_dates:
        # 1) manage open positions (exits: stop, then target, then time; never a red-day exit)
        for tkr in list(open_pos):
            p = open_pos[tkr]
            i = didx[tkr].get(d)
            if i is None:
                continue
            s = sig[tkr]
            lo, hi, cl = s["l"][i], s["h"][i], s["c"][i]
            p["held"] += 1
            exit_px = None
            if lo <= p["stop"]:
                exit_px = p["stop"]                      # gap-through conservatively filled at stop
            elif hi >= p["target"]:
                exit_px = p["target"]
            elif p["held"] >= MAXHOLD:
                exit_px = cl
            if exit_px is not None:
                proceeds = p["shares"] * exit_px * (1 - COST)
                cash += proceeds
                r = (exit_px - p["entry"]) / (p["entry"] - p["stop"])
                trades.append({"tkr": tkr, "R": r,
                               "pnl": p["shares"] * (exit_px - p["entry"]) - COST * p["shares"] * (exit_px + p["entry"])})
                del open_pos[tkr]
        # 2) new entries (signal fired on the PRIOR bar, breaks the green-candle high today)
        if len(open_pos) < MAXPOS:
            for tkr, s in sig.items():
                if tkr in open_pos:
                    continue
                i = didx[tkr].get(d)
                if i is None or i == 0 or not s["setup"][i - 1]:
                    continue
                trig_hi, trig_lo = s["h"][i - 1], s["l"][i - 1]
                if s["h"][i] < trig_hi:                  # never broke the green-candle high -> no fill
                    continue
                entry = max(s["o"][i], trig_hi)
                stop = min(trig_lo, entry * (1 - STOP_FLOOR))
                if entry <= stop:
                    continue
                shares = (equity * RISK) / (entry - stop)
                notional = shares * entry * (1 + COST)
                if notional > cash or shares <= 0:
                    continue
                cash -= notional
                open_pos[tkr] = {"entry": entry, "stop": stop,
                                 "target": entry + RR * (entry - stop), "shares": shares, "held": 0}
                if len(open_pos) >= MAXPOS:
                    break
        # 3) mark-to-market equity
        mtm = 0.0
        for tkr, p in open_pos.items():
            i = didx[tkr].get(d)
            px = sig[tkr]["c"][i] if i is not None else p["entry"]
            mtm += p["shares"] * px
        equity = cash + mtm
        eq_curve.append((d, equity))

    eq = pd.Series({d: v for d, v in eq_curve}).sort_index()
    ret = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() else float("nan")
    dd = (eq / eq.cummax() - 1).min()
    R = np.array([t["R"] for t in trades])
    wr = (R > 0).mean() if len(R) else float("nan")
    print(f"\n=== Bhanushali 44-SMA pullback (standalone, short-horizon) ===")
    print(f"trades {len(R)} | win-rate {wr*100:.1f}% | avg R {R.mean():+.2f} | expectancy {R.mean():.2f}R")
    print(f"CAGR {cagr*100:+.1f}% | Sharpe {sharpe:.3f} | MaxDD {dd*100:.1f}% | final eq {eq.iloc[-1]/EQ0:.2f}x")
    print(f"\nvs baseline_v1 (63d momentum, DIFFERENT strategy/horizon): Sharpe 0.667 / CAGR 15.5% / DD -46.3%")
    print("caveat: 2019-2026 local cache; short-horizon (our least-trustworthy regime); gross-ish (0.25% rt cost).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
