"""Blind replica: adjusted core EPS for sample keys. Built from spec only (no nq/ imports)."""
import pandas as pd, numpy as np
from pathlib import Path
ROOT = Path(r"C:\nifty-satvik")
OUT = ROOT / "diagnostics/replica/phase0"
TAX = 0.2517
RATIOS = [1.5, 2, 2.5, 3, 4, 5, 6, 10, 20]

d = pd.read_parquet(ROOT / "data/results_xbrl.parquet")
keys = pd.read_csv(OUT / "eps_sample_keys.csv", parse_dates=["fiscal_quarter_end"])
d["company"] = np.where(d["isin"].fillna("").str.strip() != "", d["isin"], d["symbol"])
d = d[d["company"].isin(keys["company"])].copy()
d = d.dropna(subset=["period_start", "period_end", "consolidated"])
# period length in quarters: months between start and end+1day, /3, rounded
months = ((d.period_end + pd.Timedelta(days=1)).dt.year - d.period_start.dt.year) * 12 + \
         ((d.period_end + pd.Timedelta(days=1)).dt.month - d.period_start.dt.month)
d["nq"] = (months / 3).round().astype(int)
d["exact"] = (months % 3 == 0)
d = d[d.exact & d.nq.between(1, 4)]
d = d.sort_values(["broadcast_ts", "filing_seq"], kind="mergesort")

def shares_of(r):
    pu, fv = r.paid_up_equity, r.face_value
    if pd.notna(pu) and pd.notna(fv) and pu > 0 and fv > 0:
        return pu / fv
    if pd.notna(r.eps_basic) and abs(r.eps_basic) > 0.01 and pd.notna(r.pat):
        return r.pat / r.eps_basic
    return np.nan

def is_split(r):
    if not (np.isfinite(r) and r > 0): return False
    x = r if r >= 1 else 1 / r
    return any(abs(x - k) / k <= 0.03 for k in RATIOS)

rows = []
for comp, g in d.groupby("company"):
    Q = set(g.period_end); C = set(g[g.consolidated].period_end)
    basis = "consolidated" if len(C) / len(Q) >= 0.80 else "standalone"
    b = g[g.consolidated == (basis == "consolidated")]
    quarters = sorted(set(b.period_end))
    # split factor from paid-up count of each quarter's original filing
    factor, last_cnt, fac = {}, None, 1.0
    for E in quarters:
        orig = b[b.period_end == E].iloc[0]  # earliest broadcast
        pu, fv = orig.paid_up_equity, orig.face_value
        cnt = pu / fv if (pd.notna(pu) and pd.notna(fv) and pu > 0 and fv > 0) else None
        if cnt is not None:
            if last_cnt is not None and is_split(cnt / last_cnt):
                fac *= cnt / last_cnt
            last_cnt = cnt
        factor[E] = fac
    for E in keys[keys.company == comp].fiscal_quarter_end:
        rec = dict(company=comp, fiscal_quarter_end=E.date(), basis=basis, source="")
        q3 = b[(b.period_end == E) & (b.nq == 1)]
        if len(q3):
            r = q3.iloc[0]
            pat, exc, sh = r.pat, (0.0 if pd.isna(r.exceptional_items) else r.exceptional_items), shares_of(r)
            rec["source"] = "direct"
        else:
            later = b[(b.period_end == E) & (b.nq > 1)]
            pat = exc = sh = np.nan
            if len(later):
                L = later.iloc[0]
                prevE = E - pd.offsets.QuarterEnd(1)
                earlier = b[(b.period_start == L.period_start) & (b.period_end == prevE) & (b.broadcast_ts <= L.broadcast_ts)]
                if len(earlier):
                    P = earlier.iloc[-1]
                    pat = L.pat - P.pat
                    e1 = 0.0 if pd.isna(L.exceptional_items) else L.exceptional_items
                    e0 = 0.0 if pd.isna(P.exceptional_items) else P.exceptional_items
                    exc = e1 - e0
                    pu, fv = L.paid_up_equity, L.face_value
                    sh = pu / fv if (pd.notna(pu) and pd.notna(fv) and pu > 0 and fv > 0) else np.nan
                    rec["source"] = "derived"
        core = pat - exc * (1 - TAX)
        f = factor.get(E, np.nan)
        adj = sh / f if pd.notna(sh) else np.nan
        rec.update(pat=pat, core_pat=core, shares=sh, share_factor=f,
                   adj_core_eps=core / adj if pd.notna(adj) and adj else np.nan)
        rows.append(rec)
out = pd.DataFrame(rows)
missing = keys[~keys.company.isin(out.company)]
out.to_csv(OUT / "eps_replica.csv", index=False)
print(out.to_string()); print("missing companies:", missing.to_string())
