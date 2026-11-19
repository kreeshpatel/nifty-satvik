"""MEASUREMENT (exploration tier, 0 trials): does anything knowable AT STOP TIME separate noise_stop (stopped, then
recovered) from false_touch (stopped, never recovered) on the banked 0116/0117 train labels?

Method + kill rule: diagnostics/research/explore/2026-11-19_stop_conformance_and_fall_discriminator.md (committed first).
Firewall: every feature uses bars <= stop time (the last session strictly before exit_date). Train only: entry and stop
time both <= 2024-06-30.

    python pipelines/diagnostics/explore_fall_discriminator.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"), str(ROOT / "pipelines" / "diagnostics")]
from nq.brain.portfolio import cluster_bootstrap_two_sample  # noqa: E402

CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
M150 = ROOT / "diagnostics" / "research" / "benchmarks" / "tri" / "nifty_midcap_150_tri.csv"
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_fall_discriminator.json"
EXPORT = ROOT / ".cache" / "fall_discriminator" / "replica_inputs"
LO, HI = "2019-01-01", "2024-06-30"
BETA_N, MIN_LEG, DELIV_N, EARN_N = 126, 5, 60, 5


def col(df, *names):
    for n in names:
        if n in df:
            return df[n]
    raise KeyError(names)


def main() -> int:
    import config
    from run_bhanushali_path1 import corrected_universe
    d = pd.read_parquet(CTX)
    d["entry_date"], d["exit_date"] = pd.to_datetime(d["entry_date"]), pd.to_datetime(d["exit_date"])
    d = d[(d["entry_date"] >= LO) & (d["entry_date"] <= HI)]
    d = d[(d["noise_stop"] == True) | (d["false_touch"] == True)].copy()  # noqa: E712
    d["cohort"] = np.where(d["noise_stop"] == True, "noise_stop", "false_touch")  # noqa: E712
    n0 = d["cohort"].value_counts().to_dict()
    u = corrected_universe()
    cut = pd.Timestamp(HI)
    px = {}
    for t, df in u.items():
        ix = pd.DatetimeIndex(df.index).normalize()
        f = pd.DataFrame({"o": col(df, "open", "Open").to_numpy(float), "c": col(df, "close", "Close").to_numpy(float)}, index=ix)
        f = f[~f.index.duplicated(keep="last")].sort_index()
        px[t] = f[f.index <= cut]                                     # nothing past the train cut is ever loaded
    m = pd.read_csv(M150, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    m = m[m.index <= cut]
    rm = m.pct_change()
    # sector EW (excluding the ticker): sums and counts of daily close returns by SECTOR_MAP label
    rets = pd.DataFrame({t: f["c"].pct_change() for t, f in px.items()})
    sec = {t: config.SECTOR_MAP.get(t, "Others") for t in rets.columns}
    sec_sum, sec_cnt = {}, {}
    for s in set(sec.values()):
        cols = [t for t in rets.columns if sec[t] == s]
        sec_sum[s] = rets[cols].sum(axis=1, min_count=1)
        sec_cnt[s] = rets[cols].notna().sum(axis=1)
    dv = pd.read_parquet(ROOT / "data" / "_delivery_raw.parquet")
    dv = dv[(dv["series"] == "EQ") & (dv["date"] <= cut)]
    dv = {s: g.set_index(pd.DatetimeIndex(g["date"]).normalize())["deliv_pct"].sort_index() for s, g in dv.groupby("symbol")}
    ea = pd.read_parquet(ROOT / "data" / "_earnings_raw.parquet")
    ea = ea[ea["purpose"].str.contains("Financial Results", case=False, na=False)].copy()
    ea["ev"] = pd.to_datetime(ea["event_date"], format="%d-%b-%Y", errors="coerce")
    ea = {s: np.sort(g["ev"].dropna().unique()) for s, g in ea.groupby("symbol")}

    rows, drop = [], {"no_prices": 0, "stop_after_cut": 0, "short_history": 0}
    for r in d.itertuples():
        f = px.get(r.ticker)
        if f is None or not len(f):
            drop["no_prices"] += 1
            continue
        before = f.index[f.index < r.exit_date.normalize()]
        if not len(before) or before[-1] > cut:
            drop["stop_after_cut"] += 1
            continue
        st = before[-1]
        if pd.Timestamp(r.exit_date) > cut + pd.Timedelta(days=7):
            drop["stop_after_cut"] += 1
            continue
        seg = f[(f.index >= r.entry_date.normalize()) & (f.index <= st)]
        pre = f[f.index < r.entry_date.normalize()]
        if len(seg) < 2 or len(pre) < BETA_N + 1:
            drop["short_history"] += 1
            continue
        rs = f["c"].pct_change()
        pre_ix = pre.index[-BETA_N:]
        x, y = rm.reindex(pre_ix), rs.reindex(pre_ix)
        ok = x.notna() & y.notna()
        beta = float(np.cov(y[ok], x[ok], ddof=1)[0, 1] / np.var(x[ok], ddof=1)) if ok.sum() > 20 else np.nan
        s_lab = sec[r.ticker] if r.ticker in sec else "Others"
        own = rets[r.ticker] if r.ticker in rets else pd.Series(dtype=float)
        if s_lab != "Others" and int(sec_cnt[s_lab].reindex(pre_ix).median()) >= 6:
            rsec = (sec_sum[s_lab] - own.fillna(0)) / (sec_cnt[s_lab] - own.notna().astype(int)).replace(0, np.nan)
            sec_src = s_lab
        else:
            rsec, sec_src = rm, "M150_fallback"
        xs = rsec.reindex(pre_ix)
        oks = xs.notna() & y.notna()
        beta_s = float(np.cov(y[oks], xs[oks], ddof=1)[0, 1] / np.var(xs[oks], ddof=1)) if oks.sum() > 20 else np.nan
        pk = seg["c"].idxmax()
        if pk == st:
            pk = seg.index[0]
        leg = f.index[(f.index > pk) & (f.index <= st)]
        r_leg = float(f.loc[st, "c"] / f.loc[pk, "c"] - 1)
        rm_leg = float(np.prod(1 + rm.reindex(leg).fillna(0.0)) - 1)
        rsec_leg = float(np.prod(1 + rsec.reindex(leg).fillna(0.0)) - 1)
        a = r_leg - beta * rm_leg
        b = r_leg - beta_s * rsec_leg
        cc = np.nan
        if len(leg) >= MIN_LEG:
            yl, xl = rs.reindex(leg), rm.reindex(leg)
            okl = yl.notna() & xl.notna()
            if okl.sum() >= MIN_LEG and yl[okl].var() > 0:
                eps = yl[okl] - beta * xl[okl]
                cc = float(np.clip(1 - eps.var() / yl[okl].var(), -1, 1))
        dd = np.nan
        g = dv.get(r.ticker)
        if g is not None and st in g.index:
            hist = g[g.index < st].iloc[-DELIV_N:]
            if len(hist) >= 20 and hist.median() > 0:
                dd = float(g.loc[st] / hist.median())
        ee = np.nan
        evs = ea.get(r.ticker)
        if evs is not None:
            last5 = f.index[f.index <= st][-EARN_N:]
            ee = float(bool(((evs >= np.datetime64(last5[0])) & (evs <= np.datetime64(st))).any()))
        else:
            ee = 0.0
        risk = float(r.entry - r.stop)
        rows.append({"ticker": r.ticker, "cohort": r.cohort, "entry_date": r.entry_date, "stop_time": st, "peak": pk,
                     "leg_sessions": int(len(leg)), "beta_m150": beta, "a_mkt_adj": a, "b_sec_adj": b, "sector_source": sec_src,
                     "c_mkt_share": cc, "d_deliv_ratio": dd, "e_results_5s": ee,
                     "post_R21": float(r.post_ret21 * r.exit_px / risk) if risk > 0 and r.post_ret21 == r.post_ret21 else np.nan,
                     "R": float(r.R)})
    f_ = pd.DataFrame(rows)
    out = {"cohorts_train_labelled": n0, "dropped": drop, "n_used": f_["cohort"].value_counts().to_dict(),
           "sector_note": "config.SECTOR_MAP is a present-day map, NOT point-in-time; sector EW from corrected_universe "
                          "names excluding the ticker; Others / <6 names -> M150",
           "earnings_note": "results day = board-meeting event_date (ann_ts timestamps the intimation, not the release) [assumed]"}
    feats = {"a_mkt_adj": "a) leg return - beta x M150 leg return", "b_sec_adj": "b) leg return - beta_sec x sector leg return",
             "c_mkt_share": "c) 1 - idiosyncratic variance share over the leg", "d_deliv_ratio": "d) delivery % on stop day / 60d median",
             "e_results_5s": "e) results board meeting within 5 sessions up to the stop"}
    res = {}
    ns, ft = f_[f_.cohort == "noise_stop"], f_[f_.cohort == "false_touch"]
    for k, lab in feats.items():
        pt, lo, hi = cluster_bootstrap_two_sample(ns[k], ns["ticker"], ft[k], ft["ticker"], n_boot=2000, seed=20261119)
        res[k] = {"label": lab, "noise_stop_mean": round(float(ns[k].mean()), 4), "false_touch_mean": round(float(ft[k].mean()), 4),
                  "n_noise": int(ns[k].notna().sum()), "n_false": int(ft[k].notna().sum()),
                  "diff_false_minus_noise": round(pt, 4), "ci95": [round(lo, 4), round(hi, 4)],
                  "excludes_zero": bool(lo > 0 or hi < 0)}
    out["features"] = res
    out["kill_rule"] = ("all CIs straddle zero -> no exploration-lane candidate (bound, not KILL)"
                        if not any(v["excludes_zero"] for v in res.values())
                        else "candidates for the January exploration lane: " + ", ".join(k for k, v in res.items() if v["excludes_zero"]))
    sd = float(f_["a_mkt_adj"].std(ddof=1))
    skip = f_["a_mkt_adj"].abs() > sd
    h = f_[skip]
    out["hindsight_bound"] = {"rule": "keep the stop only when |a| <= 1 SD (pooled); otherwise hold; R = post_ret21 x exit_px / risk",
                              "sd_a": round(sd, 4), "n_skipped": int(skip.sum()),
                              "skipped_by_cohort": h["cohort"].value_counts().to_dict(),
                              "R_noise_stop": round(float(h.loc[h.cohort == "noise_stop", "post_R21"].sum()), 1),
                              "R_false_touch": round(float(h.loc[h.cohort == "false_touch", "post_R21"].sum()), 1),
                              "R_net": round(float(h["post_R21"].sum()), 1),
                              "R_net_by_stop_year": {int(y): round(float(v), 1) for y, v in h.groupby(h["stop_time"].dt.year)["post_R21"].sum().items()},
                              "caveat": "hindsight twice over (labels and post_ret21 look past the stop); upper bound for this rule, not a backtest"}
    EXPORT.mkdir(parents=True, exist_ok=True)
    f_[["ticker", "cohort", "entry_date", "stop_time"]].to_csv(EXPORT / "trades.csv", index=False)
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    f_.to_csv(ROOT / ".cache" / "fall_discriminator" / "features.csv", index=False)
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
