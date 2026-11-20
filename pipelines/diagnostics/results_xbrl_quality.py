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


def period_flags(df) -> dict:
    """Period-sanity guard (nq.data.results_xbrl.period_sanity), all rows:
    flagged-row counts by reason x broadcast year (a row with two reasons counts under each);
    lag_days = broadcast date - period_end: median / p95 / max for current Q rows and FY rows;
    the 20 worst rows by |lag_days| among flagged rows, with symbol, period, broadcast, chosen context."""
    y = df.broadcast_ts.dt.year
    fl = df["period_flag"].fillna("").str.split(";").explode()
    fl = fl[fl != ""]
    by = pd.crosstab(fl, y.loc[fl.index]) if len(fl) else pd.DataFrame()
    lag = {}
    for name, m in {"Q_current": (df.period_type == "Q") & (df.context_role == "current"),
                    "FY": df.period_type == "FY"}.items():
        x = df.loc[m, "lag_days"].dropna()
        lag[name] = {"n": int(len(x)), "median": float(x.median()), "p95": float(x.quantile(0.95)),
                     "max": float(x.max()), "min": float(x.min())} if len(x) else {"n": 0}
    f = df[df.period_flag.notna()]
    worst = f.assign(a=f.lag_days.abs()).sort_values("a", ascending=False).head(20)
    cols = ["symbol", "period_start", "period_end", "period_type", "context_role", "context_id", "current_rule",
            "broadcast_ts", "lag_days", "period_flag", "is_revision", "consolidated"]
    return {"rows": int(len(df)), "flagged_rows": int(df.period_flag.notna().sum()),
            "neg_lag_pct": round(100 * float((df.lag_days < 0).mean()), 3),
            "by_reason_year": {r: {int(k): int(v) for k, v in row.items()} for r, row in by.iterrows()},
            "lag_days": lag, "worst20": worst[cols].astype(str).to_dict("records")}


NOT_FOUND_STOP_PCT = 2.0


def late_by_membership(br) -> dict:
    """lag_over_120d rows split by PIT Nifty 500 membership ON THE BROADCAST DATE
    (nq.data.membership.load_membership intervals). A row counts as member if either its filing-day
    symbol or its ISIN's latest symbol (bridge_symbols) is a member that day. Shares are of all rows
    in that membership group, by broadcast year, and separately for current-quarter rows."""
    from nq.data.membership import load_membership
    mem = load_membership()

    def is_mem(sym, d):
        return any(a <= d <= b for a, b in mem.get(sym, ()))

    b = br.assign(_d=br.broadcast_ts.dt.date)
    b["_m"] = [is_mem(s, d) for s, d in zip(b.symbol, b._d)]
    key = ["xbrl_url", "context_id"]
    m = b.groupby(key)["_m"].any()                       # member under either symbol
    raw = br.drop_duplicates(key).set_index(key)
    raw = raw.assign(member=m.reindex(raw.index).fillna(False).to_numpy(),
                     late=raw.period_flag.fillna("").str.contains("lag_over_120d"))
    out = {}
    for name, r in {"all_rows": raw, "current_rows": raw[raw.context_role == "current"]}.items():
        g = r.groupby([r.broadcast_ts.dt.year, "member"])["late"].agg(["sum", "size"])
        out[name] = {f"{int(y)}_{'member' if mm else 'non_member'}": {
            "late": int(v["sum"]), "rows": int(v["size"]), "late_pct": round(100 * v["sum"] / v["size"], 2)}
            for (y, mm), v in g.iterrows()}
        tot = r.groupby("member")["late"].agg(["sum", "size"])
        out[name]["total"] = {("member" if mm else "non_member"): {
            "late": int(v["sum"]), "rows": int(v["size"]), "late_pct": round(100 * v["sum"] / v["size"], 2)}
            for mm, v in tot.iterrows()}
    return out


