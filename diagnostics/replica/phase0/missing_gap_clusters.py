"""Where do the PIT Nifty 500 member-quarters still missing after the basis fallback cluster? (measurement, no fetch)

Member-quarter, present and missing are defined exactly as in missing_member_quarters.py (same file, same rule).
Each member-quarter is then bucketed four ways and the missing rate reported per bucket:
- size: tercile of adv60_cr (data/risk_features.parquet) among members on the last Friday on or before the quarter end
  (T1 = least liquid). No Friday value -> "no_value".
- financial: the company's is_financial flag in data/fundamentals_q.parquet (any row True). Never-mapped symbols ->
  "unknown".
- filer speed: the company's median lag_days over its present quarters: <=45, 46-60, >60 days; "unknown" if none.
- position: where the quarter sits against the company's own filed history: before its first filed quarter, after its
  last, or an interior gap. Never-mapped -> "never_mapped".
Writes missing_gap_clusters.json and missing_member_quarters_list.csv (symbol, quarter_end, status; no raw data).

    python diagnostics/replica/phase0/missing_gap_clusters.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.membership import load_membership  # noqa: E402

q = pd.read_parquet(ROOT / "data" / "fundamentals_q.parquet",
                    columns=["company", "symbol", "period_end", "pat", "lag_days", "is_financial"])
sym2co = q.groupby("symbol")["company"].agg(lambda s: s.mode().iat[0]).to_dict()
pres = q.loc[q["pat"].notna()]
have = set(map(tuple, pres[["company", "period_end"]].drop_duplicates().to_numpy()))
first, last = pres.groupby("company")["period_end"].min(), pres.groupby("company")["period_end"].max()
fin = q.groupby("company")["is_financial"].any()
lag = pres.drop_duplicates(["company", "period_end"]).groupby("company")["lag_days"].median()
ends = pd.date_range("2018-03-31", "2026-06-30", freq="QE")
mem = load_membership() or {}
rows = []
for s, iv in mem.items():
    for qe in ends:
        if any(pd.Timestamp(a) <= qe <= pd.Timestamp(b) for a, b in iv):
            co = sym2co.get(s)
            st = "present" if co and (co, qe) in have else ("symbol_never_mapped" if not co else "company_quarter_absent")
            rows.append((s, co, qe, st))
t = pd.DataFrame(rows, columns=["symbol", "company", "quarter_end", "status"])
t["missing"] = t["status"] != "present"
assert int(t["missing"].sum()) == 1145, f"member-quarter list does not reproduce the close-out total: {t['missing'].sum()}"

rf = pd.read_parquet(ROOT / "data" / "risk_features.parquet", columns=["date", "symbol", "adv60_cr"])
rf["tercile"] = rf.groupby("date")["adv60_cr"].transform(lambda x: pd.qcut(x.rank(method="first"), 3, labels=["T1", "T2", "T3"]))
fr = pd.DatetimeIndex(sorted(rf["date"].unique()))
t["friday"] = fr[fr.searchsorted(t["quarter_end"], side="right") - 1]
t = t.merge(rf[["date", "symbol", "tercile"]].rename(columns={"date": "friday"}), on=["friday", "symbol"], how="left")
t["size"] = t["tercile"].astype(object).fillna("no_value")
t["financial"] = t["company"].map(fin).map({True: "financial", False: "non_financial"}).fillna("unknown")
t["filer_speed"] = pd.cut(t["company"].map(lag), [-1e9, 45, 60, 1e9], labels=["<=45d", "46-60d", ">60d"]).astype(object).fillna("unknown")


def pos(r):
    if r.company is None or r.company not in first.index:
        return "never_mapped"
    return "before_first_filed" if r.quarter_end < first[r.company] else (
        "after_last_filed" if r.quarter_end > last[r.company] else "interior_gap")


t["position"] = t.apply(pos, axis=1)
out = {"total_member_quarters": int(len(t)), "missing": int(t["missing"].sum()), "by": {}}
for col in ("size", "financial", "filer_speed", "position"):
    g = t.groupby(col)["missing"].agg(["size", "sum"])
    g["missing_pct"] = (100 * g["sum"] / g["size"]).round(2)
    out["by"][col] = {k: {"member_quarters": int(v["size"]), "missing": int(v["sum"]), "missing_pct": float(v["missing_pct"])}
                      for k, v in g.iterrows()}
m = t[t["missing"]]
out["missing_position_by_year"] = pd.crosstab(m["quarter_end"].dt.year, m["position"]).to_dict(orient="index")
out["top_companies_by_missing"] = m.groupby("symbol").size().sort_values(ascending=False).head(15).to_dict()
(HERE / "missing_gap_clusters.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
m[["symbol", "company", "quarter_end", "status", "size", "financial", "filer_speed", "position"]].to_csv(
    HERE / "missing_member_quarters_list.csv", index=False, date_format="%Y-%m-%d")
print(json.dumps(out, indent=1, default=str))
