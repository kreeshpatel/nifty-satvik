"""EXPLORE-tier (docs/PROCESS_TIERS.md tier 0): re-score the 2026-10-23 live-switch-ablation leads, and two new
fill levers, against the live book on the PATH-NOISE ENSEMBLE (nq/lab/ensemble.py, paired draws).

No pre-registration, no screen row, no n_trials change. Train window only: every price series is cut at
2024-06-30 by `nq.lab.runs.cut_universe` and the cut is asserted. The sealed judge log is never touched.

    python pipelines/diagnostics/explore_ensemble_rescore.py [N_PATHS]      # ~7s per engine run, 8 configs x N

Writes diagnostics/research/explore/2026-11-02_ensemble_rescore.md and .json.
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from nq.lab import ensemble as E  # noqa: E402
from nq.lab import runs as L  # noqa: E402
from nq.lab.stats import exclude_degenerate_stops  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "explore"
STEM = "2026-11-02_ensemble_rescore"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
SEED = E.DEFAULT_SEED
SCRATCH = Path(sys.argv[2]) if len(sys.argv) > 2 else None

REVERTED = {"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None}
# name -> (description, lab config overrides, grade_mode)
SPECS = {
    "live": ("live book (control)", {}, "default"),
    "h5": ("h5: scaled exit kept, the four caps reverted (ext_cap, grade gate, notional cap, risk cap)",
           dict(REVERTED), "default"),
    "g": ("g: all five live-only switches reverted (the bridge; engine-default exit too)",
          {**REVERTED, "exit": "base"}, "default"),
    "d6": ("D6: live + grade_a_entries(P, mem=mem, filter_before_rank=True)", {}, "filter_before_rank"),
    "rr1.0": ("min_rr_at_fill = 1.0", {"min_rr_at_fill": 1.0}, "default"),
    "rr1.5": ("min_rr_at_fill = 1.5", {"min_rr_at_fill": 1.5}, "default"),
    "whole": ("whole_shares = True (realism check)", {"whole_shares": True}, "default"),
}


def standing_counts() -> dict:
    import test_standing_counts as T
    n = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    return {"screens": T.authoritative_screens(), "sealed_opens": T.authoritative_sealed(),
            "n_trials": int(n["cumulative_n_trials"])}


def fills_realism(ctx) -> dict:
    """Unperturbed live vs whole_shares: how many fills change, entry-day share rounding."""
    R94 = L._engine()[0]
    res = {}
    for tag, extra in (("off", {}), ("on", {"whole_shares": True})):
        kw = L.engine_kwargs({**L.DEFAULT_CONFIG, **extra})
        led, plog = [], []
        out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade("default"), position_log=plog,
                           demerger_events=ctx.events, **kw)
        led, plog = pd.DataFrame(led), pd.DataFrame(plog)
        plog["date"] = pd.to_datetime(plog["date"]).dt.normalize()
        led["ed"] = pd.to_datetime(led["entry_date"]).dt.normalize()
        sh = plog.rename(columns={"tkr": "tkr", "date": "ed"})[["tkr", "ed", "shares"]]
        led = led.merge(sh, on=["tkr", "ed"], how="left")
        res[tag] = (led, out)
    a, b = res["off"][0], res["on"][0]
    ka, kb = set(zip(a["tkr"], a["ed"])), set(zip(b["tkr"], b["ed"]))
    common = a.merge(b, on=["tkr", "ed"], suffixes=("_off", "_on"))
    rel = (common["shares_off"] - common["shares_on"]) / common["shares_off"]
    return {"n_fills_off": int(len(a)), "n_fills_on": int(len(b)), "same_fill_dates": int(len(ka & kb)),
            "only_in_off": sorted(f"{t} {d.date()}" for t, d in ka - kb),
            "only_in_on": sorted(f"{t} {d.date()}" for t, d in kb - ka),
            "common_with_share_change": int((common["shares_off"] != common["shares_on"]).sum()),
            "share_rounding_rel_loss_median": float(rel.median()) if len(rel) else float("nan"),
            "share_rounding_rel_loss_max": float(rel.max()) if len(rel) else float("nan"),
            "min_shares_on": float(common["shares_on"].min()) if len(common) else float("nan"),
            "single_replay": {"sharpe_off": float(res["off"][1]["sharpe"]), "sharpe_on": float(res["on"][1]["sharpe"]),
                              "cagr_off": float(res["off"][1]["cagr"]), "cagr_on": float(res["on"][1]["cagr"])}}


def ex_degen_mean_r(ctx, cfg, grade_mode) -> dict:
    """Unperturbed per-trade mean R, raw and with degenerate stops (initial risk < 0.5% of entry) excluded."""
    m = E.run_path(cfg, ctx, grade_mode=grade_mode, keep_ledger=True)
    led = m["ledger"]
    closed = led[led["reason"] != "eos"] if len(led) else led
    ex = exclude_degenerate_stops(closed) if len(closed) else closed
    return {"n_closed": int(len(closed)), "n_degenerate": int(len(closed) - len(ex)),
            "mean_R_raw": float(closed["R"].mean()) if len(closed) else float("nan"),
            "mean_R_ex_degenerate": float(ex["R"].mean()) if len(ex) else float("nan")}


def anchor_and_rr_census(ctx) -> dict:
    """(1) Reproduce-before-trust: the unperturbed live replay on the full window must read the standing anchor
    (Sharpe 1.025 / CAGR 20.5% / MaxDD -40.1%), and its 2019-03-01 slice is what the ensemble reports.
    (2) R:R census: every in_range fill CANDIDATE the engine evaluates (funded or not) scored by `_fill_rr`
    through a recording wrapper, on a run whose floor can never bind (so it is the live book, byte for byte)."""
    R94 = L._engine()[0]
    kw = L.engine_kwargs(L.DEFAULT_CONFIG)
    led: list = []
    out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade("default"), demerger_events=ctx.events, **kw)
    full = {"sharpe": float(out["sharpe"]), "cagr": float(out["cagr"]), "maxdd": float(out["dd"]), "trades": len(led)}
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    sl = E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)
    seen: list = []
    orig = R94._fill_rr

    def rec(*a, **k):
        v = orig(*a, **k)
        seen.append(v)
        return v
    R94._fill_rr = rec
    try:
        R94.backtest(ctx.P, ctx.mem, ledger=[], a_grade=ctx.a_grade("default"), demerger_events=ctx.events,
                     **{**kw, "min_rr_at_fill": -1e9})
    finally:
        R94._fill_rr = orig
    v = np.array([x for x in seen if np.isfinite(x)], float)
    return {"full_window_2019_01_01": full, "slice_2019_03_01": {k: sl[k] for k in ("sharpe", "cagr", "maxdd", "trades")},
            "rr_census": {"n_candidate_evaluations": int(len(v)), "min": float(v.min()), "p5": float(np.percentile(v, 5)),
                          "median": float(np.median(v)), "share_below_1.0": float((v < 1.0).mean()),
                          "share_below_1.5": float((v < 1.5).mean()), "share_below_2.0": float((v < 2.0).mean()),
                          "n_below_1.0": int((v < 1.0).sum()), "n_below_1.5": int((v < 1.5).sum())}}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    counts = standing_counts()
    t0 = time.time()
    ctx = E.prepare_context()
    print("context ready", round(time.time() - t0), "s; last bar", pd.Timestamp(ctx.last_bar).date(), flush=True)
    ens, r_unp = {}, {}
    cache = SCRATCH if SCRATCH else Path(ROOT / "lab_cache" / f"rescore_{N}.pkl")
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        ens = pickle.loads(cache.read_bytes())
    for name, (desc, over, gm) in SPECS.items():
        if name in ens:
            continue
        cfg = {**L.DEFAULT_CONFIG, **over}
        ens[name] = E.replay_ensemble(cfg, n=N, seed=SEED, context=ctx, grade_mode=gm)
        s = ens[name]["summary"]["sharpe"]
        print(f"{name:6s} sharpe median {s['median']:.3f} [{s['p5']:.3f},{s['p95']:.3f}]  {ens[name]['seconds']}s "
              f"{ens[name]['manifest']['label']}", flush=True)
        cache.write_bytes(pickle.dumps(ens))
    cmp_ = {k: E.compare_ensembles(ens["live"], ens[k]) for k in SPECS if k != "live"}
    for k, (desc, over, gm) in SPECS.items():
        r_unp[k] = ex_degen_mean_r(ctx, {**L.DEFAULT_CONFIG, **over}, gm)
    realism = fills_realism(ctx)
    anchor = anchor_and_rr_census(ctx)
    payload = {
        "anchor": anchor,
        "tier": "EXPLORE (docs/PROCESS_TIERS.md tier 0)", "standing_counts": counts, "n_paths": N, "seed": SEED,
        "perturb": ens["live"]["perturb"], "skipped": ens["live"]["skipped"], "report_window": [E.REPORT_FROM, L.CUT],
        "last_bar": str(pd.Timestamp(ctx.last_bar).date()),
        "reading_rule": READING_RULE,
        "runs": {k: {"desc": SPECS[k][0], "config": ens[k]["config"], "config_hash": ens[k]["config_hash"],
                     "grade_mode": ens[k]["grade_mode"], "manifest_label": ens[k]["manifest"]["label"],
                     "differs_on": ens[k]["manifest"]["differs_on"], "summary": ens[k]["summary"],
                     "unperturbed_trade_R": r_unp[k]} for k in SPECS},
        "paired_vs_live": {k: {"summary": v["summary"], "share_better": v["share_better"], "n_paired": v["n_paired"],
                               "robust_to_path_noise": v["robust"]} for k, v in cmp_.items()},
        "whole_shares_realism": realism,
        "paths": {k: json.loads(ens[k]["paths"].to_json(orient="records")) for k in SPECS},
    }
    (OUT / f"{STEM}.json").write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    (OUT / f"{STEM}.md").write_text(render(payload, ens, cmp_), encoding="utf-8")
    print("wrote", OUT / f"{STEM}.md", round(time.time() - t0), "s")
    return 0


READING_RULE = ("A candidate is 'robust to path noise' only if its 5th-percentile paired dSharpe vs live is > 0; "
                "otherwise it is 'inside path noise'. 'Robust' means 'worth a pre-registered trial', never adoption: "
                "it is still train-window in-sample, with a statistical half-width of about 0.59 (n_eff about 37) on "
                "top of path noise.")


def _p(x, d=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%"


def _pp(x):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.1f}pp"


def _n(x, d=2, sign=False):
    return "n/a" if x is None or not np.isfinite(x) else (f"{x:+.{d}f}" if sign else f"{x:.{d}f}")


def render(pl: dict, ens: dict, cmp_: dict) -> str:
    c = pl["standing_counts"]
    L_ = []
    w = L_.append
    w("# 2026-11-02 - Path-noise ensemble re-score of the live-switch leads and two fill levers\n")
    w("**Tier:** EXPLORE (`docs/PROCESS_TIERS.md`, tier 0). No pre-registration, no screen row, no `n_trials` change. "
      "Descriptive: it adopts nothing and recommends no change to the live config; any change is a CONFIRM-tier "
      "decision (`forward/prereg_swing.md`).\n")
    w(f"**Standing counts (read from the ledgers by the script):** screens **{c['screens']}** - sealed opens "
      f"**{c['sealed_opens']}** - n_trials **{c['n_trials']}**. Unchanged by this note.\n")
    w("## Reading rule (fixed before any number was computed)\n")
    w(f"> {pl['reading_rule']}\n")
    w("## Method\n")
    w(f"`nq/lab/ensemble.py`, {pl['n_paths']} paths per config, seed {pl['seed']}, the SAME perturbation draws for every "
      "config (paired). Perturbations: cost jitter U(-10bp,+10bp) added to every cost leg by rebinding `R94._cost_leg` "
      "in-process; start date drawn from the first 20 trading days of 2019. Every path is reported on "
      f"**{pl['report_window'][0]}..{pl['report_window'][1]}** as a continuous slice of its own NAV (not a fresh-capital "
      "re-run). Fill-order tie jitter: " + pl["skipped"][0] + ". PIT membership on; prices cut at 2024-06-30 "
      f"and the cut asserted (last bar seen {pl['last_bar']}); nothing in 2024-07-01..2026-06-30 is read; "
      "the sealed judge log is not touched. Per-trade mean R applies the degenerate-stop rule "
      "(`nq/lab/stats`, initial risk < 0.5% of entry excluded).\n")
    w("**Manifest labels** (`nq/runner/manifest`):\n")
    for k, r in pl["runs"].items():
        w(f"- `{k}`: {r['manifest_label']}" + (f" (differs on: {', '.join(r['differs_on'])})" if r["differs_on"] else ""))
    w("")
    a = pl["anchor"]
    f_, s_, rc = a["full_window_2019_01_01"], a["slice_2019_03_01"], a["rr_census"]
    w("## Anchor reproduction (reproduce-before-trust)\n")
    w(f"- Unperturbed live replay, full window 2019-01-01..2024-06-28: Sharpe {_n(f_['sharpe'], 3)}, CAGR {_p(f_['cagr'])}, "
      f"MaxDD {_p(f_['maxdd'])}, {f_['trades']} trades (the standing anchor 1.025 / 20.5% / -40.1%).")
    w(f"- The same run read as the ensemble reads it (continuous slice from {pl['report_window'][0]}): Sharpe "
      f"{_n(s_['sharpe'], 3)}, CAGR {_p(s_['cagr'])}, MaxDD {_p(s_['maxdd'])}, {s_['trades']} trades. The ensemble medians "
      "below are on this slice, so they are not comparable to the 1.025 full-window anchor, only to each other.")
    w(f"- R:R census of every in_range fill candidate the engine evaluated on the live book ({rc['n_candidate_evaluations']} "
      f"evaluations, funded or not): median {_n(rc['median'])}, 5th pct {_n(rc['p5'])}, min {_n(rc['min'])}; "
      f"below 1.0: {rc['n_below_1.0']} ({_p(rc['share_below_1.0'])}); below 1.5: {rc['n_below_1.5']} ({_p(rc['share_below_1.5'])}); "
      f"below 2.0: {_p(rc['share_below_2.0'])}. A floor can only bind where this census puts mass beneath it.\n")
    w("## Each book's own path-noise band (median [5th, 95th] over the paths)\n")
    w("| run | Sharpe | CAGR | MaxDD | trades | mean R ex degen (unperturbed) |")
    w("|---|---|---|---|---|---|")
    for k, r in pl["runs"].items():
        s = r["summary"]
        f = lambda m, fm: f"{fm(s[m]['median'])} [{fm(s[m]['p5'])}, {fm(s[m]['p95'])}]"
        w(f"| **{k}** | {f('sharpe', _n)} | {f('cagr', _p)} | {f('maxdd', _p)} | {f('trades', lambda x: _n(x, 0))} "
          f"| {_n(r['unperturbed_trade_R']['mean_R_ex_degenerate'], 2, True)} (n={r['unperturbed_trade_R']['n_closed']}, "
          f"{r['unperturbed_trade_R']['n_degenerate']} degenerate) |")
    w("")
    w("## Paired differences vs live (candidate minus live, same draws)\n")
    w("| candidate | paired median dSharpe | 5-95% band | share of paths better | verdict | dMaxDD band (median) | dCAGR band (median) | median dTrades |")
    w("|---|---|---|---|---|---|---|---|")
    for k, v in pl["paired_vs_live"].items():
        s = v["summary"]
        ds, dd, dc, dt = s["sharpe"], s["maxdd"], s["cagr"], s["trades"]
        verdict = "robust to path noise" if v["robust_to_path_noise"] else "inside path noise"
        w(f"| **{k}** | {_n(ds['median'], 2, True)} | [{_n(ds['p5'], 2, True)}, {_n(ds['p95'], 2, True)}] | "
          f"{v['share_better'] * 100:.0f}% | {verdict} | [{_pp(dd['p5'])}, {_pp(dd['p95'])}] ({_pp(dd['median'])}) | "
          f"[{_pp(dc['p5'])}, {_pp(dc['p95'])}] ({_pp(dc['median'])}) | {_n(dt['median'], 0, True)} |")
    w("\n(Positive dMaxDD = shallower drawdown. n_paired = " + ", ".join(
        f"{k}: {v['n_paired']}" for k, v in pl["paired_vs_live"].items()) + ".)\n")
    w("## Per-trade mean R, paired (ex degenerate stops, medians over paths)\n")
    w("| candidate | median dMeanR (ex degenerate) | 5-95% band | median dMeanR (raw) |")
    w("|---|---|---|---|")
    for k, v in pl["paired_vs_live"].items():
        a, b = v["summary"]["mean_R_ex_degen"], v["summary"]["mean_R"]
        w(f"| {k} | {_n(a['median'], 2, True)} | [{_n(a['p5'], 2, True)}, {_n(a['p95'], 2, True)}] | {_n(b['median'], 2, True)} |")
    w("")
    r = pl["whole_shares_realism"]
    w("## whole_shares realism check (unperturbed, live vs whole_shares)\n")
    w(f"- Fills: {r['n_fills_off']} (fractional) vs {r['n_fills_on']} (whole shares); {r['same_fill_dates']} fills share the "
      f"same ticker and entry date; only in fractional: {len(r['only_in_off'])}; only in whole-share: {len(r['only_in_on'])}.")
    w(f"- Of the common fills, {r['common_with_share_change']} change size. Entry-day share rounding loss: median "
      f"{_p(r['share_rounding_rel_loss_median'], 2)}, max {_p(r['share_rounding_rel_loss_max'], 2)}; smallest whole-share "
      f"position {_n(r['min_shares_on'], 0)} shares.")
    sr = r["single_replay"]
    w(f"- Single-replay Sharpe {_n(sr['sharpe_off'], 3)} -> {_n(sr['sharpe_on'], 3)}, CAGR {_p(sr['cagr_off'])} -> "
      f"{_p(sr['cagr_on'])} (full window from 2019-01-01, one path each; the paired ensemble row above is the "
      "noise-aware number). This is about record fidelity, not an edge.\n")
    return "\n".join(L_) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
