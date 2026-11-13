"""CONFIRM 0151: h5-30 vs live on the sealed slice 2024-07-01..2026-06-30.

Implements exactly §2 and §5 of diagnostics/research/preregistry/0151-h5-caps-off-confirm.md and nothing else.

Order, enforced in code:
  G0  train reproduction. Same context as every train ensemble (prices cut at 2024-06-30), the same 20 paired draws,
      reported 2019-03-01..2024-06-30. The median paired dSharpe (h5-30 minus live) must lie in +0.34 +/- 0.10.
      If it does not, the script stops BEFORE any sealed-slice price is loaded.
  S4  the sealed read. One full run per path from the path's 2019 start to 2026-06-30 (data end), each gate read as
      the CONTINUOUS SLICE 2024-07-01..2026-06-30 of that run.

Gates (§5):
  P1 median paired dSharpe > 0 AND >= 15 of 20 paths > 0
  P2 median paired dMaxDD >= -5.0pp
  P3 unperturbed run: dSharpe not negative on BOTH halves (2024-07-01..2025-06-30, 2025-07-01..2026-06-30)
  P4 unperturbed run: h5-30 sealed net P&L minus its largest winning trade's net P&L > live sealed net P&L
     (net P&L = NAV change over the slice; trades = ledger rows entered inside the slice)
  P5 unperturbed run: no h5-30 position entered in the slice above 31% of equity at entry
Outcome: PROMOTE (all) / UNDERPOWERED (median dSharpe > 0, P2 P4 P5 hold, P1 share or P3 fails) / KILL (otherwise).

    python pipelines/diagnostics/confirm_0151_h5_30.py
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

OUT = ROOT / "diagnostics" / "research" / "confirm" / "0151_h5_30_result.json"
N = 20
LIVE = {}
H5_30 = {"ext_cap": None, "grade_gate": False, "max_notional_pct": 0.30, "max_risk_pct": None}
G0_CENTRE, G0_TOL = 0.34, 0.10
SEALED = ("2024-07-01", "2026-06-30")
HALVES = (("2024-07-01", "2025-06-30"), ("2025-07-01", "2026-06-30"))


def nav_of(ctx, over, start, cost_delta, plog=None):
    R94 = L._engine()[0]
    cfg = {**L.normalize_config(over), "start": str(start)}
    kw = L.engine_kwargs(cfg)
    led: list = []
    with E.cost_jitter(float(cost_delta)):
        out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade("default") if cfg["grade_gate"] else None,
                           position_log=plog, **kw, demerger_events=ctx.events)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    return nav[~nav.index.duplicated(keep="last")].sort_index(), pd.DataFrame(led)


def q(v):
    return {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}


def sealed_context():
    """The same preparation as nq.lab.ensemble.prepare_context, with prices to the data end (the sealed read)."""
    R94, live, load_demerger_rows, corrected_universe = L._engine()
    from nq.data.membership import load_membership
    uni = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(SEALED[1])] for t, df in corrected_universe().items()}
    uni = {t: df for t, df in uni.items() if len(df) > 60}
    last = max(df.index.max() for df in uni.values())
    P = R94.prep_weekly_rank(uni, **live["LIVE_PREP"])
    as_of = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=None)
    events = R94.build_demerger_events(uni, load_demerger_rows(), **{**live["LIVE_PREP"], "as_of": as_of})
    return E.EnsembleContext(P=P, mem=load_membership(), events=events, last_bar=last)


def main() -> int:
    draws = E.draw_perturbations(N, E.DEFAULT_SEED)
    res: dict = {"prereg": "0151", "arm": "h5-30", "arm_config": H5_30, "n_paths": N, "seed": E.DEFAULT_SEED}

    # ---- G0: train reproduction, before any sealed price is loaded ---------------------------------------------
    tctx = E.prepare_context()
    d_train = []
    for _, d in draws.iterrows():
        a = E.slice_metrics(*nav_of(tctx, LIVE, d["start"], d["cost_delta"]), E.REPORT_FROM)
        b = E.slice_metrics(*nav_of(tctx, H5_30, d["start"], d["cost_delta"]), E.REPORT_FROM)
        d_train.append(b["sharpe"] - a["sharpe"])
    g0 = float(np.median(d_train))
    res["G0"] = {"median_dSharpe_train": g0, "band": [G0_CENTRE - G0_TOL, G0_CENTRE + G0_TOL],
                 "pass": bool(abs(g0 - G0_CENTRE) <= G0_TOL), "train_last_bar": str(pd.Timestamp(tctx.last_bar).date())}
    print("G0", res["G0"], flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not res["G0"]["pass"]:
        res["outcome"] = "STOP (G0 failed; sealed slice not read)"
        OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print(res["outcome"])
        return 2
    del tctx

    # ---- S4: the sealed read ----------------------------------------------------------------------------------
    sctx = sealed_context()
    res["sealed_last_bar"] = str(pd.Timestamp(sctx.last_bar).date())
    rows = []
    for _, d in draws.iterrows():
        a = E.slice_metrics(*nav_of(sctx, LIVE, d["start"], d["cost_delta"]), SEALED[0], end=SEALED[1])
        b = E.slice_metrics(*nav_of(sctx, H5_30, d["start"], d["cost_delta"]), SEALED[0], end=SEALED[1])
        rows.append({"path": int(d["path"]), "live": a, "h5_30": b,
                     "dSharpe": b["sharpe"] - a["sharpe"], "dMaxDD_pp": (b["maxdd"] - a["maxdd"]) * 100,
                     "dCAGR_pp": (b["cagr"] - a["cagr"]) * 100})
        print("path", int(d["path"]) + 1, round(rows[-1]["dSharpe"], 3), flush=True)
    ds = np.array([r["dSharpe"] for r in rows])
    dd = np.array([r["dMaxDD_pp"] for r in rows])
    res["paths"] = rows
    res["paired"] = {"dSharpe": q(ds), "paths_better": int((ds > 0).sum()), "dMaxDD_pp": q(dd),
                     "dCAGR_pp": q([r["dCAGR_pp"] for r in rows])}
    res["bands"] = {k: {m: q([r[k][m] for r in rows]) for m in ("sharpe", "cagr", "maxdd", "trades", "mean_R_ex_degen")}
                    for k in ("live", "h5_30")}

    # ---- unperturbed run: P3, P4, P5 ---------------------------------------------------------------------------
    plog_l, plog_h = [], []
    nav_l, led_l = nav_of(sctx, LIVE, "2019-01-01", 0.0, plog_l)
    nav_h, led_h = nav_of(sctx, H5_30, "2019-01-01", 0.0, plog_h)
    halves = []
    for lo, hi in HALVES:
        sl, sh = E.slice_metrics(nav_l, led_l, lo, end=hi), E.slice_metrics(nav_h, led_h, lo, end=hi)
        halves.append({"window": [lo, hi], "live_sharpe": sl["sharpe"], "h5_30_sharpe": sh["sharpe"],
                       "dSharpe": sh["sharpe"] - sl["sharpe"]})

    def slice_pnl(nav):
        s = nav[(nav.index >= pd.Timestamp(SEALED[0])) & (nav.index <= pd.Timestamp(SEALED[1]))]
        return float(s.iloc[-1] - s.iloc[0])

    def in_slice(led):
        ed = pd.to_datetime(led["entry_date"]).dt.normalize()
        return led[(ed >= pd.Timestamp(SEALED[0])) & (ed <= pd.Timestamp(SEALED[1]))]

    th = in_slice(led_h)
    best = float(th["net_pnl"].max()) if len(th) else 0.0
    p4_lhs = slice_pnl(nav_h) - max(best, 0.0)
    pl = pd.DataFrame(plog_h)
    pl["w"] = pl.notional.astype(float) / pl.equity.astype(float)
    pl["d"] = pd.to_datetime(pl["date"]).dt.normalize()
    first = pl.sort_values("d").groupby(["tkr", "entry"]).head(1)
    first = first[(first.d >= pd.Timestamp(SEALED[0])) & (first.d <= pd.Timestamp(SEALED[1]))]
    maxw = float(first.w.max()) if len(first) else 0.0
    wmap = {(r.tkr, round(float(r.entry), 2)): r.w for r in first.itertuples()}
    th = th.assign(w=[wmap.get((t, round(float(e), 2)), np.nan) for t, e in zip(th.tkr, th.entry)])
    big_share = float(th.loc[th.w > 0.20, "net_pnl"].sum() / th["net_pnl"].sum()) if len(th) and th["net_pnl"].sum() else float("nan")
    res["unperturbed"] = {
        "halves": halves,
        "live_slice_net_pnl": slice_pnl(nav_l), "h5_30_slice_net_pnl": slice_pnl(nav_h),
        "h5_30_largest_winning_trade_net_pnl": best, "P4_lhs": p4_lhs,
        "h5_30_max_weight_at_entry_in_slice": maxw, "h5_30_positions_entered_in_slice": int(len(first)),
        "h5_30_share_of_slice_pnl_from_positions_above_20pct": big_share,
        "live_max_weight_any_day": float(pd.DataFrame(plog_l).pipe(
            lambda x: (x.notional / x.equity)).max()) if plog_l else None,
    }

    # ---- the pre-committed outcome table ----------------------------------------------------------------------
    med = float(np.median(ds))
    P1 = med > 0 and int((ds > 0).sum()) >= 15
    P2 = float(np.median(dd)) >= -5.0
    P3 = not all(h["dSharpe"] < 0 for h in halves)
    P4 = p4_lhs > slice_pnl(nav_l)
    P5 = maxw <= 0.31
    res["gates"] = {"P1": P1, "P2": P2, "P3": P3, "P4": P4, "P5": P5, "median_dSharpe": med}
    if all((P1, P2, P3, P4, P5)):
        outcome = "PROMOTE"
    elif med > 0 and P2 and P4 and P5:
        outcome = "UNDERPOWERED"
    else:
        outcome = "KILL"
    res["outcome"] = outcome
    OUT.write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    print(json.dumps({"gates": res["gates"], "paired": res["paired"], "unperturbed": res["unperturbed"],
                      "outcome": outcome}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
