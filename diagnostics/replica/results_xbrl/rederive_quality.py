"""Blind re-derivation of results-XBRL quality stats from a written spec only.

Does not read or import the original quality pipeline. Run from repo root:
    python diagnostics/replica/results_xbrl/rederive_quality.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from nq.data.membership import load_membership  # membership loader only

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("rederive_quality.json")

df = pd.read_parquet(ROOT / "data" / "results_xbrl.parquet")
mem = load_membership()
assert mem, "membership missing/empty"

# ---------- symbol bridge: isin -> symbol of row with largest broadcast_ts
b = df[df["isin"].notna()].sort_values("broadcast_ts", kind="mergesort")
bridge = b.groupby("isin")["symbol"].last().to_dict()
df["bridged"] = df["isin"].map(bridge)


def members_on(d: date) -> set[str]:
    return {t for t, ivs in mem.items() if any(s <= d <= e for s, e in ivs)}


out: dict = {}

# ---------- 1. rows parsed
out["rows_parsed"] = {"rows": int(len(df)), "distinct_xbrl_url": int(df["xbrl_url"].nunique())}

# ---------- 2. completeness by year
cur = df[df["context_role"] == "current"].copy()
max_ts = df["broadcast_ts"].max()


def keys_for(sub: pd.DataFrame) -> set[tuple[str, pd.Timestamp]]:
    k = set(zip(sub["symbol"], sub["period_end"]))
    k |= set(zip(sub["bridged"].dropna(), sub.loc[sub["bridged"].notna(), "period_end"]))
    return k


cov_sets = {
    "overall": keys_for(cur),
    "standalone": keys_for(cur[cur["consolidated"] == False]),  # noqa: E712
    "consolidated": keys_for(cur[cur["consolidated"] == True]),  # noqa: E712
}
comp = {}
for Y in range(2019, 2027):
    U = members_on(date(Y, 6, 30))
    qs = [pd.Timestamp(Y, m, d) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))]
    qs = [q for q in qs if q + timedelta(days=60) <= max_ts]
    pairs = [(t, q) for t in U for q in qs]
    row = {"n_tickers": len(U), "n_quarters": len(qs), "pairs": len(pairs)}
    for name, ks in cov_sets.items():
        c = sum(1 for p in pairs if p in ks)
        row[name] = round(100 * c / len(pairs), 1) if pairs else None
    comp[str(Y)] = row
out["completeness_by_year"] = comp

# ---------- 3. EPS sanity
orig = df[df["filing_seq"] == 0]
q = orig[(orig["context_role"] == "current") & (orig["period_type"] == "Q") & orig["eps_basic"].notna()].copy()
q["fy"] = [pe.year if pe.month <= 3 else pe.year + 1 for pe in q["period_end"]]
g = q.groupby(["symbol", "consolidated", "fy"]).agg(
    n=("eps_basic", "size"), nd=("period_end", "nunique"), s4=("eps_basic", "sum")
).reset_index()
g = g[(g["n"] == 4) & (g["nd"] == 4)]
f = orig[(orig["period_type"] == "FY") & (orig["period_end"].dt.month == 3) & orig["eps_basic"].notna()].copy()
f["fy"] = f["period_end"].dt.year
f = f.groupby(["symbol", "consolidated", "fy"], sort=False)["eps_basic"].first().rename("fy_eps").reset_index()
j = g.merge(f, on=["symbol", "consolidated", "fy"], how="inner")
j["gap"] = (j["s4"] - j["fy_eps"]).abs() / j["fy_eps"].abs().clip(lower=0.01)
out["eps_sanity"] = {
    "pairs": int(len(j)),
    "median_gap_pct": round(float(j["gap"].median() * 100), 2),
    "share_gap_gt_5pct": round(float((j["gap"] > 0.05).mean() * 100), 1),
}

# ---------- 4. late rate by membership
c4 = cur.drop_duplicates(subset=["xbrl_url", "context_id"]).copy()
c4["late"] = c4["period_flag"].fillna("").str.contains("lag_over_120d", regex=False)
memo: dict[date, set[str]] = {}
is_mem = []
for sym, br, ts in zip(c4["symbol"], c4["bridged"], c4["broadcast_ts"]):
    d = ts.date()
    if d not in memo:
        memo[d] = members_on(d)
    s = memo[d]
    is_mem.append(sym in s or (isinstance(br, str) and br in s))
c4["member"] = is_mem
lm = {}
for flag, name in ((True, "members"), (False, "non_members")):
    s = c4[c4["member"] == flag]
    lm[name] = {"n": int(len(s)), "n_late": int(s["late"].sum()), "late_pct": round(100 * s["late"].mean(), 2)}
out["late_member_rate"] = lm

OUT.write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
