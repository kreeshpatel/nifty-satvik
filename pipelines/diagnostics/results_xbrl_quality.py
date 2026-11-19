"""Quality report numbers for data/results_xbrl.parquet (data engineering only; no signal, no returns).

Writes diagnostics/research/explore/2026-11-19_results_xbrl_quality.json. Metric definitions are in
the docstrings of each function and restated in diagnostics/research/2026-11_results_xbrl_quality.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "pipelines" / "build")]

from nq.data.results_xbrl import RESULTS_XBRL_PATH, VALUE_FIELDS  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_results_xbrl_quality.json"
SEED = 20261119


def members_by_year(years) -> dict[int, set]:
    """PIT Nifty 500: members on 30 June of each year (nq.data.membership.load_membership)."""
    from nq.data.membership import load_membership
    mem = load_membership()
    return {y: {t for t, iv in mem.items() if any(a <= pd.Timestamp(f"{y}-06-30").date() <= b for a, b in iv)}
            for y in years}


def coverage(df, U) -> dict:
    """Share of 30-June members with >= 1 parsed filing broadcast in that calendar year."""
    by = df.assign(y=df.broadcast_ts.dt.year).groupby("y")["symbol"].agg(set)
    return {int(y): round(100 * len(U[y] & by.get(y, set())) / len(U[y]), 1) for y in U}


def completeness(cur, U) -> dict:
    """(member, quarter) pairs: members on 30 June of year Y x the four quarter-ends in Y (Mar/Jun/Sep/Dec).
    Share with a standalone current-quarter row, with a consolidated one, and with either.
    Only quarter-ends already past by 60 days of the last broadcast in the data are counted."""
    last = cur.broadcast_ts.max()
    have_s = set(map(tuple, cur[cur.consolidated == False][["symbol", "period_end"]].drop_duplicates().to_numpy()))  # noqa: E712
    have_c = set(map(tuple, cur[cur.consolidated == True][["symbol", "period_end"]].drop_duplicates().to_numpy()))  # noqa: E712
    out = {}
    for y, mem in U.items():
        qes = [q for q in pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="QE") if q + pd.Timedelta(days=60) <= last]
        pairs = [(s, q) for s in mem for q in qes]
        if not pairs:
            continue
        s = sum((p in have_s) for p in pairs)
        c = sum((p in have_c) for p in pairs)
        e = sum((p in have_s) or (p in have_c) for p in pairs)
        out[int(y)] = {"pairs": len(pairs), "quarters": len(qes), "standalone_pct": round(100 * s / len(pairs), 1),
                       "consolidated_pct": round(100 * c / len(pairs), 1), "either_pct": round(100 * e / len(pairs), 1)}
    return out


def parse_failures(cur) -> dict:
    """Per field and broadcast year, over current-quarter rows: % with a failure reason (parse/unit/conflict),
    and separately % absent (tag not in the filing)."""
    out = {}
    y = cur.broadcast_ts.dt.year
    for f in VALUE_FIELDS:
        r = cur[f"{f}__reason"]
        out[f] = {int(k): {"fail_pct": round(100 * float(g.isin(["parse", "unit", "conflict"]).mean()), 2),
                           "absent_pct": round(100 * float((g == "absent").mean()), 1)} for k, g in r.groupby(y)}
    return out


def eps_sanity(df) -> dict:
    """For each (symbol, consolidated, fiscal year ending 31 March): sum of the four current-quarter basic EPS
    (original filings, filing_seq 0) vs the fiscal-year basic EPS from the FY year-to-date context inside the
    March-quarter filing (original). gap = |sum4 - fy| / max(|fy|, 0.01). Flag gap > 5%."""
    d = df[df.filing_seq == 0]
    q = d[(d.context_role == "current") & (d.period_type == "Q")].dropna(subset=["eps_basic"])
    q = q.assign(fy=np.where(q.period_end.dt.month <= 3, q.period_end.dt.year, q.period_end.dt.year + 1))
    g = q.groupby(["symbol", "consolidated", "fy"]).agg(n=("eps_basic", "size"), s4=("eps_basic", "sum"),
                                                        nq=("period_end", "nunique"))
    g = g[(g.n == 4) & (g.nq == 4)]
    fy = d[(d.period_type == "FY") & (d.period_end.dt.month == 3)].dropna(subset=["eps_basic"])
    fy = fy.assign(fy=fy.period_end.dt.year).groupby(["symbol", "consolidated", "fy"])["eps_basic"].first()
    j = g.join(fy.rename("fy_eps"), how="inner")
    if not len(j):
        return {"pairs": 0}
    gap = (j.s4 - j.fy_eps).abs() / j.fy_eps.abs().clip(lower=0.01)
    return {"source_of_fy_eps": "FY year-to-date context inside the March-quarter filing",
            "pairs": int(len(j)), "gap_median_pct": round(100 * float(gap.median()), 2),
            "gap_p90_pct": round(100 * float(gap.quantile(0.9)), 2),
            "share_gap_over_5pct": round(100 * float((gap > 0.05).mean()), 1),
            "share_gap_over_5pct_and_abs_over_0.5": round(100 * float(((gap > 0.05) & ((j.s4 - j.fy_eps).abs() > 0.5)).mean()), 1),
            "by_fy": {int(k): round(100 * float((v > 0.05).mean()), 1) for k, v in gap.groupby(level="fy")}}


def cross_check(df, n=50) -> dict:
    """50 random year-end filings (FY context, March period end, original) vs data/fundamentals_pit_depth.pkl
    (Screener annual, Rs crore). Compare the consolidated row when the filing set has one for that
    (symbol, FY), else the standalone row (rule fixed before looking). diff = xbrl/1e7 / screener - 1."""
    depth = pd.read_pickle(ROOT / "data" / "fundamentals_pit_depth.pkl")
    d = df[(df.filing_seq == 0) & (df.period_type == "FY") & (df.period_end.dt.month == 3) & df.symbol.isin(depth)]
    d = d.sort_values("consolidated", ascending=False).drop_duplicates(["symbol", "period_end"])
    d = d.sample(min(n, len(d)), random_state=SEED)
    rows = []
    for r in d.itertuples():
        s = depth[r.symbol]
        m = s[pd.to_datetime(s.period_end) == r.period_end]
        if not len(m):
            continue
        m = m.iloc[0]
        rows.append({"symbol": r.symbol, "fy_end": str(r.period_end.date()), "consolidated": bool(r.consolidated),
                     "rev_diff": (r.revenue_ops / 1e7) / m.sales - 1 if m.sales else np.nan,
                     "pat_diff": (r.pat / 1e7) / m.net_profit - 1 if m.net_profit else np.nan})
    c = pd.DataFrame(rows)
    if not len(c):
        return {"matched": 0}

    def dist(x):
        x = x.dropna().abs()
        return {"n": int(len(x)), "median_abs_pct": round(100 * float(x.median()), 2),
                "within_1pct": round(100 * float((x <= 0.01).mean()), 1),
                "within_5pct": round(100 * float((x <= 0.05).mean()), 1),
                "over_20pct": round(100 * float((x > 0.20).mean()), 1)}
    return {"sampled": int(len(d)), "matched": int(len(c)), "revenue": dist(c.rev_diff), "pat": dist(c.pat_diff),
            "worst": c.assign(a=c.pat_diff.abs()).nlargest(5, "a").drop(columns="a").round(3).to_dict("records")}


def revisions(df) -> dict:
    """Revision = a later filing (filing_seq >= 1) for the same (symbol, period, consolidated) current-quarter
    context. Time to revision = its broadcast minus the original's broadcast."""
    cur = df[df.context_role == "current"]
    key = ["symbol", "period_start", "period_end", "consolidated"]
    orig = cur[cur.filing_seq == 0].set_index(key)["broadcast_ts"]
    rv = cur[cur.filing_seq >= 1].join(orig.rename("orig_ts"), on=key)
    dt = (rv.broadcast_ts - rv.orig_ts).dt.total_seconds() / 86400
    return {"revision_rows": int(len(rv)), "share_of_current_rows_pct": round(100 * len(rv) / max(len(cur), 1), 2),
            "median_days_to_revision": round(float(dt.median()), 2) if len(dt) else None,
            "p90_days_to_revision": round(float(dt.quantile(0.9)), 1) if len(dt) else None,
            "same_day_pct": round(100 * float((dt < 1).mean()), 1) if len(dt) else None}


