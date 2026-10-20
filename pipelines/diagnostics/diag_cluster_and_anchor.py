"""B5 (correlation-cluster activation count) + B7 (live-book anchor) -- EXPLORE / MEASURE tier.

Process tier (docs/PROCESS_TIERS.md): tier 0/1. No pre-registration, no screen row, no n_trials change.
Both items are DESCRIPTIVE. B5 is an ACTIVATION-BOUND INPUT ONLY: it adopts nothing, tests no rule, and
its numbers are not a verdict on any cluster rule. B7 re-measures the live book so the programme has an
anchor ON THE LIVE BOOK (the pinned anchors in docs/references/plausibility_anchors.md are on other books).

TRAIN ONLY. Every price series is cut at nq.lab.runs.CUT (2024-06-30) BEFORE the engine, the correlation
matrix, or the benchmark sees it, and the cut is asserted. Reported window 2019-01-01..2024-06-30.
Nothing in 2024-07-01..2026-06-30 is read. The sealed judge log is not touched.

LIVE CONFIGURATION. Every engine run goes through `nq.lab.runs` (`replay`, `engine_kwargs`,
DEFAULT_CONFIG with pit_membership=True). The manifest label of each run is recorded in the JSON; the
base must read LIVE BOOK and the script refuses to continue if it does not.

Run:  python pipelines/diagnostics/diag_cluster_and_anchor.py
Out:  diagnostics/research/engine_assumptions/2026-10-20_cluster_and_anchor.json
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from nq.lab import runs  # noqa: E402
from nq.validation.metrics import sortino  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "engine_assumptions" / "2026-10-20_cluster_and_anchor.json"
WIN_START, WIN_END = "2019-01-01", runs.CUT          # reported window
CORR_WINDOW, CORR_MIN_OBS = 126, 100                 # trailing sessions, min overlapping returns per pair
THRESHOLDS = (0.5, 0.7)
DUP_CORR = 0.98                                       # pair corr above this = same company under two symbols
DD_LEVEL = -0.10                                      # Nifty >=10% below its 252d high
N_CONTROL_DRAWS, N_BOOT, SEED = 20, 2000, 20261020


# =============================================================================== standing counts
def standing_counts() -> dict:
    nt = json.loads((ROOT / "diagnostics/research/n_trials.json").read_text(encoding="utf-8"))
    led = (ROOT / "diagnostics/research/label_screen_ledger.md").read_text(encoding="utf-8")
    screens = len(re.findall(r"^\| \d+ \|", led, re.M))
    sealed = len(re.findall(r"^\| S\d+ \|", led, re.M))
    return {"screens": screens, "sealed_opens": sealed, "n_trials": int(nt["cumulative_n_trials"]),
            "source": "diagnostics/research/n_trials.json + diagnostics/research/label_screen_ledger.md"}


# =============================================================================== B7 helpers
def window_stats(nav: pd.Series, ledger: pd.DataFrame, start: str, end: str) -> dict:
    """Continuous SLICE of one full-run NAV (never a fresh-capital re-run): the slice starts from the NAV
    carried in from the prior close, so positions and the equity path are the full run's own."""
    idx = pd.DatetimeIndex(nav.index)
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    prior = nav[idx < s]
    sub = nav[(idx >= s) & (idx <= e)]
    base = sub if prior.empty else pd.concat([prior.iloc[[-1]], sub])
    r = base.pct_change().dropna()
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan")
    years = (sub.index[-1] - base.index[0]).days / 365.25
    cagr = float((base.iloc[-1] / base.iloc[0]) ** (1 / years) - 1)
    dd_slice = float((base / base.cummax() - 1).min())
    dd_full_peak = float((sub / nav[idx <= e].cummax().reindex(sub.index) - 1).min())
    led = ledger.copy()
    led["entry_date"] = pd.to_datetime(led["entry_date"])
    L = led[(led["entry_date"] >= s) & (led["entry_date"] <= e)]
    return {"window": [start, end], "first_nav_date": str(sub.index[0].date()), "last_nav_date": str(sub.index[-1].date()),
            "sharpe": sh, "sortino": float(sortino(r.to_numpy())), "cagr_calendar": cagr,
            "maxdd_slice_peak": dd_slice, "maxdd_vs_full_run_peak": dd_full_peak,
            "trades_entered": int(len(L)), "win_rate": float((L["R"] > 0).mean()) if len(L) else float("nan"),
            "mean_R": float(L["R"].mean()) if len(L) else float("nan"),
            "total_R": float(L["R"].sum()) if len(L) else float("nan")}


