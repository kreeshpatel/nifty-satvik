"""Live-switch ablation -- EXPLORE / MEASURE tier (docs/PROCESS_TIERS.md tiers 0-1).

No pre-registration, no screen row, no n_trials change. Descriptive: it decomposes the live-vs-bridge gap
(1.025 vs 1.503 Sharpe, diagnostics/research/engine_assumptions/2026-10-20_cluster_and_anchor.md) into the
five live-only switches. It adopts nothing and recommends no config change.

TRAIN ONLY. Every price series is cut at nq.lab.runs.CUT (2024-06-30) BEFORE the engine sees it and the cut
is asserted. Reported window 2019-01-01..2024-06-30. The sealed judge log is never touched.

Runs (capped book, PIT membership, same plumbing as the bridge = nq.lab.runs.replay):
  a  live (control)                       b-f  live with ONE switch reverted
  g  all five reverted (the bridge)       h    all reverted except ONE (leave-one-in), x5
  i  live + D6 filter-before-rank A-set   (custom backtest call; parity-checked against the control)

Run:  python pipelines/diagnostics/explore_live_switch_ablation.py     (~13 runs x ~25 s)
Out:  diagnostics/research/explore/2026-10-23_live_switch_ablation.json
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from nq.lab import runs  # noqa: E402
from nq.validation.metrics import sortino  # noqa: E402

try:                                                  # declared R-sanity rule (nq/lab/stats.py) if on this branch
    from nq.lab.stats import exclude_degenerate_stops, r_sanity_flags  # noqa: E402
    RULE_SOURCE = "nq.lab.stats"
except ImportError:                                   # mirror of the rule declared in e3eae32 (flag only, engine untouched)
    RULE_SOURCE = "inline mirror of nq.lab.stats (commit e3eae32; not yet on main)"

    def r_sanity_flags(ledger: pd.DataFrame, *, min_risk_frac: float = 0.005, r_abs_cap: float = 20.0) -> pd.DataFrame:
        out = ledger.copy()
        entry = out["entry"].astype(float)
        risk0 = (entry - out["stop0"].astype(float)) / entry
        out["risk0_frac"] = risk0
        out["degenerate_stop"] = (risk0 < float(min_risk_frac)) & risk0.notna()
        out["extreme_R"] = (out["R"].astype(float).abs() > float(r_abs_cap)) & out["R"].notna()
        out["r_flagged"] = out["degenerate_stop"] | out["extreme_R"]
        return out

    def exclude_degenerate_stops(ledger: pd.DataFrame, *, min_risk_frac: float = 0.005) -> pd.DataFrame:
        f = r_sanity_flags(ledger, min_risk_frac=min_risk_frac)
        return ledger.loc[~f["degenerate_stop"].to_numpy()].copy()

OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-10-23_live_switch_ablation.json"
WIN_START, WIN_END = "2019-01-01", runs.CUT
SWITCHES = ("ext_cap", "grade_gate", "max_notional_pct", "max_risk_pct", "exit")
REVERTED = {"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None, "exit": "base"}
METRICS = ("sharpe", "cagr", "maxdd", "calmar", "sortino")


def standing_counts() -> dict:
    nt = json.loads((ROOT / "diagnostics/research/n_trials.json").read_text(encoding="utf-8"))
    led = (ROOT / "diagnostics/research/label_screen_ledger.md").read_text(encoding="utf-8")
    return {"screens": len(re.findall(r"^\| \d+ \|", led, re.M)), "sealed_opens": len(re.findall(r"^\| S\d+ \|", led, re.M)),
            "n_trials": int(nt["cumulative_n_trials"]),
            "source": "diagnostics/research/n_trials.json + diagnostics/research/label_screen_ledger.md"}


def window_stats(nav: pd.Series, ledger: pd.DataFrame, start: str, end: str) -> dict:
    """Continuous SLICE of one full-run NAV (never a fresh-capital re-run)."""
    idx = pd.DatetimeIndex(nav.index)
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    prior = nav[idx < s]
    sub = nav[(idx >= s) & (idx <= e)]
    base = sub if prior.empty else pd.concat([prior.iloc[[-1]], sub])
    r = base.pct_change().dropna()
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan")
    years = (sub.index[-1] - base.index[0]).days / 365.25
    cagr = float((base.iloc[-1] / base.iloc[0]) ** (1 / years) - 1)
    dd = float((base / base.cummax() - 1).min())
    led = ledger.copy()
    led["entry_date"] = pd.to_datetime(led["entry_date"])
    L = led[(led["entry_date"] >= s) & (led["entry_date"] <= e)]
    return {"sharpe": sh, "sortino": float(sortino(r.to_numpy())), "cagr": cagr, "maxdd": dd,
            "calmar": float(cagr / abs(dd)) if dd < 0 else float("nan"), "trades_entered": int(len(L)), "n_returns": int(len(r))}


def year_returns(nav: pd.Series) -> dict:
    out, prev = {}, None
    for y in sorted(set(nav.index.year)):
        seg = nav[nav.index.year == y]
        start = prev if prev is not None else seg.iloc[0]
        out[str(y) + ("H1" if y == 2024 else "")] = float(seg.iloc[-1] / start - 1)
        prev = float(seg.iloc[-1])
    return out


def summarise(name: str, desc: str, res: dict, n_study: int, manifest_label: str, differs_on: list) -> dict:
    nav, led, plog = res["nav"], res["ledger"], res["position_log"]
    full = window_stats(nav, led, WIN_START, WIN_END)
    dsr = runs.deflated_sharpe(full["sharpe"], full["n_returns"], n_study)
    seats = plog.groupby("date")["tkr"].nunique().reindex(pd.DatetimeIndex(nav.index)).fillna(0)
    seats = seats[(seats.index >= pd.Timestamp(WIN_START)) & (seats.index <= pd.Timestamp(WIN_END))]
    yrs = year_returns(nav)
    worst = min(yrs, key=yrs.get)
    flags = r_sanity_flags(led)
    deg = flags[flags["degenerate_stop"]]
    kept = exclude_degenerate_stops(led)
    return {"name": name, "desc": desc, "manifest_label": manifest_label, "differs_on": differs_on,
            "config": res["config"], "config_hash": res["config_hash"],
            "engine_reported": {"sharpe": res["sharpe"], "cagr": res["cagr"], "maxdd": res["maxdd"], "n_trades": res["n_trades"]},
            "full": full, "deflated_sharpe": dsr, "avg_seats_held": float(seats.mean()),
            "2019-21": window_stats(nav, led, "2019-01-01", "2021-12-31"),
            "2022-24H1": window_stats(nav, led, "2022-01-01", WIN_END),
            "year_returns": yrs, "worst_year": {"year": worst, "return": yrs[worst]},
            "mean_R_raw": float(led["R"].mean()), "n_degenerate_stops": int(len(deg)),
            "degenerate_trades": [{"tkr": r.tkr, "entry_date": str(pd.Timestamp(r.entry_date).date()), "R": float(r.R),
                                   "risk0_frac": float(r.risk0_frac)} for r in deg.itertuples()],
            "mean_R_excl_degenerate": float(kept["R"].mean()), "n_trades_excl_degenerate": int(len(kept)),
            "win_rate": float((led["R"] > 0).mean())}


def main() -> None:
    t0 = time.time()
    R94, live, load_demerger_rows, corrected_universe = runs._engine()
    from nq.data.membership import load_membership
    counts = standing_counts()
    print("standing counts:", counts)
    cut = runs.cut_universe(corrected_universe())
    last_bar = runs.assert_within_cut(cut)
    assert last_bar <= pd.Timestamp(runs.CUT)
    print(f"universe {len(cut)} names, last bar {last_bar.date()} (CUT {runs.CUT})")
    scratch = Path(tempfile.mkdtemp()) / "lab_runs.jsonl"      # keep the lab multiplicity meter untouched

    names = {"ext_cap": "no ext_cap", "grade_gate": "grade gate off (all grades)",
             "max_notional_pct": "max_notional_pct to frozen default (None)",
             "max_risk_pct": "max_risk_pct to frozen default (None)", "exit": "engine-default exit instead of config P"}
    specs = [("a_live", "live control (DEFAULT_CONFIG)", {})]
    for k in SWITCHES:
        specs.append((f"b_revert_{k}", f"live, ONLY {names[k]}", {k: REVERTED[k]}))
    specs.append(("g_all_reverted", "all five switches reverted (the bridge)", dict(REVERTED)))
    for k in SWITCHES:
        specs.append((f"h_only_{k}_live", f"all reverted EXCEPT {k} kept live",
                      {j: REVERTED[j] for j in SWITCHES if j != k}))
    n_study = len(specs) + 1                                    # + (i)
    print("configs in this study:", n_study)

    results, order, store = {}, [], {}
    for name, desc, over in specs:
        cfg = {**runs.DEFAULT_CONFIG, **over}
        res = runs.replay(cfg, use_cache=False, ohlcv=cut, runs_path=scratch)
        m = res["manifest"]
        print(f"{name:32s} sharpe {res['sharpe']:.3f} cagr {res['cagr']:.3f} dd {res['maxdd']:.3f} n {res['n_trades']} "
              f"[{m['label']}] differs_on={m['differs_on']}", flush=True)
        store[name] = res
        results[name] = summarise(name, desc, res, n_study, m["label"], m["differs_on"])
        order.append(name)
    a = store["a_live"]
    assert a["manifest"]["is_live_book"], a["manifest"]
    assert set(store["g_all_reverted"]["manifest"]["differs_on"]) == {"ext_cap", "grade_gate", "max_notional_pct", "max_risk_pct", "scaled_exit"}, store["g_all_reverted"]["manifest"]

    # ---- (i) D6 filter-before-rank: same call as replay(), explicit A-set. Parity first.
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    as_of = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=None)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **{**live["LIVE_PREP"], "as_of": as_of})
    mem = load_membership()
    kw = runs.engine_kwargs(runs.DEFAULT_CONFIG)

    def custom(a_grade) -> dict:
        led, plog, elog = [], [], []
        out = R94.backtest(P, mem, ledger=led, a_grade=a_grade, **kw, demerger_events=events, position_log=plog, event_log=elog)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        nav = nav[nav.index >= pd.Timestamp(runs.DEFAULT_CONFIG["start"])]
        r = nav.pct_change().dropna()
        return {"config": runs.normalize_config(runs.DEFAULT_CONFIG), "config_hash": "custom-a_grade",
                "nav": nav, "ledger": pd.DataFrame(led), "position_log": pd.DataFrame(plog),
                "sharpe": float(r.mean() / r.std() * np.sqrt(252)), "maxdd": float((nav / nav.cummax() - 1).min()),
                "cagr": float(out["cagr"]), "n_trades": len(led)}
    par = custom(R94.grade_a_entries(P))
    assert abs(par["sharpe"] - a["sharpe"]) < 1e-12 and par["n_trades"] == a["n_trades"] and par["nav"].equals(a["nav"]), \
        "custom call path != replay (control)"
    print("parity: custom call with the default A-set reproduces the control exactly")
    ri = custom(R94.grade_a_entries(P, mem=mem, filter_before_rank=True))
    print(f"{'i_d6_filter_before_rank':32s} sharpe {ri['sharpe']:.3f} cagr {ri['cagr']:.3f} dd {ri['maxdd']:.3f} n {ri['n_trades']}")
    results["i_d6_filter_before_rank"] = summarise(
        "i_d6_filter_before_rank", "live + R94.grade_a_entries(P, mem=mem, filter_before_rank=True)", ri, n_study,
        "NOT LIVE BOOK (a_grade=filter_before_rank; replay has no such key)", ["a_grade=filter_before_rank"])
    order.append("i_d6_filter_before_rank")

    # ---- attribution
    A, G = results["a_live"]["full"], results["g_all_reverted"]["full"]
    gap = {m: G[m] - A[m] for m in METRICS}
    one_off = {k: {m: results[f"b_revert_{k}"]["full"][m] - A[m] for m in METRICS} for k in SWITCHES}
    leave_in = {k: {m: results[f"h_only_{k}_live"]["full"][m] - G[m] for m in METRICS} for k in SWITCHES}
    attribution = {"gap_all_reverted_minus_live": gap, "one_off_revert_minus_live": one_off,
                   "leave_one_in_minus_all_reverted": leave_in,
                   "sum_of_one_offs": {m: float(sum(one_off[k][m] for k in SWITCHES)) for m in METRICS},
                   "sum_of_leave_one_in": {m: float(sum(leave_in[k][m] for k in SWITCHES)) for m in METRICS},
                   "interaction_all_minus_sum_one_offs": {m: float(gap[m] - sum(one_off[k][m] for k in SWITCHES)) for m in METRICS},
                   "d6_minus_live": {m: results["i_d6_filter_before_rank"]["full"][m] - A[m] for m in METRICS}}
    out = {"label": "EXPLORE / MEASURE -- descriptive, zero-trial; adopts nothing", "standing_counts": counts,
           "window": [WIN_START, WIN_END], "data_vintage": str(last_bar.date()), "n_configs_in_study": n_study,
           "deflation": "nq.lab.runs.deflated_sharpe(sharpe, n_returns, n_trials=n_configs_in_study); per-window basis",
           "r_sanity_rule": {"source": RULE_SOURCE, "degenerate_stop": "initial risk (entry-stop0)/entry < 0.5%",
                             "extreme_R": "|R| > 20 review flag only (not excluded)",
                             "scope": "applied to per-trade mean R only; NAV / Sharpe / CAGR unchanged (engine untouched)"},
           "noise_caveats": {"delta_sharpe_halfwidth_n_eff37": 0.59, "single_replay_path_noise_sharpe": 0.2},
           "manifest_code_sha": a["manifest"]["code_sha"], "runs": results, "order": order, "attribution": attribution,
           "seconds": round(time.time() - t0, 1)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("wrote", OUT, f"({out['seconds']}s)")


if __name__ == "__main__":
    main()
