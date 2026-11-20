"""MEASUREMENT: excess-return Sharpe, DSR at the lifetime trial count, and the blend against a RISK-MATCHED index.

Owner request 2026-11-18 (research/robust-sizing, follow-up). Analysis only: no rule, vol target, trial counter or
sealed slice changes. Swing prices are cut at 2024-06-30 (nq.lab asserts it); nothing reads 2024-07-01..2026-06-30
of the swing substrate or the sealed judge log.

SERIES
  swing      nq.lab.runs.replay({}) daily NAV (live book, PIT membership), via explore_blend_drawdown_sizing.navs()
  momentum   0001 run of record, 2017-01-01..2026-06-30, same cache
  blend(T)   pipelines/lifecycle/core.py::vol_target_blend(r_mom, r_swing, w_a=0.70, target=T, lookback=20,
             cash_rate=0.06): exposure = min(1, T / (20-session std of the 70/30 daily return, lagged one session,
             * sqrt(252))), the rest in cash at 6%/252 a day (the FROZEN blend definition, unchanged)
  bench(T)   Nifty Midcap150 Momentum 50 TRI (diagnostics/research/benchmarks/tri/nifty_midcap150_momentum_50_tri.csv)
             daily returns put through THE SAME RULE: exposure = min(1, T / (20-session std lagged one session *
             sqrt(252))), the rest in cash at 6.5%/yr compounded daily, (1.065)^(1/252) - 1 a session (owner spec)
  bench@e    static exposure e to the TRI, 1-e in cash at 6.5% compounded daily, rebalanced daily (the "index fund
             plus a liquid fund" fallback); e on a 0.05 grid from 0.30 to 1.00

WINDOWS
  swing window   2019-03-01..2024-06-28 (build_bands.COMMON; the blend's frozen-band window)
  0001 window    2017-01-01..2026-06-30. The BLEND CANNOT BE BUILT here: the swing book has no NAV before 2019 and
                 2024-07-01 onward is sealed. The nearest construction, 0001 momentum alone through the same
                 vol-target rule with the frozen 6% cash, is reported in its place and labelled as such.

METRICS (every one on the series' own daily returns over the window)
  CAGR            (NAV_end / NAV_start) ** (365.25 / calendar days) - 1
  Sharpe raw      mean(r) / std(r, ddof=1) * sqrt(252)                        (the convention of the earlier table)
  Sharpe excess   (mean(r) - rf_d) / std(r, ddof=1) * sqrt(252), rf_d = 1.065 ** (1/252) - 1
                  (same formula as nq/validation/metrics.py::sharpe_excess, which uses ddof=0; ddof=1 here so the raw
                  column reproduces the published 1.932 / 1.801 exactly)
  156w p95 DD     explore_blend_drawdown_sizing.boot_dd: stationary bootstrap of Friday-to-Friday weekly returns,
                  mean block 26 (owner spec) and 8 (the block Part 2 used), 10,000 draws, 156-week paths, depth %
  worst 3y        min over every session t >= start + 3 calendar years of NAV(t) / NAV(asof t - 3 years) - 1, also
                  annualised. Rolling windows overlap almost entirely; this is ONE number from one path, not a
                  distribution
  delta Sharpe    paired moving-block bootstrap (nq.validation.bootstrap.bootstrap_delta, block 63 sessions, 5000
                  draws, seed 12345) of excess Sharpe(blend) - excess Sharpe(bench) on date-aligned daily returns

"BEATS" (fixed before any number was computed): blend excess Sharpe > risk-matched benchmark excess Sharpe at the
same target on that window. CAGR, drawdown and the paired CI are reported beside it; the CI decides nothing.

DSR  the harness path (nq.runner.research._dsr_from_bootstrap: 63-session non-overlapping windows, cross-trial
     variance from the 63-session block-bootstrap Sharpe CI, 5000 draws, seed 12345) at three trial counts:
     (a) cumulative_n_trials() = the post-reset ledger count; (b) lifetime_n_trials() = pre-reset 138 + post-reset;
     (c) an ENTRY COUNT: every pre-registration file (diagnostics/research/preregistry/*.md except README,
     research/preregistry_*.md, research/*/prereg.md) plus every numbered research/findings/NNNN-*.md. The two
     ID namespaces collide (55 shared numbers name different studies), so files are counted, not IDs; a study
     with both a pre-registration and a finding counts twice, and measurements are counted as if they were trials
     -> (c) is an upper bound on the search, (b) the ledger's own lifetime figure.

    python pipelines/diagnostics/explore_risk_matched_benchmark.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_risk_matched_benchmark.json"
TRI = ROOT / "diagnostics" / "research" / "benchmarks" / "tri" / "nifty_midcap150_momentum_50_tri.csv"
RF = 0.065
RF_D = (1 + RF) ** (1 / 252) - 1
SWING_WIN = B.COMMON
FULL_WIN = ("2017-01-01", "2026-06-30")
TARGETS_RM = (0.11, 0.13, 0.15)
EXPOSURES = tuple(round(x / 100, 2) for x in range(30, 101, 5))
BAR = 25.0


def win(s: pd.Series, w) -> pd.Series:
    return s[(s.index >= pd.Timestamp(w[0])) & (s.index <= pd.Timestamp(w[1]))]


def tri_returns() -> pd.Series:
    t = pd.read_csv(TRI, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    return t.pct_change().dropna()


def vt(r: pd.Series, target: float, cash_d: float) -> pd.Series:
    """The blend's vol-target rule applied to one return series (20-session lagged vol, cap 1.0)."""
    vol = r.rolling(20).std().shift(1) * np.sqrt(252)
    e = (target / vol).clip(upper=1.0).fillna(1.0)
    return e * r + (1 - e) * cash_d


