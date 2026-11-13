"""EXPLORE (tier 0): 20-path paired ensemble of the S1 market-trend throttle against the live book.

S1 (screen row 24, 2026-11-02_problem1_throttle_bound.md): no new entries in a week whose signal-week Nifty close is
below its 40-week SMA. Single path there: MaxDD -40.1% -> -26.6%, a RISK DIAL. Owner question 2026-11-12 ("half our
trades hit stop"); every one of the 55 live trades was signalled with the Nifty below its 40w SMA.
READING RULE, fixed before any number (same as 2026-11-03_ensemble_breakeven_d6.md): a candidate is 'robust to path
noise' only if its 5th-percentile paired dSharpe vs live is > 0. Because S1 is a risk dial, the paired dMaxDD band is
reported alongside and read the same way (p5 of the drawdown improvement > 0). 'Robust' means 'worth a pre-registered
trial', never adoption. No screen row, no n_trials change. Same draws as every ensemble (nq.lab.ensemble), PIT
membership, prices cut at 2024-06-30.

    python pipelines/diagnostics/explore_ensemble_s1_throttle.py [n_paths]
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
from nq.lab import ensemble as E  # noqa: E402
from nq.lab import runs as L  # noqa: E402
import diag_problem1_throttle_bound as T  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
REVERTED = {"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None}
# name -> (lab config overrides, use S1 throttle)
SPECS = {"live": ({}, False), "s1": ({}, True), "h5": (dict(REVERTED), False), "s1_h5": (dict(REVERTED), True)}
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-12_ensemble_s1_throttle.json"


def _verdict(v) -> str:
    """Three states: the whole 5-95 band above zero, below zero, or straddling it."""
    if np.percentile(v, 5) > 0:
        return "robustly better"
    if np.percentile(v, 95) < 0:
        return "robustly worse"
    return "inside path noise"


def run(cfg_over, s1, scale, ctx, d):
    R94 = L._engine()[0]
    cfg = {**L.normalize_config(cfg_over), "start": str(d["start"])}
    kw = L.engine_kwargs(cfg)
    if s1:
        kw["entry_size_scale_by_week"] = scale
    led: list = []
    with E.cost_jitter(float(d["cost_delta"])):
        out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade("default") if cfg["grade_gate"] else None,
                           **kw, demerger_events=ctx.events)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    return E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)


def main() -> int:
    ctx = E.prepare_context()
    nifty = L.load_nifty()
    wk = nifty.resample("W-FRI").last().dropna()
    scale = T.s1_scale(nifty, wk, T.iso_weeks(pd.Timestamp(L.MIN_START), pd.Timestamp(L.CUT)))
    off = sum(1 for v in scale.values() if v == 0.0)
    print(f"S1 blocks {off} of {len(scale)} entry weeks", flush=True)
    draws = E.draw_perturbations(N, E.DEFAULT_SEED)
    paths = {k: [] for k in SPECS}
    for _, d in draws.iterrows():
        for k, (over, s1) in SPECS.items():
            paths[k].append(run(over, s1, scale, ctx, d))
        print("path", int(d["path"]) + 1, "/", N, {k: round(v[-1]["sharpe"], 3) for k, v in paths.items()}, flush=True)
    df = {k: pd.DataFrame(v) for k, v in paths.items()}
    q = lambda v: {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}
    res = {"tier": "EXPLORE", "n_paths": N, "seed": E.DEFAULT_SEED, "report_from": E.REPORT_FROM, "cut": L.CUT,
           "last_bar": str(pd.Timestamp(ctx.last_bar).date()), "s1_blocked_weeks": off, "s1_total_weeks": len(scale),
           "rule": "robust iff p5 paired dSharpe > 0; drawdown read as p5 paired dMaxDD > 0",
           "bands": {k: {m: q(v[m]) for m in ("sharpe", "cagr", "maxdd", "trades")} for k, v in df.items()}, "paired": {}}
    for k in SPECS:
        if k == "live":
            continue
        ds = df[k]["sharpe"] - df["live"]["sharpe"]
        dd = (df[k]["maxdd"] - df["live"]["maxdd"]) * 100
        res["paired"][k] = {"dSharpe": q(ds), "share_better": float((ds > 0).mean()), "dMaxDD_pp": q(dd),
                            "share_shallower": float((dd > 0).mean()),
                            "dCAGR_pp": q((df[k]["cagr"] - df["live"]["cagr"]) * 100),
                            "verdict_sharpe": _verdict(ds), "verdict_maxdd": _verdict(dd)}
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    for k, v in res["paired"].items():
        print(k, json.dumps(v, default=lambda x: round(x, 3)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
