"""Return-focused (DD-tolerant) config analysis — the owner cares about CAGR, treats 2020/2025 DD as
unavoidable macro. Compares single-book SHARED-cap configs (a one-line live cfg change: enable detectors)
on per-year CAGR, when the max-DD occurred, bootstrap significance of dCAGR/dSharpe vs the live book, and
DSR. Reuses the engine of record (post stop-fix).

    python scripts/diag_return_configs.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from nq.validation.bootstrap import bootstrap_delta
from nq.validation.dsr import cumulative_n_trials, deflated_sharpe_ratio
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import filter_P, P2_EXIT

CONFIGS = {
    "A live (touch)":            [0],
    "B all-7 shared":            [0, 1, 2, 3, 6, 7, 8],
    "B' drop trend+sr":          [0, 1, 6, 7, 8],          # touch+box+cup+ascending+dblbottom
    "B'' touch+box+dbl+cup":     [0, 1, 6, 8],
}


def ann_ret(r):
    r = np.asarray(r, float); return (1 + r.mean()) ** 252 - 1 if len(r) else np.nan


def sharpe(r):
    r = np.asarray(r, float); s = r.std(); return r.mean() / s * np.sqrt(252) if s else np.nan


def curve_returns(curve):
    e = curve.sort_index(); r = e.pct_change().fillna(0.0)
    return pd.Series(r.values, index=pd.DatetimeIndex(e.index)), e


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv, box_breakout=True, trend_pullback=True, sr_pivot=True, zoo_origins=(6, 7, 8))
    runs = {}
    for name, ori in CONFIGS.items():
        m = R94.backtest(filter_P(P, ori), mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
        r, e = curve_returns(m["curve"])
        dd = (e / e.cummax() - 1)
        yrs = (e.index[-1] - e.index[0]).days / 365.25
        cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
        runs[name] = dict(r=r, e=e, trades=m["trades"], sharpe=sharpe(r), cagr=cagr,
                          dd=dd.min(), dd_date=dd.idxmin())

    print(f"{'config':22s} {'tr':>4s} {'Sharpe':>6s} {'CAGR':>6s} {'MaxDD':>7s} {'DD date':>10s}")
    for n, d in runs.items():
        print(f"{n:22s} {d['trades']:4d} {d['sharpe']:6.2f} {d['cagr']*100:5.1f}% {d['dd']*100:6.1f}% {str(d['dd_date'].date()):>10s}")

    print("\n=== per-year net CAGR ===")
    yrs = sorted(set(runs['A live (touch)']['r'].index.year))
    print("year   " + "  ".join(f"{n.split()[0]:>7s}" for n in runs))
    for y in yrs:
        row = []
        for n, d in runs.items():
            ry = d['r'][d['r'].index.year == y]; row.append((1 + ry).prod() - 1)
        print(f"{y}  " + "  ".join(f"{v*100:6.1f}%" for v in row))

    base = runs['A live (touch)']['r']
    n = cumulative_n_trials() + 1
    print(f"\n=== significance vs live book A (paired block-bootstrap, n_trials={n} for DSR) ===")
    for name in ["B all-7 shared", "B' drop trend+sr", "B'' touch+box+dbl+cup"]:
        r = runs[name]['r']
        dS = bootstrap_delta(r.values, base.values, sharpe, n_samples=2000)
        dC = bootstrap_delta(r.values, base.values, ann_ret, n_samples=2000)
        per = runs[name]['sharpe'] / np.sqrt(252)
        dsr = deflated_sharpe_ratio(per, len(r), skewness=pd.Series(r.values).skew(),
                                    kurtosis=pd.Series(r.values).kurt() + 3.0, n_trials=n)
        print(f"  {name:22s} dSharpe={dS.point:+.2f} CI[{dS.lower:+.2f},{dS.upper:+.2f}]{' SIG' if dS.lower>0 else ' ns '}"
              f"  dCAGR={dC.point*100:+.1f}% CI[{dC.lower*100:+.1f}%,{dC.upper*100:+.1f}%]{' SIG' if dC.lower>0 else ' ns '}"
              f"  DSR={dsr:.2f}")


if __name__ == "__main__":
    main()