def static(r: pd.Series, e: float) -> pd.Series:
    return e * r + (1 - e) * RF_D


def nav(r: pd.Series) -> pd.Series:
    return (1 + r).cumprod()


def stats(r: pd.Series, *, blocks=(26, 8)) -> dict:
    n = nav(r)
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    sd = r.std()
    out = {"cagr_pct": round(float(n.iloc[-1] ** (1 / yrs) - 1) * 100, 2),
           "sharpe_raw": round(float(r.mean() / sd * np.sqrt(252)), 3),
           "sharpe_excess": round(float((r.mean() - RF_D) / sd * np.sqrt(252)), 3),
           "worst_daily_dd_pct": round(float((n / n.cummax() - 1).min() * 100), 2)}
    w = C.weekly_returns(1e6 * n).to_numpy()
    for b in blocks:
        out[f"boot156_p95_b{b}"] = round(float(np.percentile(B.boot_dd(w, 156, b), 95)), 2)
    # worst rolling 3-calendar-year return
    first = n.index[0] + pd.DateOffset(years=3)
    ends = n.index[n.index >= first]
    if len(ends):
        base = n.reindex(ends - pd.DateOffset(years=3), method="ffill").to_numpy()
        roll = n.loc[ends].to_numpy() / base - 1
        k = int(np.nanargmin(roll))
        out["worst_3y_pct"] = round(float(roll[k]) * 100, 2)
        out["worst_3y_ann_pct"] = round(float((1 + roll[k]) ** (1 / 3) - 1) * 100, 2)
        out["worst_3y_end"] = str(ends[k].date())
        out["n_3y_end_dates"] = int(len(ends))
    return out


def paired_delta(a: pd.Series, b: pd.Series) -> dict:
    from nq.validation.bootstrap import bootstrap_delta
    idx = a.index.intersection(b.index)
    f = lambda x: float((np.mean(x) - RF_D) / np.std(x, ddof=1) * np.sqrt(252))  # noqa: E731
    d = bootstrap_delta(a.reindex(idx).to_numpy(), b.reindex(idx).to_numpy(), f, block_size=63, n_samples=5000,
                        seed=12345)
    return {"n_days": int(len(idx)), "delta_excess_sharpe": round(d.point, 3), "ci_5_95": [round(d.lower, 3), round(d.upper, 3)]}


