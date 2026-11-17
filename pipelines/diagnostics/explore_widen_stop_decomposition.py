"""EXPLORE (tier 0): what actually earns the widen-to-8% gain — the stop level, or the target distance?

Owner request 2026-11-17, before signing pre-registration 0152. Train window only (prices cut at 2024-06-30 and the
cut asserted); no trial, no screen row, no sealed read, nothing live changes.

The owner asked to split the gain into (a) the stop effect at fixed position sizes and (b) an extra-seat funding
effect. Measured first, before the split: **position size is already fixed**. With 2% risk per trade, the 10% stop cap
and the 20% per-name notional cap, risk sizing always asks for at least 20% of equity, so the notional cap binds on
essentially every live position (median weight at entry 0.200, 55% exactly at the cap). Widening a stop therefore
cannot shrink a position, and there is no funding-through-sizing channel to measure. What a wider stop does change is:

  1. the STOP LEVEL — the exit sits further away, so fewer trades stop out, and those that do lose more rupees
     (the position is the same size);
  2. the TARGET DISTANCE — every level in the scaled exit is defined in R, and R is measured on entry minus stop. A
     wider stop pushes the +2R tranche, the +2.5R pattern arm and the ratchets further away, and shrinks every
     reported R.

So the decomposition run here is stop level against target distance, which together make up the full rule:

  live             the live configuration
  widen            min_stop_pct 0.08, mode "widen"           — both channels (the 0152 candidate)
  stop_only        stop moved to the floor, R basis kept at the original distance — channel 1 alone
  risk_basis_only  stop left alone, R measured on the floor distance            — channel 2 alone

Seats are reported as measured occupancy (mean names held, and mean weight at entry), which is the "extra seats"
question answered on the evidence rather than assumed.

    python pipelines/diagnostics/explore_widen_stop_decomposition.py [n_paths]
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
FLOOR = 0.08
BIG = 2.0
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-17_widen_stop_decomposition.json"
ARMS = {"live": {}, "widen": dict(min_stop_pct=FLOOR, min_stop_mode="widen"),
        "stop_only": dict(min_stop_pct=FLOOR, min_stop_mode="stop_only"),
        "risk_basis_only": dict(min_stop_pct=FLOOR, min_stop_mode="risk_basis_only")}


def verdict(v) -> str:
    if np.percentile(v, 5) > 0:
        return "robustly better"
    if np.percentile(v, 95) < 0:
        return "robustly worse"
    return "inside path noise"


def q(v) -> dict:
    return {"median": round(float(np.median(v)), 3), "p5": round(float(np.percentile(v, 5)), 3),
            "p95": round(float(np.percentile(v, 95)), 3)}


def main() -> int:
    ctx = E.prepare_context()
    R94 = L._engine()[0]
    draws = E.draw_perturbations(N, E.DEFAULT_SEED)

    def run(extra, d, plog=None):
        cfg = {**L.normalize_config({}), "start": str(d["start"])}
        kw = L.engine_kwargs(cfg)
        kw.update(extra)
        led: list = []
        with E.cost_jitter(float(d["cost_delta"])):
            out = R94.backtest(ctx.P, ctx.mem, ledger=led, position_log=plog,
                               a_grade=ctx.a_grade("default"), **kw, demerger_events=ctx.events)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        return E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM), pd.DataFrame(led)

    paths: dict[str, list] = {k: [] for k in ARMS}
    trade: dict[str, list] = {k: [] for k in ARMS}
    for _, d in draws.iterrows():
        for k, extra in ARMS.items():
            m, led = run(extra, d)
            paths[k].append(m)
            led = led[(led.entry - led.stop0) / led.entry >= 0.005]
            c = led[led.reason != "eos"]
            trade[k].append({"n_closed": len(c), "mean_R": float(c.R.mean()), "total_R": float(led.R.sum()),
                             "big_winners": int((led.R >= BIG).sum()),
                             "full_stop_pct": float((c.reason == "stop").mean() * 100)})
        sys.stdout.write(f"path {int(d['path']) + 1}/{N} " + str({k: round(v[-1]['sharpe'], 3) for k, v in paths.items()}) + "\n")
        sys.stdout.flush()

    PARTIAL = OUT.with_suffix(".paths.json")
    PARTIAL.write_text(json.dumps({"paths": paths, "trade": trade}, indent=1), encoding="utf-8")

    # unperturbed run: how often the floor binds, and what it does to seats
    plog: list = []
    UNPERTURBED = {"start": "2019-01-01", "cost_delta": 0.0}
    _, base_led = run({}, UNPERTURBED, plog)
    pl = pd.DataFrame(plog)
    first = pl.sort_values("date").groupby(["tkr", "entry"]).head(1)
    sp = (base_led.entry - base_led.stop0) / base_led.entry
    occupancy = {}
    for k, extra in ARMS.items():
        pg: list = []
        run(extra, UNPERTURBED, pg)
        g = pd.DataFrame(pg)
        f = g.sort_values("date").groupby(["tkr", "entry"]).head(1)
        occupancy[k] = {"mean_names_held": round(float(g.groupby("date").tkr.nunique().mean()), 2),
                        "positions_opened": int(len(f)),
                        "median_weight_at_entry": round(float((f.notional / f.equity).median()), 3)}

    res = {"tier": "EXPLORE", "n_paths": N, "floor_pct": FLOOR, "seed": E.DEFAULT_SEED, "report_from": E.REPORT_FROM,
           "cut": L.CUT, "last_bar": str(pd.Timestamp(ctx.last_bar).date()),
           "sizing_fact": {"note": "the 20% per-name notional cap binds on essentially every position, so a wider stop "
                                   "does not shrink it; there is no funding-through-sizing channel",
                           "median_weight_at_entry": round(float((first.notional / first.equity).median()), 3),
                           "share_at_cap": round(float(((first.notional / first.equity) > 0.199).mean()), 2)},
           "floor_bite": {"share_of_live_trades_with_stop_under_8pct": round(float((sp < FLOOR).mean()), 3),
                          "median_stop_pct": round(float(sp.median()), 3)},
           "occupancy_unperturbed": occupancy,
           "bands": {k: {m: q([p[m] for p in v]) for m in ("sharpe", "cagr", "maxdd")} for k, v in paths.items()},
           "per_trade": {k: {m: q([t[m] for t in v]) for m in ("mean_R", "total_R", "big_winners", "n_closed", "full_stop_pct")}
                         for k, v in trade.items()}, "paired": {}}
    for k in ARMS:
        if k == "live":
            continue
        ds = np.array([a["sharpe"] - b["sharpe"] for a, b in zip(paths[k], paths["live"])])
        dd = np.array([(a["maxdd"] - b["maxdd"]) * 100 for a, b in zip(paths[k], paths["live"])])
        dr = np.array([a["mean_R"] - b["mean_R"] for a, b in zip(trade[k], trade["live"])])
        dbw = np.array([a["big_winners"] - b["big_winners"] for a, b in zip(trade[k], trade["live"])])
        res["paired"][k] = {"dSharpe": q(ds), "paths_better": int((ds > 0).sum()), "dMaxDD_pp": q(dd),
                            "dMeanR": q(dr), "dBigWinners": q(dbw),
                            "dCAGR_pp": q([(a["cagr"] - b["cagr"]) * 100 for a, b in zip(paths[k], paths["live"])]),
                            "verdict_sharpe": verdict(ds)}
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    sys.stdout.buffer.write((json.dumps({k: {"dSharpe": v["dSharpe"], "better": v["paths_better"], "dMeanR": v["dMeanR"]["median"],
                                             "dBigWinners": v["dBigWinners"]["median"], "verdict": v["verdict_sharpe"]}
                                         for k, v in res["paired"].items()}, indent=1) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
