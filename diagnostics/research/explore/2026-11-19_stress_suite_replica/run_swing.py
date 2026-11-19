"""Swing book: anchor, S1 (20 paths, baseline + latency), N1 (100 seeds). Usage: run_swing.py anchor|s1|n1"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

import common as K

R94, CTX = K.swing_context()
from nq.lab import ensemble as E  # noqa: E402


def shift_entry_windows(P: dict) -> dict:
    """S1(a): every window's session list shifted +1 session index (activation key unchanged)."""
    out = {}
    for t, s in P.items():
        n = len(s["dates"])
        ew = {}
        for k, (days, lo, hi, rk, sma, org) in s["entry_win"].items():
            nd = [int(x) + 1 for x in days if int(x) + 1 < n]
            if nd:
                ew[k] = (nd, lo, hi, rk, sma, org)
        out[t] = {**s, "entry_win": ew}
    return out


# ----------------------------------------------------------------------------- N1 shuffle machinery
FR = K.swing_member_frames(CTX)
MEMB = FR["M"]
DIDX = {t: {pd.Timestamp(d).normalize(): i for i, d in enumerate(s["dates"])} for t, s in CTX.P.items()}
DATES = {t: pd.DatetimeIndex(pd.to_datetime(list(s["dates"]))).normalize() for t, s in CTX.P.items()}
SIGS = []                                      # (iso, ticker, e0, entry_date, win)
for t, s in CTX.P.items():
    for e0, win in s["entry_win"].items():
        ed = DATES[t][e0]
        if ed >= pd.Timestamp("2019-01-01"):
            iso = ed.isocalendar()
            SIGS.append(((int(iso[0]), int(iso[1])), t, int(e0), ed, win))
SIGS.sort(key=lambda x: (x[0], x[1], x[2]))
BY_WEEK = defaultdict(list)
for x in SIGS:
    BY_WEEK[x[0]].append(x)
_CANDS = {}


def cands_on(d: pd.Timestamp) -> list:
    if d not in _CANDS:
        row = MEMB.loc[d]
        _CANDS[d] = sorted(row.index[row.to_numpy(bool)])
    return _CANDS[d]


def shuffled_P(seed: int):
    rng = np.random.default_rng(seed)
    new = defaultdict(dict)
    stats = {"signals": 0, "assigned": 0, "no_candidate": 0, "no_prior_week_bar": 0, "sma_fallback": 0,
             "u_missing_some_entry_days": 0}
    for wk in sorted(BY_WEEK):
        used = set()
        for _iso, t, e0, ed, win in BY_WEEK[wk]:
            stats["signals"] += 1
            days, _lo, _hi, rk, _sma, org = win
            pool = [u for u in cands_on(ed) if u != t and u not in used]
            if not pool:
                stats["no_candidate"] += 1
                continue
            u = pool[int(rng.integers(len(pool)))]
            used.add(u)
            su = CTX.P[u]
            wdates = [DATES[t][int(x)] for x in days]
            ud = [DIDX[u][x] for x in wdates if x in DIDX[u]]
            if len(ud) < len(wdates):
                stats["u_missing_some_entry_days"] += 1
            mon = ed - pd.Timedelta(days=ed.weekday())
            lo_d, hi_d = mon - pd.Timedelta(days=7), mon - pd.Timedelta(days=1)
            m = (DATES[u] >= lo_d) & (DATES[u] <= hi_d)
            pw = np.flatnonzero(m)
            if not len(pw):
                stats["no_prior_week_bar"] += 1
                continue
            lo = float(np.min(np.asarray(su["l"], float)[pw]))
            hi = float(np.max(np.asarray(su["h"], float)[pw]))
            sma = su["wsma_at"].get(int(pw[-1]), float("nan"))
            if not (sma == sma):
                sma = lo
                stats["sma_fallback"] += 1
            key = DIDX[u][ed]
            new[u][key] = (ud, lo, hi, float(rk), float(sma), int(org))
            stats["assigned"] += 1
    P_new = {t: {**s, "entry_win": dict(new.get(t, {}))} for t, s in CTX.P.items()}
    return P_new, stats


def bench_swing() -> pd.Series:
    R, M = FR["R"], FR["M"]
    return R.where(M).mean(axis=1)


def main(mode: str) -> int:
    t0 = time.time()
    a_def = CTX.a_grade("default")
    if mode in ("anchor", "s1"):
        draws = E.draw_perturbations(20, E.DEFAULT_SEED)
        d0 = draws.iloc[0]
        R94.S1_EXIT_DELAY = False
        sh0 = K.sharpe(K.swing_returns(K.run_swing(R94, CTX, CTX.P, a_def, d0)))
        print("ANCHOR path0", round(sh0, 6), "want 1.348913", flush=True)
        if round(sh0, 6) != 1.348913:
            raise SystemExit("swing anchor mismatch: stop")
        if mode == "anchor":
            return 0
        P1 = shift_entry_windows(CTX.P)
        rows = []
        for _, d in draws.iterrows():
            R94.S1_EXIT_DELAY = False
            base = K.sharpe(K.swing_returns(K.run_swing(R94, CTX, CTX.P, a_def, d)))
            R94.S1_EXIT_DELAY = True
            R94.S1_STATS["wait_on_weekend"] = 0
            lat = K.sharpe(K.swing_returns(K.run_swing(R94, CTX, P1, a_def, d)))
            R94.S1_EXIT_DELAY = False
            rows.append({"path": int(d["path"]), "start": d["start"], "cost_delta": float(d["cost_delta"]),
                         "sharpe_base": base, "sharpe_s1": lat,
                         "s1_wait_on_weekend_session": int(R94.S1_STATS["wait_on_weekend"])})
            print(rows[-1], round(time.time() - t0), flush=True)
        df = pd.DataFrame(rows)
        res = {"paths": rows, "median_base": float(df["sharpe_base"].median()),
               "median_s1": float(df["sharpe_s1"].median())}
        (K.HERE / "swing_s1.json").write_text(json.dumps(res, indent=1))
        print(json.dumps({k: v for k, v in res.items() if k != "paths"}))
        return 0
    if mode == "n1":
        bench = bench_swing()
        draws = E.draw_perturbations(100, E.DEFAULT_SEED)
        out_f = K.HERE / "swing_n1_rows.jsonl"
        done = set()
        if out_f.exists():
            done = {json.loads(l)["seed"] for l in out_f.read_text().splitlines() if l.strip()}
        R94.S1_EXIT_DELAY = False
        for k, d in draws.iterrows():
            if int(k) in done:
                continue
            Pn, st = shuffled_P(int(k))
            ag = R94.grade_a_entries(Pn)
            r = K.swing_returns(K.run_swing(R94, CTX, Pn, ag, d))
            row = {"seed": int(k), "start": d["start"], "cost_delta": float(d["cost_delta"]),
                   "sharpe": K.sharpe(r), **K.appraisal(r, bench), **st}
            with open(out_f, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, round(time.time() - t0), flush=True)
        return 0
    raise SystemExit(mode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
