"""EXPLORE (tier 0): 20-path paired ensemble of the 2026-11-13 candidates against the live book, train window only.

Owner request 2026-11-13. Arms (each vs live, same draws, paired):
  h5            the four caps off (pre-reg 0151 as first drafted), for reference
  h5_cap30      h5 with max_notional_pct = 0.30 (the arm the owner moved 0151 to): ext_cap off, grade gate off,
                risk cap off, one position at most 30% of sizing equity
  results_4w    skip a Grade-A signal when a results board meeting announced on or before the signal Friday
                falls within the next 28 days (nq.data.earnings, PIT)
  half_weak     half size for entries in weeks whose signal-week Nifty close is below its 40-week SMA
  add_half_1R   one add of half the original rupee risk at the next open after a Friday close at or above +1R
                (engine lever scaled_exit.add_at_r / add_frac, inside the live per-name cap)
READING RULE, fixed before any number (same as every ensemble): robustly better iff p5 of the paired delta vs live is
> 0, robustly worse iff p95 < 0, otherwise inside path noise; read for Sharpe and for MaxDD. Train window only, prices
cut at 2024-06-30 and asserted; the sealed slice is not read. No screen row, no n_trials change.
Also reports, on the unperturbed run, each arm's largest position at entry (share of equity).

    python pipelines/diagnostics/explore_ensemble_jan_candidates.py [n_paths]
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
import diag_problem1_throttle_bound as T  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-13_ensemble_jan_candidates.json"
H5 = {"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None}
H5_30 = {**H5, "max_notional_pct": 0.30}


def _verdict(v) -> str:
    if np.percentile(v, 5) > 0:
        return "robustly better"
    if np.percentile(v, 95) < 0:
        return "robustly worse"
    return "inside path noise"


def signal_friday(d: pd.Timestamp) -> pd.Timestamp:
    back = (d.weekday() - 4) % 7 or 7
    return (d - pd.Timedelta(days=back)).normalize()


def results_filtered(ctx) -> set:
    from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table
    events = build_event_table(pd.read_parquet(EARNINGS_RAW_PATH))
    by = {s: g for s, g in events.groupby("symbol")}
    keep = set()
    for (t, i) in ctx.a_grade("default"):
        f = signal_friday(pd.Timestamp(ctx.P[t]["dates"][i]))
        g = by.get(t)
        hit = g is not None and bool(((g.ann_ts <= f + pd.Timedelta(hours=23, minutes=59)) & (g.event_date > f)
                                      & (g.event_date <= f + pd.Timedelta(days=28))).any())
        if not hit:
            keep.add((t, i))
    return keep


def main() -> int:
    ctx = E.prepare_context()
    R94 = L._engine()[0]
    nifty = L.load_nifty()
    nifty = nifty[nifty.index <= pd.Timestamp(L.CUT)]
    nwk = nifty.resample("W-FRI").last().dropna()
    s1 = T.s1_scale(nifty, nwk, T.iso_weeks(pd.Timestamp(L.MIN_START), pd.Timestamp(L.CUT)))
    half = {k: (0.5 if v == 0.0 else 1.0) for k, v in s1.items()}
    a_res = results_filtered(ctx)
    a_def = ctx.a_grade("default")
    print(f"results filter keeps {len(a_res)} of {len(a_def)} Grade-A signals; half size in "
          f"{sum(1 for v in half.values() if v < 1)} of {len(half)} weeks", flush=True)

    # name -> (lab config overrides, a_grade override, extra engine kwargs, scaled_exit additions)
    SPECS = {
        "live": ({}, None, {}, {}),
        "h5": (H5, None, {}, {}),
        "h5_cap30": (H5_30, None, {}, {}),
        "results_4w": ({}, a_res, {}, {}),
        "half_weak": ({}, None, {"entry_size_scale_by_week": half}, {}),
        "add_half_1R": ({}, None, {}, {"add_at_r": 1.0, "add_frac": 0.5}),
    }

    def run(name, start, cost_delta, plog=None):
        over, a_set, extra, se = SPECS[name]
        cfg = {**L.normalize_config(over), "start": str(start)}
        kw = L.engine_kwargs(cfg)
        kw.update(extra)
        if se:
            kw["scaled_exit"] = {**kw["scaled_exit"], **se}
        a = a_set if a_set is not None else (ctx.a_grade("default") if cfg["grade_gate"] else None)
        led: list = []
        with E.cost_jitter(float(cost_delta)):
            out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=a, position_log=plog, **kw, demerger_events=ctx.events)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        return E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)

    conc = {}
    for k in SPECS:                                     # unperturbed run: concentration at entry
        plog: list = []
        run(k, "2019-01-01", 0.0, plog)
        pl = pd.DataFrame(plog)
        pl["w"] = pl.notional.astype(float) / pl.equity.astype(float)
        first = pl.sort_values("date").groupby(["tkr", "entry"]).head(1)
        conc[k] = {"max_weight_at_entry": round(float(first.w.max()), 3), "positions": int(len(first)),
                   "above_30pct": int((first.w > 0.30).sum()), "max_weight_any_day": round(float(pl.w.max()), 3)}
        print(k, conc[k], flush=True)

    draws = E.draw_perturbations(N, E.DEFAULT_SEED)
    paths = {k: [] for k in SPECS}
    for _, d in draws.iterrows():
        for k in SPECS:
            paths[k].append(run(k, d["start"], d["cost_delta"]))
        print("path", int(d["path"]) + 1, "/", N, {k: round(v[-1]["sharpe"], 3) for k, v in paths.items()}, flush=True)
    df = {k: pd.DataFrame(v) for k, v in paths.items()}
    q = lambda v: {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}
    res = {"tier": "EXPLORE", "n_paths": N, "seed": E.DEFAULT_SEED, "report_from": E.REPORT_FROM, "cut": L.CUT,
           "last_bar": str(pd.Timestamp(ctx.last_bar).date()),
           "rule": "robustly better iff p5 paired delta > 0; robustly worse iff p95 < 0",
           "concentration_unperturbed": conc,
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
