"""Is a bad period for THIS strategy family knowable in advance? A PIT market-state screen.

MOTIVATION. The owner wants a capital-preservation mode that stands the book down before a
downturn. 0133 §6b already showed the naive version is wrong-signed: the family lost in 2018
(Nifty +3.2%) and 2025 (Nifty +10.5%) and made money in 2026 (Nifty -8.7%). Index DIRECTION is not
the variable. This screen asks whether any PIT-computable market state IS.

The instrument is the family factor: the equal-weight daily return of the nine surveyed strategies
(0133), which is legitimate because their annual returns correlate at rho=0.678 with zero negative
pairs -- they are one bet, so one factor represents them.

NINE STATE VARIABLES, all trailing-only and computable at the close of day t, chosen to span
genuinely different "fronts" rather than nine flavours of the same one:

  DIRECTION    idx_above_200   Nifty > its own 200DMA                (the naive incumbent)
               idx_dd_252      Nifty drawdown from its trailing 1y peak
  BREADTH      breadth_200     % of the eligible universe above its own 200DMA
               breadth_50      % above its own 50DMA
               breadth_chg_21  21-day change in breadth_200          (deterioration, not level)
  PERSISTENCE  persist_63      fraction of the last 63d Nifty closed above its 20DMA
               newhigh_pct     % of the universe within 5% of its own 52-week high
  VOLATILITY   rvol_63         realised vol of the Nifty over 63d
  DISPERSION   disp_63         cross-sectional stdev of 63d stock returns

PRE-COMMITTED BAR, fixed before running. A state variable is INFORMATIVE only if:
  (1) Spearman rank-IC vs the FORWARD 63-day family return has |IC| >= 0.10, AND
  (2) the top-vs-bottom quintile spread has a bootstrap CI excluding zero, AND
  (3) the sign is consistent in >= 7 of the 10 calendar years.
Failing any leg is a NULL for that front. Anything that passes is a MEASUREMENT, not a licence to
trade -- 0103 (switch not learnable OOS) still governs, and a passing variable would have to clear
an activation bound before any trial is proposed.

CONFOUND NAMED IN ADVANCE: forward 63d windows overlap heavily, so naive CIs are far too tight.
The quintile CI is therefore a BLOCK bootstrap on 63-day blocks, and the per-year leg is the real
robustness test.

This costs one screen-ledger row (19). `n_trials` stays 138.

    python scripts/diag_market_state_screen.py
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
FWD = 63
IC_BAR, YEAR_BAR = 0.10, 7
BOOT, SEED = 5000, 20260806


def build_state(P) -> pd.DataFrame:
    """All nine state variables, trailing-only, on the common date index."""
    close = pd.DataFrame({t: pd.Series(d["c"], index=d["idx"]) for t, d in P.items()})
    memb = pd.DataFrame({t: pd.Series(d["mem"], index=d["idx"]) for t, d in P.items()})
    close = close.sort_index()
    memb = memb.reindex(close.index).fillna(False).astype(bool)
    elig = memb & close.notna()

    sma200 = close.rolling(200).mean()
    sma50 = close.rolling(50).mean()
    hi52 = close.rolling(252).max()
    ret63 = close / close.shift(63) - 1.0

    def frac(mask):
        m = (mask & elig).sum(axis=1)
        n = elig.sum(axis=1)
        return (m / n.replace(0, np.nan))

    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index()).reindex(close.index, method="ffill")

    S = pd.DataFrame(index=close.index)
    S["idx_above_200"] = (n50 / n50.rolling(200).mean() - 1.0)
    S["idx_dd_252"] = n50 / n50.rolling(252).max() - 1.0
    S["breadth_200"] = frac(close > sma200)
    S["breadth_50"] = frac(close > sma50)
    S["breadth_chg_21"] = S["breadth_200"] - S["breadth_200"].shift(21)
    S["persist_63"] = (n50 > n50.rolling(20).mean()).rolling(63).mean()
    S["newhigh_pct"] = frac(close >= hi52 * 0.95)
    S["rvol_63"] = n50.pct_change().rolling(63).std() * np.sqrt(252)
    S["disp_63"] = ret63.where(elig).std(axis=1)
    return S


def block_boot_ci(x: np.ndarray, block: int = FWD, n: int = BOOT) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    if len(x) < block * 2:
        return (np.nan, np.nan)
    nb = int(np.ceil(len(x) / block))
    starts = np.arange(len(x) - block + 1)
    out = np.empty(n)
    for i in range(n):
        s = rng.choice(starts, nb)
        out[i] = np.concatenate([x[j:j + block] for j in s])[:len(x)].mean()
    return tuple(np.percentile(out, [2.5, 97.5]))


def main() -> int:
    print("=== PIT MARKET-STATE SCREEN — is a bad period for this family knowable in advance? ===")
    print(f"    target = FORWARD {FWD}d return of the equal-weight family factor (the 9 strategies)")
    print(f"    bar: |rank-IC| >= {IC_BAR}  AND  Q5-Q1 block-bootstrap CI excludes 0  "
          f"AND  sign consistent in >= {YEAR_BAR}/10 years\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}")

    rets = {}
    for tag, fn, prov in SPECS:
        if "RANDOM" in tag.upper():
            continue
        m = run(P, fn, start=START, end=END)
        rets[tag] = m["eq"].pct_change()
    fam = pd.DataFrame(rets).mean(axis=1).dropna()
    fam_eq = (1 + fam).cumprod()
    print(f"  family factor built from {len(rets)} strategies, {len(fam):,} days\n")

    S = build_state(P).reindex(fam.index).dropna(how="all")
    fwd = (fam_eq.shift(-FWD) / fam_eq - 1.0)
    df = S.join(fwd.rename("fwd")).dropna()
    print(f"  usable observations {len(df):,}  ({df.index[0].date()} -> {df.index[-1].date()})\n")

    print("=== PER-YEAR: state variable averages vs the family's actual year ===")
    yr_ret = fam_eq.resample("YE").last().pct_change()
    hdr = "  year   fam%" + "".join(f"{c[:11]:>13}" for c in S.columns)
    print(hdr)
    for y, g in df.groupby(df.index.year):
        r = yr_ret[yr_ret.index.year == y]
        rv = r.iloc[0] * 100 if len(r) and np.isfinite(r.iloc[0]) else np.nan
        print(f"  {y} {rv:>6.1f}%" + "".join(f"{g[c].mean():>12.3f} " for c in S.columns))

    print("\n=== SCREEN RESULT (rank-IC vs forward 63d family return) ===")
    verdicts = []
    for c in S.columns:
        sub = df[[c, "fwd"]].dropna()
        ic = sub[c].corr(sub["fwd"], method="spearman")
        q = pd.qcut(sub[c], 5, labels=False, duplicates="drop")
        lo_x = sub["fwd"][q == 0].to_numpy()
        hi_x = sub["fwd"][q == q.max()].to_numpy()
        spread = hi_x.mean() - lo_x.mean()
        lo_ci = block_boot_ci(lo_x)
        hi_ci = block_boot_ci(hi_x)
        overlap = not (hi_ci[0] > lo_ci[1] or lo_ci[0] > hi_ci[1])
        signs = []
        for y, g in sub.groupby(sub.index.year):
            if len(g) < 60:
                continue
            qq = pd.qcut(g[c], 3, labels=False, duplicates="drop")
            if qq.nunique() < 2:
                continue
            signs.append(np.sign(g["fwd"][qq == qq.max()].mean() - g["fwd"][qq == 0].mean()))
        agree = int(max(sum(1 for s in signs if s > 0), sum(1 for s in signs if s < 0)))
        ok = (abs(ic) >= IC_BAR) and (not overlap) and (agree >= YEAR_BAR)
        verdicts.append((c, ic, spread, overlap, agree, len(signs), ok))
        print(f"  {c:<16} IC {ic:>+6.3f}   Q5-Q1 {spread*100:>+7.2f}pp   "
              f"CIs {'OVERLAP' if overlap else 'SEPARATE'}   years {agree}/{len(signs)}   "
              f"{'** PASSES' if ok else 'null'}")

    print("\n=== VERDICT ===")
    passed = [v for v in verdicts if v[6]]
    if not passed:
        print("  NO front passes all three legs. A capital-preservation switch on these states has")
        print("  no measurable basis: the bad periods are not flagged in advance by direction,")
        print("  breadth, persistence, volatility or dispersion.")
    else:
        for v in passed:
            print(f"  {v[0]} PASSES (IC {v[1]:+.3f}, {v[4]}/{v[5]} years). MEASUREMENT ONLY —")
            print("  0103 (switch not learnable OOS) still governs; an activation bound is required")
            print("  before any trial may be pre-registered.")

    print("\n  standing counts: screens 19 · sealed opens 1 · n_trials 138")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
