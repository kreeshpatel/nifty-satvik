"""MEASURE / RE-RUN (tier 1, docs/PROCESS_TIERS.md) 2026-10-23 — degenerate-stop outliers in two findings.

No pre-registration, no screen row, no n_trials change: standing counts are READ from the ledgers below.

DECLARED RULE (committed in nq/lab/stats.py, commit e3eae32, BEFORE this script produced any number):
    a trade is a DEGENERATE STOP when its initial risk (entry - stop0) is below 0.5% of entry.
    Its R-multiple measures the sliver, not the trade. Such trades are EXCLUDED from the restated uncapped
    means. |R| > 20 is a REVIEW flag only (real compounders such as SUVEN +40.8R sit there) and is NOT
    excluded; a sensitivity that also drops it is reported separately and labelled as such.

WHAT IS RE-RUN
  A. finding 0148 (giveback ratchet), UNCAPPED arms: the same three engine runs
     (`diag_giveback_ratchet_0148.run_arm`, live config, PIT membership), then the same bound arithmetic,
     once on the raw ledger (must reproduce the committed result.json) and once with degenerate trades
     removed. The capped arms are checked for degenerate trades (expected: none) and left alone.
  B. finding 0150 Part 1 (the CRS rank as a rating): the same uncapped all-grade ledger, rank-within-week,
     week-clustered bootstrap with the SAME seeds; raw (must reproduce) vs degenerate trades removed.
     Ranks are recomputed among the remaining filled trades of each week (primary); a second variant
     keeps the original ranks and only drops rows.

TRAIN ONLY: every series is cut at 2024-06-30 before the engine sees it, asserted. Nothing in a production
path is edited.

    python pipelines/diagnostics/diag_degenerate_stop_restate_2026_10_23.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipelines" / "diagnostics"))

import diag_engine_layer_audit_0150 as D150          # noqa: E402  (pure helpers + constants reused verbatim)
import diag_giveback_ratchet_0148 as D148            # noqa: E402
from nq.lab import stats as S                        # noqa: E402

START, CUT = D148.START, D148.CUT
OUT = ROOT / "diagnostics" / "research" / "degenerate_stop" / "result.json"
RULE = (f"degenerate stop = initial risk < {S.MIN_RISK_FRAC:.1%} of entry (EXCLUDED); "
        f"|R| > {S.R_ABS_CAP:g} = review flag only (not excluded)")


def standing_counts() -> dict:
    nt = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    led = (ROOT / "diagnostics" / "research" / "label_screen_ledger.md").read_text(encoding="utf-8")
    screens = [int(m.group(1)) for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*20\d\d-", led, re.M)]
    sealed = {m.group(1) for m in re.finditer(r"^\|\s*(S\d+)\s*\|", led, re.M)}
    return {"screens": max(screens) if screens else None, "sealed_opens": len(sealed),
            "n_trials": nt["cumulative_n_trials"]}


def flag_table(led: pd.DataFrame, book: str) -> list[dict]:
    f = S.r_sanity_flags(led)
    cols = ["tkr", "entry_date", "entry", "stop0", "risk0_frac", "exit_date", "exit_px", "reason", "R"]
    out = f[f["r_flagged"]][cols].copy()
    out["book"] = book
    out["degenerate_stop"] = f.loc[out.index, "degenerate_stop"]
    return out.to_dict("records")


# ───────────────────────────── A. 0148 uncapped arms ─────────────────────────────
def arm_row(led: pd.DataFrame) -> dict:
    led = led.copy()
    led["year"] = pd.to_datetime(led["entry_date"]).dt.year
    closed = led[led["reason"] != "eos"]
    return {"n_trades": int(len(led)), "n_open_at_cut": int((led["reason"] == "eos").sum()),
            "mean_R": float(closed["R"].mean()), "sum_R": float(closed["R"].sum()),
            "median_R": float(closed["R"].median()), "win_pct": float((closed["R"] > 0).mean() * 100),
            "sum_R_incl_open_at_mark": float(led["R"].sum()),
            "R_by_year": closed.groupby("year")["R"].sum().round(2).to_dict()}


def bound(arms: dict) -> dict:
    """Exactly diag_giveback_ratchet_0148's bound arithmetic, uncapped book only."""
    years = (pd.Timestamp(CUT) - pd.Timestamp(START)).days / 365.25
    b = arms["base"]
    res = {}
    for name in list(D148.ARMS)[1:]:
        a = arms[name]
        byy = {y: round(a["R_by_year"].get(y, 0.0) - b["R_by_year"].get(y, 0.0), 2)
               for y in sorted(set(a["R_by_year"]) | set(b["R_by_year"]))}
        d_yr = (a["sum_R_incl_open_at_mark"] - b["sum_R_incl_open_at_mark"]) / years
        sub = {k: round(sum(v for y, v in byy.items() if lo[:4] <= str(y) <= hi[:4]), 2)
               for k, (lo, hi) in D148.SUBPERIODS.items()}
        reading = ("ELIGIBLE for a pre-registered trial proposal at a review"
                   if d_yr >= D148.NOISE_FLOOR_R_PER_YR and all(v > 0 for v in sub.values())
                   else "BOUND RECORDED — below the floor or wrong-signed; no trial")
        res[name] = {"delta_R_per_yr": round(d_yr, 2),
                     "delta_R_per_yr_closed_only_censored": round((a["sum_R"] - b["sum_R"]) / years, 2),
                     "delta_mean_R": round(a["mean_R"] - b["mean_R"], 4),
                     "delta_R_by_year": byy, "delta_R_by_subperiod": sub, "reading": reading}
    return res


