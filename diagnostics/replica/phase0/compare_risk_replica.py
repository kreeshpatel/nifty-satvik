"""Difference the blind replica of the L5 risk features (C) and the 60/40 week (D) against the original.

Flag rule: a pair differs if exactly one side is NaN, or if |a - b| / max(|a|, |b|) > 5% where max(|a|, |b|) > 1e-9.
Integer-coded columns (stages, counts, flags, the label) must match exactly.

    python diagnostics/replica/phase0/compare_risk_replica.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EXACT = {"lo_hits63", "lo_hits252", "up_hits63", "up_hits252", "gsm_stage", "asm_stage", "asm_days_in_stage",
         "n_down5_252", "ttm_core_pat_pos", "late_filer", "label_crash", "pledge_declared_none", "last_lag_days"}


def diff(a, b, exact):
    if pd.isna(a) and pd.isna(b):
        return None
    if pd.isna(a) or pd.isna(b):
        return "nan-mismatch"
    a, b = float(a), float(b)
    if exact:
        return None if a == b else "exact-mismatch"
    den = max(abs(a), abs(b))
    return None if den <= 1e-9 or abs(a - b) / den <= 0.05 else f"rel {abs(a - b) / den:.3f}"


o = pd.read_csv(HERE / "risk_original.csv", parse_dates=["date"])
r = pd.read_csv(HERE / "risk_replica.csv", parse_dates=["date"])
cols = [c for c in r.columns if c not in ("symbol", "date") and c in o.columns]
m = o.merge(r, on=["symbol", "date"], suffixes=("_o", "_r"))
rows = []
for _, x in m.iterrows():
    for c in cols:
        d = diff(x[f"{c}_o"], x[f"{c}_r"], c in EXACT)
        rows.append({"symbol": x["symbol"], "date": str(x["date"].date()), "col": c,
                     "original": x[f"{c}_o"], "replica": x[f"{c}_r"], "flag": d})
t = pd.DataFrame(rows)
flagged = t[t["flag"].notna()]
fam = {"price": ["rv63", "rv126", "dvol126", "beta126", "dbeta126", "mdd252", "n_down5_252", "adv20_cr", "adv60_cr"],
       "bands": ["lo_hits63", "lo_hits252", "up_hits63", "up_hits252", "band_pct", "gsm_stage"],
       "asm": ["asm_stage", "asm_days_in_stage"], "pledge": ["pledge_pct", "pledge_chg_1q", "pledge_declared_none"],
       "fundamentals": ["de_ratio", "int_cover", "ttm_core_pat_pos", "ttm_core_pat_chg4", "last_lag_days", "late_filer"],
       "label": ["label_crash"]}
by_fam = {f: {"pairs": int(t["col"].isin(c).sum()), "flagged": int(flagged["col"].isin(c).sum()),
              "both_non_nan": int((t["col"].isin(c) & t["original"].notna() & t["replica"].notna()).sum())}
          for f, c in fam.items()}

od = json.loads((HERE / "benchmark_week_original.json").read_text(encoding="utf-8"))
rd = json.loads((HERE / "benchmark_week_replica.json").read_text(encoding="utf-8"))
d_rows = {k: {"original": od.get(k), "replica": rd.get(k),
              "flag": (None if od.get(k) == rd.get(k) else "mismatch") if isinstance(od.get(k), str)
              else diff(od.get(k), rd.get(k), False)}
          for k in ("nav_index", "nav_index_date", "nav_arbitrage", "nav_arbitrage_date", "pre_tax_nav",
                    "after_tax_nav", "index_weight", "status")}
out = {"keys": int(len(m)), "pairs": int(len(t)), "flagged": int(len(flagged)), "by_family": by_fam,
       "flagged_rows": flagged.astype(str).to_dict("records"), "benchmark_week": d_rows}
(HERE / "risk_replica_compare.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, indent=1, default=str))
