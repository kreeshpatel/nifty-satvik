"""DISSECT CRS-RANK — is its selection skill REAL (regime-robust) or an in-sample artifact?
And HOW does it work?

The Monte-Carlo null showed CRS sits at the 99-100th percentile of random selection. But CRS was CHOSEN
in-sample (0037/0094), so part of that may be selection bias — which sets the forward expectation
anywhere in 0.67 (no skill) .. 1.03 (full skill). This attacks that question IN-SAMPLE, two ways:

  1. PER-SUB-PERIOD NULL — is CRS at the top of the null in BOTH 2017-21 and 2022-26, or only one?
     Skill that holds across two very different regimes is far stronger evidence than skill in one.
  2. MECHANISM — what does CRS actually PICK vs random, bucketed by entry extension? And crucially,
     WITHIN the dead 5-10% band, is CRS's selected subset better than random's? (The pool test implied
     CRS's skill lives inside that band — this tests it directly.)

    python scripts/diag_crs_dissect.py [N_SIMS]
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

N_SIMS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
OUT = ROOT / "research" / "substrate" / "crs_dissect_sims.csv"
BINS = [-100, 0, 5, 10, 15, 100]
LAB = ["<0%", "0-5%", "5-10%", "10-15%", ">15%"]


def sub_sharpes(curve):
    e = curve.sort_index(); r = e.pct_change().dropna()
    def sh(a, b):
        rr = r[(r.index >= a) & (r.index < b)]
        return rr.mean() / rr.std() * np.sqrt(252) if len(rr) > 5 and rr.std() else np.nan
    return sh("2017-01-01", "2022-01-01"), sh("2022-01-01", "2027-01-01")


def ledger_df(led, smamap, didx):
    rows = []
    for r in led:
        t = r["tkr"]; j0 = didx[t].get(pd.Timestamp(r["entry_date"]))
        sm = smamap[t].get(j0)
        if sm is None or not sm > 0:
            continue
        rows.append(dict(ticker=t, R=float(r["R"]), ext=(float(r["entry"]) / sm - 1) * 100,
                         entry_date=pd.Timestamp(r["entry_date"])))
    df = pd.DataFrame(rows)
    df["b"] = pd.cut(df.ext, bins=BINS, labels=LAB)
    return df


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in P.items()}
    # per-ticker {fill_day -> signal-week SMA} so every filled trade can be bucketed by extension
    smamap = {t: {d: w[4] for w in s["entry_win"].values() for d in w[0]} for t, s in P.items()}
    keys = [(t, e0) for t, s in P.items() for e0 in s["entry_win"]]

    # ---- CRS (the live selector) ----
    ledC = []
    mC = R94.backtest(P, mem, ledger=ledC, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mC["sharpe"] - 1.034) < 0.005 and mC["trades"] == 168, "R1 baseline FAILED"
    c17, c22 = sub_sharpes(mC["curve"])
    dC = ledger_df(ledC, smamap, didx)

    # ---- random null: sub-period sharpes + pooled ledgers ----
    rows, rand_led = [], []
    for seed in range(N_SIMS):
        rng = np.random.default_rng(seed)
        conv = {k: float(v) for k, v in zip(keys, rng.random(len(keys)))}
        led = []
        m = R94.backtest(P, mem, ledger=led, start="2017-01-01", eq0=EQ0,
                         fill_order="conviction", conv_score=conv, **P2_EXIT)
        s17, s22 = sub_sharpes(m["curve"])
        rows.append(dict(seed=seed, s17_21=s17, s22_26=s22, sharpe=m["sharpe"]))
        rand_led.extend(led)
        if (seed + 1) % 10 == 0:
            print(f"  ...{seed+1}/{N_SIMS}", flush=True)
    d = pd.DataFrame(rows); d.to_csv(OUT, index=False)
    dR = ledger_df(rand_led, smamap, didx)

    # ================= 1. per-sub-period null =================
    print("\n=== 1. IS CRS SKILFUL IN BOTH REGIMES? (CRS vs the null, per sub-period) ===")
    for lab, val, col in [("2017-21", c17, "s17_21"), ("2022-26", c22, "s22_26")]:
        dist = d[col].dropna()
        pct = (dist < val).mean() * 100
        print(f"  {lab}:  CRS={val:5.2f}   null mean={dist.mean():5.2f} +-{dist.std():.2f}  "
              f"(max {dist.max():.2f})  -> CRS at {pct:5.1f}th percentile"
              f"{'   SKILFUL' if pct >= 90 else '   <-- NOT skilful here'}")

    # ================= 2. mechanism =================
    print("\n=== 2. WHAT DOES CRS PICK? (share of selected trades by entry-extension bucket) ===")
    print(f"  {'bucket':8s} {'CRS %':>7s} {'random %':>9s} {'tilt':>7s}")
    for b in LAB:
        pc = (dC.b == b).mean() * 100; pr = (dR.b == b).mean() * 100
        print(f"  {b:8s} {pc:6.1f}% {pr:8.1f}% {pc-pr:+6.1f}pp")

    print("\n=== 3. WITHIN each bucket, does CRS pick BETTER trades than random? (meanR) ===")
    print(f"  {'bucket':8s} {'CRS N':>6s} {'CRS meanR':>10s} {'rand N':>7s} {'rand meanR':>11s} {'edge':>7s}")
    for b in LAB:
        gc = dC[dC.b == b]; gr = dR[dR.b == b]
        if len(gc) < 3 or len(gr) < 3:
            print(f"  {b:8s} {len(gc):6d} {'--':>10s} {len(gr):7d} {'--':>11s} {'(thin)':>7s}")
            continue
        print(f"  {b:8s} {len(gc):6d} {gc.R.mean():10.3f} {len(gr):7d} {gr.R.mean():11.3f} "
              f"{gc.R.mean()-gr.R.mean():+7.3f}")
    print(f"\n  ALL      {len(dC):6d} {dC.R.mean():10.3f} {len(dR):7d} {dR.R.mean():11.3f} "
          f"{dC.R.mean()-dR.R.mean():+7.3f}   <-- CRS's per-trade selection edge")


if __name__ == "__main__":
    main()