def part_a(P, events, R94, live) -> dict:
    raw_leds, committed = {}, json.loads((ROOT / "diagnostics" / "research" / "giveback_ratchet" / "result.json")
                                         .read_text(encoding="utf-8"))
    flags: list[dict] = []
    for name, extra in D148.ARMS.items():
        _out, led, _fired = D148.run_arm(P, events, R94, live, extra, uncapped=True)
        raw_leds[name] = led
        flags += [{**r, "arm": name} for r in flag_table(led, "uncapped")]
    raw_arms = {n: arm_row(l) for n, l in raw_leds.items()}
    clean_arms = {n: arm_row(S.exclude_degenerate_stops(l)) for n, l in raw_leds.items()}
    # sensitivity: also drop |R|>20 (labelled; NOT the declared rule)
    both = {n: arm_row(l.loc[~S.r_sanity_flags(l)["r_flagged"].to_numpy()]) for n, l in raw_leds.items()}
    repro = {n: abs(raw_arms[n]["sum_R_incl_open_at_mark"]
                    - committed["arms"]["uncapped"][n]["sum_R_incl_open_at_mark"]) < 1e-6 for n in raw_arms}
    dropped = {n: int(len(raw_leds[n]) - len(S.exclude_degenerate_stops(raw_leds[n]))) for n in raw_leds}
    return {"raw": raw_arms, "raw_bound": bound(raw_arms), "raw_reproduces_committed": repro,
            "restated": clean_arms, "restated_bound": bound(clean_arms), "n_degenerate_dropped": dropped,
            "sensitivity_also_drop_absR_gt_20": {"arms": both, "bound": bound(both)},
            "flagged_trades_by_arm": flags}


def capped_check(P, events, R94, live) -> dict:
    out = {}
    for name, extra in D148.ARMS.items():
        _o, led, _f = D148.run_arm(P, events, R94, live, extra, uncapped=False)
        f = S.r_sanity_flags(led)
        out[name] = {"n": int(len(f)), "degenerate": int(f["degenerate_stop"].sum()),
                     "extreme_R": int(f["extreme_R"].sum()), "min_risk0_frac": float(f["risk0_frac"].min()),
                     "worst_R": float(f["R"].min()), "best_R": float(f["R"].max())}
    return out


