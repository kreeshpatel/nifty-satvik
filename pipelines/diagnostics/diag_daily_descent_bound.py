"""0144 — daily-resolution descent. ACTIVATION BOUND (ledger row #20). No trial.

Pre-registration: `diagnostics/research/preregistry/0144-daily-descent-bound.md`. Every definition, the
cohort thresholds, the management set and the gate are frozen there and are not re-opened here.

The owner's observation: *"when the stock is extensively down on the daily charts, the trade goes to SL."*

0127 measured that archetype on WEEKLY bars and closed both responses — excluding the cohort COSTS
1.92 R/yr, and managing it differently gains 0.0 R/yr with perfect hindsight. What it could not answer
is whether a **daily** measure separates the weekly cohort, which is the only new question here:

  (a) EXCLUSION            — re-run at daily resolution, for comparability with 0127
  (b) CONDITIONAL MGMT     — same, on 0127's FROZEN management set (imported, not re-typed)
  (c) DOES DAILY SPLIT WEEKLY? — the 2x2, and the clairvoyant conditional gain of the daily split
                             computed INSIDE the weekly cohort

Both re-run bounds are deliberately inflated (uncapped population, favourable excursion ordering): a
bound whose purpose is to fail should fail on the friendliest ground available.

TRAIN ONLY: `entry_date <= 2024-06-30`, enforced by `nq.brain.io.assert_unsealed`. The sealed 2024H2+
slice is not read.

    python pipelines/diagnostics/diag_daily_descent_bound.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipelines" / "diagnostics"))

from diag_hegclass_bound_0127 import (  # noqa: E402 — 0127's frozen machinery, imported not re-typed
    PEAK_LOOKBACK, PRIMARY as WEEKLY_PRIMARY, apply_management, descent_features, md_table,
    per_year_sign,
)
from nq.brain.io import assert_unsealed  # noqa: E402
from nq.brain.portfolio import cluster_bootstrap_two_sample  # noqa: E402
from nq.data.weekly import build_weekly_panel  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# ---- FROZEN (pre-reg §1). No sweep anywhere in this file. ----
DAILY_LOOKBACK = 63             # sessions searched for the pre-signal daily peak
SMA_LEN = 50                    # the daily line `days_below_50dma` counts against
PRIMARY_DD = 20.0               # THE decision cohort: dd63 >= 20%
ROBUSTNESS_DD = [15.0, 25.0]    # reported, never used to choose
ROBUSTNESS_COMBO = (20.0, 32)   # dd63 >= 20% AND days_below_50dma >= 32
START, TRAIN_END = pd.Timestamp("2019-01-01"), pd.Timestamp("2024-06-30")
FLOOR_R_PER_YR = 10.0           # 0109 / 0117 path-noise floor
BAD_DROP, BAD_JUMP = -0.45, 0.90   # unadjusted-split guard (DATA_BUG_unadjusted_splits.md)

OUT_JSON = ROOT / "diagnostics" / "research" / "daily_descent_bound_0144.json"
OUT_MD = ROOT / "diagnostics" / "research" / "daily_descent_bound_0144.md"


def daily_features(ohlcv: dict, tr: pd.DataFrame) -> pd.DataFrame:
    """dd63 / sessions_since_peak63 / days_below_50dma / daily_velocity at the DECISION bar.

    PIT by construction: every window ends at the last session STRICTLY BEFORE the entry date, because
    the fill is at that entry session's open.
    """
    rows = []
    for tkr, sub in tr.groupby("ticker", sort=False):
        df = ohlcv.get(tkr)
        if df is None or len(df) < DAILY_LOOKBACK + SMA_LEN:
            continue
        idx = pd.DatetimeIndex(df.index).normalize()
        high = df["High"].to_numpy(float)
        close = df["Close"].to_numpy(float)
        sma = pd.Series(close).rolling(SMA_LEN).mean().to_numpy()
        for row_id, t in sub.iterrows():
            k = int(idx.searchsorted(pd.Timestamp(t["entry_date"]).normalize()))   # first bar >= entry
            if k < DAILY_LOOKBACK + SMA_LEN or k >= len(idx):
                continue
            w_hi = high[k - DAILY_LOOKBACK:k]                                      # strictly before entry
            w_cl = close[k - DAILY_LOOKBACK:k]
            w_sma = sma[k - DAILY_LOOKBACK:k]
            if not np.isfinite(w_hi).any() or not np.isfinite(w_cl[-1]):
                continue
            j = int(np.nanargmax(w_hi))
            peak = float(w_hi[j])
            if not peak > 0:
                continue
            mv = w_cl[1:] / w_cl[:-1] - 1.0
            if np.any(mv <= BAD_DROP) or np.any(mv >= BAD_JUMP):
                continue          # an unadjusted split inside the window is not a drawdown (B4)
            dd = 100.0 * (peak - float(w_cl[-1])) / peak
            since = DAILY_LOOKBACK - j
            below = int(np.nansum(w_cl < w_sma))
            rows.append(dict(row=row_id, dd63=round(dd, 3), sessions_since_peak63=since,
                             days_below_50dma=below,
                             daily_velocity=round(dd / since, 4) if since else np.nan))
    return pd.DataFrame(rows).set_index("row")


def weekly_depth_pit(panel: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """0127's descent features, with the depth measured to the LAST COMPLETED week before entry.

    THE DEFECT THIS REPLACES. `diag_hegclass_bound_0127.descent_features` takes
    `k = searchsorted(week_end, entry_date)` and measures the depth to `cl[k]` — the close of the week
    CONTAINING the entry, a median 4 days (up to 5 sessions) AFTER the fill, which is that day's open.
    A trade that falls in its first week is therefore labelled into the cohort BY ITS OWN OUTCOME: the
    shipped cohort's mean entry-week return is −2.73% against +0.85% for the rest. Found by the red-team
    read of this study, 2026-09-25; it is 0127's instrument, inherited here through the import.

    This version uses `cl[k-1]`, everything else identical, and is the one every conclusion reads.
    """
    rows = []
    for tkr, g in panel.groupby("ticker", sort=False):
        sub = tr[tr["ticker"] == tkr]
        if sub.empty:
            continue
        g = g.sort_values("week_end", kind="mergesort")
        we = g["week_end"].to_numpy()
        hi, cl = g["h"].to_numpy(float), g["c"].to_numpy(float)
        for idx, row in sub.iterrows():
            k = int(np.searchsorted(we, np.datetime64(row["entry_date"])))
            if k < PEAK_LOOKBACK + 1 or k >= len(we):
                continue
            w = hi[k - PEAK_LOOKBACK:k]
            if not np.isfinite(w).any():
                continue
            j = int(np.nanargmax(w))
            peak = float(w[j])
            prev_close = float(cl[k - 1])                 # the last COMPLETED week before the fill
            if not (peak > 0) or not np.isfinite(prev_close):
                continue
            dur = PEAK_LOOKBACK - j
            dep = 100.0 * (peak - prev_close) / peak
            rows.append(dict(row=idx, pit_descent_duration=dur, pit_descent_depth=round(dep, 3)))
    return pd.DataFrame(rows).set_index("row")


def _gap(d: pd.DataFrame, hot: pd.Series) -> dict:
    """The cohort-minus-rest gap with its own interval. The first version reported bare means."""
    pt, lo, hi = cluster_bootstrap_two_sample(d.loc[~hot, "R"], d.loc[~hot, "ticker"],
                                              d.loc[hot, "R"], d.loc[hot, "ticker"],
                                              n_boot=2000, seed=20260925)
    return {"cohort_minus_rest_R": round(pt, 3), "ci": [round(lo, 3), round(hi, 3)],
            "excludes_zero": bool(lo > 0 or hi < 0)}


def _bounds(d: pd.DataFrame, hot: pd.Series, span: float, label: str) -> dict:
    """The two 0127 bounds for any cohort mask, so daily and weekly are computed by ONE code path."""
    coh, rest = d[hot], d[~hot]
    out: dict = {"definition": label, "N": int(hot.sum()),
                 "share_of_trades_pct": round(100.0 * float(hot.mean()), 1)}
    if coh.empty or rest.empty:
        return out
    out.update(cohort_meanR=round(float(coh["R"].mean()), 3), rest_meanR=round(float(rest["R"].mean()), 3),
               cohort_win_pct=round(100.0 * float((coh["R"] > 0).mean()), 1),
               rest_win_pct=round(100.0 * float((rest["R"] > 0).mean()), 1),
               cohort_total_R=round(float(coh["R"].sum()), 1),
               share_of_book_R_pct=round(100.0 * float(coh["R"].sum() / d["R"].sum()), 1))
    refused = float(coh["R"].sum()) / span
    clair = -float(coh[coh["R"] < 0]["R"].sum()) / span
    out["gap_vs_rest"] = _gap(d, hot)
    out["bound_a_exclusion"] = {
        "R_per_yr_refused": round(refused, 2),
        "interpretation": ("refusing the cohort COSTS this much R/yr (positive-EV cohort)" if refused > 0
                           else "refusing the cohort SAVES this much R/yr"),
        "clairvoyant_refuse_only_losers_R_per_yr": round(clair, 2),
        "note": "the clairvoyant leg is an unreachable ceiling (perfect foresight on which lose) and "
                "ignores redeployment, which 0121 measured as the dominant term",
        "clears_floor": bool(abs(refused) >= FLOOR_R_PER_YR and refused < 0),
        "per_year": per_year_sign(coh, coh["R"].to_numpy(float), coh["entry_date"].dt.year),
    }
    mgmt = apply_management(d)
    tot_all, tot_coh, tot_rest = mgmt.sum(), mgmt[hot].sum(), mgmt[~hot].sum()
    best_all, best_coh, best_rest = tot_all.idxmax(), tot_coh.idxmax(), tot_rest.idxmax()
    gain = float(tot_coh[best_coh] + tot_rest[best_rest] - tot_all[best_all])
    out["bound_b_conditional_management"] = {
        "management_totals_R": {k: round(float(v), 1) for k, v in tot_all.items()},
        "cohort_totals_R": {k: round(float(v), 1) for k, v in tot_coh.items()},
        "best_single_for_all": best_all, "best_for_cohort": best_coh, "best_for_rest": best_rest,
        "clairvoyant_conditional_gain_R": round(gain, 1),
        "clairvoyant_conditional_gain_R_per_yr": round(gain / span, 2),
        "clears_floor": bool(gain / span >= FLOOR_R_PER_YR),
    }
    return out


def main() -> None:
    tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    tr = tr[tr["setup"] == "touch44"].copy()
    tr["entry_date"] = pd.to_datetime(tr["entry_date"])
    tr = tr[(tr["entry_date"] >= START) & (tr["entry_date"] <= TRAIN_END)].copy()
    assert_unsealed(tr["entry_date"])          # train only; the sealed slice is not read

    ohlcv = corrected_universe()
    daily = daily_features(ohlcv, tr)
    panel = build_weekly_panel(ohlcv).assign(week_end=lambda x: pd.to_datetime(x["week_end"]))
    weekly_leaked = descent_features(panel, tr)          # 0127's, kept ONLY as the defect exhibit
    weekly_pit = weekly_depth_pit(panel, tr)             # the one every conclusion reads
    d = tr.join(daily, how="inner").join(weekly_leaked, how="left").join(weekly_pit, how="left")
    d = d.dropna(subset=["dd63", "R"]).copy()
    span = max((d["entry_date"].max() - d["entry_date"].min()).days / 365.25, 1e-9)

    res: dict = {
        "_doc": "0144 daily-resolution descent activation bound (ledger #20; 0 trials; train only).",
        "prereg": "diagnostics/research/preregistry/0144-daily-descent-bound.md",
        "population": f"uncapped substrate, setup=touch44, entry_date in [{START.date()}, {TRAIN_END.date()}]",
        "n_trades": int(len(d)), "span_years": round(span, 2),
        "total_R": round(float(d["R"].sum()), 1),
        "total_R_per_yr": round(float(d["R"].sum()) / span, 1),
        "floor_R_per_yr": FLOOR_R_PER_YR,
        "daily_quartiles": {c: [round(float(d[c].quantile(q)), 2) for q in (.25, .5, .75)]
                            for c in ("dd63", "sessions_since_peak63", "days_below_50dma", "daily_velocity")},
    }

    # ---- (a) + (b): the daily cohort, and the robustness rows (reported, never used to choose) ----
    res["daily_primary"] = _bounds(d, d["dd63"] >= PRIMARY_DD, span, f"dd63 >= {PRIMARY_DD:.0f}%")
    res["daily_robustness"] = {
        **{f"dd63>={x:.0f}%": _bounds(d, d["dd63"] >= x, span, f"dd63 >= {x:.0f}%") for x in ROBUSTNESS_DD},
        f"dd63>={ROBUSTNESS_COMBO[0]:.0f}% & below50dma>={ROBUSTNESS_COMBO[1]}":
            _bounds(d, (d["dd63"] >= ROBUSTNESS_COMBO[0]) & (d["days_below_50dma"] >= ROBUSTNESS_COMBO[1]),
                    span, "combo"),
    }

    # ---- 0127's WEEKLY cohort, recomputed on THIS train-only window for comparability ----
    wk_leaked = ((d["descent_duration"] >= WEEKLY_PRIMARY[0])
                 & (d["descent_depth"] >= WEEKLY_PRIMARY[1])).fillna(False)
    wk = ((d["pit_descent_duration"] >= WEEKLY_PRIMARY[0])
          & (d["pit_descent_depth"] >= WEEKLY_PRIMARY[1])).fillna(False)
    res["weekly_cohort_PIT"] = _bounds(
        d, wk, span, f">={WEEKLY_PRIMARY[0]}wk AND >={WEEKLY_PRIMARY[1]:.0f}% depth to the LAST COMPLETED week")
    res["weekly_cohort_0127_AS_SHIPPED_leaked"] = {
        **_bounds(d, wk_leaked, span, "0127's own definition — depth to the week CONTAINING the entry"),
        "_defect": ("LOOKAHEAD: the depth is measured a median 4 days after the fill, so a trade that "
                    "falls in its first week is selected into the cohort by its own outcome"),
        "cohort_entry_week_return_pct": round(float(d.loc[wk_leaked, "R"].notna().sum() and
                                                    d.loc[wk_leaked, "mae_first2wk"].mean()), 3),
    }

    # ---- (c) THE NEW LEG: does the daily view split the weekly cohort? ----
    dy = d["dd63"] >= PRIMARY_DD
    cells = []
    for wk_hot in (True, False):
        for dy_hot in (True, False):
            m = (wk == wk_hot) & (dy == dy_hot)
            cells.append(dict(weekly_hegclass=wk_hot, daily_cohort=dy_hot, N=int(m.sum()),
                              meanR=round(float(d[m]["R"].mean()), 3) if m.any() else None,
                              win_pct=round(100.0 * float((d[m]["R"] > 0).mean()), 1) if m.any() else None,
                              total_R=round(float(d[m]["R"].sum()), 1) if m.any() else None))
    # ---- the LOOKAHEAD, measured here rather than asserted ----
    # reproduce-before-trust: this evidence re-opens a published finding, so it must come from the
    # committed pipeline, not from a reviewer's scratchpad.
    lag_days, entry_week_ret = [], []
    for _, row in d.iterrows():
        g = panel[panel["ticker"] == row["ticker"]].sort_values("week_end", kind="mergesort")
        we = g["week_end"].to_numpy()
        k = int(np.searchsorted(we, np.datetime64(row["entry_date"])))
        if k >= len(we):
            lag_days.append(np.nan)
            entry_week_ret.append(np.nan)
            continue
        lag_days.append((pd.Timestamp(we[k]) - pd.Timestamp(row["entry_date"])).days)
        cl_k = float(g["c"].to_numpy(float)[k])
        entry_week_ret.append(100.0 * (cl_k / float(row["entry"]) - 1.0) if row["entry"] else np.nan)
    d["_leak_lag_days"] = lag_days
    d["_entry_week_return_pct"] = entry_week_ret
    res["lookahead_evidence"] = {
        "_what": ("0127's descent_depth is measured to cl[k], the close of the week CONTAINING the entry; "
                  "the fill is that day's OPEN, so the depth sees up to a full week of post-entry price"),
        "weekend_minus_entry_days": {
            "median": float(np.nanmedian(d["_leak_lag_days"])),
            "min": float(np.nanmin(d["_leak_lag_days"])),
            "share_non_negative": round(float((d["_leak_lag_days"] >= 0).mean()), 4),
        },
        "entry_week_return_pct": {
            "leaked_cohort_mean": round(float(d.loc[wk_leaked, "_entry_week_return_pct"].mean()), 3),
            "rest_mean": round(float(d.loc[~wk_leaked, "_entry_week_return_pct"].mean()), 3),
            "cell_weekly_hot_daily_cold_mean": (
                round(float(d.loc[wk_leaked & ~dy, "_entry_week_return_pct"].mean()), 3)
                if (wk_leaked & ~dy).any() else None),
            "_reads": "a cohort selected partly by what price did AFTER the fill",
        },
    }

    # ---- what dd63 actually is: correlations against columns the substrate already carries ----
    res["dd63_correlations"] = {
        c: round(float(d[["dd63", c]].dropna().corr().iloc[0, 1]), 3)
        for c in ("dist_52wh_pct", "ext_vs_sma", "risk_pct", "atr_pct") if c in d.columns
    }
    ext_gaps = []
    if "ext_vs_sma" in d.columns:
        bands = pd.cut(d["ext_vs_sma"], [-np.inf, 5, 10, 15, 25, np.inf])
        for b, g in d.groupby(bands, observed=True):
            hot_b = g["dd63"] >= PRIMARY_DD
            if hot_b.sum() >= 5 and (~hot_b).sum() >= 5:
                ext_gaps.append({"ext_band": str(b), "n_hot": int(hot_b.sum()),
                                 "gap": round(float(g[hot_b]["R"].mean() - g[~hot_b]["R"].mean()), 3)})
    res["dd63_gap_within_ext_bands"] = {
        "_what": "is dd63 just extension in disguise? ext is the known engine (EXT_IS_THE_ENGINE)",
        "bands": ext_gaps,
        "weighted_mean_gap": (round(float(np.average([x["gap"] for x in ext_gaps],
                                                     weights=[x["n_hot"] for x in ext_gaps])), 3)
                              if ext_gaps else None),
    }

    # ---- 0127's population: a DATE census only, no outcome column is read ----
    all_tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet",
                             columns=["setup", "entry_date"])
    all_tr = all_tr[all_tr["setup"] == "touch44"]
    all_tr["entry_date"] = pd.to_datetime(all_tr["entry_date"])
    as_0127 = all_tr[all_tr["entry_date"] >= START]
    sealed = as_0127[(as_0127["entry_date"] >= pd.Timestamp("2024-07-01"))
                     & (as_0127["entry_date"] <= pd.Timestamp("2026-06-30"))]
    res["population_0127_date_census"] = {
        "_what": ("0127 filters entry_date >= 2019 with NO upper bound. This is a census of DATES only "
                  "(no outcome column is read), reported because it bears on a governance decision"),
        "n_rows_0127_filter": int(len(as_0127)),
        "max_entry_date": str(as_0127["entry_date"].max().date()),
        "n_rows_in_sealed_window": int(len(sealed)),
        "share_sealed_pct": round(100.0 * len(sealed) / max(len(as_0127), 1), 1),
    }

    res["split_2x2"] = cells
    res["split_2x2_leaked_for_comparison"] = [
        dict(weekly_hegclass=w, daily_cohort=x,
             N=int(((wk_leaked == w) & (dy == x)).sum()),
             meanR=(round(float(d[(wk_leaked == w) & (dy == x)]["R"].mean()), 3)
                    if ((wk_leaked == w) & (dy == x)).any() else None))
        for w in (True, False) for x in (True, False)]
    inside = d[wk]
    if len(inside) > 10 and inside["dd63"].notna().any():
        res["does_daily_split_the_weekly_cohort"] = _bounds(
            inside, inside["dd63"] >= PRIMARY_DD, span,
            f"dd63 >= {PRIMARY_DD:.0f}% WITHIN the weekly HEG-class cohort")

    # The "worst cell" block that stood here is REMOVED, not fixed. It existed to bound the
    # weekly-hot/daily-cold cell, and under a point-in-time weekly depth that cell is EMPTY (N=0) — it
    # was an artifact of 0127's lookahead. Picking a cell by minimum mean was also post-hoc selection
    # over the four pre-registered cells (red-team B3), so there is nothing here worth keeping.
    res["worst_cell_exclusion_bound"] = {
        "_withdrawn": ("the cell this bounded (weekly HEG-class with no deep daily drawdown) contains 0 "
                       "trades once the weekly depth is point-in-time; it was selected by the lookahead"),
    }

    # Post-hoc sensitivity, labelled: the cohort earns a large share of its R in one year.
    hot_p = d["dd63"] >= PRIMARY_DD
    by_year = d[hot_p].groupby(d.loc[hot_p, "entry_date"].dt.year)["R"].sum()
    top_year = int(by_year.idxmax())
    ex = d[d["entry_date"].dt.year != top_year]
    ex_hot = ex["dd63"] >= PRIMARY_DD
    res["primary_sensitivity_drop_biggest_year"] = {
        "_selection": "POST HOC, and labelled: the year is chosen as the cohort's largest R contributor",
        "year_dropped": top_year,
        "share_of_cohort_R_from_that_year": round(float(by_year.max() / d[hot_p]["R"].sum()), 3),
        "cohort_meanR_ex": round(float(ex[ex_hot]["R"].mean()), 3),
        "rest_meanR_ex": round(float(ex[~ex_hot]["R"].mean()), 3),
        "gap_ex": _gap(ex, ex_hot),
    }

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    lines = [
        "# 0144 — daily-resolution descent: activation bound", "",
        f"**Ledger row #20 · 0 trials · train only ({START.date()}..{TRAIN_END.date()}) · "
        f"floor ±{FLOOR_R_PER_YR:.0f} R/yr.**",
        f"Pre-reg: `{res['prereg']}`. Population: {res['population']} — "
        f"{res['n_trades']} trades, {res['span_years']}y, {res['total_R']}R ({res['total_R_per_yr']} R/yr).", "",
        "## The 2x2 — does the daily view split 0127's weekly cohort?", "",
        md_table(pd.DataFrame(cells)), "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = res["daily_primary"]
    print(f"0144 daily descent: N={p['N']} ({p['share_of_trades_pct']}% of {res['n_trades']}) "
          f"cohort meanR {p.get('cohort_meanR')} vs rest {p.get('rest_meanR')}")
    print(f"  (a) exclusion {p['bound_a_exclusion']['R_per_yr_refused']} R/yr "
          f"(clairvoyant {p['bound_a_exclusion']['clairvoyant_refuse_only_losers_R_per_yr']}) "
          f"| clears floor: {p['bound_a_exclusion']['clears_floor']}")
    print(f"  (b) conditional mgmt {p['bound_b_conditional_management']['clairvoyant_conditional_gain_R_per_yr']} R/yr "
          f"| clears floor: {p['bound_b_conditional_management']['clears_floor']}")
    print(f"  -> {OUT_JSON}")


if __name__ == "__main__":
    main()
