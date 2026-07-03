"""CORRECTED-faithful Bhanushali backtest — implements what he ACTUALLY teaches (the letter-faithful version
in run_bhanushali_faithful.py violated his spirit). Fixes: (1) TRAILING STOP / let winners run (chandelier
ATR trail ratcheting up from the candle-low initial stop; NO fixed target, NO hard time-cut) -- this is the
core fix, it stops cutting the rockets; (2) curated LIQUID watchlist (min ADV filter + cap-tiered slippage:
large-caps get 0.05% not 0.22%); (3) real 2% risk sizing (fewer, larger positions, not the 20% notional-cap
pathology); (4) VOLUME/HVC confirmation; (5) visibly-sustained trend. Gross + net reported.

Engine A (RSI-35 weekly-trend + daily RSI) and Engine B (daily 44-SMA pullback). MEASUREMENT/analysis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import BROKERAGE_PCT, SLIPPAGE, STT_PCT  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_faithful import EQ0, START, prep, signal  # noqa: E402

STT_BROK = BROKERAGE_PCT + STT_PCT                      # 0.13%/leg fixed part
ADV_LARGE, ADV_MIN = 5e8, 5e7                           # >=50cr -> large-cap slippage; skip <5cr (illiquid)


def _cost_leg(adv, cost_off=False):
    if cost_off:
        return 0.0
    slip = SLIPPAGE["LARGE_CAP"] if adv >= ADV_LARGE else SLIPPAGE["MID_CAP"]
    return STT_BROK + slip


def enrich(P, ohlcv):
    for t, s in P.items():
        g = ohlcv[t]
        s["adv"] = (g["Close"] * g["Volume"]).rolling(20).mean().to_numpy()
        vol = g["Volume"].to_numpy(float)
        s["vspike"] = np.nan_to_num(vol > 1.5 * pd.Series(vol).rolling(20).mean().to_numpy(), nan=False).astype(bool)
    return P


def backtest(P, membership, engine, *, trend="sustained", rsi_thr=35, vol_confirm=True, chand=3.0,
             min_adv=ADV_MIN, maxhold=250, risk=0.02, notional_cap=0.34, maxpos=8, cost_off=False):
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    sig = {t: (signal(s, engine, trend, rsi_thr) & (s["vspike"] if vol_confirm else True)) for t, s in P.items()}
    eq = cash = EQ0; op = {}; curve = []; T = []
    for d in dts:
        dd = d.date()
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            p["held"] += 1
            p["hw"] = max(p["hw"], P[t]["h"][i])
            p["stop"] = max(p["stop"], p["hw"] - chand * P[t]["atr"][i])   # chandelier trail, ratchet up
            ex = rs = None
            if P[t]["l"][i] <= p["stop"]:
                ex, rs = p["stop"], "trail"
            elif p["held"] >= maxhold:
                ex, rs = P[t]["c"][i], "time"
            if ex is not None:
                cash += p["sh"] * ex * (1 - _cost_leg(p["adv"], cost_off))
                T.append(dict(R=(ex - p["en"]) / (p["en"] - p["stop0"]), reason=rs, held=p["held"]))
                del op[t]
        if len(op) < maxpos:
            for t, s in P.items():
                if t in op:
                    continue
                i = didx[t].get(d)
                if i is None or i == 0 or not sig[t][i - 1]:
                    continue
                if membership is not None and not ticker_in_index_on(t, dd, membership):
                    continue
                adv = s["adv"][i - 1]
                if not (adv >= min_adv):                                   # curated liquid watchlist
                    continue
                sh_, sl_ = s["h"][i - 1], s["l"][i - 1]
                if s["h"][i] < sh_:
                    continue
                en = max(s["o"][i], sh_); st = sl_ * (1 - 0.001)
                if en <= st:
                    continue
                sh = min(eq * risk / (en - st), eq * notional_cap / en)
                notion = sh * en * (1 + _cost_leg(adv, cost_off))
                if notion > cash or sh <= 0:
                    continue
                cash -= notion
                op[t] = dict(en=en, stop=st, stop0=st, hw=en, sh=sh, held=0, adv=adv)
                if len(op) >= maxpos:
                    break
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm; curve.append((d, eq))
    e = pd.Series(dict(curve)).sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    R = np.array([t["R"] for t in T]); hold = np.array([t["held"] for t in T])
    return dict(trades=len(R), wr=(R > 0).mean() if len(R) else float("nan"), expR=R.mean() if len(R) else float("nan"),
                maxR=R.max() if len(R) else float("nan"), avghold=hold.mean() if len(hold) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0, ret=r)


def _row(tag, m):
    return (f"  {tag:<24} tr {m['trades']:>4} | win {m['wr']*100:>4.1f}% | expR {m['expR']:+.2f} | maxR {m['maxR']:>4.1f} "
            f"| hold {m['avghold']:>4.0f}d | CAGR {m['cagr']*100:+6.1f}% | Sh {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}%")


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    P = enrich(prep(ohlcv), ohlcv)
    mem = load_membership()
    print(f"names {len(P)} | trailing let-winners-run + curated liquid + 2% sizing + volume | window {START}..2026\n")
    for engine, label in (("A", "RSI-35 system"), ("B", "44-SMA pullback")):
        print(f"===== ENGINE {engine}: {label} (CORRECTED-faithful) =====")
        base = dict(trend="sustained", rsi_thr=35, vol_confirm=True, chand=3.0, min_adv=ADV_MIN)
        print(_row("baseline GROSS (no cost)", backtest(P, mem, engine, **base, cost_off=True)))
        print(_row("baseline NET (real cost)", backtest(P, mem, engine, **base)))
        for tag, kw in (("chandelier 2.5x", {**base, "chand": 2.5}), ("chandelier 4x", {**base, "chand": 4.0}),
                        ("no volume filter", {**base, "vol_confirm": False}),
                        ("liquid ADV>=25cr", {**base, "min_adv": 2.5e8})):
            print(_row(tag + " (net)", backtest(P, mem, engine, **kw)))
        print()
    print("baseline_v1 (63d momentum): Sharpe 0.667 / CAGR 15.5% / DD -46.3%  (measurement, no cfg change)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