# ───────────────────────────── B. 0150 Part 1 ─────────────────────────────
def fast_boot(led: pd.DataFrame, rng) -> dict:
    """`diag_engine_layer_audit_0150.boot`, same RNG draws and same statistic, vectorised.

    The original re-concatenates frames and re-ranks every resample (about 12 minutes per call); a week's
    Spearman IC and its rank-1-5 / rest R sums do not depend on the resample, so they are computed once per
    week and the bootstrap just indexes them. Equality with the committed CIs is asserted in `part_b`."""
    weeks = led["week"].unique()
    pos = {w: i for i, w in enumerate(weeks)}
    ic_w = np.array([D150.week_spearman(g) for _w, g in led.groupby("week")], dtype=float)
    ic_w = pd.Series(ic_w, index=[w for w, _g in led.groupby("week")]).reindex(weeks).to_numpy()
    a_sum = np.zeros(len(weeks)); a_n = np.zeros(len(weeks)); r_sum = np.zeros(len(weeks)); r_n = np.zeros(len(weeks))
    for w, g in led.groupby("week"):
        i = pos[w]; a = g[g.wrank <= 5]["R"]; r = g[g.wrank > 5]["R"]
        a_sum[i], a_n[i], r_sum[i], r_n[i] = a.sum(), len(a), r.sum(), len(r)
    ic, edge = [], []
    for _ in range(D150.N_BOOT):
        pick = rng.choice(weeks, len(weeks))
        idx = np.fromiter((pos[w] for w in pick), dtype=int, count=len(pick))
        na, nr = a_n[idx].sum(), r_n[idx].sum()
        if na and nr:
            edge.append(a_sum[idx].sum() / na - r_sum[idx].sum() / nr)
        v = ic_w[idx]
        v = v[~np.isnan(v)]
        if len(v):
            ic.append(float(np.mean(v)))
    ci = lambda x: [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))] if x else None  # noqa: E731
    return {"rank_ic_ci95": ci(ic), "edge_ci95": ci(edge)}


def p1_block(L: pd.DataFrame, *, rerank: bool) -> dict:
    """0150's Part-1 statistics on ledger ``L`` with 0150's seeds. ``rerank`` recomputes wrank among the rows."""
    if rerank:
        L = D150.rank_within_week(L.drop(columns=["week", "wrank", "n_week"]))
    p1 = {"all": {**D150.rating_stats(L), **fast_boot(L, np.random.default_rng(D150.SEED))}}
    for k, (lo, hi) in D150.SUB.items():
        s = L[(pd.to_datetime(L.entry_date) >= pd.Timestamp(lo)) & (pd.to_datetime(L.entry_date) <= pd.Timestamp(hi))]
        p1[k] = {**D150.rating_stats(s), **fast_boot(s, np.random.default_rng(D150.SEED + len(k)))}
    ci = p1["all"]["edge_ci95"]
    pos_sub = all((p1[k]["edge_A_minus_rest_same_weeks"] or 0) > 0 for k in D150.SUB)
    p1["reading"] = ("ON POINT" if ci and ci[0] > 0 and pos_sub else
                     "REGIME-DEPENDENT" if ci and ci[0] > 0 else
                     "NOT DISTINGUISHABLE FROM NOISE" if ci and ci[0] <= 0 <= ci[1] else "NEGATIVE")
    p1["n_trades"] = int(len(L))
    return p1


def part_b(P, mem, R94, cut, kw_live, live_exit) -> dict:
    from nq.brain.excursions import null_p_target_first
    led: list = []
    R94.backtest(P, mem, ledger=led, uncapped=True, a_grade=None, **kw_live, **live_exit)
    L = pd.DataFrame(led)
    L = L[pd.to_datetime(L["entry_date"]) >= pd.Timestamp(START)].reset_index(drop=True)
    L = D150.rank_within_week(L)
    L["hit2r"] = D150.hit_2r(L, cut)
    L["null_p"] = [null_p_target_first(e, s, e + 2 * (e - s)) if e > s else np.nan
                   for e, s in zip(L["entry"], L["stop0"])]
    flags = flag_table(L, "uncapped_all_grades")
    deg = S.r_sanity_flags(L)["degenerate_stop"].to_numpy()
    committed = json.loads((ROOT / "diagnostics" / "research" / "engine_layer_audit" / "result.json")
                           .read_text(encoding="utf-8"))["part1_rating"]
    raw = p1_block(L, rerank=False)
    repro = np.allclose(raw["all"]["edge_ci95"], committed["all"]["edge_ci95"], atol=1e-9) and np.allclose(
        raw["all"]["rank_ic_ci95"], committed["all"]["rank_ic_ci95"], atol=1e-9) and abs(raw["all"]["edge_A_minus_rest_same_weeks"]
                - committed["all"]["edge_A_minus_rest_same_weeks"]) < 1e-9
    clean_rerank = p1_block(L.loc[~deg].reset_index(drop=True), rerank=True)
    clean_keep = p1_block(L.loc[~deg].reset_index(drop=True), rerank=False)
    keep_r20 = ~S.r_sanity_flags(L)["r_flagged"].to_numpy()
    sens = p1_block(L.loc[keep_r20].reset_index(drop=True), rerank=True)
    return {"raw": raw, "raw_reproduces_committed": bool(repro), "restated_rerank": clean_rerank,
            "restated_keep_ranks": clean_keep, "sensitivity_also_drop_absR_gt_20_rerank": sens,
            "n_degenerate_dropped": int(deg.sum()), "n_total": int(len(L)),
            "meanR_all": float(L["R"].mean()), "meanR_all_restated": float(L.loc[~deg, "R"].mean()),
            "flagged_trades": flags}


