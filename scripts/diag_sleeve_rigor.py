"""Stage-4 RIGOR — the honest promotion-bar scorecard for the sleeve book (config D:
touch+cup+double_bottom) vs the live touch-only baseline, before any change to main.

Battery: point metrics, paired block-bootstrap CI on dSharpe & dMaxDD (PROMOTE needs lower>0),
per-year walk-forward win-rate, return-correlation to base, DSR at the cumulative trial count, and a
gross-vs-net cost/turnover check. Reuses the engine of record via scripts/diag_sleeves helpers.

    python scripts/diag_sleeve_rigor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.validation.bootstrap import block_bootstrap_metric, bootstrap_delta  # noqa: E402
from nq.validation.dsr import cumulative_n_trials, deflated_sharpe_ratio  # noqa: E402
from run_bhanushali_faithful import EQ0  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from diag_sleeves import P2_EXIT, filter_P, combine  # noqa: E402

BASE = [0]                       # touch-only
SLEEVE = [0, 6, 8]               # touch + cup_handle + double_bottom (config D)


def sharpe(r):
    r = np.asarray(r, float); s = r.std()
    return r.mean() / s * np.sqrt(252) if s else np.nan


def maxdd(r):
    e = np.cumprod(1 + np.asarray(r, float)); return float((e / np.maximum.accumulate(e) - 1).min())


def sleeve_curve(P, mem, origins, per_budget):
    curves = []
    for f in origins:
        m = R94.backtest(filter_P(P, [f]), mem, start="2017-01-01", eq0=per_budget, **P2_EXIT)
        curves.append(m["curve"])
    return combine(curves)


def aligned_returns(cA, cD):
    idx = sorted(set(cA.index) | set(cD.index))
    a = cA.reindex(idx).ffill().bfill(); d = cD.reindex(idx).ffill().bfill()
    ra = a.pct_change().fillna(0.0); rd = d.pct_change().fillna(0.0)
    return pd.Series(ra.values, index=pd.DatetimeIndex(idx)), pd.Series(rd.values, index=pd.DatetimeIndex(idx))


def stats(r):
    e = (1 + r).cumprod(); yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    return dict(sharpe=sharpe(r), cagr=cagr, dd=maxdd(r), calmar=cagr / abs(maxdd(r)))


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv, box_breakout=True, trend_pullback=True, sr_pivot=True, zoo_origins=(6, 7, 8))
    mA = R94.backtest(filter_P(P, BASE), mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    cA = mA["curve"]; cD = sleeve_curve(P, mem, SLEEVE, EQ0 / len(SLEEVE))
    rA, rD = aligned_returns(cA, cD)
    sA, sD = stats(rA), stats(rD)

    print("=== POINT METRICS (net of costs) ===")
    print(f"  {'':14s} {'Sharpe':>7s} {'CAGR':>7s} {'MaxDD':>8s} {'Calmar':>7s}")
    for lab, s in [("baseline A", sA), ("sleeve D", sD)]:
        print(f"  {lab:14s} {s['sharpe']:7.2f} {s['cagr']*100:6.1f}% {s['dd']*100:7.1f}% {s['calmar']:7.2f}")
    print(f"  base trades={mA['trades']}")

    print("\n=== PAIRED BLOCK-BOOTSTRAP (promote needs CI-lower > 0) ===")
    dS = bootstrap_delta(rD.values, rA.values, sharpe, n_samples=2000)
    dD = bootstrap_delta(rD.values, rA.values, maxdd, n_samples=2000)   # maxdd is negative; delta>0 = less DD
    print(f"  dSharpe  point={dS.point:+.3f}  95% CI=[{dS.lower:+.3f}, {dS.upper:+.3f}]  "
          f"{'SIG' if dS.lower > 0 else 'ns'}")
    print(f"  dMaxDD   point={dD.point:+.3f}  95% CI=[{dD.lower:+.3f}, {dD.upper:+.3f}]  "
          f"{'SIG (DD reduced)' if dD.lower > 0 else 'ns'}")

    print("\n=== per-year walk-forward (net CAGR) ===")
    yrs = sorted(set(rA.index.year))
    wins = 0
    for y in yrs:
        ca = (1 + rA[rA.index.year == y]).prod() - 1
        cd = (1 + rD[rD.index.year == y]).prod() - 1
        w = cd > ca; wins += w
        print(f"  {y}: A={ca*100:6.1f}%  D={cd*100:6.1f}%  {'D' if w else 'A'}")
    print(f"  D beats A in {wins}/{len(yrs)} years ({wins/len(yrs)*100:.0f}%)  [bar >=60%]")

    print("\n=== correlation & DSR ===")
    corr = np.corrcoef(rA.values, rD.values)[0, 1]
    n = cumulative_n_trials() + 1
    per = sD["sharpe"] / np.sqrt(252)
    exc_kurt = pd.Series(rD.values).kurt()   # excess
    dsr = deflated_sharpe_ratio(per, len(rD), skewness=pd.Series(rD.values).skew(),
                                kurtosis=exc_kurt + 3.0, n_trials=n)
    print(f"  return-correlation D~A = {corr:.2f}")
    print(f"  DSR(sleeve D) at n_trials={n}: {dsr:.3f}  [bar >0.95]")

    print("\n=== cost / turnover check (gross vs net) ===")
    def net_gross(origins, per):
        cn = sleeve_curve(P, mem, origins, per) if len(origins) > 1 else R94.backtest(filter_P(P, origins), mem, start='2017-01-01', eq0=per, **P2_EXIT)['curve']
        cg_parts = [R94.backtest(filter_P(P, [f]), mem, start='2017-01-01', eq0=per, cost_off=True, **P2_EXIT)['curve'] for f in origins]
        cg = combine(cg_parts) if len(origins) > 1 else cg_parts[0]
        return stats(aligned_returns(cn, cn)[0])['cagr'], stats(aligned_returns(cg, cg)[0])['cagr']
    dn, dg = net_gross(SLEEVE, EQ0 / len(SLEEVE))
    print(f"  sleeve D  gross CAGR={dg*100:.1f}%  net CAGR={dn*100:.1f}%  cost drag={ (dg-dn)*100:.1f}pp")

    print("\n=== PROMOTION-BAR VERDICT ===")
    dCalmar = sD["calmar"] - sA["calmar"]; dCagr = sD["cagr"] - sA["cagr"]
    print(f"  dSharpe >= +0.10 & CI>0 : {dS.point:+.3f} / lower {dS.lower:+.3f}  -> {'PASS' if (dS.point>=0.10 and dS.lower>0) else 'FAIL'}")
    print(f"  dCalmar >= +0.05        : {dCalmar:+.3f}  -> {'PASS' if dCalmar>=0.05 else 'FAIL'}")
    print(f"  dCAGR   >  0            : {dCagr*100:+.1f}% -> {'PASS' if dCagr>0 else 'FAIL'}")
    print(f"  walk-fwd >= 60%         : {wins/len(yrs)*100:.0f}%  -> {'PASS' if wins/len(yrs)>=0.6 else 'FAIL'}")
    print(f"  DSR > 0.95              : {dsr:.3f} -> {'PASS' if dsr>0.95 else 'FAIL'}")


if __name__ == "__main__":
    main()
