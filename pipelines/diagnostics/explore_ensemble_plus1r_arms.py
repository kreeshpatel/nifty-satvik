"""EXPLORE (tier 0): 20-path paired ensemble of the +1R management arms against the live book.

Arms are defined in explore_plus1r_arms.py. READING RULE, fixed before any number (same as the 2026-11-03 and
2026-11-12 ensembles): robustly better iff the 5th percentile of the paired delta vs live is > 0, robustly worse iff
the 95th percentile is < 0, otherwise inside path noise. Read for Sharpe and for MaxDD. 'Robust' means 'worth a
pre-registered trial', never adoption. No screen row, no n_trials change. Same draws as every ensemble
(nq.lab.ensemble), PIT membership, prices cut at 2024-06-30.

    python pipelines/diagnostics/explore_ensemble_plus1r_arms.py [n_paths] [week_high]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
from nq.lab import ensemble as E  # noqa: E402
from nq.lab import runs as L  # noqa: E402
from explore_plus1r_arms import ARMS, ARMS_WH  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
WEEK_HIGH = len(sys.argv) > 2 and sys.argv[2] == "week_high"      # second run: the ratchet arms on the week's high
if WEEK_HIGH:
    ARMS = {"live": {}, **ARMS_WH}
OUT = ROOT / "diagnostics" / "research" / "explore" / (
    "2026-11-13_ensemble_plus1r_arms_week_high.json" if WEEK_HIGH else "2026-11-13_ensemble_plus1r_arms.json")


def _verdict(v) -> str:
    if np.percentile(v, 5) > 0:
        return "robustly better"
    if np.percentile(v, 95) < 0:
        return "robustly worse"
    return "inside path noise"


def run(extra, ctx, d):
    R94 = L._engine()[0]
    cfg = {**L.normalize_config({}), "start": str(d["start"])}
    kw = L.engine_kwargs(cfg)
    if extra:
        kw["scaled_exit"] = {**kw["scaled_exit"], **extra}
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
    draws = E.draw_perturbations(N, E.DEFAULT_SEED)
    paths = {k: [] for k in ARMS}
    for _, d in draws.iterrows():
        for k, extra in ARMS.items():
            paths[k].append(run(extra, ctx, d))
        print("path", int(d["path"]) + 1, "/", N, {k: round(v[-1]["sharpe"], 3) for k, v in paths.items()}, flush=True)
    df = {k: pd.DataFrame(v) for k, v in paths.items()}
    q = lambda v: {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}
    res = {"tier": "EXPLORE", "n_paths": N, "seed": E.DEFAULT_SEED, "report_from": E.REPORT_FROM, "cut": L.CUT,
           "last_bar": str(pd.Timestamp(ctx.last_bar).date()),
           "rule": "robustly better iff p5 paired delta > 0; robustly worse iff p95 < 0",
           "bands": {k: {m: q(v[m]) for m in ("sharpe", "cagr", "maxdd", "trades")} for k, v in df.items()}, "paired": {}}
    for k in ARMS:
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