def run_summary(res: dict) -> dict:
    nav, led = res["nav"], res["ledger"]
    m = res["manifest"]
    return {"label": m["label"], "is_live_book": m["is_live_book"], "differs_on": m["differs_on"],
            "membership": m["membership"], "config_hash": m["config_hash"], "data_vintage": m["data_vintage"],
            "code_sha": m["code_sha"], "config": res["config"],
            "engine_reported": {"sharpe": res["sharpe"], "cagr": res["cagr"], "maxdd": res["maxdd"],
                                "n_trades": res["n_trades"]},
            "full": window_stats(nav, led, WIN_START, WIN_END),
            "2019-21": window_stats(nav, led, "2019-01-01", "2021-12-31"),
            "2022-24H1": window_stats(nav, led, "2022-01-01", WIN_END)}


# =============================================================================== B5 helpers
def iso(ts) -> tuple:
    c = pd.Timestamp(ts).isocalendar()
    return int(c.year), int(c.week)


def corr_pairs(cm: pd.DataFrame, names: list) -> list:
    out = []
    for a, b in combinations(names, 2):
        v = cm.at[a, b]
        if np.isfinite(v):
            out.append((a, b, float(v)))
    return out


def week_row(pairs: list) -> dict:
    cs = [p[2] for p in pairs]
    return {"n_pairs": len(cs), "max_corr": max(cs), "mean_corr": float(np.mean(cs)),
            **{f"has_{t}": any(c > t for c in cs) for t in THRESHOLDS}}


def aggregate(rows: list[dict]) -> dict:
    """rows: one per week with >=1 computable pair."""
    df = pd.DataFrame(rows)
    out = {"weeks_with_pairs": int(len(df))}
    for t in THRESHOLDS:
        out[f"share_weeks_pair_gt_{t}"] = float(df[f"has_{t}"].mean())
        out[f"n_weeks_pair_gt_{t}"] = int(df[f"has_{t}"].sum())
    out["mean_pairwise_corr_all"] = float(df["mean_corr"].mean())
    out["mean_max_pair_corr"] = float(df["max_corr"].mean())
    for lab, sel in (("drawdown", df["mkt_dd_flag"] == True), ("calm", df["mkt_dd_flag"] == False)):  # noqa: E712
        d = df[sel]
        out[f"{lab}_weeks"] = int(len(d))
        out[f"{lab}_mean_pairwise_corr"] = float(d["mean_corr"].mean()) if len(d) else None
        for t in THRESHOLDS:
            out[f"{lab}_share_pair_gt_{t}"] = float(d[f"has_{t}"].mean()) if len(d) else None
    dd, ca = df[df["mkt_dd_flag"] == True]["mean_corr"].to_numpy(), df[df["mkt_dd_flag"] == False]["mean_corr"].to_numpy()  # noqa: E712
    if len(dd) > 1 and len(ca) > 1:
        rng = np.random.default_rng(SEED)
        diffs = [rng.choice(dd, len(dd)).mean() - rng.choice(ca, len(ca)).mean() for _ in range(N_BOOT)]
        out["dd_minus_calm_mean_corr"] = float(dd.mean() - ca.mean())
        out["dd_minus_calm_ci95_week_bootstrap"] = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
    return out


