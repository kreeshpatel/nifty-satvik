"""EXPLORE (tier 0): 20-path paired ensemble of the breakeven-stop leads, D6 and h5 against the live book.

Follows 2026-11-03_giveback_breakeven.md (single-path leads) and 2026-11-02_ensemble_rescore.md (2 paths only).
READING RULE, fixed before any number: a candidate is 'robust to path noise' only if its 5th-percentile paired
dSharpe vs live is > 0; 'robust' means 'worth a pre-registered trial at the 2027-01-01 review', never adoption
(train-window in-sample, statistical half-width ~0.59 on top of path noise). No screen row, no n_trials change.
Same draws for every config (nq.lab.ensemble.draw_perturbations), PIT membership, prices cut at 2024-06-30.

    python pipelines/diagnostics/explore_ensemble_breakeven_d6.py [n_paths]
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
from nq.lab import ensemble as E  # noqa: E402
from nq.lab import runs as L  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
REVERTED = {"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None}
# name -> (lab config overrides, grade_mode, scaled_exit additions)
SPECS = {
    "live": ({}, "default", {}),
    "be1.0": ({}, "default", {"lockin_mfe": 1.0, "lockin_at": 0.0}),
    "be1.5": ({}, "default", {"lockin_mfe": 1.5, "lockin_at": 0.0}),
    "d6": ({}, "filter_before_rank", {}),
    "h5": (dict(REVERTED), "default", {}),
}
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-03_ensemble_breakeven_d6.json"


def run(cfg_over, grade_mode, lock, ctx, d):
    R94 = L._engine()[0]
    cfg = {**L.normalize_config(cfg_over), "start": str(d["start"])}
    kw = L.engine_kwargs(cfg)
    if lock:
        kw["scaled_exit"] = {**kw["scaled_exit"], **lock}
    led: list = []
    with E.cost_jitter(float(d["cost_delta"])):
        out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade(grade_mode) if cfg["grade_gate"] else None,
                           **kw, demerger_events=ctx.events)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    return E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)


def main() -> int:
    ctx = E.prepare_context()
    draws = E.draw_perturbations(N, E.DEFAULT_SEED)
    paths = {k: [] for k in SPECS}
    for _, d in draws.iterrows():
        for k, (over, gm, lock) in SPECS.items():
            paths[k].append(run(over, gm, lock, ctx, d))
        print("path", int(d["path"]) + 1, "/", N, {k: round(v[-1]["sharpe"], 3) for k, v in paths.items()}, flush=True)
    df = {k: pd.DataFrame(v) for k, v in paths.items()}
    q = lambda v: {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}
    res = {"tier": "EXPLORE", "n_paths": N, "seed": E.DEFAULT_SEED, "report_from": E.REPORT_FROM, "cut": L.CUT,
           "last_bar": str(pd.Timestamp(ctx.last_bar).date()), "rule": "robust iff p5 paired dSharpe > 0",
           "bands": {k: {m: q(v[m]) for m in ("sharpe", "cagr", "maxdd", "trades")} for k, v in df.items()}, "paired": {}}
    for k in SPECS:
        if k == "live":
            continue
        ds = df[k]["sharpe"] - df["live"]["sharpe"]
        res["paired"][k] = {"dSharpe": q(ds), "share_better": float((ds > 0).mean()),
                            "dMaxDD_pp": q((df[k]["maxdd"] - df["live"]["maxdd"]) * 100),
                            "dCAGR_pp": q((df[k]["cagr"] - df["live"]["cagr"]) * 100),
                            "verdict": "robust to path noise" if np.percentile(ds, 5) > 0 else "inside path noise"}
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    for k, v in res["paired"].items():
        print(k, json.dumps(v, default=lambda x: round(x, 3)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
