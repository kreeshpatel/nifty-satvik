"""Blind replica (v2) of Phase-0 adjusted core EPS, built from the spec only.

Does not import nq/. Reads data/results_xbrl.parquet and eps_sample_keys.csv.
Writes eps_replica_v2.csv next to this file.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FALLBACK = 0.2517
STEPS = [1.5, 2, 2.5, 3, 4, 5, 6, 10, 20]

COLS = ["symbol", "isin", "period_start", "period_end", "consolidated", "context_role",
        "broadcast_ts", "filing_seq", "pat", "exceptional_items", "tax_expense", "pbt",
        "eps_basic", "paid_up_equity", "face_value"]
VALS = ["pat", "exceptional_items", "tax_expense", "pbt", "eps_basic", "paid_up_equity", "face_value"]


def n_quarters(start, end):
    # length in days (inclusive) -> nearest whole month count; whole quarter if
    # months in {3,6,9,12} and day count within 5 days of months*30.4375.
    days = (end - start).days + 1
    months = int(round(days / 30.4375))
    if months in (3, 6, 9, 12) and abs(days - months * 30.4375) <= 5:
        return months // 3
    return 0


def qindex(ts):
    # integer quarter index from period_end (month granularity / 3)
    return (ts.year * 12 + ts.month - 1) // 3


def load():
    d = pd.read_parquet(ROOT / "data" / "results_xbrl.parquet", columns=COLS)
    isin = d["isin"].fillna("").astype(str).str.strip()
    d["company"] = np.where(isin != "", isin, d["symbol"])
    d = d.dropna(subset=["period_start", "period_end", "consolidated"]).copy()
    d["nq"] = [n_quarters(s, e) for s, e in zip(d["period_start"], d["period_end"])]
    d = d[d["nq"] > 0].copy()
    d["consolidated"] = d["consolidated"].astype(bool)
    d["q"] = d["period_end"].map(qindex)
    return d


def primary_basis(g):
    Q = set(g["period_end"])
    C = set(g.loc[g["consolidated"], "period_end"])
    return "consolidated" if len(Q) and len(C) / len(Q) >= 0.80 else "standalone"


def discrete_versions(g):
    """3-month rows of one company on one basis -> one row per (quarter, filing).
    Filing = (broadcast_ts, filing_seq). Within a filing, several 3-month contexts
    for the same quarter may exist (current + ytd-labelled): prefer role 'current',
    then the row with most non-null values."""
    x = g[g["nq"] == 1].copy()
    x["role_rank"] = (x["context_role"] != "current").astype(int)
    x["nn"] = -x[VALS].notna().sum(axis=1)
    x = x.sort_values(["q", "broadcast_ts", "filing_seq", "role_rank", "nn"])
    x = x.drop_duplicates(["q", "broadcast_ts", "filing_seq"], keep="first")
    x["version"] = x.groupby("q").cumcount()
    return x.drop(columns=["role_rank", "nn"])


def latest_known(disc, q, b, col):
    r = disc[(disc["q"] == q) & (disc["broadcast_ts"] <= b) & disc[col].notna()]
    if r.empty:
        return np.nan
    return r.sort_values(["broadcast_ts", "filing_seq"]).iloc[-1][col]


def tax_rate(disc, row):
    q, b = row["q"], row["broadcast_ts"]
    T = [row["tax_expense"]] + [latest_known(disc, q - k, b, "tax_expense") for k in (1, 2, 3)]
    P = [row["pbt"]] + [latest_known(disc, q - k, b, "pbt") for k in (1, 2, 3)]
    if all(pd.notna(v) for v in T + P) and sum(P) > 0:
        return float(np.clip(sum(T) / sum(P), 0.0, 0.40)), False
    return FALLBACK, True


def shares_of(row):
    pu, fv = row["paid_up_equity"], row["face_value"]
    if pd.notna(pu) and pd.notna(fv) and pu > 0 and fv > 0:
        return pu / fv
    pat, eps = row["pat"], row["eps_basic"]
    if pd.notna(pat) and pd.notna(eps) and abs(eps) > 0.01:
        return pat / eps
    return np.nan


def share_factors(disc):
    v0 = disc[disc["version"] == 0].sort_values("q")
    out, prev, f = {}, None, 1.0
    for _, r in v0.iterrows():
        pu, fv = r["paid_up_equity"], r["face_value"]
        cnt = pu / fv if (pd.notna(pu) and pd.notna(fv) and pu > 0 and fv > 0) else np.nan
        if pd.notna(cnt):
            if prev is not None:
                ratio = cnt / prev
                for s in STEPS:
                    if abs(ratio - s) <= 0.03 * s or abs(1 / ratio - s) <= 0.03 * s:
                        f *= ratio
                        break
            prev = cnt
        out[r["q"]] = f  # quarters without a count inherit current f
    return out


def main():
    d = load()
    keys = pd.read_csv(HERE / "eps_sample_keys.csv", parse_dates=["fiscal_quarter_end"])
    rows, skipped = [], []
    for _, k in keys.iterrows():
        g = d[d["company"] == k["company"]]
        if g.empty:
            skipped.append((k["company"], k["fiscal_quarter_end"].date(), "no usable rows"))
            continue
        basis = primary_basis(g)
        gb = g[g["consolidated"] == (basis == "consolidated")]
        disc = discrete_versions(gb)
        q = qindex(k["fiscal_quarter_end"])
        r0 = disc[(disc["q"] == q) & (disc["version"] == 0)]
        if r0.empty:
            skipped.append((k["company"], k["fiscal_quarter_end"].date(), f"no 3m {basis} row"))
            continue
        r0 = r0.iloc[0]
        rate, fb = tax_rate(disc, r0)
        exc = r0["exceptional_items"]
        core = r0["pat"] - exc * (1 - rate) if pd.notna(exc) else np.nan
        sh = shares_of(r0)
        sf = share_factors(disc).get(q, 1.0)
        adj = sh / sf
        eps = core / adj if pd.notna(core) and pd.notna(adj) and adj != 0 else np.nan
        rows.append(dict(company=k["company"], fiscal_quarter_end=k["fiscal_quarter_end"].date(),
                         basis=basis, tax_rate=rate, tax_rate_fallback=fb, core_pat=core,
                         shares=sh, share_factor=sf, adj_core_eps=eps))
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "eps_replica_v2.csv", index=False)
    print(out.to_string())
    print("rows", len(out), "skipped", skipped)


if __name__ == "__main__":
    main()
