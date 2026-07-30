"""0122 audit gate + tail screen — run ONCE as pre-registered. MEASUREMENT: 0 trials.
Ledger row #11 (running count 11; sealed opens 1).

    python scripts/diag_ratings_screen_0122.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.delivery import apply_alias_map  # noqa: E402

RAW = ROOT/"data"/"_ratings_raw.parquet"
CTX = ROOT/"research"/"substrate"/"context_windows.parquet"
ERA_LO, TRAIN_HI = "2023-02-01", "2024-06-30"
LOOKBACK = 180  # cd, frozen
RNG = np.random.default_rng(20260728)

def main() -> int:
    print("LEDGER: row #11 (running count 11; sealed opens 1).")
    r = pd.read_parquet(RAW)
    n0 = len(r)
    r = r.drop_duplicates(subset=[c for c in r.columns if c != "fetched_win"])   # API windows overlap
    print(f"AUDIT: raw rows {n0} -> deduped {len(r)} (window-overlap guard)")
    r = r[r["Symbol"].notna() & (r["Symbol"] != "NOTLISTED")].copy()
    r["symbol"] = r["Symbol"].astype(str).str.strip()
    r = apply_alias_map(r.rename(columns={"symbol": "symbol"}))
    r["bc"] = pd.to_datetime(r["BroadcastDateTime"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    neg = r[(r["RatingAction"].fillna("").str.contains("owngrade")) |
            (r["Outlook"].fillna("").str.contains("egative"))].dropna(subset=["bc"])
    print(f"AUDIT: filings {len(r)} | equity-symboled | NEGATIVE signals {len(neg)} "
          f"({neg['symbol'].nunique()} symbols) | span {neg['bc'].min().date()}..{neg['bc'].max().date()}")
    per_yr = neg.groupby(neg["bc"].dt.year).size()
    print("  negative signals per year:", per_yr.to_dict())
    t = pd.read_parquet(CTX)
    col = {c.lower(): c for c in t.columns}
    t["entry_date"] = pd.to_datetime(t[col["entry_date"]])
    era = t[(t["entry_date"] >= ERA_LO) & (t["entry_date"] <= TRAIN_HI)].copy()
    era["sig_fri"] = era["entry_date"] - pd.to_timedelta(era["entry_date"].dt.weekday + 3, unit="D")
    rr = col["r"]
    uni_syms = set(era[col["ticker"]].unique())
    cov = len(uni_syms & set(r["symbol"].unique())) / len(uni_syms) * 100
    print(f"  era-universe symbols with ANY rating filing: {cov:.0f}%  (coverage context)")
    ns = {s: g["bc"].to_numpy() for s, g in neg.groupby("symbol")}
    def preceded(row):
        a = ns.get(row[col["ticker"]])
        if a is None: return False
        sf = np.datetime64(row["sig_fri"])
        return bool(((a <= sf) & (a >= np.datetime64(row["sig_fri"] - pd.Timedelta(days=LOOKBACK)))).any())
    era["neg_pre"] = era.apply(preceded, axis=1)
    dis = era[era[rr] <= -1.5]; ctl = era[era[rr] > -1.5]
    era["ext_band"] = pd.cut(era[col["ext_vs_sma"]], [-np.inf, 10, 20, np.inf], labels=["e0","e1","e2"])
    era["crs_t"] = pd.qcut(era[col["rank_crs"]].rank(method="first"), 3, labels=["c0","c1","c2"])
    print(f"\nSCREEN universe: era trades {len(era)} | disasters {len(dis)} | controls {len(ctl)}")
    p_d = dis["neg_pre"].mean(); p_c = ctl["neg_pre"].mean()
    nd, nc = int(dis["neg_pre"].sum()), int(ctl["neg_pre"].sum())
    print(f"preceded-by-negative-rating (180cd, PIT): disasters {nd}/{len(dis)} = {p_d*100:.1f}% | "
          f"controls {nc}/{len(ctl)} = {p_c*100:.1f}%")
    # cell-matched contrast + bootstrap CI on the rate difference
    diffs = []
    a = dis["neg_pre"].to_numpy(float); b = ctl["neg_pre"].to_numpy(float)
    for _ in range(3000):
        diffs.append(RNG.choice(a, len(a)).mean() - RNG.choice(b, len(b)).mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print(f"rate difference {p_d-p_c:+.3f} [{lo:+.3f},{hi:+.3f}]")
    ok = (p_d - p_c) > 0 and lo > 0 and p_d >= 0.15
    print(f"\nBAR: disaster rate > control rate, CI excluding 0, AND preceded fraction >= 15%.")
    print("VERDICT:", "PASS -> rare-fire-veto question goes to the owner (0109-class judgment)"
          if ok else "KILL -> census #4 closes; the mechanism-mismatch flag was right"
          if p_d < 0.15 else "KILL -> no separation from controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
