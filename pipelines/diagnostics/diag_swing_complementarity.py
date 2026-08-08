"""Is there anything to switch TO? Per-year returns and annual-return correlation across all
nine surveyed swing strategies plus the random control.

MOTIVATION. The owner asked whether we can detect bad years and switch to a different system in
them. Regime switching is the programme's most-killed idea (O-001, 0056, 0086, 0090, and 0103
specifically: "switch not learnable OOS; static blend dominates"), so the proposal collides head-on.
Rather than restate the law, this asks the question the law does NOT answer for this new family:

    do these nine strategies actually have different good and bad years?

If their annual returns are near-perfectly correlated there is nothing to switch to and the idea is
closed by arithmetic, not by precedent. If some are genuinely complementary, a STATIC BLEND is the
form 0103 says dominates a learned switch — so that is what gets priced here, not a switch.

This spends no new selection: every cell is already-run code re-expressed per year, and the equal-
weight blend is a fixed rule with no fitted parameter. Continuous 2016-2026 so the equity path is
one run, per the continuous-slice law.

MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_swing_complementarity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from diag_swing_strategy_survey import SPECS, build_base, run  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END = "2016-01-01", "2026-06-30"


def annual(eq: pd.Series) -> pd.Series:
    y = eq.resample("YE").last()
    y = pd.concat([pd.Series([eq.iloc[0]], index=[eq.index[0]]), y])
    return pd.Series({b.year: y[b] / y[a] - 1.0 for a, b in zip(y.index[:-1], y.index[1:])})


def main() -> int:
    print("=== COMPLEMENTARITY — do these strategies have DIFFERENT bad years? ===")
    print(f"    continuous {START}..{END}, one equity path per strategy\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")

    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    n50 = n50[(n50.index >= START) & (n50.index <= END)]
    nifty_yr = annual(n50)

    curves, short = {}, {}
    for tag, fn, prov in SPECS:
        m = run(P, fn, start=START, end=END)
        name = tag.split("(")[0].strip().replace(">> ", "")[:22]
        curves[name] = annual(m["eq"])
        short[name] = m
    A = pd.DataFrame(curves)

    print("=== ANNUAL NET RETURN (%) — rows are years, last column is the Nifty-50 ===")
    hdr = "  year " + "".join(f"{c[:11]:>13}" for c in A.columns) + f"{'NIFTY50':>10}"
    print(hdr)
    for yr in A.index:
        cells = "".join(f"{A.loc[yr, c]*100:>12.1f}%" for c in A.columns)
        nv = nifty_yr.get(yr, np.nan)
        print(f"  {yr}" + cells + f"{nv*100:>9.1f}%")

    print("\n=== HOW MANY STRATEGIES WERE POSITIVE IN EACH YEAR? ===")
    for yr in A.index:
        pos = int((A.loc[yr] > 0).sum())
        nv = nifty_yr.get(yr, np.nan)
        flag = "NIFTY DOWN" if nv < 0 else ""
        print(f"  {yr}  {pos}/{len(A.columns)} positive   nifty {nv*100:>6.1f}%  {flag}"
              f"   {'#' * pos}")

    print("\n=== CORRELATION OF ANNUAL RETURNS (the answer to 'is there anything to switch to?') ===")
    C = A.corr()
    iu = np.triu_indices_from(C.values, k=1)
    off = C.values[iu]
    print(f"  mean pairwise correlation {np.nanmean(off):+.3f}   median {np.nanmedian(off):+.3f}   "
          f"min {np.nanmin(off):+.3f}   max {np.nanmax(off):+.3f}")
    print(f"  pairs with corr < 0 : {(off < 0).sum()} of {len(off)}")
    print(f"  correlation of each strategy to the NIFTY-50 annual return:")
    for c in A.columns:
        j = A[c].reindex(nifty_yr.index)
        print(f"    {c:<24} {j.corr(nifty_yr):+.3f}")

    print("\n=== STATIC EQUAL-WEIGHT BLEND (the form 0103 says dominates a learned switch) ===")
    real = [c for c in A.columns if "RANDOM" not in c.upper()]
    blend = A[real].mean(axis=1)
    print(f"  blend of all {len(real)} strategies, rebalanced annually, no fitted parameter:")
    for yr in blend.index:
        print(f"    {yr}  {blend[yr]*100:>+7.2f}%")
    cagr = float(np.prod(1 + blend.values) ** (1 / len(blend)) - 1)
    print(f"  blend CAGR {cagr*100:+.2f}%   positive years {int((blend>0).sum())}/{len(blend)}   "
          f"worst {blend.min()*100:+.2f}%")
    print(f"  best single strategy CAGR for reference: "
          f"{max(short[c]['cagr'] for c in real)*100:+.2f}%")

    A.to_csv(ROOT / "diagnostics" / "research" / "swing_annual_returns.csv")
    print("\n  -> diagnostics/research/swing_annual_returns.csv")
    print("  standing counts: screens 18 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