def sym_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson of the SYMMETRISED pair list (each pair enters as (a,b) and (b,a)) -- orientation-free."""
    if len(a) < 3:
        return float("nan")
    x, y = np.concatenate([a, b]), np.concatenate([b, a])
    return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else float("nan")


def sym_spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    return sym_corr(pd.Series(np.concatenate([a, b])).rank().to_numpy()[:len(a)],
                    pd.Series(np.concatenate([a, b])).rank().to_numpy()[len(a):])


def comove(pairs: pd.DataFrame) -> dict:
    if pairs.empty:
        return {"n_pairs": 0}
    a, b = pairs["R_a"].to_numpy(float), pairs["R_b"].to_numpy(float)
    return {"n_pairs": int(len(pairs)), "n_weeks": int(pairs["week"].nunique()),
            "pearson_sym": sym_corr(a, b), "spearman_sym": sym_spearman(a, b),
            "both_win_share": float(((a > 0) & (b > 0)).mean()), "both_lose_share": float(((a <= 0) & (b <= 0)).mean()),
            "mean_R_pair": float(np.mean(np.concatenate([a, b])))}


def boot_week_diff(hi: pd.DataFrame, lo: pd.DataFrame) -> list | None:
    """Cluster (by week) bootstrap CI of pearson_sym(hi) - pearson_sym(lo)."""
    if len(hi) < 6 or len(lo) < 6:
        return None
    rng = np.random.default_rng(SEED)
    gh = {w: g for w, g in hi.groupby("week")}
    gl = {w: g for w, g in lo.groupby("week")}
    kh, kl = list(gh), list(gl)
    ds = []
    for _ in range(N_BOOT):
        h = pd.concat([gh[kh[i]] for i in rng.integers(0, len(kh), len(kh))])
        l_ = pd.concat([gl[kl[i]] for i in rng.integers(0, len(kl), len(kl))])
        d = sym_corr(h["R_a"].to_numpy(float), h["R_b"].to_numpy(float)) - \
            sym_corr(l_["R_a"].to_numpy(float), l_["R_b"].to_numpy(float))
        if np.isfinite(d):
            ds.append(d)
    return [float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))] if len(ds) > 100 else None


# =============================================================================== main
def main() -> None:
    t0 = time.time()
    R94, live, load_demerger_rows, corrected_universe = runs._engine()
    from nq.data.membership import load_membership

    counts = standing_counts()
    print("standing counts:", counts)

    # ---- train-only universe, cut + asserted, shared by every run below
    cut = runs.cut_universe(corrected_universe())
    last_bar = runs.assert_within_cut(cut)
    print(f"universe: {len(cut)} names, last bar {last_bar.date()} (CUT {runs.CUT})")
    nifty = runs.load_nifty()
    assert nifty.index.max() <= pd.Timestamp(runs.CUT)

    # =========================================================================== B7
    print("\n[B7] base replay (DEFAULT_CONFIG, LIVE BOOK) ...")
    base = runs.replay(runs.DEFAULT_CONFIG, use_cache=False, ohlcv=cut)
    assert base["manifest"]["label"] == "LIVE BOOK" and base["manifest"]["is_live_book"], base["manifest"]
    assert base["config"] == runs.normalize_config(runs.DEFAULT_CONFIG) and base["config"]["pit_membership"] is True
    B7 = {"base_live_book": run_summary(base)}
    print("  base:", {k: B7["base_live_book"]["full"][k] for k in ("sharpe", "cagr_calendar", "maxdd_slice_peak", "trades_entered")})

    # bridge: the live book with every live-only SWITCH turned back to the frozen-0094 default
    # (all grades, no ext/risk/notional cap, engine default exit), on the same window/universe/membership.
    bridge_cfg = {"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None, "exit": "base"}
    print("[B7] bridge replay (frozen-0094 switches, train window, PIT) ...")
    bridge = runs.replay(bridge_cfg, use_cache=False, ohlcv=cut)
    B7["bridge_frozen0094_switches_on_train_window"] = run_summary(bridge)
    print("  bridge label:", bridge["manifest"]["label"], bridge["manifest"]["differs_on"])
    print("  bridge:", {k: B7["bridge_frozen0094_switches_on_train_window"]["full"][k] for k in ("sharpe", "cagr_calendar", "maxdd_slice_peak", "trades_entered")})

    # record-spec replica on TRAIN-CUT data: the exact call tests/test_swing_adapter.py and build_substrate.guard()
    # use for the 1.132 / 255 run of record (default prep, mem=PIT, all levers at engine defaults), started 2017-01-01,
    # but fed the cut universe. The engine is causal, so slices that end before the cut must reproduce the record's
    # published slices (2017-18 +1.17, 2019-21 +1.05) -- that is the validity check on this whole comparison.
    # 2017-18 is shown ONLY as that check; it is train data (before the cut) and is not part of the reported window.
    P0 = R94.prep_weekly_rank(cut)
    led0: list = []
    out0 = R94.backtest(P0, load_membership(), ledger=led0, start="2017-01-01")
    nav0 = pd.Series(out0["curve"], dtype=float)
    nav0.index = pd.DatetimeIndex(nav0.index).normalize()
    nav0 = nav0[~nav0.index.duplicated(keep="last")].sort_index()
    L0 = pd.DataFrame(led0)
    B7["record_spec_replica_on_cut_data"] = {
        "spec": "R94.backtest(prep_weekly_rank(cut), load_membership(), start='2017-01-01'), engine defaults, all grades, no demerger events",
        "n_trades_2017_to_cut": int(len(L0)), "engine_sharpe_2017_to_cut": float(out0["sharpe"]),
        "slice_2017-18_reproduction_check": window_stats(nav0, L0, "2017-01-01", "2018-12-31"),
        "2019-21": window_stats(nav0, L0, "2019-01-01", "2021-12-31"),
        "2022-24H1": window_stats(nav0, L0, "2022-01-01", WIN_END),
        "full_window_2019_to_cut": window_stats(nav0, L0, WIN_START, WIN_END)}
    r0 = B7["record_spec_replica_on_cut_data"]
    print("  replica 2017-18 / 2019-21 sharpe:", round(r0["slice_2017-18_reproduction_check"]["sharpe"], 3), round(r0["2019-21"]["sharpe"], 3))

    # =========================================================================== B5
    print("\n[B5] prep + A-sets ...")
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    events = R94.build_demerger_events(cut, load_demerger_rows(), **live["LIVE_PREP"])
    mem = load_membership()
    cfg_unc = {**runs.DEFAULT_CONFIG, "uncapped": True}

    A1 = R94.grade_a_entries(P)                                                 # live Grade-A (unfiltered rank)
    A2 = R94.grade_a_entries(P, mem=mem, filter_before_rank=True)               # filter-before-rank variant

    def uncapped_ledger(a_grade) -> pd.DataFrame:
        """Same call pattern as runs.replay (uncapped live config) with an explicit a_grade set."""
        led: list = []
        R94.backtest(P, mem, ledger=led, a_grade=a_grade, **runs.engine_kwargs(cfg_unc),
                     demerger_events=events, position_log=[], event_log=[])
        return pd.DataFrame(led)

    print("[B5] uncapped live-config replay (replay()) ...")
    unc = runs.replay(cfg_unc, use_cache=False, ohlcv=cut)
    assert unc["manifest"]["differs_on"] == ["uncapped"], unc["manifest"]
    L1 = unc["ledger"]
    L1b = uncapped_ledger(A1)                                                    # parity check of the helper
    assert len(L1b) == len(L1) and abs(float(L1b["R"].sum()) - float(L1["R"].sum())) < 1e-9, "helper != replay"
    print("[B5] uncapped ledger for the filter-before-rank A-set ...")
    L2 = uncapped_ledger(A2)
    ledgers = {"live_grade_a": L1, "filter_before_rank": L2}
    manifests_b5 = {"uncapped_live_grade_a": {"label": unc["manifest"]["label"], "differs_on": unc["manifest"]["differs_on"],
                                              "config_hash": unc["manifest"]["config_hash"]},
                    "uncapped_filter_before_rank": {
                        "label": unc["manifest"]["label"], "differs_on": unc["manifest"]["differs_on"] + ["a_grade=filter_before_rank"],
                        "note": "same engine call as replay(uncapped); only the A-set passed as a_grade differs "
                                "(replay has no filter_before_rank key). Not a lab config; not LIVE BOOK either."}}

    # ---- returns matrix (PIT: every correlation below slices it at <= the signal-week close)
    ret = pd.concat({t: pd.Series(np.asarray(s["c"], float), index=pd.DatetimeIndex(s["dates"])).pct_change()
                     for t, s in P.items()}, axis=1).sort_index()
    ret = ret[~ret.index.duplicated(keep="last")]
    assert ret.index.max() <= pd.Timestamp(runs.CUT)
    nifty_dd = (nifty / nifty.rolling(252, min_periods=252).max() - 1.0)

    # ---- pool of ALL signals per setup week (the set the top-5 was ranked from) and the two A-sets
    def week_of(t, e0):
        return iso(P[t]["dates"][e0])
    pool = defaultdict(list)
    for t, s in P.items():
        for e0 in s["entry_win"]:
            d0 = pd.Timestamp(P[t]["dates"][e0])
            if pd.Timestamp(WIN_START) <= d0 <= pd.Timestamp(WIN_END) and e0 >= 1:
                pool[week_of(t, e0)].append((t, e0))
    a_by_week = {k: defaultdict(list) for k in ("live_grade_a", "filter_before_rank")}
    for name, A in (("live_grade_a", A1), ("filter_before_rank", A2)):
        for t, e0 in A:
            d0 = pd.Timestamp(P[t]["dates"][e0])
            if pd.Timestamp(WIN_START) <= d0 <= pd.Timestamp(WIN_END) and e0 >= 1:
                a_by_week[name][week_of(t, e0)].append((t, e0))

    rng = np.random.default_rng(SEED)
    rows = {k: [] for k in a_by_week}
    rows_nd = {k: [] for k in a_by_week}
    n_dup_weeks, n_dup_names = defaultdict(int), defaultdict(int)
    pair_rows = {k: [] for k in a_by_week}
    control_draws = []                                   # per-draw share of weeks with a pair > thr (pool, size 5)
    ctrl_week_rows = defaultdict(list)                   # draw -> list of week rows
    ctrl_nd_rows = defaultdict(list)                     # same, alias-de-duplicated pool
    skipped = defaultdict(int)
    for wk in sorted(pool):
        members = pool[wk]
        cutoff = max(pd.Timestamp(P[t]["dates"][e0 - 1]) for t, e0 in members)    # signal-week last session
        assert cutoff < min(pd.Timestamp(P[t]["dates"][e0]) for t, e0 in members)  # strictly before the entry week
        W = ret[ret.index <= cutoff].iloc[-CORR_WINDOW:]
        assert W.index.max() <= cutoff
        tick = sorted({t for t, _ in members})
        cm = W[tick].corr(min_periods=CORR_MIN_OBS)
        nd = nifty_dd[nifty_dd.index <= cutoff]
        dd_val = float(nd.iloc[-1]) if len(nd) and np.isfinite(nd.iloc[-1]) else None
        dd_flag = None if dd_val is None else bool(dd_val <= DD_LEVEL)
        for name in a_by_week:
            ents = a_by_week[name].get(wk, [])
            names = sorted({t for t, _ in ents})
            if len(names) < 2:
                skipped[name] += 1
                continue
            pairs = corr_pairs(cm, names)
            if not pairs:
                skipped[name] += 1
                continue
            r = {"week": f"{wk[0]}-W{wk[1]:02d}", "cutoff": str(cutoff.date()), "n_names": len(names),
                 "mkt_dd": dd_val, "mkt_dd_flag": dd_flag, **week_row(pairs)}
            rows[name].append(r)
            # alias-duplicate handling: corr > DUP_CORR means the same company under two symbols (renamed /
            # merged tickers stitched in the corrected universe). Drop one leg per such pair (the non-member leg
            # if there is one) and re-measure the week on the de-duplicated set.
            emap0 = {t: e0 for t, e0 in ents}
            drop = set()
            for a, b, c in pairs:
                if c > DUP_CORR:
                    ia = R94.ticker_in_index_on(a, pd.Timestamp(P[a]["dates"][emap0[a]]).date(), mem)
                    drop.add(b if ia else a)
            names_nd = [n for n in names if n not in drop]
            pairs_nd = corr_pairs(cm, names_nd) if len(names_nd) >= 2 else []
            if pairs_nd:
                rows_nd[name].append({"week": r["week"], "cutoff": r["cutoff"], "n_names": len(names_nd),
                                      "mkt_dd": dd_val, "mkt_dd_flag": dd_flag, **week_row(pairs_nd)})
            n_dup_weeks[name] += int(bool(drop))
            n_dup_names[name] += len(drop)
            rmap = {}
            led = ledgers[name]
            for _, x in led.iterrows():
                rmap.setdefault((x["tkr"], iso(x["entry_date"])), float(x["R"]))
            emap = {t: e0 for t, e0 in ents}
            for a, b, c in pairs:
                ma = bool(R94.ticker_in_index_on(a, pd.Timestamp(P[a]["dates"][emap[a]]).date(), mem))
                mb = bool(R94.ticker_in_index_on(b, pd.Timestamp(P[b]["dates"][emap[b]]).date(), mem))
                pair_rows[name].append({"week": r["week"], "a": a, "b": b, "corr": c, "mkt_dd_flag": dd_flag,
                                        "dup_involved": bool(a in drop or b in drop),
                                        "member_a": ma, "member_b": mb,
                                        "R_a": rmap.get((a, wk)), "R_b": rmap.get((b, wk))})
        # control: random 5 from the week's signal pool (only where the pool is larger than 5 names)
        if len(tick) > 5:
            for dr in range(N_CONTROL_DRAWS):
                pick = list(rng.choice(tick, 5, replace=False))
                pairs = corr_pairs(cm, pick)
                if pairs:
                    ctrl_week_rows[dr].append({"week": f"{wk[0]}-W{wk[1]:02d}", "mkt_dd_flag": dd_flag, **week_row(pairs)})
        # same control on the alias-de-duplicated pool (one leg of every corr > DUP_CORR pair removed)
        gone = {b for a, b, c in corr_pairs(cm, tick) if c > DUP_CORR}
        tick_nd = [t for t in tick if t not in gone]
        if len(tick_nd) > 5:
            for dr in range(N_CONTROL_DRAWS):
                pick = list(rng.choice(tick_nd, 5, replace=False))
                pairs = corr_pairs(cm, pick)
                if pairs:
                    ctrl_nd_rows[dr].append({"week": f"{wk[0]}-W{wk[1]:02d}", "mkt_dd_flag": dd_flag, **week_row(pairs)})
    # like-for-like top-5 rows restricted to weeks where the pool exceeds 5 names
    big_weeks = {f"{wk[0]}-W{wk[1]:02d}" for wk in pool if len({t for t, _ in pool[wk]}) > 5}

    B5 = {"label": "ACTIVATION-BOUND INPUT ONLY -- descriptive, zero-trial; adopts nothing, tests no rule",
          "window": [WIN_START, WIN_END], "corr_window_sessions": CORR_WINDOW, "corr_min_overlap": CORR_MIN_OBS,
          "pit_rule": "returns sliced at <= last session of the signal week (strictly before the entry week, asserted)",
          "market_drawdown_rule": f"Nifty-50 close >= {abs(DD_LEVEL):.0%} below its trailing 252-session high at the signal-week close",
          "setup_weeks_in_pool": len(pool), "weeks_skipped_lt2_names_or_no_pairs": dict(skipped),
          "variants": {}, "control_random5_from_signal_pool": {}, "matched_trade_comovement": {}}
    for name in a_by_week:
        agg = aggregate(rows[name])
        agg["mean_names_per_week"] = float(np.mean([r["n_names"] for r in rows[name]]))
        B5["variants"][name] = agg
        nd = aggregate(rows_nd[name])
        nd["mean_names_per_week"] = float(np.mean([r["n_names"] for r in rows_nd[name]]))
        nd["weeks_with_an_alias_duplicate_pair"] = int(n_dup_weeks[name])
        nd["alias_duplicate_names_dropped"] = int(n_dup_names[name])
        B5["variants"][name]["alias_deduplicated"] = nd
        agg_big = aggregate([r for r in rows[name] if r["week"] in big_weeks])
        B5["variants"][name]["restricted_to_pool_gt5_weeks"] = {k: agg_big[k] for k in agg_big if k.startswith(("share", "weeks", "mean_pairwise"))}

    # control summary: mean over draws
    def summarise_ctrl(store) -> dict:
        ctrl = [aggregate(rs) for rs in store.values()]
        return {
            "n_draws": N_CONTROL_DRAWS, "weeks_per_draw": int(np.mean([c["weeks_with_pairs"] for c in ctrl])),
            "share_weeks_pair_gt_0.5_mean": float(np.mean([c["share_weeks_pair_gt_0.5"] for c in ctrl])),
            "share_weeks_pair_gt_0.7_mean": float(np.mean([c["share_weeks_pair_gt_0.7"] for c in ctrl])),
            "mean_pairwise_corr_mean": float(np.mean([c["mean_pairwise_corr_all"] for c in ctrl])),
            "drawdown_mean_pairwise_corr_mean": float(np.nanmean([c["drawdown_mean_pairwise_corr"] for c in ctrl if c["drawdown_mean_pairwise_corr"] is not None])),
            "calm_mean_pairwise_corr_mean": float(np.nanmean([c["calm_mean_pairwise_corr"] for c in ctrl if c["calm_mean_pairwise_corr"] is not None]))}
    B5["control_random5_from_signal_pool"] = {
        "as_measured": summarise_ctrl(ctrl_week_rows), "alias_deduplicated": summarise_ctrl(ctrl_nd_rows),
        "note": "context only: 5 names drawn at random from the same week's full signal pool (weeks with >5 signal names)"}

    # ---- trade co-movement of high-corr pairs vs non-clustered pairs, matched on ticker + entry ISO week
    for name in a_by_week:
        pr = pd.DataFrame(pair_rows[name])
        n_all = len(pr)
        pr["legs_filled"] = pr["R_a"].notna().astype(int) + pr["R_b"].notna().astype(int)
        pr["bucket"] = pd.cut(pr["corr"], [-1.01, 0.5, 0.7, 1.01], labels=["<=0.5", "0.5-0.7", ">0.7"])
        fill = {str(b): {"pairs": int(len(g)), "both_legs_filled": float((g["legs_filled"] == 2).mean()),
                         "one_leg": float((g["legs_filled"] == 1).mean()), "no_leg": float((g["legs_filled"] == 0).mean()),
                         "leg_fill_rate": float(g["legs_filled"].sum() / (2 * len(g)))}
                for b, g in pr.groupby("bucket", observed=True)}
        pr["both_members"] = pr["member_a"] & pr["member_b"]
        fill_by_membership = {str(b): {"pairs": int(len(g)), "share_both_members": float(g["both_members"].mean())}
                              for b, g in pr.groupby("bucket", observed=True)}
        pr.to_csv(OUT.with_name(f"2026-10-20_cluster_pairs_{name}.csv"), index=False)     # ALL pairs (audit)
        n_dup_pairs = int((pr["corr"] > DUP_CORR).sum())
        pr = pr.dropna(subset=["R_a", "R_b"])
        out = {"share_pairs_both_legs_index_members_by_bucket": fill_by_membership, "pairs_total": int(n_all),
               "pairs_with_both_trades_matched": int(len(pr)), "alias_duplicate_pairs_corr_gt_0.98": n_dup_pairs,
               "fill_rate_by_corr_bucket": fill}
        for tag, prx in (("as_measured", pr), ("alias_deduplicated", pr[~pr["dup_involved"]])):
            sub = {}
            for t in THRESHOLDS:
                hi = prx[prx["corr"] > t]
                lo = prx[prx["corr"] <= t]
                lo_same = lo[lo["week"].isin(set(hi["week"]))]
                sub[f"corr_gt_{t}"] = {
                    "high_corr_pairs": comove(hi),
                    "control_non_clustered_same_weeks": comove(lo_same),
                    "control_non_clustered_all_weeks": comove(lo),
                    "pearson_diff_high_minus_same_week_control": (None if not (len(hi) and len(lo_same)) else
                        float(comove(hi)["pearson_sym"] - comove(lo_same)["pearson_sym"])),
                    "pearson_diff_ci95_week_bootstrap": boot_week_diff(hi, lo_same),
                }
            out[tag] = sub
        B5["matched_trade_comovement"][name] = out

    result = {"generated": "2026-10-20", "tier": "EXPLORE/MEASURE (docs/PROCESS_TIERS.md): no pre-registration, no screen row, no n_trials change",
              "standing_counts": counts, "train_only": {"cut": runs.CUT, "last_bar_seen": str(last_bar.date()), "reported_window": [WIN_START, WIN_END]},
              "manifests_b5": manifests_b5, "B7": B7, "B5": B5, "seconds": round(time.time() - t0, 1)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=lambda o: None if o is None else str(o)), encoding="utf-8")
    print(f"\nwrote {OUT} in {result['seconds']}s")


if __name__ == "__main__":
    main()