def timing(df) -> dict:
    """Broadcast time of day (IST, listing timestamp), one per filing: <09:15, 09:15-15:30, >15:30."""
    f = df.drop_duplicates("xbrl_url")
    m = f.broadcast_ts.dt.hour * 60 + f.broadcast_ts.dt.minute
    b = pd.cut(m, [-1, 554, 930, 2000], labels=["pre_0915", "0915_1530", "post_1530"])
    t = pd.crosstab(f.broadcast_ts.dt.year, b, normalize="index").mul(100).round(1)
    return {int(y): r.to_dict() for y, r in t.iterrows()}


def bridge_symbols(df):
    """Membership uses today's tickers; filings carry the ticker of their day. Map each row's ISIN to the
    latest symbol that ISIN files under in the full NSE listing (2019..2026) -> column symbol_latest.
    Reported both raw and bridged (bridge added after first look: raw coverage missed renamed names)."""
    from harvest_results_xbrl import load_listing_frame
    L = load_listing_frame().dropna(subset=["isin", "symbol"]).sort_values("broadcast_ts")
    latest = L.groupby("isin")["symbol"].last()
    b = df.assign(symbol=df["isin"].map(latest).fillna(df["symbol"]))
    # a member matches on either its filing-day ticker or the ISIN's latest ticker (membership mixes both)
    return pd.concat([df, b[b["symbol"] != df["symbol"]]], ignore_index=True)


def main():
    raw = pd.read_parquet(RESULTS_XBRL_PATH)
    df = raw
    br = bridge_symbols(raw)
    cur = df[(df.context_role == "current")]
    years = sorted(df.broadcast_ts.dt.year.unique())
    U = members_by_year([y for y in years if y >= 2019])
    res = {"rows": int(len(df)), "filings": int(df.xbrl_url.nunique()), "current_rows": int(len(cur)),
           "broadcast_range": f"{df.broadcast_ts.min()}..{df.broadcast_ts.max()}",
           "period_type_current": cur.period_type.value_counts().to_dict(),
           "coverage_pit_n500_raw_symbol": coverage(raw, U), "coverage_pit_n500": coverage(br, U),
           "uncovered_members": {int(y): sorted(U[y] - set(br[br.broadcast_ts.dt.year == y].symbol)) for y in U},
           "quarter_completeness_raw_symbol": completeness(raw[raw.context_role == "current"], U),
           "quarter_completeness": completeness(br[br.context_role == "current"], U),
           "parse_failures": parse_failures(cur), "eps_sanity": eps_sanity(df), "cross_check_depth": cross_check(df),
           "revisions": revisions(df), "broadcast_timing": timing(df)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
