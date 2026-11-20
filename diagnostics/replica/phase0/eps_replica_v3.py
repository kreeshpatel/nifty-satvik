"""Blind replica (spec-only) of adjusted core EPS, v3. Does not import nq/."""
import numpy as np
import pandas as pd

ROOT = "C:/nifty-satvik"
d = pd.read_parquet(f"{ROOT}/data/results_xbrl.parquet")
keys = pd.read_csv(f"{ROOT}/diagnostics/replica/phase0/eps_sample_keys_v3.csv")

# 0. company key
d["i9"] = d["isin"].where(d["isin"].astype(str).str.len() >= 9).astype("string").str[:9]
modal = {}
for sym, g in d.groupby("symbol"):
    vc = g["i9"].dropna().value_counts()
    modal[sym] = vc.index[0] if len(vc) else sym
d["company"] = d["symbol"].map(modal)

# 1. usable contexts: whole 1-4 quarters (start + 3k months == end + 1 day)
d = d.dropna(subset=["period_start", "period_end", "consolidated"]).copy()
def nq(ps, pe):
    nxt = pe + pd.Timedelta(days=1)
    months = (nxt.year - ps.year) * 12 + (nxt.month - ps.month)
    if ps.day == 1 and nxt.day == 1 and months in (3, 6, 9, 12):
        return months // 3
    return None
d["nq"] = [nq(a, b) for a, b in zip(d.period_start, d.period_end)]
d = d[d["nq"].notna()].copy()

# 2. primary basis
prim = {}
for co, g in d.groupby("company"):
    Q = set(g.period_end); C = set(g.loc[g.consolidated == True, "period_end"])
    prim[co] = bool(len(C) / len(Q) >= 0.80)

q3 = d[d["nq"] == 1].copy()
q3 = q3[q3["consolidated"] == q3["company"].map(prim)]
# within one filing x quarter, multiple 3m rows: prefer context_role 'current', then most non-null fields
fields = ["pat", "exceptional_items", "tax_expense", "pbt", "eps_basic", "paid_up_equity", "face_value"]
q3["_cur"] = (q3["context_role"] == "current").astype(int)
q3["_nn"] = q3[fields].notna().sum(axis=1)
q3 = q3.sort_values(["company", "period_end", "broadcast_ts", "filing_seq", "_cur", "_nn"],
                    ascending=[True, True, True, True, False, False])
q3 = q3.drop_duplicates(["company", "period_end", "broadcast_ts", "filing_seq"], keep="first")

def count(r):
    pu, fv = r["paid_up_equity"], r["face_value"]
    return pu / fv if (pd.notna(pu) and pd.notna(fv) and pu > 0 and fv > 0) else np.nan

STEPS = [1.5, 2, 2.5, 3, 4, 5, 6, 10, 20]
def is_step(r):
    for x in (r, 1 / r):
        if any(abs(x / k - 1) <= 0.03 for k in STEPS):
            return True
    return False

out = []
for _, k in keys.iterrows():
    co = k["company"]; E = pd.Timestamp(k["fiscal_quarter_end"])
    g = q3[q3.company == co]
    basis = "consolidated" if prim.get(co) else "standalone"
    rows = g[g.period_end == E]
    if rows.empty:
        out.append(dict(company=co, fiscal_quarter_end=E.date(), basis=basis, note="no 3m row")); continue
    v0 = rows.iloc[0]; b = v0["broadcast_ts"]
    # 4. tax rate
    T = [v0["tax_expense"]]; P = [v0["pbt"]]
    for j in (1, 2, 3):
        Ej = E - pd.offsets.MonthEnd(3 * j)
        rj = g[(g.period_end == Ej) & (g.broadcast_ts <= b)]
        if rj.empty:
            T.append(np.nan); P.append(np.nan)
        else:
            last = rj.iloc[-1]; T.append(last["tax_expense"]); P.append(last["pbt"])
    if all(pd.notna(x) for x in T + P) and sum(P) > 0:
        rate = float(np.clip(sum(T) / sum(P), 0, 0.40)); fb = False
    else:
        rate = 0.2517; fb = True
    # 5. core PAT
    core = v0["pat"] - v0["exceptional_items"] * (1 - rate) if pd.notna(v0["exceptional_items"]) else np.nan
    # 6. shares
    sh = count(v0)
    if np.isnan(sh):
        e = v0["eps_basic"]
        sh = v0["pat"] / e if (pd.notna(e) and abs(e) > 0.01 and pd.notna(v0["pat"])) else np.nan
    # 7. share factor from version-0 counts across quarters
    v0all = g.drop_duplicates("period_end", keep="first").sort_values("period_end")
    f = 1.0; prev = np.nan; fac = {}
    for _, r in v0all.iterrows():
        c = count(r)
        if not np.isnan(c):
            if not np.isnan(prev):
                ratio = c / prev
                if is_step(ratio):
                    f *= ratio
            prev = c
        fac[r["period_end"]] = f
    sf = fac[E]
    adj = sh / sf
    out.append(dict(company=co, fiscal_quarter_end=E.date(), basis=basis, tax_rate=rate,
                    tax_rate_fallback=fb, core_pat=core, shares=sh, share_factor=sf,
                    adj_core_eps=core / adj if pd.notna(adj) and adj != 0 else np.nan))

res = pd.DataFrame(out)
res.to_csv(f"{ROOT}/diagnostics/replica/phase0/eps_replica_v3.csv", index=False)
print(res.to_string())
