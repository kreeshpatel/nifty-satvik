"""Monte-Carlo year-on-year returns for config P (40%@2R / 40% blow-off pattern / 20% runner-to-44wSMA).

Owner request 2026-07-16: "year on year return on monte carlo simulation for 500 iterations of P with
10 lakh capital."

Method: run P on the LIVE book (A-only + LIVE_DISCIPLINE), take its DAILY return series, block-bootstrap
(63-trading-day blocks — one quarter, preserves the swing book's autocorrelation) into 500 synthetic
paths of the same length, start each at Rs 10,00,000, and report the per-year and terminal distributions.

This is a REVIEW artifact on an already-tested config (no trial). P fails the 2022-26 gate (0.91) and runs
a -39.5% drawdown; the MC shows the dispersion of outcomes, not a recommendation.

    python scripts/mc_year_on_year_P.py
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
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe

CAP = 1_000_000.0                      # Rs 10 lakh
N_ITER = 500
BLOCK = 63                             # ~1 quarter of trading days
SEED = 20260716
P_CFG = dict(scaled_exit=dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0,
                              pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0))


def pctl(a, p):
    return float(np.percentile(a, p))


def main():
    ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
    a = R94.grade_a_entries(P)
    # EXACT config P from FINDING_pattern_exit: A-only + LIVE_DISCIPLINE + the scaled pattern exit.
    # (scaled_exit replaces the P2 trend exit, so P2_EXIT keys are not passed.) Parity-asserted below.
    m = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, a_grade=a, **LIVE_DISCIPLINE, **P_CFG)
    _yrs0 = (m["curve"].index[-1] - m["curve"].index[0]).days / 365.25
    _cagr0 = (m["curve"].sort_index().iloc[-1] / EQ0) ** (1 / _yrs0) - 1
    _dd0 = (m["curve"].sort_index() / m["curve"].sort_index().cummax() - 1).min()
    assert m["trades"] == 130 and abs(_cagr0 - 0.272) < 0.01 and abs(_dd0 + 0.395) < 0.01, \
        f"config-P parity FAILED: tr={m['trades']} cagr={_cagr0:.3f} dd={_dd0:.3f} (expected 130 / 0.272 / -0.395)"
    eq = m["curve"].sort_index()
    eq = eq / eq.iloc[0] * CAP                                  # rebase to Rs 10L
    r = eq.pct_change().dropna()
    rv = r.to_numpy()
    n = len(rv)

    # ---- realized calendar-year returns (the anchor) ----
    print(f"=== CONFIG P — REALIZED path, Rs {CAP:,.0f} start ({eq.index[0].date()} -> {eq.index[-1].date()}) ===")
    yr = eq.groupby(eq.index.year)
    yend = yr.last(); ystart = yr.first()
    prev = CAP
    print(f"  {'year':6s} {'start Rs':>14s} {'end Rs':>14s} {'return':>9s}")
    for y in yend.index:
        s0 = prev; s1 = yend[y]; ret = s1 / s0 - 1
        print(f"  {y:6d} {s0:14,.0f} {s1:14,.0f} {ret*100:8.1f}%")
        prev = s1
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / CAP) ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    print(f"  realized CAGR {cagr*100:.1f}%  |  terminal Rs {eq.iloc[-1]:,.0f}  |  max drawdown {dd*100:.1f}%")

    # ---- Monte-Carlo: 63-day block bootstrap, 500 paths ----
    rng = np.random.RandomState(SEED)
    n_blocks = int(np.ceil(n / BLOCK))
    yr_len = 252
    n_years = n // yr_len
    year_rets = np.zeros((N_ITER, n_years))
    terminals = np.zeros(N_ITER); cagrs = np.zeros(N_ITER); mdds = np.zeros(N_ITER)
    for it in range(N_ITER):
        starts = rng.randint(0, n - BLOCK + 1, size=n_blocks)
        path = np.concatenate([rv[s:s + BLOCK] for s in starts])[:n]
        curve = CAP * np.cumprod(1 + path)
        peak = np.maximum.accumulate(curve)
        mdds[it] = (curve / peak - 1).min()
        terminals[it] = curve[-1]
        cagrs[it] = (curve[-1] / CAP) ** (252 / n) - 1
        c0 = CAP
        for y in range(n_years):
            seg = curve[y * yr_len:(y + 1) * yr_len]
            c1 = seg[-1]
            year_rets[it, y] = c1 / c0 - 1
            c0 = c1

    print(f"\n=== MONTE-CARLO — {N_ITER} iterations, 63-day block bootstrap, Rs {CAP:,.0f} start ===")
    print(f"  (synthetic years = {yr_len} trading days each; {n_years} years per path)\n")
    print(f"  {'year':6s} {'p5':>9s} {'p25':>9s} {'MEDIAN':>9s} {'p75':>9s} {'p95':>9s} {'P(loss)':>8s}")
    for y in range(n_years):
        col = year_rets[:, y] * 100
        ploss = (year_rets[:, y] < 0).mean() * 100
        print(f"  yr {y+1:2d}  {pctl(col,5):8.1f}% {pctl(col,25):8.1f}% {pctl(col,50):8.1f}% "
              f"{pctl(col,75):8.1f}% {pctl(col,95):8.1f}% {ploss:6.0f}%")

    print(f"\n  --- across all {N_ITER} paths ---")
    print(f"  annual return   : median {pctl(cagrs,50)*100:5.1f}%   p5 {pctl(cagrs,5)*100:5.1f}%   p95 {pctl(cagrs,95)*100:5.1f}%")
    print(f"  terminal Rs     : median {pctl(terminals,50):12,.0f}   p5 {pctl(terminals,5):12,.0f}   p95 {pctl(terminals,95):12,.0f}")
    print(f"  max drawdown    : median {pctl(mdds,50)*100:5.1f}%   p5(worst) {pctl(mdds,5)*100:5.1f}%   worst {mdds.min()*100:5.1f}%")
    allyr = year_rets.flatten()
    print(f"  single-year     : best {allyr.max()*100:5.1f}%   worst {allyr.min()*100:5.1f}%   P(any loss year) {(year_rets.min(axis=1)<0).mean()*100:.0f}%")
    print(f"\n  NOTE: P is IN-SAMPLE, fails the 2022-26 gate (0.91) and runs a -39.5% realized DD. The block")
    print(f"        bootstrap assumes future return blocks resemble 2017-26; it does NOT model regime change,")
    print(f"        and the realized edge is concentrated in the 2017-21 bull. Treat the upside percentiles")
    print(f"        as optimistic. Not indicative of future results.")


if __name__ == "__main__":
    main()
