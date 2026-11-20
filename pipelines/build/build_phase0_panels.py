"""Company-engine Phase 0 panels (data engineering + measurement only; no returns, no signal).

  python pipelines/build/build_phase0_panels.py probe        # pre-2019 listing availability by year
  python pipelines/build/build_phase0_panels.py fundamentals # data/fundamentals_q.parquet + EPS diagnosis
  python pipelines/build/build_phase0_panels.py events       # data/events_results.parquet
  python pipelines/build/build_phase0_panels.py clusters     # data/peer_clusters.parquet + stability

Each command merges its summary into diagnostics/research/explore/2026-11-20_phase0_panels.json.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "pipelines" / "build")]

from harvest_results_xbrl import CACHE, LEGACY, load_listing_frame  # noqa: E402
from nq.data.fundamentals_q import FEATURES, build_panel, company_key, feature_view, first_tradable_session  # noqa: E402
from nq.data.results_xbrl import RESULTS_XBRL_PATH  # noqa: E402

OUT = ROOT / "diagnostics/research/explore/2026-11-20_phase0_panels.json"
FQ = ROOT / "data/fundamentals_q.parquet"            # long: both bases
FV = ROOT / "data/fundamentals_q_features.parquet"   # primary basis + per-feature fallback
EV = ROOT / "data/events_results.parquet"
PC = ROOT / "data/peer_clusters.parquet"


def _save(key, val):
    d = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    d[key] = val
    OUT.write_text(json.dumps(d, indent=1, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------------------------- probe
def probe() -> dict:
    out = {}
    first_link = None
    for name in LEGACY:
        for f in sorted((CACHE / name).glob("201[3-8]-*.json")):
            j = json.loads(f.read_text(encoding="utf-8"))
            rows = j if isinstance(j, list) else j.get("data", []) if isinstance(j, dict) else []
            links = [r for r in rows if str(r.get("xbrl") or "").lower().endswith(".xml")]
            y = f.stem[:4]
            o = out.setdefault(y, {}).setdefault(name, {"rows": 0, "xbrl_links": 0})
            o["rows"] += len(rows)
            o["xbrl_links"] += len(links)
            if links and (first_link is None or f.stem < first_link[0]):
                first_link = (f.stem, name)
    res = {"by_year": out, "first_month_with_links": first_link,
           "integrated": "not probed before 2024-10: the integrated-filing regime began with SEBI's 2024 circular"}
    _save("pre2019_probe", res)
    return res


# ---------------------------------------------------------------------------------------------- fundamentals
def _names() -> pd.Series:
    lf = load_listing_frame()
    a = lf.dropna(subset=["company"]).drop_duplicates("symbol", keep="last").set_index("symbol")["company"]
    b = lf.dropna(subset=["isin", "company"]).drop_duplicates("isin", keep="last").set_index("isin")["company"]
    s = pd.concat([b, a])
    return s[~s.index.duplicated()]


def eps_diagnosis(d: pd.DataFrame, p: pd.DataFrame) -> dict:
    """Split PR #217's EPS non-additivity cases (sum of 4 quarterly basic EPS vs FY basic EPS, gap > 5%) into causes,
    first match wins, in this fixed order: derived-quarter artefact, consolidated/standalone mix, restatement,
    share-count change, unexplained."""
    o = d[d.filing_seq == 0]
    q = o[(o.context_role == "current") & (o.period_type == "Q")].dropna(subset=["eps_basic"]).copy()
    q["fy"] = np.where(q.period_end.dt.month <= 3, q.period_end.dt.year, q.period_end.dt.year + 1)
    k = ["symbol", "consolidated", "fy"]
    g = q.groupby(k).agg(n=("eps_basic", "size"), nq=("period_end", "nunique"), s4=("eps_basic", "sum"),
                         pat4=("pat", "sum"))
    g = g[(g.n == 4) & (g.nq == 4)]
    fyr = o[(o.period_type == "FY") & (o.period_end.dt.month == 3)].dropna(subset=["eps_basic"]).copy()
    fyr["fy"] = fyr.period_end.dt.year
    fy = fyr.groupby(k).agg(fy_eps=("eps_basic", "first"), fy_pat=("pat", "first"))
    j = g.join(fy, how="inner")
    j["gap"] = (j.s4 - j.fy_eps).abs() / j.fy_eps.abs().clip(lower=0.01)
    bad = j[j.gap > 0.05].copy()
    # 1 derived-quarter artefact: a quarterly EPS equals a cumulative (span > 1) EPS in the same filing
    ytd = d[(d.context_role == "ytd") & (d.period_type.isin(["H", "9M", "FY"]))][["xbrl_url", "eps_basic"]]
    qq = q.merge(ytd.rename(columns={"eps_basic": "ytd_eps"}), on="xbrl_url", how="left")
    qq["cum_tag"] = (qq.eps_basic - qq.ytd_eps).abs() <= 0.01 * qq.ytd_eps.abs().clip(lower=0.01)
    qq["cum_tag"] &= (qq.ytd_eps.abs() > 0.05)
    art = qq.groupby(k)["cum_tag"].any()
    q4fy = q[q.period_end.dt.month == 3].set_index(k)["eps_basic"].groupby(level=k).first()
    art = art.reindex(bad.index).fillna(False) | (
        (q4fy.reindex(bad.index) - bad.fy_eps).abs() <= 0.01 * bad.fy_eps.abs().clip(lower=0.01))
    # 2 basis mix: the opposite-basis FY EPS matches the quarterly sum
    opp = fy["fy_eps"].copy()
    opp.index = opp.index.set_levels(opp.index.levels[1].map(lambda x: not x), level=1) \
        if opp.index.levels[1].dtype == bool else opp.index
    oppx = opp.reindex(bad.index)
    mix = ((bad.s4 - oppx).abs() / oppx.abs().clip(lower=0.01) <= 0.05).fillna(False)
    # 3 restatement: latest versions close the gap
    lq = d[(d.context_role == "current") & (d.period_type == "Q")].dropna(subset=["eps_basic"]).copy()
    lq["fy"] = np.where(lq.period_end.dt.month <= 3, lq.period_end.dt.year, lq.period_end.dt.year + 1)
    lq = lq.sort_values("filing_seq").drop_duplicates(k + ["period_end"], keep="last").groupby(k)["eps_basic"].sum()
    lf = d[(d.period_type == "FY") & (d.period_end.dt.month == 3)].dropna(subset=["eps_basic"]).copy()
    lf["fy"] = lf.period_end.dt.year
    lf = lf.sort_values("filing_seq").drop_duplicates(k, keep="last").set_index(k)["eps_basic"]
    rest = ((lq.reindex(bad.index) - lf.reindex(bad.index)).abs() / lf.reindex(bad.index).abs().clip(lower=0.01)
            <= 0.05).fillna(False)
    dr = d[d.filing_seq > 0].dropna(subset=["period_end"])
    dr = dr.assign(fy=np.where(dr.period_end.dt.month <= 3, dr.period_end.dt.year, dr.period_end.dt.year + 1))
    rest &= (dr.groupby(k).size().reindex(bad.index).fillna(0) > 0)
    # 4 share-count change: PAT is additive (<= 2%) and the implied share count moves > 2% inside the year
    sh = q.assign(sh=q.pat / q.eps_basic.where(q.eps_basic.abs() > 0.01)).groupby(k)["sh"].agg(["min", "max"])
    shc = (sh["max"] / sh["min"] - 1).reindex(bad.index) > 0.02
    padd = ((bad.pat4 - bad.fy_pat).abs() / bad.fy_pat.abs().clip(lower=1) <= 0.02)
    share = (shc.fillna(False) & padd.fillna(False))
    cause = np.select([art, mix, rest, share], ["derived_quarter_artefact", "basis_mix", "restatement",
                                                "share_count_change"], "unexplained")
    bad["cause"] = cause
    ratio = (bad.s4 / bad.fy_eps).abs()
    typo = bad.cause.eq("unexplained") & np.isclose(np.log10(ratio.clip(lower=1e-9)).round(),
                                                    np.log10(ratio.clip(lower=1e-9)), atol=0.02) & \
        (np.log10(ratio.clip(lower=1e-9)).round() != 0)
    # after the fix: panel PAT / adjusted shares on the chosen basis, originals, 4 quarters vs FY PAT / Q4 adj shares
    v0 = p[(p.version == 0) & p.adj_eps.notna() & p.is_primary]
    a4 = v0.groupby(["company", "fiscal_year"]).agg(n=("qn", "nunique"), s4=("adj_eps", "sum"), p4=("pat", "sum"),
                                                     sym=("symbol", "last"))
    q4 = v0[v0.fiscal_quarter_end.dt.month == 3].set_index(["company", "fiscal_year"])[["adj_shares", "basis"]]
    a4 = a4[a4.n == 4].join(q4, how="inner")
    fyp = o[(o.period_type == "FY") & (o.period_end.dt.month == 3)].copy()
    fyp["company"] = company_key(fyp["isin"], fyp["symbol"])
    fyp["fiscal_year"] = fyp.period_end.dt.year
    fyp["basis"] = np.where(fyp.consolidated.astype(bool), "consolidated", "standalone")
    fyp = fyp.drop_duplicates(["company", "fiscal_year", "basis"]).set_index(["company", "fiscal_year", "basis"])["pat"]
    a4["fy_pat"] = fyp.reindex(pd.MultiIndex.from_arrays([a4.index.get_level_values(0),
                                                          a4.index.get_level_values(1), a4.basis])).to_numpy()
    a4 = a4.dropna(subset=["fy_pat"])
    a4["fy_adj_eps"] = a4.fy_pat / a4.adj_shares
    # quarterly EPS each on its own quarter's adjusted shares (still moves with QIPs / buybacks)
    a4["gap_own"] = (a4.s4 - a4.fy_adj_eps).abs() / a4.fy_adj_eps.abs().clip(lower=0.01)
    # the fix: one adjusted-share denominator for the year, so only PAT additivity remains
    a4["gap"] = (a4.p4 - a4.fy_pat).abs() / a4.fy_pat.abs().clip(lower=1)
    after = a4.gap > 0.05
    vc = bad.cause.value_counts()
    return {"pr217_pairs": int(len(j)), "pr217_gap_over_5pct": int(len(bad)),
            "pr217_gap_over_5pct_pct": round(100 * len(bad) / len(j), 2),
            "causes_n": vc.to_dict(), "causes_pct_of_flagged": (100 * vc / len(bad)).round(1).to_dict(),
            "unexplained_that_look_like_scale_typos": int(typo.sum()),
            "unexplained_pct_of_all_pairs": round(100 * float((bad.cause == "unexplained").sum()) / len(j), 2),
            "after_fix_pairs": int(len(a4)), "after_fix_gap_over_5pct_pct": round(100 * float(after.mean()), 2),
            "after_fix_gap_median_pct": round(100 * float(a4.gap.median()), 3),
            "after_fix_own_quarter_shares_gap_over_5pct_pct": round(100 * float((a4.gap_own > 0.05).mean()), 2)}


def _recovered(d: pd.DataFrame, v: pd.DataFrame) -> dict:
    """Share of company-quarters with a current filing (either basis) that have a feature-view row, by year."""
    c = d[(d.context_role == "current") & d.period_end.notna()].copy()
    c["company"] = company_key(c["isin"], c["symbol"])
    c["qe"] = c.period_end + pd.offsets.QuarterEnd(0)
    allq = c.drop_duplicates(["company", "qe"])
    have = v.drop_duplicates(["company", "fiscal_quarter_end"]).set_index(["company", "fiscal_quarter_end"]).index
    prim = v[~v.row_recovered].drop_duplicates(["company", "fiscal_quarter_end"]).set_index(
        ["company", "fiscal_quarter_end"]).index
    k = allq.set_index(["company", "qe"]).index
    yr = allq.qe.dt.year.values
    return {"present_pct_by_year": (100 * pd.Series(k.isin(have), index=yr).groupby(level=0).mean()).round(1).to_dict(),
            "primary_only_present_pct_by_year": (100 * pd.Series(k.isin(prim), index=yr).groupby(level=0).mean()).round(1).to_dict()}


def fundamentals() -> dict:
    d = pd.read_parquet(RESULTS_XBRL_PATH)
    p = build_panel(d, _names())
    p.to_parquet(FQ, index=False)
    v = feature_view(p)
    v.to_parquet(FV, index=False)
    pv0 = p[(p.version == 0) & p.is_primary]
    vv0 = v[v.version == 0]
    fb = {f: (vv0.groupby("fiscal_year")[f + "_basis_fallback"].sum()).astype(int).to_dict() for f in FEATURES}
    pr = pv0[~pv0.tax_rate_fallback]
    q = pr.tax_rate.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(4)
    # exceptional-items sign: PBT = PBEIT + exceptional (sign as tagged) where all three are present
    e = pv0.dropna(subset=["pbt", "pbeit", "exceptional_items"])
    e = e[e.exceptional_items.abs() > 0]
    plus = ((e.pbeit + e.exceptional_items - e.pbt).abs() <= 0.01 * e.pbt.abs().clip(lower=1)).mean()
    minus = ((e.pbeit - e.exceptional_items - e.pbt).abs() <= 0.01 * e.pbt.abs().clip(lower=1)).mean()
    res = {"rows_long_both_bases": int(len(p)), "rows_feature_view": int(len(v)),
           "feature_view_recovered_rows": int(v.row_recovered.sum()), "companies": int(p.company.nunique()),
           "quarters_v0_primary": int(len(pv0)), "revision_rows_primary": int((p.is_revision & p.is_primary).sum()),
           "derived_rows_primary": int((p.derived & p.is_primary).sum()),
           "primary_basis_companies": p.drop_duplicates("company").primary_basis.value_counts().to_dict(),
           "financial_companies": int(p.drop_duplicates("company").is_financial.sum()),
           "split_bonus_events_primary": int(pv0.drop_duplicates(["company", "qn"]).split_event.sum()),
           "coverage": _recovered(d, v),
           "feature_fallback_rows_by_fiscal_year": fb,
           "tax_rate": {"fallback_pct_primary_v0": round(100 * float(pv0.tax_rate_fallback.mean()), 2),
                        "fallback_pct_by_fiscal_year": (100 * pv0.groupby("fiscal_year").tax_rate_fallback.mean()).round(1).to_dict(),
                        "effective_quantiles": q.to_dict(), "at_clip_0_pct": round(100 * float((pr.tax_rate == 0).mean()), 2),
                        "at_clip_40_pct": round(100 * float((pr.tax_rate == 0.40).mean()), 2),
                        "pbt_present_pct": round(100 * float(pv0.pbt.notna().mean()), 2),
                        "tax_present_pct": round(100 * float(pv0.tax_expense.notna().mean()), 2)},
           "exceptional_sign_check": {"rows_nonzero": int(len(e)), "pbt_eq_pbeit_plus_exc_pct": round(100 * float(plus), 1),
                                      "pbt_eq_pbeit_minus_exc_pct": round(100 * float(minus), 1)},
           "adj_core_eps_present_pct": round(100 * float(pv0.adj_core_eps.notna().mean()), 2),
           "ttm_pat_present_pct_primary": round(100 * float(pv0.ttm_pat.notna().mean()), 2),
           "ttm_pat_present_pct_view": round(100 * float(vv0.ttm_pat.notna().mean()), 2),
           "eps_diagnosis": eps_diagnosis(d, p)}
    _save("fundamentals", res)
    return res


# ---------------------------------------------------------------------------------------------- events
def _sessions() -> tuple[pd.DatetimeIndex, str]:
    from nq.data import trading_calendar as tc
    m = pickle.load(open(ROOT / ".cache/phase0_market.pkl", "rb"))
    s = set(m.close.index.normalize())
    last = max(s)
    extra = [d for d in pd.date_range(last + pd.Timedelta(days=1), "2026-12-31") if tc.is_regular_session(d.date())]
    early = [d for d in pd.bdate_range("2012-01-01", min(s) - pd.Timedelta(days=1))]
    return pd.DatetimeIndex(sorted(s | set(extra) | set(early))), str(min(s).date())


def events() -> dict:
    p = pd.read_parquet(FV)
    sess, ohlcv_start = _sessions()
    ev = p.copy()
    ev["first_tradable_session"] = first_tradable_session(ev["broadcast_ts"], sess)
    ev["calendar_source"] = np.where(ev["broadcast_ts"] < pd.Timestamp(ohlcv_start), "weekday_approx",
                                     "ohlcv_sessions+nse_holidays")
    cols = ["company", "symbol", "isin", "basis", "primary_basis", "row_recovered", "is_financial", "fiscal_year", "fiscal_quarter_end",
            "period_start", "period_end", "version", "is_revision", "derived", "broadcast_ts",
            "first_tradable_session", "calendar_source", "lag_days", "period_flag", "xbrl_url", "revenue_ops",
            "pat", "core_pat", "exceptional_items", "shares", "share_factor", "adj_shares", "adj_core_eps",
            "adj_eps", "ttm_pat", "ttm_revenue_ops", "ttm_margin", "yoy_core_pat", "tax_rate", "tax_rate_fallback",
            "nan_reason"] + [f"{f}_{x}" for f in FEATURES for x in ("basis", "basis_fallback")]
    ev = ev[cols].sort_values(["broadcast_ts", "company"]).reset_index(drop=True)
    ev.to_parquet(EV, index=False)
    t = ev.broadcast_ts
    after = (t - t.dt.normalize()) >= pd.Timedelta(hours=15, minutes=30)
    res = {"events": int(len(ev)), "originals": int((~ev.is_revision).sum()),
           "by_broadcast_year": ev.groupby(t.dt.year).size().to_dict(),
           "same_day_pct": round(100 * float((ev.first_tradable_session == t.dt.normalize()).mean()), 1),
           "after_close_pct": round(100 * float(after.mean()), 1),
           "no_session_nat": int(ev.first_tradable_session.isna().sum()),
           "weekday_approx_rows": int((ev.calendar_source == "weekday_approx").sum())}
    _save("events", res)
    return res


# ---------------------------------------------------------------------------------------------- clusters
def clusters() -> dict:
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform
    from sklearn.metrics import adjusted_rand_score
    m = pickle.load(open(ROOT / ".cache/phase0_market.pkl", "rb"))
    ret = m.close.pct_change(fill_method=None)
    idx = ret.index
    month_ends = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max()
    rows, prev, ari, sizes = [], None, [], []
    for me in month_ends:
        i = idx.get_loc(me)
        if i < 252:
            continue
        mem = m.member.loc[me]
        w = ret.iloc[i - 251:i + 1].loc[:, mem[mem].index]
        w = w.loc[:, w.notna().sum() >= 200]
        if w.shape[1] < 30:
            continue
        mk = w.mean(axis=1)
        mc = mk - mk.mean()
        beta = w.sub(w.mean()).mul(mc, axis=0).sum() / (mc ** 2).sum()
        res = w - np.outer(mk, beta)
        c = res.corr(min_periods=150).fillna(0).to_numpy().copy()
        np.fill_diagonal(c, 1.0)
        dist = np.sqrt(np.clip(2 * (1 - c), 0, None))
        np.fill_diagonal(dist, 0)
        n = w.shape[1]
        k = int(round(n / 15))
        lab = fcluster(linkage(squareform(dist, checks=False), method="average"), t=k, criterion="maxclust")
        cur = pd.Series(lab, index=w.columns)
        rows.append(pd.DataFrame({"month_end": me, "symbol": cur.index, "cluster": cur.values, "k": k, "n": n}))
        sizes.append(np.bincount(lab)[1:])
        if prev is not None:
            common = cur.index.intersection(prev.index)
            ari.append((me, adjusted_rand_score(prev[common], cur[common])))
        prev = cur
    pc = pd.concat(rows, ignore_index=True)
    pc.to_parquet(PC, index=False)
    a = pd.Series(dict(ari))
    allsz = np.concatenate(sizes)
    res = {"months": int(pc.month_end.nunique()), "first": str(pc.month_end.min().date()),
           "last": str(pc.month_end.max().date()), "members_median": int(pc.groupby("month_end").n.first().median()),
           "k_median": int(pc.groupby("month_end").k.first().median()),
           "ari_by_year_median": a.groupby(a.index.year).median().round(3).to_dict(),
           "ari_all_median": round(float(a.median()), 3), "ari_all_p10": round(float(a.quantile(0.1)), 3),
           "cluster_size": {"median": float(np.median(allsz)), "p90": float(np.quantile(allsz, 0.9)),
                            "max": int(allsz.max()), "singletons_pct": round(100 * float((allsz == 1).mean()), 1),
                            "largest_share_median_pct": round(float(np.median([100 * s.max() / s.sum() for s in sizes])), 1)}}
    _save("clusters", res)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "fundamentals", "events", "clusters"])
    r = {"probe": probe, "fundamentals": fundamentals, "events": events, "clusters": clusters}[ap.parse_args().cmd]()
    print(json.dumps(r, indent=1, default=str))
