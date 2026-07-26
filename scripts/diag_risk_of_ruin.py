"""MEASUREMENT (0 trials): risk-of-ruin / half-Kelly / barbell capital-fraction curve for the book.

Turns the survival research (MacLean-Ziemba half-Kelly; Taleb barbell; RoR<5% target) into an actual
number on our own return series. Sizes the SATELLITE fraction so total-capital drawdown stays inside a
personal tolerance, using a STRESSED drawdown (out-of-sample is deeper than the -42/-46% backtest).
Bootstrap is block-resampled to preserve momentum autocorrelation. Judged on OUR data; owner supplies
the personal DD tolerance (the one input no backtest can set).

    python scripts/diag_risk_of_ruin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "research" / "exports" / "sleeve_daily_returns.csv"
BLOCK = 21          # ~1 trading month blocks (preserve autocorrelation / momentum crashes)
N_BOOT = 3000
STRESS = 1.4        # out-of-sample DD deepener: -42% backtest -> ~-59% stressed (research: -55..-65%)
TOL_GRID = [0.10, 0.15, 0.20, 0.25]   # personal tolerance on TOTAL capital drawdown


def _maxdd(eq):
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def _block_paths(r, n, block, rng):
    a = r.to_numpy(float); N = len(a); nb = int(np.ceil(N / block))
    for _ in range(n):
        starts = rng.integers(0, N - block + 1, size=nb)
        yield np.concatenate([a[s:s + block] for s in starts])[:N]


def main() -> int:
    if not CACHE.exists():
        print("run diag_regime_sleeve_learnability.py first to cache sleeve returns"); return 1
    d = pd.read_csv(CACHE, index_col=0, parse_dates=True)
    r = d["r_mom"].dropna()   # the momentum book (frozen base); generalize to whichever vehicle ships
    ann_ret = (1 + r).prod() ** (252 / len(r)) - 1
    ann_vol = r.std() * np.sqrt(252)
    sharpe = r.mean() / r.std() * np.sqrt(252)
    hist_dd = _maxdd((1 + r).cumprod())
    kelly = float(r.mean() / r.var())        # f* = mu/sigma^2 (leverage on the strategy itself)
    print("=== MEASUREMENT: risk-of-ruin / half-Kelly / barbell fraction (0 trials) ===")
    print(f"book (r_mom): annRet {ann_ret*100:.1f}% | annVol {ann_vol*100:.1f}% | Sharpe {sharpe:.2f} | "
          f"hist MaxDD {hist_dd*100:.1f}%")
    print(f"Kelly leverage f* = {kelly:.2f}x  ->  HALF-Kelly {kelly/2:.2f}x  (full Kelly overbets an "
          f"in-sample edge; use <= half)\n")

    rng = np.random.default_rng(20260726)
    # stressed strategy DD from the block-bootstrap 95th-percentile (worse-than-history is the planning number)
    dds = np.array([_maxdd(np.cumprod(1 + p)) for p in _block_paths(r, N_BOOT, BLOCK, rng)])
    boot_p95_dd = np.percentile(dds, 5)   # 5th pct of (negative) DD = the deep 95%-tail
    stressed_dd = min(hist_dd * STRESS, boot_p95_dd)
    print(f"drawdown planning number: hist {hist_dd*100:.0f}% | bootstrap 95%-tail {boot_p95_dd*100:.0f}% | "
          f"STRESSED (x{STRESS}) {hist_dd*STRESS*100:.0f}%  ->  plan against {stressed_dd*100:.0f}%\n")

    print("barbell satellite fraction  (core = safe/cash; total-capital DD kept inside tolerance)")
    print(f"  {'your total-DD tolerance':<24}{'DD-budget frac':>16}{'unproven (halved)':>20}{'boot P(DD>tol)@half':>22}")
    for tol in TOL_GRID:
        frac = min(1.0, tol / abs(stressed_dd))        # satellite = tolerance / stressed strategy DD
        half = frac / 2                                 # halve until forward-proven
        # bootstrap check: at the halved fraction, P(total-capital DD worse than tolerance)?
        exceed = np.mean([_maxdd(np.cumprod(1 + half * p)) < -tol for p in _block_paths(r, N_BOOT, BLOCK, rng)])
        print(f"  {tol*100:>6.0f}% of total capital {frac*100:>13.0f}%{half*100:>18.0f}%{exceed*100:>20.1f}%")

    print("\nReadout: the satellite fraction is set by YOUR total-DD tolerance / the STRESSED book DD, not by")
    print("the backtest Sharpe. Start at the halved (unproven) column; earn size only on forward-wall evidence.")
    print("At those halved fractions the bootstrap P(breaching tolerance) should sit well under 5% (RoR target).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