def not_found_by_year() -> dict:
    """From data/xbrl_raw/manifest.csv (every fetch attempt, latest status per URL), by listing broadcast
    year: attempted URLs, listed URLs, HTTP 404 count, the same split by PIT N500 membership at broadcast
    (member 404 rate; the member (symbol, period) pairs are listed for any complete year over 2%), other non-200 count, not-found % = 404 / attempted.
    A year is complete when every listed XBRL URL of that year has been attempted. While the fetch runs,
    partial years hold only a handful of sample fetches, so the stop applies to complete years only:
    stop = any complete year's not-found % > NOT_FOUND_STOP_PCT. Once the fetch ends all years are complete."""
    from harvest_results_xbrl import load_listing_frame, read_manifest
    m = pd.DataFrame(list(read_manifest().values()))
    if not len(m):
        return {"by_year": {}, "stop": False}
    listed = load_listing_frame()
    listed = listed.groupby(listed.broadcast_ts.dt.year)["xbrl_url"].nunique()
    y = pd.to_datetime(m.broadcast_ts, errors="coerce").dt.year
    out = {}
    for yr, g in m.groupby(y):
        n404 = int((g.http_status == "404").sum())
        other = int((~g.http_status.isin(["200", "404"])).sum())
        out[int(yr)] = {"attempted": int(len(g)), "listed": int(listed.get(yr, 0)),
                        "complete": bool(len(g) >= listed.get(yr, 0)), "not_found_404": n404,
                        "other_non200": other, "not_found_pct": round(100 * n404 / len(g), 2)}
    # member split: PIT Nifty 500 membership on the broadcast date, under the filing-day symbol or the
    # ISIN's latest symbol (same bridge as bridge_symbols). Member 404 rate = member 404 / member attempted.
    from nq.data.membership import load_membership
    mem = load_membership()
    L = load_listing_frame()
    latest = L.dropna(subset=["isin", "symbol"]).sort_values("broadcast_ts").groupby("isin")["symbol"].last()
    Lu = L.set_index("xbrl_url")
    m = m.assign(isin=m.url.map(Lu["isin"]), period_end=m.url.map(Lu["to_date"]),
                 consolidated=m.url.map(Lu["consolidated_listing"]), _d=pd.to_datetime(m.broadcast_ts).dt.date)
    m["sym2"] = m["isin"].map(latest).fillna(m["symbol"])
    m["member"] = [any(a <= d <= b for sy in {s1, s2} for a, b in mem.get(sy, ()))
                   for s1, s2, d in zip(m["symbol"], m["sym2"], m["_d"])]
    for yr, g in m.groupby(y):
        gm = g[g.member]
        n404 = int((gm.http_status == "404").sum())
        out[int(yr)].update(member_attempted=int(len(gm)), member_404=n404,
                            member_not_found_pct=round(100 * n404 / len(gm), 2) if len(gm) else None,
                            non_member_404=int(((g.http_status == "404") & ~g.member).sum()))
        if out[int(yr)]["complete"] and len(gm) and 100 * n404 / len(gm) > NOT_FOUND_STOP_PCT:
            out[int(yr)]["member_404_pairs"] = (gm[gm.http_status == "404"]
                                                [["symbol", "period_end", "consolidated", "broadcast_ts"]]
                                                .sort_values(["symbol", "period_end"]).to_dict("records"))
    done = {k: v for k, v in out.items() if v["complete"]}
    worst = max(done, key=lambda k: done[k]["not_found_pct"]) if done else None
    return {"by_year": out, "worst_complete_year": worst, "limit_pct": NOT_FOUND_STOP_PCT,
            "member_over_limit_years": [k for k, v in done.items()
                                        if (v.get("member_not_found_pct") or 0) > NOT_FOUND_STOP_PCT],
            "stop": bool(worst is not None and done[worst]["not_found_pct"] > NOT_FOUND_STOP_PCT)}


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
    U = members_by_year([y for y in years if y >= 2018])  # 2018 added (Phase 0 extension)
    res = {"rows": int(len(df)), "filings": int(df.xbrl_url.nunique()), "current_rows": int(len(cur)),
           "broadcast_range": f"{df.broadcast_ts.min()}..{df.broadcast_ts.max()}",
           "period_type_current": cur.period_type.value_counts().to_dict(),
           "coverage_pit_n500_raw_symbol": coverage(raw, U), "coverage_pit_n500": coverage(br, U),
           "uncovered_members": {int(y): sorted(U[y] - set(br[br.broadcast_ts.dt.year == y].symbol)) for y in U},
           "quarter_completeness_raw_symbol": completeness(raw[raw.context_role == "current"], U),
           "quarter_completeness": completeness(br[br.context_role == "current"], U),
           "parse_failures": parse_failures(cur), "eps_sanity": eps_sanity(df), "cross_check_depth": cross_check(df),
           "revisions": revisions(df), "period_sanity": period_flags(df),
           "late_by_membership": late_by_membership(br), "not_found": not_found_by_year(), "broadcast_timing": timing(df)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    if res["not_found"]["stop"]:
        nf = res["not_found"]
        print(f"STOP: not-found rate {nf['by_year'][nf['worst_complete_year']]['not_found_pct']}% in {nf['worst_complete_year']} "
              f"exceeds {nf['limit_pct']}%. Report before using these quality numbers.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
