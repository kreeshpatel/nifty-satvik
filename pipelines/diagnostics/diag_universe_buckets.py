"""Does a narrower / higher-quality universe help? PIT size buckets, each judged against ITSELF.

THE QUESTION. The owner asks whether the Nifty-500 universe is too broad and noisy, and whether
restricting to midcap-index-type names (or a curated "good stocks" list) would raise returns.

TWO TRAPS THIS DESIGN AVOIDS, both fatal if ignored:

  1. **Hindsight curation.** Any "universe of good stocks" chosen with knowledge of what did well is
     survivorship bias by construction and produces a beautiful backtest with zero live value. The
     buckets here are assigned **per date** from **trailing** turnover only -- a stock migrates
     between buckets over time exactly as it would have in life. (0108 separately killed a
     fundamentals growth-filter universe, so that route is already answered.)
  2. **Benchmark substitution.** Midcaps outperformed over this window, so a midcap-restricted
     strategy looks better with zero skill if compared to the Nifty-50. Each bucket is therefore
     ALSO benchmarked against **its own equal-weight buy-and-hold return**, which is the only
     comparison that isolates selection skill from size beta.

BUCKETS (PIT, reassigned daily, within the corrected PIT Nifty-500 membership):
    LARGE  turnover rank   1-100   (~Nifty-100 analogue)
    MID    turnover rank 101-250   (~Nifty Midcap-150 analogue)
    SMALL  turnover rank 251+      (~Smallcap analogue)
Rank is on trailing 63-day median turnover (close x volume), so it uses no future information.

Strategy under test: Supertrend + Pivot (0133's survivor), the same book as everywhere else.

Window 2017-01-01..2026-06-30 (2016 excluded per 0133 §3a-CORRECTION: ~21 eligible names).

**The bar that matters**: a bucket is interesting only if the strategy beats THAT BUCKET's own
equal-weight return. Beating the Nifty-50 by holding midcaps is size beta, not edge.

MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_universe_buckets.py
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
from diag_ranade_deepdive import engine  # noqa: E402
from diag_swing_strategy_survey import build_base  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
BANDS = {"LARGE  (turnover rank 1-100)": (0, 100),
         "MID    (rank 101-250)": (100, 250),
         "SMALL  (rank 251+)": (250, 10_000)}


def attach_buckets(P) -> pd.DataFrame:
    """Per-date turnover rank within eligible PIT members. Writes d['trank'] per name."""
    tover = {}
    for t, d in P.items():
        s = pd.Series(d["c"] * d["v"], index=d["idx"]).rolling(63).median()
        tover[t] = s.where(pd.Series(d["mem"], index=d["idx"]))
    T = pd.DataFrame(tover).sort_index()
    T = T[(T.index >= START) & (T.index <= END)]
    rank = T.rank(axis=1, ascending=False, method="first")
    for t, d in P.items():
        if t in rank.columns:
            d["trank"] = rank[t].reindex(d["idx"]).to_numpy()
        else:
            d["trank"] = np.full(len(d["idx"]), np.nan)
    return rank


def bucket_benchmark(P, lo, hi) -> dict:
    """Equal-weight buy-and-hold of whatever is in the bucket each day (daily rebalance).
    NOTE: daily EW rebalancing carries a small rebalancing bonus vs a real tradable index; it is
    used identically for every bucket so the COMPARISON between buckets is unaffected."""
    rets, wts = {}, {}
    for t, d in P.items():
        r = pd.Series(d["c"], index=d["idx"]).pct_change()
        inb = pd.Series((d["trank"] > lo) & (d["trank"] <= hi) & d["mem"], index=d["idx"])
        rets[t] = r
        wts[t] = inb
    R = pd.DataFrame(rets)
    W = pd.DataFrame(wts).reindex(R.index).fillna(False)
    R = R[(R.index >= START) & (R.index <= END)]
    W = W.loc[R.index]
    daily = (R.where(W)).mean(axis=1).fillna(0.0)
    eq = (1 + daily).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return dict(cagr=eq.iloc[-1] ** (1 / yrs) - 1,
                sharpe=daily.mean() / daily.std() * np.sqrt(252) if daily.std() else np.nan,
                dd=(eq / eq.cummax() - 1).min(), n=int(W.sum(axis=1).mean()), eq=eq)


def main() -> int:
    print("=== UNIVERSE BUCKETS — is a narrower universe better, or just different beta? ===")
    print(f"    strategy = Supertrend + Pivot (0133 survivor) | window {START}..{END}")
    print("    buckets assigned PER DATE from TRAILING 63d median turnover -> no hindsight\n")
    P = build_base(corrected_universe(), load_membership())
    rank = attach_buckets(P)
    print(f"  names {len(P)}   mean eligible/day {int(rank.notna().sum(axis=1).mean())}\n")

    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    n50 = n50[(n50.index >= START) & (n50.index <= END)]
    nr = n50.pct_change().dropna()
    neq = (1 + nr).cumprod()
    nyrs = (neq.index[-1] - neq.index[0]).days / 365.25
    print("=== BENCHMARKS ===")
    print(f"  NIFTY-50 buy-and-hold                CAGR {(neq.iloc[-1]**(1/nyrs)-1)*100:>7.2f}%  "
          f"Sh {nr.mean()/nr.std()*np.sqrt(252):>6.3f}  DD {(neq/neq.cummax()-1).min()*100:>7.1f}%")
    bench = {}
    for tag, (lo, hi) in BANDS.items():
        b = bucket_benchmark(P, lo, hi)
        bench[tag] = b
        print(f"  {tag:<34} CAGR {b['cagr']*100:>7.2f}%  Sh {b['sharpe']:>6.3f}  "
              f"DD {b['dd']*100:>7.1f}%   ~{b['n']} names/day  [equal-weight buy-and-hold]")

    print("\n=== THE STRATEGY, RESTRICTED TO EACH BUCKET ===")
    full, _ = engine(P, start=START, end=END)
    print(f"  {'UNRESTRICTED (all N500)':<34} CAGR {full['cagr']*100:>7.2f}%  Sh {full['sharpe']:>6.3f}  "
          f"DD {full['dd']*100:>7.1f}%  n {full['n']:>4,}  R {full['meanR']:>+5.2f}")
    rows = []
    for tag, (lo, hi) in BANDS.items():
        Q = {}
        for t, d in P.items():
            d2 = dict(d)
            d2["mem"] = d["mem"] & (d["trank"] > lo) & (d["trank"] <= hi)
            Q[t] = d2
        m, _ = engine(Q, start=START, end=END)
        rows.append((tag, m, bench[tag]))
        print(f"  {tag:<34} CAGR {m['cagr']*100:>7.2f}%  Sh {m['sharpe']:>6.3f}  "
              f"DD {m['dd']*100:>7.1f}%  n {m['n']:>4,}  R {m['meanR']:>+5.2f}")

    print("\n=== THE ONLY COMPARISON THAT ISOLATES SKILL: strategy MINUS its own bucket ===")
    print("  (beating the Nifty-50 by holding midcaps is size beta, not edge)")
    for tag, m, b in rows:
        d_cagr = (m["cagr"] - b["cagr"]) * 100
        d_sh = m["sharpe"] - b["sharpe"]
        verdict = "ADDS" if (d_cagr > 0 and d_sh > 0) else "SUBTRACTS"
        print(f"  {tag:<34} dCAGR {d_cagr:>+7.2f}pp   dSharpe {d_sh:>+6.3f}   -> selection {verdict}")

    print("\n=== PER-YEAR of the strategy by bucket (%) ===")
    print("  year " + "".join(f"{t.split(' ')[0]:>12}" for t, _, _ in rows) + f"{'UNRESTR':>12}")
    def ann(eq):
        y = eq.resample("YE").last()
        y = pd.concat([pd.Series([eq.iloc[0]], index=[eq.index[0]]), y])
        return pd.Series({b.year: y[b] / y[a] - 1 for a, b in zip(y.index[:-1], y.index[1:])})
    A = {t: ann(m["eq"]) for t, m, _ in rows}
    A["UNRESTR"] = ann(full["eq"])
    for yr in sorted(A["UNRESTR"].index):
        print(f"  {yr}" + "".join(f"{A[k].get(yr, np.nan)*100:>11.1f}%" for k in A))

    print("\n  standing counts: screens 19 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
