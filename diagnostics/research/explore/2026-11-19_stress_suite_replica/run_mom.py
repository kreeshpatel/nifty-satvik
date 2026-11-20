"""0001 momentum: anchor, S1 (20 paths) baseline + latency, N1 (100 seeds). Usage: run_mom.py anchor|s1|n1"""
from __future__ import annotations

import json
import sys
import time
import types

import numpy as np
import pandas as pd

import common as K

import run_0001_xsec_momentum as M  # noqa: E402
from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book  # noqa: E402
from nq.lab import ensemble as E  # noqa: E402

_OLD = "    rebals = set(rebalance_dates(dates, cfg.cadence))\n"
_NEW = ("    rebals = set(rebalance_dates(dates, cfg.cadence))\n"
        "    if S1_SHIFT:\n"
        "        _tp = {pd.Timestamp(x): k for k, x in enumerate(dates)}\n"
        "        rebals = {pd.Timestamp(dates[_tp[pd.Timestamp(r)] + 1]) for r in rebals\n"
        "                  if _tp[pd.Timestamp(r)] + 1 < len(dates)}\n")


def engine_copy():
    import nq.engine.rebalance_book as RB
    src = open(RB.__file__, encoding="utf-8").read()
    assert src.count(_OLD) == 1
    mod = types.ModuleType("nq.engine.rebalance_book_s1")
    mod.__file__ = RB.__file__
    mod.__package__ = "nq.engine"
    mod.S1_SHIFT = True
    sys.modules[mod.__name__] = mod
    exec(compile(src.replace(_OLD, _NEW), RB.__file__, "exec"), mod.__dict__)
    return mod


def shift_ranks_one_session(b: pd.DataFrame) -> pd.DataFrame:
    """rank at panel date D+1 := the same ticker's rank at panel date D (NaN if no row at D)."""
    dates = np.sort(b["date"].unique())
    prev = pd.Series(dates[:-1], index=dates[1:])
    q = b.copy()
    key = b.set_index(["date", "ticker"])["rank"]
    pd_ = q["date"].map(prev)
    q["rank"] = key.reindex(pd.MultiIndex.from_arrays([pd_, q["ticker"]])).to_numpy()
    return q


def shuffle_ranks(b: pd.DataFrame, seed: int) -> pd.DataFrame:
    """On every date (ascending), permute the non-NaN rank values among those rows (rows in ticker order)."""
    rng = np.random.default_rng(seed)
    q = b.sort_values(["date", "ticker"]).reset_index(drop=True)
    rk = q["rank"].to_numpy(float).copy()
    d = q["date"].to_numpy()
    bounds = np.flatnonzero(np.r_[True, d[1:] != d[:-1], True])
    for a, z in zip(bounds[:-1], bounds[1:]):
        seg = rk[a:z]
        nn = np.flatnonzero(~np.isnan(seg))
        if len(nn) > 1:
            seg[nn] = seg[nn][rng.permutation(len(nn))]
        rk[a:z] = seg
    q["rank"] = rk
    return q


def run(sim, b, d):
    bt = sim(b, cfg=RebalanceConfig(**M.BOOK, cost_mult=1 + float(d["cost_delta"]) / 0.0035),
             start=str(d["start"]), end=M.END, initial_capital=1e6)
    return bt


def main(mode: str) -> int:
    b = K.mom_panel()
    t0 = time.time()
    if mode == "anchor":
        bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**M.BOOK), start=M.START, end=M.END, initial_capital=1e6)
        nav = K.mom_nav(bt)
        r = nav.pct_change().dropna()
        yrs = (nav.index[-1] - nav.index[0]).days / 365.25
        res = {"engine_metrics": {k: bt["metrics"][k] for k in ("cagr_pct", "sharpe")},
               "replica_sharpe_ddof1": K.sharpe(r), "replica_sharpe_ddof0": float(r.mean() / r.std(ddof=0) * np.sqrt(252)),
               "replica_cagr_calendar_365.25": float((nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1),
               "first_nav_date": str(nav.index[0].date()), "last_nav_date": str(nav.index[-1].date())}
        print(res)
        (K.HERE / "mom_anchor.json").write_text(json.dumps(res, indent=1))
        return 0
    first = json.loads((K.HERE / "mom_anchor.json").read_text())["first_nav_date"]
    bench = K.mom_ew_bench(b)
    if mode == "s1":
        S1 = engine_copy()
        bs = shift_ranks_one_session(b)
        draws = E.draw_perturbations(20, E.DEFAULT_SEED, start_base=first)
        rows = []
        for _, d in draws.iterrows():
            base = K.sharpe(K.mom_nav(run(simulate_rebalance_book, b, d)).pct_change())
            lat = K.sharpe(K.mom_nav(run(S1.simulate_rebalance_book, bs, d)).pct_change())
            rows.append({"path": int(d["path"]), "start": d["start"], "cost_delta": float(d["cost_delta"]),
                         "sharpe_base": base, "sharpe_s1": lat})
            print(rows[-1], round(time.time() - t0), flush=True)
        df = pd.DataFrame(rows)
        res = {"paths": rows, "median_base": float(df["sharpe_base"].median()),
               "median_s1": float(df["sharpe_s1"].median())}
        (K.HERE / "mom_s1.json").write_text(json.dumps(res, indent=1))
        print(json.dumps({k: v for k, v in res.items() if k != "paths"}))
        return 0
    if mode == "n1":
        draws = E.draw_perturbations(100, E.DEFAULT_SEED, start_base=first)
        out_f = K.HERE / "mom_n1_rows.jsonl"
        done = set()
        if out_f.exists():
            done = {json.loads(l)["seed"] for l in out_f.read_text().splitlines() if l.strip()}
        for k, d in draws.iterrows():
            if int(k) in done:
                continue
            bk = shuffle_ranks(b, int(k))
            r = K.mom_nav(run(simulate_rebalance_book, bk, d)).pct_change().dropna()
            row = {"seed": int(k), "start": d["start"], "cost_delta": float(d["cost_delta"]),
                   "sharpe": K.sharpe(r), **K.appraisal(r, bench)}
            with open(out_f, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, round(time.time() - t0), flush=True)
        return 0
    raise SystemExit(mode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
