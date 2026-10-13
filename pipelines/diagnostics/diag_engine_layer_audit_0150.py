"""0150 — engine layer audit: the Grade-A rating trade by trade, and one-layer-off attribution.

Pre-registration: diagnostics/research/preregistry/0150-engine-layer-audit.md (committed before this file
existed). Screen ledger row 23. Measurement only; nothing here changes a layer.

TRAIN ONLY: every price series is CUT at 2024-06-30 before the engine sees it.

    python pipelines/diagnostics/diag_engine_layer_audit_0150.py
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

START, CUT = "2019-01-01", "2024-06-30"
SUB = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", CUT)}
N_BOOT, N_RANDOM, SEED = 5000, 20, 20261013
FLOOR_R_YR, FLOOR_SHARPE = 10.0, 0.10
OUT = ROOT / "diagnostics" / "research" / "engine_layer_audit" / "result.json"


# ── Part 1 helpers ───────────────────────────────────────────────────────────────────────────────
def week_key(d) -> str:
    iso = pd.Timestamp(d).isocalendar()
    return f"{int(iso.year)}-W{int(iso.week):02d}"


def rank_within_week(led: pd.DataFrame) -> pd.DataFrame:
    led = led.copy()
    led["week"] = led["entry_date"].map(week_key)
    led["wrank"] = led.groupby("week")["rank"].rank(ascending=False, method="first").astype(int)
    led["n_week"] = led.groupby("week")["rank"].transform("size")
    return led


def hit_2r(led: pd.DataFrame, ohlcv: dict) -> pd.Series:
    """Did the path touch entry+2R before the initial stop (bars from the entry session, both-touch = stop)?"""
    from nq.brain.excursions import HIT, first_passage
    out = []
    for r in led.itertuples(index=False):
        df = ohlcv.get(r.tkr)
        risk = r.entry - r.stop0
        if df is None or risk <= 0:
            out.append(np.nan); continue
        end = pd.Timestamp(r.exit_date) if isinstance(r.exit_date, str) or r.exit_date is not None else df.index[-1]
        p = df[(df.index >= pd.Timestamp(r.entry_date)) & (df.index <= end)]
        if not len(p):
            out.append(np.nan); continue
        ps = first_passage(p["High"].to_numpy(), p["Low"].to_numpy(), entry=r.entry, stop=r.stop0,
                           target=r.entry + 2 * risk)
        out.append(1.0 if ps.outcome == HIT else 0.0)
    return pd.Series(out, index=led.index)


def week_spearman(g: pd.DataFrame) -> float:
    if len(g) < 3 or g["R"].nunique() < 2:
        return np.nan
    return float(pd.Series(-g["wrank"].to_numpy()).corr(pd.Series(g["R"].to_numpy()), method="spearman"))


def rating_stats(led: pd.DataFrame) -> dict:
    a, rest = led[led["wrank"] <= 5], led[led["wrank"] > 5]
    weeks_ic = led.groupby("week").apply(week_spearman).dropna()
    both = led[led["week"].isin(set(a["week"]) & set(rest["week"]))]
    return {"n": int(len(led)), "n_weeks": int(led["week"].nunique()),
            "rank_ic_mean": float(weeks_ic.mean()) if len(weeks_ic) else None,
            "meanR_rank1_5": float(a["R"].mean()) if len(a) else None,
            "meanR_rank6_10": float(led[(led.wrank > 5) & (led.wrank <= 10)]["R"].mean()),
            "meanR_rank11plus": float(led[led.wrank > 10]["R"].mean()),
            "edge_A_minus_rest_same_weeks": float(both[both.wrank <= 5]["R"].mean() - both[both.wrank > 5]["R"].mean())
            if len(both) else None,
            "hit2R_A": float(a["hit2r"].mean()), "hit2R_rest": float(rest["hit2r"].mean()),
            "null_p_A": float(a["null_p"].mean()), "null_p_rest": float(rest["null_p"].mean())}


def boot(led: pd.DataFrame, rng) -> dict:
    weeks = led["week"].unique()
    by = {w: g for w, g in led.groupby("week")}
    ic, edge = [], []
    for _ in range(N_BOOT):
        pick = rng.choice(weeks, len(weeks))
        s = pd.concat([by[w] for w in pick], ignore_index=True)
        a, r = s[s.wrank <= 5]["R"], s[s.wrank > 5]["R"]
        if len(a) and len(r):
            edge.append(a.mean() - r.mean())
        w_ic = [week_spearman(by[w]) for w in pick]
        w_ic = [x for x in w_ic if x == x]
        if w_ic:
            ic.append(np.mean(w_ic))
    ci = lambda x: [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))] if x else None  # noqa: E731
    return {"rank_ic_ci95": ci(ic), "edge_ci95": ci(edge)}


# ── Part 2 helpers ───────────────────────────────────────────────────────────────────────────────
def curve_stats(curve: pd.Series, lo, hi) -> dict:
    e = curve[(curve.index >= pd.Timestamp(lo)) & (curve.index <= pd.Timestamp(hi))]
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() else None,
            "cagr_pct": float(((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100),
            "maxdd_pct": float((e / e.cummax() - 1).min() * 100)}


def random_top5(P, seed: int) -> set:
    from collections import defaultdict
    rng = np.random.default_rng(seed)
    by_week = defaultdict(list)
    for t, s in P.items():
        for e0 in s["entry_win"]:
            by_week[week_key(s["dates"][e0])].append((t, e0))
    out = set()
    for lst in by_week.values():
        idx = rng.choice(len(lst), min(5, len(lst)), replace=False)
        out.update(lst[i] for i in idx)
    return out


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from nq.brain.excursions import null_p_target_first
    from nq.data.membership import load_membership
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe

    ohlcv = corrected_universe()
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(CUT)] for t, df in ohlcv.items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    last = max(df.index.max() for df in cut.values())
    assert last <= pd.Timestamp(CUT), f"sealed data reached the engine: {last}"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem = load_membership()
    live_kw = dict(**LIVE_DISCIPLINE, **LIVE_STALENESS, demerger_events=events, start=START)
    years = (pd.Timestamp(CUT) - pd.Timestamp(START)).days / 365.25
    res: dict = {"window": [START, CUT], "last_bar_seen": str(last.date())}

    # Part 1 — every filled signal, uncapped, all grades, live exit.
    led: list = []
    R94.backtest(P, mem, ledger=led, uncapped=True, a_grade=None, **live_kw, **LIVE_EXIT)
    L = pd.DataFrame(led)
    L = L[pd.to_datetime(L["entry_date"]) >= pd.Timestamp(START)].reset_index(drop=True)
    L = rank_within_week(L)
    L["hit2r"] = hit_2r(L, cut)
    L["null_p"] = [null_p_target_first(e, s, e + 2 * (e - s)) if e > s else np.nan
                   for e, s in zip(L["entry"], L["stop0"])]
    rng = np.random.default_rng(SEED)
    p1 = {"all": {**rating_stats(L), **boot(L, rng)}, "censoring": "signals that never filled are absent",
          "open_at_cut": int((L["reason"] == "eos").sum())}
    for k, (lo, hi) in SUB.items():
        s = L[(pd.to_datetime(L.entry_date) >= pd.Timestamp(lo)) & (pd.to_datetime(L.entry_date) <= pd.Timestamp(hi))]
        p1[k] = {**rating_stats(s), **boot(s, np.random.default_rng(SEED + len(k)))}
    p1["by_year"] = {int(y): {"edge": float(g[g.wrank <= 5]["R"].mean() - g[g.wrank > 5]["R"].mean()),
                              "rank_ic": float(g.groupby("week").apply(week_spearman).dropna().mean()),
                              "n": int(len(g))}
                     for y, g in L.groupby(pd.to_datetime(L.entry_date).dt.year)}
    ci = p1["all"]["edge_ci95"]
    pos_sub = all((p1[k]["edge_A_minus_rest_same_weeks"] or 0) > 0 for k in SUB)
    p1["reading"] = ("ON POINT" if ci and ci[0] > 0 and pos_sub else
                     "REGIME-DEPENDENT" if ci and ci[0] > 0 else
                     "NOT DISTINGUISHABLE FROM NOISE" if ci and ci[0] <= 0 <= ci[1] else "NEGATIVE")
    res["part1_rating"] = p1

    # Part 2 — capped book, one layer off at a time.
    a_live = R94.grade_a_entries(P)
    arms = {"live": dict(a_grade=a_live, **LIVE_EXIT),
            "no_ext_cap": dict(a_grade=a_live, **{**LIVE_EXIT}),
            "no_grade_gate": dict(a_grade=None, **LIVE_EXIT),
            "base_exit": dict(a_grade=a_live)}
    out2: dict = {}

    def run(name, kw, ext_cap=LIVE_DISCIPLINE["ext_cap"]):
        lg: list = []
        kw2 = {**live_kw, "ext_cap": ext_cap}
        o = R94.backtest(P, mem, ledger=lg, **kw2, **kw)
        lr = pd.DataFrame(lg)
        return {"full": curve_stats(o["curve"], START, CUT),
                "sub": {k: curve_stats(o["curve"], *v) for k, v in SUB.items()},
                "sumR_per_yr": float(lr["R"].sum() / years) if len(lr) else 0.0,
                "sub_sumR": {k: float(lr[(pd.to_datetime(lr.entry_date) >= pd.Timestamp(lo)) &
                                         (pd.to_datetime(lr.entry_date) <= pd.Timestamp(hi))]["R"].sum())
                             for k, (lo, hi) in SUB.items()} if len(lr) else {},
                "n_trades": int(len(lr))}

    for name, kw in arms.items():
        out2[name] = run(name, kw, ext_cap=None if name == "no_ext_cap" else LIVE_DISCIPLINE["ext_cap"])
    rnd = [run(f"random_{s}", dict(a_grade=random_top5(P, SEED + s), **LIVE_EXIT)) for s in range(N_RANDOM)]
    rs = [r["full"]["sharpe"] for r in rnd]
    out2["random_top5"] = {"sharpe": rs, "sumR_per_yr": [r["sumR_per_yr"] for r in rnd]}
    live = out2["live"]
    layer = {}
    for name in ("no_ext_cap", "no_grade_gate", "base_exit"):
        a = out2[name]
        d_r = live["sumR_per_yr"] - a["sumR_per_yr"]
        d_s = live["full"]["sharpe"] - a["full"]["sharpe"]
        sub_d = {k: round(live["sub"][k]["sharpe"] - a["sub"][k]["sharpe"], 3) for k in SUB}
        carries = (abs(d_r) >= FLOOR_R_YR or abs(d_s) >= FLOOR_SHARPE) and \
            len({np.sign(v) for v in sub_d.values()} | {np.sign(d_s)}) == 1
        layer[name] = {"value_dR_per_yr": round(d_r, 2), "value_dSharpe": round(d_s, 3),
                       "value_dSharpe_by_sub": sub_d, "value_dMaxDD_pp": round(live["full"]["maxdd_pct"] - a["full"]["maxdd_pct"], 2),
                       "reading": ("CARRIES ITS WEIGHT" if carries and d_s > 0 else
                                   "COSTS (removing it helps)" if carries and d_s < 0 else
                                   "NOT DISTINGUISHABLE FROM NOISE")}
    pct = float((np.array(rs) < live["full"]["sharpe"]).mean() * 100)
    layer["crs_rank_vs_random"] = {"live_sharpe": live["full"]["sharpe"], "random_mean": float(np.mean(rs)),
                                   "random_max": float(np.max(rs)), "live_percentile": pct,
                                   "dR_per_yr_vs_random_mean": round(live["sumR_per_yr"] - float(np.mean(out2["random_top5"]["sumR_per_yr"])), 2)}
    res["part2_arms"] = out2
    res["part2_layer_value"] = layer

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    a = p1["all"]
    print(f"PART 1 rating: n {a['n']} weeks {a['n_weeks']} | rank IC {a['rank_ic_mean']:+.3f} CI {a['rank_ic_ci95']} | "
          f"edge A-rest {a['edge_A_minus_rest_same_weeks']:+.3f} CI {a['edge_ci95']} -> {p1['reading']}")
    print(f"  meanR 1-5 {a['meanR_rank1_5']:+.3f} | 6-10 {a['meanR_rank6_10']:+.3f} | 11+ {a['meanR_rank11plus']:+.3f} | "
          f"hit2R A {a['hit2R_A']:.3f} vs null {a['null_p_A']:.3f} | rest {a['hit2R_rest']:.3f} vs null {a['null_p_rest']:.3f}")
    for k in SUB:
        s = p1[k]
        print(f"  {k}: edge {s['edge_A_minus_rest_same_weeks']:+.3f} CI {s['edge_ci95']} | IC {s['rank_ic_mean']:+.3f}")
    print(f"  by year: {p1['by_year']}")
    print("PART 2 layers (capped):")
    for k, v in layer.items():
        print(f"  {k}: {v}")
    print(f"-> {OUT.relative_to(ROOT).as_posix()} (last bar {res['last_bar_seen']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