def entry_count() -> dict:
    pre_dir = [f for f in (ROOT / "diagnostics" / "research" / "preregistry").glob("*.md") if f.name != "README.md"]
    pre_root = list((ROOT / "research").glob("preregistry_*.md"))
    pre_sub = list((ROOT / "research").glob("*/prereg.md"))
    fnd = [f for f in (ROOT / "research" / "findings").glob("*.md") if re.match(r"\d{4}", f.name)]
    ids_p = {re.match(r"(\d{4})", f.name).group(1) for f in pre_dir if re.match(r"\d{4}", f.name)}
    ids_f = {f.name[:4] for f in fnd}
    return {"preregistry_dir": len(pre_dir), "research_preregistry_files": len(pre_root), "research_sub_prereg": len(pre_sub),
            "findings_numbered": len(fnd), "total": len(pre_dir) + len(pre_root) + len(pre_sub) + len(fnd),
            "shared_numbers_between_prereg_and_findings": len(ids_p & ids_f),
            "rule": "files, not IDs (namespaces collide); upper bound on the search"}


def dsr_at(r: pd.Series, counts: dict) -> dict:
    from nq.runner.research import _dsr_from_bootstrap, block_bootstrap_metric, sharpe
    x = r.to_numpy(float)
    ci = block_bootstrap_metric(x, sharpe, block_size=63, n_samples=5000, seed=12345)
    return {k: round(_dsr_from_bootstrap(x, int(n), (ci.lower, ci.upper)), 4) for k, n in counts.items()}