def main() -> int:
    print("DECLARED RULE:", RULE)
    import run_bhanushali_weekly_rank as R94
    from nq.data.membership import load_membership
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe

    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(CUT)] for t, df in corrected_universe().items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    last = max(df.index.max() for df in cut.values())
    assert last <= pd.Timestamp(CUT), f"sealed data reached the engine: {last}"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem = load_membership()
    live = dict(LIVE_DISCIPLINE=LIVE_DISCIPLINE, LIVE_EXIT=LIVE_EXIT, LIVE_STALENESS=LIVE_STALENESS, mem=mem)
    kw_live = dict(**LIVE_DISCIPLINE, **LIVE_STALENESS, demerger_events=events, start=START)

    res = {"rule": RULE, "window": [START, CUT], "last_bar_seen": str(last.date()),
           "standing_counts": standing_counts()}
    res["part_a_0148_uncapped"] = part_a(P, events, R94, live)
    res["part_a_capped_check"] = capped_check(P, events, R94, live)
    res["part_b_0150_part1"] = part_b(P, mem, R94, cut, kw_live, LIVE_EXIT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")

    A = res["part_a_0148_uncapped"]
    print("standing counts:", res["standing_counts"])
    print("0148 reproduces committed (raw):", A["raw_reproduces_committed"], "| dropped:", A["n_degenerate_dropped"])
    for tag, arms, bd in (("RAW", A["raw"], A["raw_bound"]), ("RESTATED", A["restated"], A["restated_bound"])):
        print(f"-- 0148 uncapped {tag}")
        for n, a in arms.items():
            print(f"   {n:<18} n {a['n_trades']} open {a['n_open_at_cut']} meanR {a['mean_R']:+.3f} med {a['median_R']:+.3f} "
                  f"sumR {a['sum_R']:+.1f} markedR {a['sum_R_incl_open_at_mark']:+.1f} win {a['win_pct']:.1f}%")
        for n, v in bd.items():
            print(f"   {n:<18} dR/yr {v['delta_R_per_yr']:+.2f} dMeanR {v['delta_mean_R']:+.4f} sub {v['delta_R_by_subperiod']} {v['reading']}")
    print("capped degenerate check:", res["part_a_capped_check"])
    B = res["part_b_0150_part1"]
    print("0150 P1 reproduces committed (raw):", B["raw_reproduces_committed"], "| dropped", B["n_degenerate_dropped"], "of", B["n_total"])
    for tag in ("raw", "restated_rerank", "restated_keep_ranks", "sensitivity_also_drop_absR_gt_20_rerank"):
        a = B[tag]["all"]
        print(f"-- 0150 P1 {tag}: n {B[tag]['n_trades']} IC {a['rank_ic_mean']:+.4f} {a['rank_ic_ci95']} edge {a['edge_A_minus_rest_same_weeks']:+.3f} "
              f"{a['edge_ci95']} | meanR 1-5 {a['meanR_rank1_5']:+.3f} 6-10 {a['meanR_rank6_10']:+.3f} 11+ {a['meanR_rank11plus']:+.3f} "
              f"| hit2R A {a['hit2R_A']:.3f}/{a['null_p_A']:.3f} rest {a['hit2R_rest']:.3f}/{a['null_p_rest']:.3f} -> {B[tag]['reading']}")
        for k in D150.SUB:
            s = B[tag][k]
            print(f"     {k}: edge {s['edge_A_minus_rest_same_weeks']:+.3f} {s['edge_ci95']} IC {s['rank_ic_mean']:+.4f}")
    print(f"-> {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
