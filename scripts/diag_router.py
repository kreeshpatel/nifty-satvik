"""Context-router — the gated test of its genuinely-new element: PER-BRANCH EXITS in one shared book.

A1 gate finding (verified): the zoo's `& ~wsig` masking ALREADY assigns exactly one origin per
name-week in a fixed priority order — i.e. the entry-side "state router" exists (Jaccard=1.0 vs any
one-state-per-name classifier). So the only untested element of the router spec is: each branch running
its OWN exit inside one shared-capital book (Stage 3: touch wants P2 book+blowoff, box wants let-run).

Gates enforced (plan Part C):
  R1 baseline = pure touch P2 asserted at 1.034 / -34.8% / 168
  R3 judge on the continuous-slice 2022-26 (baseline to beat = 1.29), never the full-period headline
  A5 branch-pair return correlations (all > 0.80 => diversification thesis dead)
  R9 multiple-testing: 4 configs declared up front

    python scripts/diag_router.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import filter_P

P2 = dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)          # touch's validated exit
LETRUN = dict(no_time_cap=True, wk20_trail_pct=None, blowoff_arm_r=0.0)      # box's validated exit
NAMES = {0: "touch44", 1: "box", 2: "trend_pullback", 3: "sr_pivot", 6: "cup_handle",
         7: "ascending_base", 8: "double_bottom"}
GOOD = [0, 1, 6, 7, 8]          # drop trend_pullback (22-26 Sharpe -0.06, DD -56%) + thin sr_pivot
# The router: each branch on ITS validated exit (Stage 3).
EXIT_BY_ORIGIN = {0: P2, 1: LETRUN, 6: P2, 7: P2, 8: P2}


def stats(curve, trades=None):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    dd = (e / e.cummax() - 1).min()
    rr = r[r.index >= "2022-01-01"]
    s22 = rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan
    return dict(sharpe=sh, cagr=cagr, dd=dd, calmar=cagr / abs(dd) if dd else np.nan, s22=s22, trades=trades, r=r)


def show(lab, m):
    print(f"  {lab:34s} tr={m['trades'] if m['trades'] is not None else '   -':>4} Sh={m['sharpe']:5.2f} "
          f"CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% Calmar={m['calmar']:4.2f} "
          f"22-26={m['s22']:5.2f}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    Pp = R94.prep_weekly_rank(ohlcv)
    Pw = R94.prep_weekly_rank(ohlcv, box_breakout=True, trend_pullback=True, sr_pivot=True, zoo_origins=(6, 7, 8))

    # ---- R1: baseline assertion ----
    mA = R94.backtest(Pp, mem, start="2017-01-01", eq0=EQ0, **P2)
    assert abs(mA["sharpe"] - 1.034) < 0.005 and mA["trades"] == 168, "R1 baseline assertion FAILED"
    a = stats(mA["curve"], mA["trades"])
    print("=== configs (Rs10L shared book, continuous-slice 2022-26; baseline to beat = 1.29) ===")
    show("A  live touch (P2)  [BASELINE]", a)

    # ---- B: all-7 shared, uniform exit ----
    mB = R94.backtest(filter_P(Pw, [0, 1, 2, 3, 6, 7, 8]), mem, start="2017-01-01", eq0=EQ0, **P2)
    show("B  all-7 shared, uniform P2", stats(mB["curve"], mB["trades"]))

    # ---- B': good branches, uniform exit ----
    mBp = R94.backtest(filter_P(Pw, GOOD), mem, start="2017-01-01", eq0=EQ0, **P2)
    show("B' good branches, uniform P2", stats(mBp["curve"], mBp["trades"]))

    # ---- R: THE ROUTER — good branches, PER-BRANCH exits ----
    mR = R94.backtest(filter_P(Pw, GOOD), mem, start="2017-01-01", eq0=EQ0, exit_by_origin=EXIT_BY_ORIGIN, **P2)
    r = stats(mR["curve"], mR["trades"])
    show("R  ROUTER: per-branch exits", r)

    print(f"\n  ROUTER vs BASELINE on the 2022-26 gate: {r['s22']:.2f} vs {a['s22']:.2f} -> "
          f"{'BEATS' if r['s22'] > a['s22'] else 'LOSES (a FINDING, not a retune trigger — R11)'}")

    # ---- A5: branch-pair return correlations ----
    print("\n=== A5 gate — branch-pair return correlations (all >0.80 => diversification dead) ===")
    rets = {}
    for f in GOOD:
        ec = R94.backtest(filter_P(Pw, [f]), mem, start="2017-01-01", eq0=EQ0,
                          exit_by_origin=EXIT_BY_ORIGIN, **P2)["curve"]
        rets[NAMES[f]] = ec.sort_index().pct_change().fillna(0.0)
    idx = sorted(set().union(*[set(s.index) for s in rets.values()]))
    M = pd.DataFrame({k: v.reindex(idx).fillna(0.0) for k, v in rets.items()})
    C = M.corr()
    print(C.round(2).to_string())
    pairs = [(i, j, C.loc[i, j]) for i in C.index for j in C.columns if i < j]
    hi = [p for p in pairs if p[2] > 0.80]
    print(f"\n  pairs >0.80: {len(hi)}/{len(pairs)} -> "
          f"{'DIVERSIFICATION DEAD (A5 kill-gate)' if len(hi) == len(pairs) else 'some genuine diversification exists'}")


if __name__ == "__main__":
    main()
