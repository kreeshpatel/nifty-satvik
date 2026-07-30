"""Step-0 DISASTER CENSUS (final campaign round; MEASUREMENT, 0 trials; touches outcomes only as a
COUNT — no features, no labels joined).

FROZEN DEFINITION (fixed here, before counting): a DISASTER is a substrate trade with realized
R <= -1.5 — a loss materially beyond the intended -1R stop geometry (the outcome signature of
gap-throughs and circuit-locked exits on a stop-geometry book). Train window 2019-01-01..2024-06-30
governs the gate; full-span reported for context.

GATE (owner, pre-committed): fewer than ~10 train events -> census #4 (credit ratings) closes WITHOUT
acquisition ("power precondition failed"); the same precondition is then applied on paper to census
#5/#6/#7.

    python scripts/diag_disaster_census.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

THRESH = -1.5   # FROZEN

def main() -> int:
    t = pd.read_parquet(ROOT/"research"/"substrate"/"trades.parquet")
    col = {c.lower(): c for c in t.columns}
    t["entry_date"] = pd.to_datetime(t[col["entry_date"]])
    rr = col["r"]
    full = t[t[rr] <= THRESH]
    tr = full[(full["entry_date"] >= "2019-01-01") & (full["entry_date"] <= "2024-06-30")]
    print(f"FROZEN definition: R <= {THRESH}")
    print(f"full-span disasters: {len(full)} / {len(t)} trades ({len(full)/len(t)*100:.1f}%) | "
          f"aggregate R {full[rr].sum():+.1f}")
    print(f"TRAIN disasters (2019-01..2024-06): {len(tr)} | aggregate R {tr[rr].sum():+.1f} | "
          f"mean {tr[rr].mean():+.2f} | worst {tr[rr].min():+.2f}")
    print("\nper-year (train):")
    print(tr.groupby(tr["entry_date"].dt.year)[rr].agg(["count", "sum"]).round(1).to_string())
    print("\nworst 15 (names/dates):")
    w = tr.nsmallest(15, rr)
    for _, r in w.iterrows():
        print(f"  {r[col['ticker']]:<12} {r['entry_date'].date()} -> {pd.to_datetime(r[col['exit_date']]).date()} "
              f"R {r[rr]:+.2f} reason {r[col['reason']]}")
    n = len(tr)
    print(f"\nGATE (<~10 train events => #4 closes without acquisition): {n} events -> "
          f"{'PASSES the power precondition' if n >= 10 else 'FAILS — census #4 closes'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