def main() -> int:
    d = B.navs()
    mo = d["momentum_metrics"]
    if (round(mo["cagr_pct"], 2), round(mo["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("0001 anchor mismatch: stop")
    rb15 = B.blend_daily(d["momentum"], d["swing"], 0.15)
    worst = float((B.to_nav(rb15) / B.to_nav(rb15).cummax() - 1).min() * 100)
    if round(worst, 2) != -22.85:
        raise SystemExit(f"blend anchor mismatch {worst:.2f}: stop")
    prior = json.loads(B.OUT_JSON.read_text(encoding="utf-8"))["q3_vol_target"]["sweep"]
    res: dict = {"rf_annual": RF, "rf_daily": RF_D, "anchors": {"0001": [21.73, 1.13], "blend_daily_worst": round(worst, 2)}}

    # ---- 1. Part 2 sweep, both Sharpes (block 8, as published)
    sweep = []
    for row in prior:
        t = row["target_pct"] / 100
        r = B.blend_daily(d["momentum"], d["swing"], t)
        s = stats(r, blocks=(8,))
        assert abs(s["sharpe_raw"] - row["sharpe"]) < 1e-3 and abs(s["cagr_pct"] - row["cagr_pct"]) < 1e-2, (t, s, row)
        e = r.index  # exposure share in cash, for the explanation
        _, expo = C.vol_target_blend(B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna(), target=t)
        sweep.append({"target_pct": row["target_pct"], "cagr_pct": s["cagr_pct"], "sharpe_raw": s["sharpe_raw"],
                      "sharpe_excess": s["sharpe_excess"], "boot156_p95_b8": row["boot156_p95"],
                      "mean_exposure": round(float(expo.mean()), 3), "n_days": int(len(e))})
    by = {s["target_pct"]: s for s in sweep}
    res["q1_part2_both_sharpes"] = {"sweep": sweep,
                                    "delta_11_vs_15": {"raw": round(by[11]["sharpe_raw"] - by[15]["sharpe_raw"], 3),
                                                       "excess": round(by[11]["sharpe_excess"] - by[15]["sharpe_excess"], 3)}}

    # ---- 2. DSR at three trial counts
    from nq.validation.dsr import cumulative_n_trials, lifetime_n_trials
    ec = entry_count()
    counts = {"n_trials_ledger": cumulative_n_trials(), "lifetime_ledger": lifetime_n_trials(), "entry_count": ec["total"]}
    WF = ("2019-01-01", "2024-06-28")
    books = {"live_swing": win(d["swing"], WF).pct_change().dropna(),
             "xsec_momentum_0001": win(d["momentum"], WF).pct_change().dropna(),
             "blend_vt15": rb15, "blend_vt11": B.blend_daily(d["momentum"], d["swing"], 0.11)}
    res["q2_dsr"] = {"counts": counts, "entry_count_detail": ec, "window_books": WF, "window_blend": SWING_WIN,
                     "dsr": {k: dsr_at(v, counts) for k, v in books.items()}}

    # ---- 3. risk-matched benchmark
    tr = tri_returns()
    q3 = {}
    # swing window
    rows = {}
    for t in TARGETS_RM:
        bl = B.blend_daily(d["momentum"], d["swing"], t)
        bm = vt(win(tr, (bl.index[0], SWING_WIN[1])), t, RF_D)   # windowed first, like the blend's legs
        # parity sensitivity: blend with the benchmark's cash (6.5% compounded) instead of the frozen 6% simple
        a, b = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
        idx = a.index.intersection(b.index)
        raw = 0.7 * a.reindex(idx).fillna(0) + 0.3 * b.reindex(idx).fillna(0)
        bl_par = vt(raw, t, RF_D)
        rows[f"{int(t*100)}"] = {"blend": stats(bl), "bench_vt": stats(bm), "blend_cash65_parity": stats(bl_par),
                                 "paired": paired_delta(bl, bm), "beats": None}
        rows[f"{int(t*100)}"]["beats"] = rows[f"{int(t*100)}"]["blend"]["sharpe_excess"] > rows[f"{int(t*100)}"]["bench_vt"]["sharpe_excess"]
    q3["swing_window"] = {"window": SWING_WIN, "note": "both series are windowed BEFORE the vol rule, so both run their first 20 "
                          "sessions at exposure 1.0 (the blend's frozen construction, mirrored for the benchmark)",
                          "bench_unlevered": stats(win(tr, SWING_WIN)), "by_target": rows}
    # 0001 full window: blend not constructible -> momentum alone through the same rule
    rows = {}
    mr = win(d["momentum"], FULL_WIN).pct_change().dropna()
    trw = win(tr, FULL_WIN)
    for t in TARGETS_RM:
        m_vt = vt(mr, t, 0.06 / 252)
        b_vt = vt(trw, t, RF_D)
        rows[f"{int(t*100)}"] = {"momentum_0001_vt": stats(m_vt), "bench_vt": stats(b_vt), "paired": paired_delta(m_vt, b_vt),
                                 "beats_momentum_alone": None}
        rows[f"{int(t*100)}"]["beats_momentum_alone"] = rows[f"{int(t*100)}"]["momentum_0001_vt"]["sharpe_excess"] > rows[f"{int(t*100)}"]["bench_vt"]["sharpe_excess"]
    q3["full_0001_window"] = {"window": FULL_WIN, "blend": "NOT CONSTRUCTIBLE (swing NAV starts 2019; 2024-07+ sealed)",
                              "bench_unlevered": stats(trw), "momentum_unlevered": stats(mr), "by_target": rows}
    # benchmark alone at the exposure that meets -25% (static e, and vol target), both windows, block 26
    for key, w in (("swing_window", SWING_WIN), ("full_0001_window", FULL_WIN)):
        tw = win(tr, w)
        grid = []
        for e in EXPOSURES:
            s = stats(static(tw, e))
            grid.append({"exposure": e, **{k: s[k] for k in ("cagr_pct", "sharpe_excess", "boot156_p95_b26", "boot156_p95_b8", "worst_3y_ann_pct", "worst_daily_dd_pct")}})
        ok = [g for g in grid if g["boot156_p95_b26"] <= BAR]
        ok8 = [g for g in grid if g["boot156_p95_b8"] <= BAR]
        q3[key]["bench_static_grid"] = grid
        q3[key]["bench_static_meeting_bar_b26"] = max(ok, key=lambda g: g["exposure"]) if ok else None
        q3[key]["bench_static_meeting_bar_b8"] = max(ok8, key=lambda g: g["exposure"]) if ok8 else None
    res["q3_risk_matched"] = q3
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
