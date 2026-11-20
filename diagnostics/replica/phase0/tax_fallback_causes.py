"""Split the effective-tax-rate fallback rows (25.17%) by cause, fiscal year 2019 onward.

Population: primary-basis, original-version (version 0) quarters of data/fundamentals_q.parquet.
A row is a fallback row when tax_rate_fallback is true. Causes, checked in this order (the first that applies wins):
1. fewer_than_4_quarters: fewer than 4 same-basis quarters (this one and the 3 before it) were broadcast by this
   row's broadcast time, so no trailing-4Q rate can exist;
2. financial_tag_set: a financial company with the tax or PBT tag missing in any of the 4 quarters;
3. both_tags_missing, tax_tag_missing, pbt_tag_missing: the tag is missing in any of the 4 quarters;
4. pbt_nonpositive: trailing-4Q PBT <= 0, so tax / PBT is undefined;
5. other.

    python diagnostics/replica/phase0/tax_fallback_causes.py [data/fundamentals_q.parquet]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
p = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "fundamentals_q.parquet")
pr = p[p.is_primary].copy()
tot = pr[(pr.version == 0) & (pr.fiscal_year >= 2019)]
fb = tot[tot.tax_rate_fallback.astype(bool)].copy()
first = pr.groupby(["company", "qn"]).broadcast_ts.min()


def have(k):
    b = first.reindex(pd.MultiIndex.from_arrays([fb.company, fb.qn - k])).to_numpy()
    return pd.notna(b) & (b <= fb.broadcast_ts.to_numpy())


fb["nq"] = 1 + sum(have(k).astype(int) for k in (1, 2, 3))
vals = pr.sort_values("broadcast_ts").drop_duplicates(["company", "qn"], keep="first").set_index(["company", "qn"])


def miss(col):
    m = fb[col].isna().to_numpy().copy()
    for k in (1, 2, 3):
        m |= vals[col].reindex(pd.MultiIndex.from_arrays([fb.company, fb.qn - k])).isna().to_numpy()
    return m


mt, mp = miss("tax_expense"), miss("pbt")
fb["cause"] = np.select(
    [fb.nq.to_numpy() < 4, fb.is_financial.to_numpy() & (mt | mp), mt & mp, mt, mp, fb.ttm_pbt.to_numpy() <= 0],
    ["fewer_than_4_quarters", "financial_tag_set", "both_tags_missing", "tax_tag_missing", "pbt_tag_missing",
     "pbt_nonpositive"], "other")
out = {"population_rows_fy2019plus": int(len(tot)), "fallback_rows": int(len(fb)),
       "causes": fb.cause.value_counts().to_dict(),
       "causes_by_fiscal_year": pd.crosstab(fb.fiscal_year, fb.cause).to_dict("index"),
       "fallback_share_pct_by_fiscal_year": (100 * tot.groupby("fiscal_year").tax_rate_fallback.mean()).round(1).to_dict()}
dst = Path(__file__).with_name("tax_fallback_causes.json")
dst.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, indent=1, default=str))
