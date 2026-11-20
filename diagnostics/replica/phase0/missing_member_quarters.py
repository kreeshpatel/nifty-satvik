"""PIT Nifty 500 member-quarters with no quarterly result after the basis fallback, by calendar year.

- Member-quarter: a symbol that was a PIT Nifty 500 member (nq.data.membership) on the quarter-end date. Quarter
  ends run from 2018-03-31 to 2026-06-30, the last quarter whose filing deadline has passed for the whole panel.
- Present: data/fundamentals_q.parquet has a row for that company and period_end on EITHER basis (consolidated or
  standalone) with PAT filed or derived. That is the basis fallback.
- Missing: no such row. These are split into
  - symbol_never_mapped: the symbol has no results filing at all, so there is no company key;
  - company_quarter_absent: the company files, but not this quarter.
No re-fetch.

    python diagnostics/replica/phase0/missing_member_quarters.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from nq.data.membership import load_membership  # noqa: E402

q = pd.read_parquet(ROOT / "data" / "fundamentals_q.parquet",
                    columns=["company", "symbol", "period_end", "pat", "basis"])
sym2co = q.groupby("symbol")["company"].agg(lambda s: s.mode().iat[0]).to_dict()
have = set(map(tuple, q.loc[q["pat"].notna(), ["company", "period_end"]].drop_duplicates().to_numpy()))
ends = pd.date_range("2018-03-31", "2026-06-30", freq="QE")
mem = load_membership() or {}
rows = []
for s, iv in mem.items():
    for qe in ends:
        if any(pd.Timestamp(a) <= qe <= pd.Timestamp(b) for a, b in iv):
            co = sym2co.get(s)
            st = "present" if co and (co, qe) in have else ("symbol_never_mapped" if not co else "company_quarter_absent")
            rows.append((s, qe, st))
t = pd.DataFrame(rows, columns=["symbol", "quarter_end", "status"])
tab = pd.crosstab(t["quarter_end"].dt.year, t["status"])
tab["member_quarters"] = tab.sum(axis=1)
tab["missing"] = tab.get("symbol_never_mapped", 0) + tab.get("company_quarter_absent", 0)
tab["missing_pct"] = (100 * tab["missing"] / tab["member_quarters"]).round(2)
out = {"by_year": tab.to_dict("index"), "total": {k: int(v) for k, v in tab.drop(columns="missing_pct").sum().items()},
       "never_mapped_symbols": sorted(t.loc[t.status == "symbol_never_mapped", "symbol"].unique().tolist())}
Path(__file__).with_name("missing_member_quarters.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(tab.to_string())
print("never-mapped symbols:", out["never_mapped_symbols"][:30], len(out["never_mapped_symbols"]))
