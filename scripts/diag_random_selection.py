"""MONTE-CARLO NULL: what are the book's stats if we fund RANDOM candidates instead of CRS-rank?

The live book activates 6,359 entry windows and funds only 168 (2.6%) — so selection is the dominant
decision. But every number we have (CRS-rank 1.29, conviction-rank 0.44) has only ever been compared to
another selector, never to CHANCE. This builds the null distribution: N random fill-orderings over the
SAME candidate pool (same setup, same exits, same capital) — only WHO gets the cash is randomised.

It answers three things at once:
  1. How much value does CRS-rank actually add? (its percentile in the null)
  2. Was conviction-rank's 0.44 genuinely bad, or just inside random noise?
  3. What is the book's inherent edge (the null's centre) vs its SELECTION edge (the gap above it)?

    python scripts/diag_random_selection.py [N_SIMS]
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
from diag_sleeves import P2_EXIT

N_SIMS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SIMS_CSV = ROOT / "research" / "substrate" / "random_selection_sims.csv"   # incremental: survives interruption


def stats(curve, trades=None):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]
    return dict(sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan,
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                dd=(e / e.cummax() - 1).min(),
                s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan,
                trades=trades)


def pct_rank(dist, val):
    d = np.asarray([x for x in dist if x == x])
    return (d < val).mean() * 100 if len(d) else np.nan


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)                      # touch-only = the LIVE book

    mA = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mA["sharpe"] - 1.034) < 0.005 and mA["trades"] == 168, "R1 baseline FAILED"
    a = stats(mA["curve"], mA["trades"])
    print(f"CRS-rank (live baseline): Sharpe {a['sharpe']:.2f}  CAGR {a['cagr']*100:.1f}%  "
          f"DD {a['dd']*100:.1f}%  22-26 {a['s22']:.2f}  tr {a['trades']}")

    keys = [(t, e0) for t, s in P.items() for e0 in s["entry_win"]]
    print(f"candidate pool: {len(keys)} entry windows; running {N_SIMS} random-selection sims...\n")

    # resume: keep any sims already persisted (an interrupted run costs nothing)
    done = {}
    if SIMS_CSV.exists():
        prev = pd.read_csv(SIMS_CSV)
        done = {int(r.seed): r._asdict() for r in prev.itertuples()}
        print(f"  resuming: {len(done)} sims already on disk")
    for seed in range(N_SIMS):
        if seed in done:
            continue
        rng = np.random.default_rng(seed)
        conv = {k: float(v) for k, v in zip(keys, rng.random(len(keys)))}
        m = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, fill_order="conviction",
                         conv_score=conv, **P2_EXIT)
        row = stats(m["curve"], m["trades"]); row["seed"] = seed
        pd.DataFrame([row]).to_csv(SIMS_CSV, mode="a", header=not SIMS_CSV.exists(), index=False)
        done[seed] = row
        if (seed + 1) % 10 == 0:
            print(f"  ...{seed+1}/{N_SIMS}", flush=True)

    df = pd.read_csv(SIMS_CSV).drop_duplicates(subset="seed").head(N_SIMS)
    print(f"\n=== RANDOM-SELECTION NULL (n={len(df)} sims; same setup/exits/capital, random fill order) ===")
    print(f"{'metric':10s} {'mean':>7s} {'median':>7s} {'std':>6s} {'p5':>7s} {'p95':>7s} {'min':>7s} {'max':>7s}")
    for col, scale, fmt in [("sharpe", 1, "6.2f"), ("cagr", 100, "6.1f"), ("dd", 100, "6.1f"),
                            ("s22", 1, "6.2f"), ("trades", 1, "6.0f")]:
        v = df[col].dropna() * scale
        print(f"{col:10s} {v.mean():{fmt}} {v.median():{fmt}} {v.std():{fmt}} "
              f"{np.percentile(v,5):{fmt}} {np.percentile(v,95):{fmt}} {v.min():{fmt}} {v.max():{fmt}}")

    print("\n=== WHERE THE REAL SELECTORS SIT IN THE NULL ===")
    for lab, val, col in [("CRS-rank (live)  Sharpe", a["sharpe"], "sharpe"),
                          ("CRS-rank (live)  22-26", a["s22"], "s22"),
                          ("CRS-rank (live)  CAGR", a["cagr"] * 100, "cagr"),
                          ("conviction-rank  22-26", 0.44, "s22")]:
        d = df[col] * (100 if col == "cagr" else 1)
        p = pct_rank(d, val)
        print(f"  {lab:26s} = {val:6.2f}  -> {p:5.1f}th percentile of random"
              f"{'   <-- adds real value' if p >= 90 else ('   <-- inside noise' if 5 <= p <= 95 else '   <-- WORSE than random')}")


if __name__ == "__main__":
    main()
