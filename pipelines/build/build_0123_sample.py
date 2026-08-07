"""0123 — Stratified matched sample for the vision-grader screen (train years only).

3-way cohorts: false_touch vs noise_stop vs strong-winner (R>=2), MATCHED within
ext-band x CRS-tercile cells (take min-across-cohorts per cell so the joint ext x CRS
distribution is identical across cohorts by construction — this is how we control the
r=+0.48 ext<->candle-size confound). Deterministic (seeded). Sealed 2024-07+ never touched.

Writes: research/substrate/sample_0123.csv (manifest) + prints the power-check.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "research" / "substrate" / "context_windows.parquet"
OUT = ROOT / "research" / "substrate" / "sample_0123.csv"
SEED = 20260730
CAP_PER_CELL = 40          # cap per cohort per cell (before min-matching); raised from 20
                           # per the pre-reg power-check contingency (thin per-year/ADV legs at
                           # 136/cohort). Availability-bound cells are unaffected; matched design intact.

# frozen ext bands (train q33/q67 from the pre-reg) and CRS terciles (computed on train)
EXT_Q = (13.99, 27.9)


def band(v, q):
    return 0 if v <= q[0] else (1 if v <= q[1] else 2)


def main():
    df = pd.read_parquet(PARQUET)
    tr = df[df["entry_date"] <= "2024-06-30"].reset_index(drop=True).copy()

    # disjoint cohorts: stop-out labels take priority; SW = clean strong winner
    tr["ft"] = tr["false_touch"].astype(bool)
    tr["ns"] = tr["noise_stop"].astype(bool) & ~tr["ft"]
    tr["sw"] = (tr["R"] >= 2.0) & ~tr["ft"] & ~tr["ns"]

    crs_q = tuple(tr["rank_crs"].quantile([0.33, 0.67]).values)
    tr["ext_band"] = tr["ext_vs_sma"].apply(lambda v: band(v, EXT_Q))
    tr["crs_tercile"] = tr["rank_crs"].apply(lambda v: band(v, crs_q))
    tr["cell"] = tr["ext_band"] * 3 + tr["crs_tercile"]

    rng = np.random.default_rng(SEED)
    picks = []
    print(f"train n={len(tr)}  FT={tr['ft'].sum()} NS={tr['ns'].sum()} SW={tr['sw'].sum()}  crs_q={tuple(round(x,3) for x in crs_q)}")
    print("cell (ext,crs): FT/NS/SW available -> matched n_each")
    for cell in range(9):
        sub = tr[tr["cell"] == cell]
        avail = {c: sub[sub[c]].index.to_numpy() for c in ("ft", "ns", "sw")}
        n_each = min(min(len(v) for v in avail.values()), CAP_PER_CELL)
        eb, ct = divmod(cell, 3)
        print(f"  ({eb},{ct}): {len(avail['ft'])}/{len(avail['ns'])}/{len(avail['sw'])} -> {n_each}")
        if n_each == 0:
            continue
        for coh in ("ft", "ns", "sw"):
            chosen = rng.choice(avail[coh], size=n_each, replace=False)
            for i in chosen:
                picks.append((i, coh, cell))

    rows = []
    cohmap = {"ft": "false_touch", "ns": "noise_stop", "sw": "strong_winner"}
    for i, coh, cell in picks:
        r = tr.loc[i]
        eb, ct = divmod(cell, 3)
        cid = hashlib.sha1(f"{r['ticker']}|{pd.Timestamp(r['entry_date']).date()}".encode()).hexdigest()[:12]
        rows.append(dict(id=cid, ticker=r["ticker"], entry_date=pd.Timestamp(r["entry_date"]).date(),
                         cohort=cohmap[coh], ext_band=eb, crs_tercile=ct,
                         false_touch=int(r["false_touch"]), noise_stop=int(r["noise_stop"]),
                         exit_too_early=int(r["exit_too_early"]), R=round(float(r["R"]), 3),
                         opp_quality_R=round(float(r["opp_quality_R"]), 3),
                         ext_vs_sma=round(float(r["ext_vs_sma"]), 2),
                         rank_crs=round(float(r["rank_crs"]), 4)))
    out = pd.DataFrame(rows).drop_duplicates("id").reset_index(drop=True)
    out.to_csv(OUT, index=False)
    per = out["cohort"].value_counts().to_dict()
    print(f"\nSAMPLE LOCKED: n={len(out)}  per-cohort={per}")
    print(f"unique names={out['ticker'].nunique()}  cells populated={out.groupby(['ext_band','crs_tercile']).ngroups}")
    print(f"written -> {OUT}")
    # crude MDE: within-cell tercile-spread SE ~ sd(R)/sqrt(n_per_cohort). 0118 ref effect +0.363R.
    sd = out["R"].std()
    n_min = min(per.values())
    mde = 2.8 * sd / np.sqrt(n_min)   # ~2.8*SE two-sided 95% detectable at this n
    print(f"POWER: sd(R)={sd:.2f}  min-cohort n={n_min}  crude MDE(cohort-mean R)~{mde:.2f}R (ref 0118 effect 0.363R)")


if __name__ == "__main__":
    main()
