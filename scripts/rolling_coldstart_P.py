"""Rolling cold-start simulation — the FORWARD portfolio experience from an arbitrary start date.

Owner question 2026-07-16: "if i have already taken the initial stocks then what about the stocks that
come my way from that day. how to test that."

The 2017-start backtest is ONE history. This starts FRESH with Rs 10L on many different dates, runs each
forward for a fixed horizon (fresh cash, 0 positions -> ramp -> steady state), and reports the
DISTRIBUTION of outcomes. It captures exactly the owner's worry: regime luck at the start, which initial
stocks you catch, and the capital those tie up (so later signals are skipped for cash — the same
skipped_cash mechanism, now measured per start date).

Config = P (40%@2R / 40% blow-off pattern / 20% runner-to-44wSMA) on the A-only + LIVE_DISCIPLINE book.
Also runs the shipped LIVE (P2 exit) for comparison. Review artifact; no trial.

    python scripts/rolling_coldstart_P.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from run_bhanushali_cron import LIVE_DISCIPLINE, P2_EXIT
from run_bhanushali_path1 import corrected_universe

CAP = 1_000_000.0
P_CFG = dict(scaled_exit=dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0,
                              pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0))
LIVE_CFG = dict(**P2_EXIT)
HORIZONS = {"1yr": 365, "2yr": 730}


def pctl(a, p):
    return float(np.percentile(a, p)) if len(a) else float("nan")


def run_grid(P, mem, a, cfg, starts):
    """For each start date: fresh CAP, run forward, slice each horizon, record fwd return / maxDD / names."""
    rows = []
    for sd in starts:
        m = R94.backtest(P, mem, start=sd, eq0=CAP, a_grade=a, **LIVE_DISCIPLINE, **cfg)
        eq = m["curve"].sort_index()
        if len(eq) < 30:
            continue
        eq = eq / eq.iloc[0] * CAP
        rec = {"start": sd}
        for hz, days in HORIZONS.items():
            w = eq[eq.index <= eq.index[0] + pd.Timedelta(days=days)]
            if len(w) < 20:
                rec[hz + "_ret"] = np.nan; rec[hz + "_dd"] = np.nan; continue
            rec[hz + "_ret"] = w.iloc[-1] / CAP - 1
            rec[hz + "_dd"] = (w / w.cummax() - 1).min()
        rows.append(rec)
    return pd.DataFrame(rows)


def show(df, cfgname):
    print(f"\n=== {cfgname} — {len(df)} cold starts (fresh Rs 10L each) ===")
    for hz in HORIZONS:
        r = df[hz + "_ret"].dropna() * 100
        d = df[hz + "_dd"].dropna() * 100
        term = (df[hz + "_ret"].dropna() + 1) * CAP
        print(f"  {hz} forward return : p5 {pctl(r,5):6.1f}%  p25 {pctl(r,25):6.1f}%  MED {pctl(r,50):6.1f}%  "
              f"p75 {pctl(r,75):6.1f}%  p95 {pctl(r,95):6.1f}%  |  P(loss) {(r<0).mean()*100:.0f}%")
        print(f"  {hz} terminal Rs    : p5 {pctl(term,5):11,.0f}   MED {pctl(term,50):11,.0f}   p95 {pctl(term,95):11,.0f}")
        print(f"  {hz} max drawdown   : median {pctl(d,50):6.1f}%   worst {d.min():6.1f}%")
        print(f"  {hz} SPREAD (best - worst start): {r.max()-r.min():.0f} pp  [worst start {r.min():.0f}%, best {r.max():.0f}%]")


def main():
    ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
    a = R94.grade_a_entries(P)
    # first trading day of each quarter, 2017Q1 .. 2024Q2 (>= 2yr forward for every start)
    qs = pd.date_range("2017-01-01", "2024-04-01", freq="QS")
    starts = [str(q.date()) for q in qs]
    print(f"rolling cold-start grid: {len(starts)} quarterly starts, {starts[0]} .. {starts[-1]}")
    print(f"each = fresh Rs {CAP:,.0f}, 0 positions, ramp up (the real cold start), forward 1yr & 2yr")

    dfP = run_grid(P, mem, a, P_CFG, starts)
    dfL = run_grid(P, mem, a, LIVE_CFG, starts)
    show(dfL, "LIVE (shipped: P2 exit)")
    show(dfP, "P (40/40/20 pattern exit)")

    print("\n=== the answer to your worry ===")
    for hz in HORIZONS:
        rP = dfP[hz + "_ret"].dropna() * 100; rL = dfL[hz + "_ret"].dropna() * 100
        print(f"  {hz}: your outcome depends HEAVILY on start date — LIVE ranges {rL.min():.0f}%..{rL.max():.0f}%, "
              f"P ranges {rP.min():.0f}%..{rP.max():.0f}% across the {len(rL)} start dates.")
    print("  A single 2017-start backtest hides this spread. The cold-start distribution is the honest read")
    print("  of 'what if I start today'. NOTE: still in-sample; P fails the 2022-26 gate. Not a forecast.")


if __name__ == "__main__":
    main()
