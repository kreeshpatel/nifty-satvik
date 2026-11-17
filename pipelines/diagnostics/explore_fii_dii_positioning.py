"""EXPLORE (tier 0, descriptive): does institutional positioning see anything the book's trades do not?

Owner approval 2026-11-17 of the FII/DII backlog entry. Dataset A only (entries 2019-01-01..2024-06-30, prices cut at
2024-06-30 and the cut asserted). No trial, no screen row, no sealed read, nothing live changes. It adopts nothing:
any rule out of it would need its own pre-registration and its own trial.

**The data is not what the backlog spec assumed, and the difference matters.** The spec asked for NSE's daily FII/DII
*cash* net buy/sell figures. Those are not programmatically retrievable as history: the NSE endpoint serves only the
current day and ignores a date parameter, and both archive filename patterns 404 for past dates
(see pipelines/diagnostics/fetch_nse_participant_flows.py). What IS retrievable as a dated daily archive is the
participant-wise open interest file (fao_participant_oi_DDMMYYYY.csv), which is **derivatives POSITIONING**, not cash
flows: how many index-future, stock-future and option contracts FIIs, DIIs, proprietary desks and clients hold long
and short at each day's close. It is a genuine point-in-time series with its own publication date, so it can be
measured honestly, but it answers a different question and every table here is labelled accordingly.

Features, all trailing, read at the signal Friday (the last session on or before it):
  fii_idx_net, dii_idx_net     index futures long minus short, in contracts (the classic positioning gauge)
  fii_stk_net                  stock futures long minus short
  *_chg20                      the 20-session change in that net, i.e. the flow rather than the level
  z(x)                         the z-score of x over the trailing 252 sessions, computed point-in-time

Reported for every live-configuration trade in A: mean R per closed trade, total R, runner share and stop-out rate by
z-bucket (<-1, -1..0, 0..+1, >+1), cross-tabbed with the loss-diagnosis regime state (Nifty vs its 40-week SMA, VIX
bucket, midcap-breadth bucket), and by year so one episode is visible. Plus the correlation of each positioning
feature with the regime variables already in hand: if it is the same information as VIX or breadth, that is the
finding.

    python pipelines/diagnostics/explore_fii_dii_positioning.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
import diag_giveback_ratchet_0148 as G  # noqa: E402
import diag_loss_diagnosis_2026_11 as D  # noqa: E402
from nq.lab.stats import cluster_bootstrap_mean  # noqa: E402

OI = ROOT / "data" / "nse_participant_oi.csv"
OUT_MD = ROOT / "diagnostics" / "research" / "explore" / "2026-11-17_fii_dii_positioning.md"
OUT_JSON = OUT_MD.with_suffix(".json")
ZB = [-np.inf, -1, 0, 1, np.inf]
ZL = ["z<-1", "-1..0", "0..+1", "z>+1"]
FEATS = ["fii_idx_net", "fii_idx_net_chg20", "dii_idx_net", "dii_idx_net_chg20",
         "fii_stk_net", "fii_stk_net_chg20", "combined_idx_net", "combined_idx_net_chg20"]


def build_positioning() -> pd.DataFrame:
    """Daily positioning levels, their 20-session changes, and point-in-time 252-session z-scores."""
    raw = pd.read_csv(OI)
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw[raw["date"] <= pd.Timestamp(G.CUT)]
    w = raw.pivot_table(index="date", columns="client_type",
                        values=["future_index_long", "future_index_short", "future_stock_long", "future_stock_short"])
    d = pd.DataFrame(index=w.index.sort_values())
    for who, tag in (("FII", "fii"), ("DII", "dii")):
        d[f"{tag}_idx_net"] = w[("future_index_long", who)] - w[("future_index_short", who)]
        d[f"{tag}_stk_net"] = w[("future_stock_long", who)] - w[("future_stock_short", who)]
    d["combined_idx_net"] = d.fii_idx_net + d.dii_idx_net
    for c in [c for c in d.columns]:
        d[f"{c}_chg20"] = d[c] - d[c].shift(20)
    for c in FEATS:
        m, s = d[c].rolling(252, min_periods=126).mean(), d[c].rolling(252, min_periods=126).std()
        d[f"z_{c}"] = (d[c] - m) / s.replace(0, np.nan)
    return d


def at_friday(d: pd.DataFrame, fridays: pd.Series) -> pd.DataFrame:
    """As-of read: the last published session on or before each signal Friday. No forward fill past the Friday."""
    idx = d.index.searchsorted(pd.DatetimeIndex(fridays), side="right") - 1
    out = pd.DataFrame(index=range(len(fridays)))
    for c in d.columns:
        v = np.where(idx >= 0, d[c].values[np.clip(idx, 0, None)], np.nan)
        out[c] = v
    return out


def clustered(g: pd.DataFrame) -> dict:
    """Mean R over closed trades with an interval clustered on the ENTRY WEEK (audit 2026-11-17).

    Trades entered in the same week share a market, a regime state and one flow reading, so an interval over trades
    would treat dependent observations as independent and come out far too narrow. The cluster bootstrap in
    nq.lab.stats resamples whole entry weeks instead.
    """
    c = g[g.closed]
    r = cluster_bootstrap_mean(c.R.values, c.entry_week.values)
    return {"mean_R_ci95": None if r["ci95"] is None else [round(r["ci95"][0], 3), round(r["ci95"][1], 3)],
            "n_entry_weeks": r["n_clusters"]}


def ci_txt(r: dict) -> str:
    return "—" if r.get("mean_R_ci95") is None else f"[{r['mean_R_ci95'][0]:+.2f}, {r['mean_R_ci95'][1]:+.2f}]"


def bucket_rows(dd: pd.DataFrame, col: str) -> list[dict]:
    rows = []
    for b in ZL:
        g = dd[dd[col] == b]
        if not len(g):
            continue
        m = D.trade_metrics(g)
        rows.append({"bucket": b, "n": m["n"], "n_closed": m["n_closed"], "mean_R": m["avg_R_closed"],
                     **clustered(g),
                     "total_R": m["total_R"], "runner_pct": m["runner_pct"], "full_stop_pct": m["full_stop_pct_closed"],
                     "win_pct": m["win_pct"]})
    return rows


def main() -> int:
    pos = build_positioning()
    cut, P, mem, nifty, run = D.build_A()
    _, led = run(True)
    led = led.reset_index(drop=True)
    d = pd.DataFrame({"tkr": led.tkr, "entry_date": pd.to_datetime(led.entry_date), "entry": led.entry,
                      "stop0": led.stop0, "reason": led.reason, "R": led.R.astype(float),
                      "weeks": led.held_weeks.astype(float)})
    d["closed"] = d.reason != "eos"
    d["signal_friday"] = [D.signal_friday(x) for x in d.entry_date]
    d["year"] = d.entry_date.dt.year
    d["entry_week"] = d.signal_friday.astype(str)   # the cluster: one market week, one flow reading

    macro = pd.read_parquet(ROOT / "data" / "macro_pit.parquet")
    vix = macro.set_index(pd.to_datetime(macro["date"]))["vix_level"].dropna()
    vix = vix[vix.index <= pd.Timestamp(G.CUT)]
    fridays = pd.date_range("2018-06-01", G.CUT, freq="W-FRI")
    reg = D.regime_tables(nifty, vix, D.midcap_breadth(cut, mem, fridays))
    d = D.tag(d, reg)

    ap = at_friday(pos, d.signal_friday)
    for c in ap.columns:
        d[c] = ap[c].values
    for f in FEATS:
        d[f"b_{f}"] = pd.cut(d[f"z_{f}"], ZB, labels=ZL).astype(str)

    res: dict = {"tier": "EXPLORE", "dataset": "A only (entries 2019-01-01..2024-06-30, prices cut 2024-06-30)",
                 "instrument": "NSE participant-wise F&O open interest — institutional POSITIONING, not cash flows",
                 "source_note": "NSE cash FII/DII daily history is not programmatically retrievable; see "
                                "pipelines/diagnostics/fetch_nse_participant_flows.py",
                 "coverage": {"sessions": int(len(pos)), "from": str(pos.index.min().date()),
                              "to": str(pos.index.max().date()),
                              "trades": int(len(d)), "trades_with_a_reading": int(d["z_fii_idx_net"].notna().sum())},
                 "by_bucket": {}, "by_bucket_and_regime": {}, "by_year": {}, "correlations": {}}

    md = ["# 2026-11-17 — Institutional positioning (FII / DII) against the book's trades",
          "",
          "**Tier:** EXPLORE, descriptive. Dataset A only — entries 2019-01-01..2024-06-30, prices cut at 2024-06-30 "
          "and the cut asserted. No trial, no screen row, **no sealed read**, nothing live changed. Standing counts "
          "unchanged. It adopts nothing: any rule out of it needs its own pre-registration and its own trial.",
          "",
          "## The instrument is not the one the backlog spec assumed",
          "",
          "The spec asked for NSE's daily FII/DII **cash** net buy/sell figures. Those are not retrievable as history: "
          "the NSE endpoint serves the current day and ignores a date parameter, and both archive filename patterns "
          "404 for past dates. What is retrievable, as a dated daily archive with its own publication date, is the "
          "**participant-wise open-interest** file — institutional **positioning** in index futures, stock futures and "
          "options, not cash flows. It is point-in-time and honest, and it answers a different question. Every table "
          "below is about positioning.",
          "",
          f"Coverage: **{len(pos)} sessions**, {pos.index.min().date()} to {pos.index.max().date()}; "
          f"**{len(d)} trades** in A, {int(d['z_fii_idx_net'].notna().sum())} of them with a reading at the signal "
          "Friday (the rest are before the 126-session minimum for a z-score).", ""]

    # ---- headline: by bucket, each feature
    md += ["## Mean R per closed trade by positioning z-bucket, at the signal Friday", ""]
    for f in FEATS:
        rows = bucket_rows(d, f"b_{f}")
        res["by_bucket"][f] = rows
        md += [f"**{f}** — z over the trailing 252 sessions", "",
               D.md_table([{**r, "ci": ci_txt(r)} for r in rows],
                          ["bucket", "n", "n_closed", "mean_R", "ci", "n_entry_weeks", "total_R", "full_stop_pct", "win_pct"],
                          ["z bucket", "trades", "closed", "mean R", "95% CI (clustered on entry week)", "weeks",
                           "total R", "stop-out %", "win %"]), ""]

    # ---- the headline feature crossed with the regime state from the loss diagnosis
    key = "fii_idx_net"
    md += ["## The headline feature crossed with the regime state", "",
           "`fii_idx_net` (FII index-futures long minus short) against the three regime dimensions from the "
           "2026-11 loss diagnosis. The weak-but-calm state is `above` / `<15` / `>60%`.", ""]
    for dim in ("nifty_vs_40w", "vix_bucket", "breadth_bucket"):
        rows = []
        for v in sorted(x for x in d[dim].dropna().unique() if x != "nan"):
            for b in ZL:
                g = d[(d[dim] == v) & (d[f"b_{key}"] == b)]
                if len(g) < 5:
                    continue
                m = D.trade_metrics(g)
                rows.append({"state": v, "bucket": b, "n": m["n"], "mean_R": m["avg_R_closed"], **clustered(g),
                             "total_R": m["total_R"], "full_stop_pct": m["full_stop_pct_closed"]})
        res["by_bucket_and_regime"][dim] = rows
        md += [f"**{dim}** (cells with fewer than 5 trades are dropped)", "",
               D.md_table([{**r, "ci": ci_txt(r)} for r in rows],
                          ["state", "bucket", "n", "mean_R", "ci", "n_entry_weeks", "total_R", "full_stop_pct"],
                          [dim, "z bucket", "trades", "mean R", "95% CI (clustered)", "weeks", "total R", "stop-out %"]), ""]

    # ---- by year
    rows = []
    for y in sorted(d.year.unique()):
        for b in ZL:
            g = d[(d.year == y) & (d[f"b_{key}"] == b)]
            if len(g) < 5:
                continue
            m = D.trade_metrics(g)
            rows.append({"year": int(y), "bucket": b, "n": m["n"], "mean_R": m["avg_R_closed"], **clustered(g),
                         "total_R": m["total_R"]})
    res["by_year"][key] = rows
    md += ["## By year, so one episode is visible", "",
           D.md_table([{**r, "ci": ci_txt(r)} for r in rows], ["year", "bucket", "n", "mean_R", "ci", "total_R"],
                      ["year", "z bucket", "trades", "mean R", "95% CI (clustered)", "total R"]), ""]

    # ---- is it the same information as what we already have?
    wk = pd.DataFrame(index=reg.index)
    pf = at_friday(pos, pd.Series(reg.index))
    for f in FEATS:
        wk[f"z_{f}"] = pf[f"z_{f}"].values
    wk["vix"] = reg.vix.values
    wk["breadth_pct"] = reg.breadth_pct.values
    wk["ret13_pct"] = reg.ret13_pct.values
    wk["above_40w"] = reg.above_40w.astype(float).values
    corr = wk.dropna().corr(method="spearman")
    rows = [{"feature": f, "vs_vix": round(float(corr.loc[f"z_{f}", "vix"]), 3),
             "vs_breadth": round(float(corr.loc[f"z_{f}", "breadth_pct"]), 3),
             "vs_ret13": round(float(corr.loc[f"z_{f}", "ret13_pct"]), 3),
             "vs_above_40w": round(float(corr.loc[f"z_{f}", "above_40w"]), 3)} for f in FEATS]
    res["correlations"] = {"method": "spearman, weekly at the signal Friday", "n_weeks": int(len(wk.dropna())),
                           "rows": rows}
    md += ["## Is this the same information we already have?", "",
           f"Spearman correlation, weekly at the signal Friday, {len(wk.dropna())} weeks.", "",
           D.md_table(rows, ["feature", "vs_vix", "vs_breadth", "vs_ret13", "vs_above_40w"],
                      ["feature", "vs VIX", "vs midcap breadth", "vs Nifty 13w return", "vs above 40w SMA"]), ""]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD.name} and {OUT_JSON.name}")
    for f in FEATS[:4]:
        print(f, [(r["bucket"], r["n"], r["mean_R"]) for r in res["by_bucket"][f]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
