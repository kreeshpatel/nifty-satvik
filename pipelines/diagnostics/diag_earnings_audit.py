"""Step-2 AUDIT GATE for the 0120 earnings screen (STOP if it fails).

    python scripts/diag_earnings_audit.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table  # noqa: E402
from nq.data.delivery import apply_alias_map  # noqa: E402

def main() -> int:
    raw = pd.read_parquet(EARNINGS_RAW_PATH)
    ev = build_event_table(apply_alias_map(raw))
    print(f"raw records {len(raw)} | results-events after dedup {len(ev)} | symbols {ev['symbol'].nunique()}")
    # 2. announcement->event lag sanity
    lag = (ev["event_date"] - ev["ann_ts"].dt.normalize()).dt.days
    print(f"\nann->event lag (days): median {lag.median():.0f} | p10 {lag.quantile(.1):.0f} | "
          f"p90 {lag.quantile(.9):.0f} | share <=0d {(lag<=0).mean()*100:.1f}%")
    # 1. per-year coverage vs the substrate
    t = pd.read_parquet(ROOT/"research"/"substrate"/"context_windows.parquet")
    col = {c.lower(): c for c in t.columns}
    t["entry_date"] = pd.to_datetime(t[col["entry_date"]])
    t = t[t["entry_date"] >= "2019-01-01"]
    evs = {s: g["event_date"].to_numpy() for s, g in ev.groupby("symbol")}
    cov = []
    for _, r in t.iterrows():
        a = evs.get(r[col["ticker"]])
        if a is None:
            cov.append(False); continue
        y = r["entry_date"].year
        cov.append(bool(((a >= np.datetime64(f"{y}-01-01")) & (a <= np.datetime64(f"{y}-12-31"))).any()))
    t["cov"] = cov
    tab = t.groupby(t["entry_date"].dt.year)["cov"].agg(["count", "mean"])
    tab["mean"] = (tab["mean"]*100).round(1)
    print("\nper-year coverage (trade's symbol has >=1 results event that year):")
    print(tab.rename(columns={"count":"trades","mean":"coverage_%"}).to_string())
    rcov = t[t["cov"]][col["r"]].mean(); runc = t[~t["cov"]][col["r"]].mean() if (~t["cov"]).any() else np.nan
    print(f"meanR covered {rcov:+.3f} vs uncovered {runc:+.3f} | uncovered n={int((~t['cov']).sum())}")
    # delisted presence: event symbols whose last event is >1y before max
    ended = ev.groupby("symbol")["event_date"].max()
    print(f"symbols whose events END >1y before archive max (delisted-in-window presence): "
          f"{int((ended < ev['event_date'].max()-pd.Timedelta(days=365)).sum())}")
    # 3. spot checks
    print("\nspot-checks (raw):")
    for _, r in raw.sample(3, random_state=7).iterrows():
        print(f"  {r['symbol']}: ann {r['ann_ts']} -> event {r['event_date']} | {str(r['purpose'])[:70]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
