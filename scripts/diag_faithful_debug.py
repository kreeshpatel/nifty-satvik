"""Bug-hunt on the faithful backtest (finding 0022 looked implausibly bad). Isolate cost vs strategy, and
instrument the trades: cost sweep {0, STT+brokerage only, current 0.70%}, plus per-trade notional%, realized
risk%, hold days, turnover, R distribution, extreme-R (data-glitch) check, and sample trades. Engine B faithful.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_faithful import BAND, EQ0, MAXPOS, NOTIONAL_CAP, RISK, START, prep, signal  # noqa: E402


def run(P, membership, cost_leg, engine="B", maxhold=10, RR=2.0, collect=False):
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    sig = {t: signal(s, engine, "literal", 35) for t, s in P.items()}
    eq = cash = EQ0; op = {}; curve = []; T = []
    for d in dts:
        dd = d.date()
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            p["held"] += 1; ex = rs = None
            if P[t]["l"][i] <= p["stop"]:
                ex, rs = p["stop"], "stop"
            elif P[t]["h"][i] >= p["tp"]:
                ex, rs = p["tp"], "target"
            elif p["held"] >= maxhold:
                ex, rs = P[t]["c"][i], "time"
            if ex is not None:
                cash += p["sh"] * ex * (1 - cost_leg)
                if collect:
                    T.append(dict(tkr=t, entry=p["en"], stop=p["stop"], exit=ex, R=(ex - p["en"]) / (p["en"] - p["stop"]),
                                  reason=rs, held=p["held"], notional_pct=p["notion0"] / p["eq0"],
                                  risk_pct=p["sh"] * (p["en"] - p["stop"]) / p["eq0"], stopdist=(p["en"] - p["stop"]) / p["en"]))
                del op[t]
        if len(op) < MAXPOS:
            for t, s in P.items():
                if t in op:
                    continue
                i = didx[t].get(d)
                if i is None or i == 0 or not sig[t][i - 1]:
                    continue
                if membership is not None and not ticker_in_index_on(t, dd, membership):
                    continue
                sh_, sl_ = s["h"][i - 1], s["l"][i - 1]
                if s["h"][i] < sh_:
                    continue
                en = max(s["o"][i], sh_); st = sl_ * (1 - 0.001)
                if en <= st:
                    continue
                sh = min(eq * RISK / (en - st), eq * NOTIONAL_CAP / en); notion = sh * en * (1 + cost_leg)
                if notion > cash or sh <= 0:
                    continue
                cash -= notion
                op[t] = dict(en=en, stop=st, tp=en + RR * (en - st), sh=sh, held=0, notion0=sh * en, eq0=eq)
                if len(op) >= MAXPOS:
                    break
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm; curve.append((d, eq))
    e = pd.Series(dict(curve)).sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan")
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    return dict(sharpe=sh, cagr=cagr, mult=e.iloc[-1] / EQ0, trades=T, yrs=yrs)


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    mem = load_membership()
    print("=== COST SWEEP (engine B faithful): how much of the loss is COSTS vs the STRATEGY? ===")
    for name, c in (("cost 0.00% (gross)", 0.0), ("cost 0.13%/leg (STT+broker only)", 0.0013),
                    ("cost 0.35%/leg (current, incl 0.22% slippage)", 0.0035)):
        m = run(P, mem, c)
        print(f"  {name:<44} Sharpe {m['sharpe']:+.3f} | CAGR {m['cagr']*100:+6.1f}% | {m['mult']:.3f}x")

    print("\n=== TRADE INSTRUMENTATION (gross, cost=0) ===")
    m = run(P, mem, 0.0, collect=True)
    T = pd.DataFrame(m["trades"])
    print(f"trades {len(T)} | trades/yr {len(T)/m['yrs']:.0f}")
    print(f"avg notional/equity {T['notional_pct'].mean()*100:.1f}%  (cap {NOTIONAL_CAP*100:.0f}%) | "
          f"share hitting cap: {(T['notional_pct']>0.19).mean()*100:.0f}%")
    print(f"avg realized RISK/trade {T['risk_pct'].mean()*100:.2f}%  (intended {RISK*100:.0f}%) | "
          f"avg stop distance {T['stopdist'].mean()*100:.2f}%")
    print(f"annual turnover ~ {len(T)/m['yrs']*T['notional_pct'].mean()*100:.0f}% | "
          f"gross expR {T['R'].mean():+.3f} | win {(T['R']>0).mean()*100:.1f}%")
    print(f"R distribution: min {T['R'].min():+.1f} p5 {T['R'].quantile(.05):+.1f} med {T['R'].median():+.1f} "
          f"p95 {T['R'].quantile(.95):+.1f} max {T['R'].max():+.1f}  | |R|>5 (glitch?) {int((T['R'].abs()>5).sum())}")
    print(f"exit mix: {T['reason'].value_counts().to_dict()}")
    print("\nsample trades:")
    print(T[["tkr", "entry", "stop", "exit", "R", "reason", "held", "notional_pct", "risk_pct"]].head(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
