"""Step-1 gate for the conditionally-signed 0119 swap-tiebreak trial (MEASUREMENT, 0 trials;
screen-ledger row #8, running count 8).

Mechanically bounds what the dlv_med21 tiebreak could have been worth on the TRAIN years
(2019-01..2024-06), before any pre-reg:
  1. ACTIVATION - weeks where same-week signals competed for the last funded slot (funded > 0 and
     >= 1 candidate unfunded), and in what fraction the delivery ordering DISAGREES with the
     incumbent pick (swap triggered).
  2. CLAIRVOYANT BOUND - for exactly those marginal pairs (last-funded vs best-CRS-unfunded, both
     measured with the SAME substrate uncapped R so exits are apples-to-apples), the realized
     R(swapped-in) - R(swapped-out), summed, annualized.
  3. THE GATE (pre-committed by the owner): bound < +-10R/yr path-noise floor (0109) => the shape is
     underpowered BY CONSTRUCTION -> no trial, record addendum, STOP.

    python scripts/diag_tiebreak_bound_0119.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.delivery import DELIVERY_RAW_PATH, apply_alias_map, derive_delivery_features  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

SUB = ROOT / "research" / "substrate" / "trades.parquet"
CAPPED = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"


def main() -> int:
    print("SCREEN LEDGER: row #8 (running count 8).")
    oh = load_ohlcv_cache(OHLCV_CACHE)
    raw = apply_alias_map(pd.read_parquet(DELIVERY_RAW_PATH))
    raw["date"] = pd.to_datetime(raw["date"]).astype("datetime64[ns]")
    feats = derive_delivery_features(raw)[["symbol", "date", "dlv_med21"]]
    fa = {s: (g["date"].to_numpy(), g["dlv_med21"].to_numpy()) for s, g in feats.groupby("symbol")}

    sub = pd.read_parquet(SUB)
    scol = {c.lower(): c for c in sub.columns}
    sub["entry_date"] = pd.to_datetime(sub[scol["entry_date"]])
    sub = sub[(sub["entry_date"] >= TRAIN_LO) & (sub["entry_date"] <= TRAIN_HI)].copy()
    iso = sub["entry_date"].dt.isocalendar()
    sub["iw"] = iso.year.astype(str) + "-" + iso.week.astype(str).str.zfill(2)
    sub["sig_fri"] = (sub["entry_date"] - pd.to_timedelta(sub["entry_date"].dt.weekday + 3, unit="D")).astype("datetime64[ns]")
    dlv = []
    for _, r in sub.iterrows():
        a = fa.get(r[scol["ticker"]])
        if a is None:
            dlv.append(np.nan); continue
        i = np.searchsorted(a[0], np.datetime64(r["sig_fri"]), "right") - 1
        dlv.append(float(a[1][i]) if i >= 0 and (r["sig_fri"] - pd.Timestamp(a[0][i])).days <= 10 else np.nan)
    sub["dlv"] = dlv

    cap = pd.read_csv(CAPPED); cap["entry_date"] = pd.to_datetime(cap["entry_date"])
    cap = cap[(cap["entry_date"] >= TRAIN_LO) & (cap["entry_date"] <= TRAIN_HI)]
    iso = cap["entry_date"].dt.isocalendar()
    cap["iw"] = iso.year.astype(str) + "-" + iso.week.astype(str).str.zfill(2)
    funded = set(zip(cap["tkr"], cap["iw"]))
    sub["funded"] = [(t, w) in funded for t, w in zip(sub[scol["ticker"]], sub["iw"])]

    n_weeks = comp_weeks = swap_weeks = 0
    deltas = []
    for iw, g in sub.groupby("iw"):
        n_weeks += 1
        f = g[g["funded"]]; u = g[~g["funded"]]
        if len(f) == 0 or len(u) == 0:
            continue
        comp_weeks += 1
        last_f = f.loc[f[scol["rank_crs"]].idxmin()]          # lowest-CRS funded = the marginal slot
        best_u = u.loc[u[scol["rank_crs"]].idxmax()]          # highest-CRS unfunded = the contender
        if not (np.isfinite(last_f["dlv"]) and np.isfinite(best_u["dlv"])):
            continue
        if best_u["dlv"] > last_f["dlv"]:                     # the tiebreak would SWAP
            swap_weeks += 1
            deltas.append(float(best_u[scol["r"]]) - float(last_f[scol["r"]]))
    yrs = 5.5
    tot = float(np.sum(deltas)) if deltas else 0.0
    print(f"\ntrain weeks {n_weeks} | competitive (funded>0 & unfunded>0) {comp_weeks} "
          f"| tiebreak SWAPS {swap_weeks} ({100*swap_weeks/max(comp_weeks,1):.0f}% of competitive)")
    if deltas:
        d = np.array(deltas)
        print(f"swap R-delta: mean {d.mean():+.3f} | median {np.median(d):+.3f} | sum {tot:+.1f}R over {yrs}y")
    print(f"\nCLAIRVOYANT BOUND: {tot/yrs:+.2f} R/yr   (gate: |bound| must clear the +-10 R/yr noise floor)")
    print("GATE:", "CLEARS -> proceed to Step 2 (trial #139)" if tot / yrs >= 10.0
          else "BELOW THE FLOOR -> underpowered by construction; NO TRIAL; record addendum and STOP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
