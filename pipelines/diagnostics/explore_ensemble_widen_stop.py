"""EXPLORE (tier 0): 20-path paired ensemble of widening a tight stop to a minimum % of entry, vs the live book.

Follow-up to 2026-11-13_stop_floor_and_confirmation.md (owner request): widen to 6% and 7%, with 8% as the neighbour.
READING RULE, fixed before any number (same as every ensemble): robustly better iff p5 of the paired delta vs live is
> 0, robustly worse iff p95 < 0, otherwise inside path noise; read for Sharpe and for MaxDD. Train window only, prices
cut at 2024-06-30 and asserted; the sealed slice is not read. No screen row, no n_trials change.

    python pipelines/diagnostics/explore_ensemble_widen_stop.py [n_paths]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from nq.lab import ensemble as E  # noqa: E402
from nq.lab import runs as L  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-13_ensemble_widen_stop.json"
ARMS = {"live": {}, **{f"widen_pct_{int(p * 100)}": dict(min_stop_pct=p, min_stop_mode="widen") for p in (0.06, 0.07, 0.08)}}


def _verdict(v) -> str:
    if np.percentile(v, 5) > 0:
        return "robustly better"
    if np.percentile(v, 95) < 0:
        return "robustly worse"
    return "inside path noise"


def main() -> int:
    ctx = E.prepare_context()
    R94 = L._engine()[0]
    draws = E.draw_perturbations(N, E.DEFAULT_SEED)

    def run(extra, d):
        cfg = {**L.normalize_config({}), "start": str(d["start"])}
        kw = L.engine_kwargs(cfg)
        kw.update(extra)
        led: list = []
        with E.cost_jitter(float(d["cost_delta"])):
            out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade("default"), **kw, demerger_events=ctx.events)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        return E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)

    paths = {k: [] for k in ARMS}
    for _, d in draws.iterrows():
        for k, extra in ARMS.items():
            paths[k].append(run(extra, d))
        sys.stdout.write(f"path {int(d['path']) + 1}/{N} " + str({k: round(v[-1]['sharpe'], 3) for k, v in paths.items()}) + "\n")
        sys.stdout.flush()
    df = {k: pd.DataFrame(v) for k, v in paths.items()}
    q = lambda v: {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}
    res = {"tier": "EXPLORE", "n_paths": N, "seed": E.DEFAULT_SEED, "report_from": E.REPORT_FROM, "cut": L.CUT,
           "rule": "robustly better iff p5 paired delta > 0; robustly worse iff p95 < 0",
           "distinct_live_paths": int(df["live"]["sharpe"].round(6).nunique()),
           "bands": {k: {m: q(v[m]) for m in ("sharpe", "cagr", "maxdd", "trades")} for k, v in df.items()}, "paired": {}}
    for k in ARMS:
        if k == "live":
            continue
        ds = df[k]["sharpe"] - df["live"]["sharpe"]
        dd = (df[k]["maxdd"] - df["live"]["maxdd"]) * 100
        res["paired"][k] = {"dSharpe": q(ds), "paths_better": int((ds > 0).sum()), "dMaxDD_pp": q(dd),
                            "paths_shallower": int((dd > 0).sum()),
                            "dCAGR_pp": q((df[k]["cagr"] - df["live"]["cagr"]) * 100),
                            "verdict_sharpe": _verdict(ds), "verdict_maxdd": _verdict(dd)}
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(res["paired"], indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
