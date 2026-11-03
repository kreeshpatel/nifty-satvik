"""Problem 1 exposure-throttle BOUND (screen row 24; SCREEN/BOUND tier; not a trial).

Would an exposure throttle on NEW seats, driven by a point-in-time market-state signal, have bought
drawdown cheaply on the live book (train window only)?  Signals, levels, measures and the verdict reading
are frozen in diagnostics/research/diagnosis/2026-11-02_problem1_throttle_bound.md BEFORE this ran.

One continuous live-config replay per row (nq.lab.runs engine setup: PIT membership, prices cut at
2024-06-30, start 2019-01-01), differing only in the cfg-gated lever ``entry_size_scale_by_week`` (scale of
NEW fills by ISO week; existing positions untouched; freed cash stays in cash). Sub-periods and correction
windows are CONTINUOUS SLICES of each row's one run.

Run:  python pipelines/diagnostics/diag_problem1_throttle_bound.py [--cache-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nq.lab import runs                                    # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "diagnosis" / "2026-11-02_problem1_throttle_bound.json"
LEDGER = ROOT / "diagnostics" / "research" / "label_screen_ledger.md"
SUBS = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", "2024-06-30")}
N_TRIALS = 7                       # S1..S4 + CONTROL + CV0 + CVh
LIVE_WINDOW_DAYS, DD_LOOKBACK, MERGE_GAP, EP_THR = 116, 252, 21, 0.08
TD = 252


# ----------------------------------------------------------------------------- decision calendar
def iso_weeks(lo: pd.Timestamp, hi: pd.Timestamp) -> list[tuple[int, int]]:
    """ISO (year, week) of every Monday from the week containing ``lo`` to the week containing ``hi``."""
    d = (lo - pd.Timedelta(days=lo.weekday())).date()
    out = []
    while pd.Timestamp(d) <= hi:
        iso = d.isocalendar()
        out.append((int(iso[0]), int(iso[1])))
        d += timedelta(days=7)
    return out


def monday(key: tuple[int, int]) -> pd.Timestamp:
    return pd.Timestamp(date.fromisocalendar(key[0], key[1], 1))


def decision_date(idx: pd.DatetimeIndex, key: tuple[int, int]) -> pd.Timestamp | None:
    """Last session on or before the Sunday before the entry week's Monday (the signal-week close)."""
    pos = idx.searchsorted(monday(key) - pd.Timedelta(days=1), side="right") - 1
    return idx[pos] if pos >= 0 else None


# ----------------------------------------------------------------------------- signals (PIT)
def week_label(d: pd.Timestamp) -> pd.Timestamp:
    return (d + pd.Timedelta(days=(4 - d.weekday()) % 7)).normalize() if d.weekday() <= 4 else d


def s1_scale(nifty: pd.Series, wk: pd.Series, keys) -> dict:
    out = {}
    for k in keys:
        D = decision_date(nifty.index, k)
        sub = wk[wk.index <= week_label(D)] if D is not None else wk.iloc[:0]
        out[k] = 0.0 if (len(sub) >= 40 and sub.iloc[-1] < sub.iloc[-40:].mean()) else 1.0
    return out


def s2_scale(nifty: pd.Series, keys) -> dict:
    ret20 = nifty / nifty.shift(20) - 1.0
    sma50 = nifty.rolling(50).mean()
    out = {}
    for k in keys:
        D = decision_date(nifty.index, k)
        on = D is not None and ret20.loc[D] < 0 and nifty.loc[D] < sma50.loc[D]
        out[k] = 0.5 if bool(on) else 1.0
    return out


def breadth_series(P: dict, mem, lo: pd.Timestamp) -> pd.Series:
    """Weekly breadth: share of PIT Nifty-500 members (>= 44 weekly closes) with close > own 44w SMA."""
    from run_bhanushali_weekly_rank import ticker_in_index_on
    cols = {}
    for t, s in P.items():
        ser = pd.Series(np.asarray(s["c"], dtype=float), index=pd.DatetimeIndex(s["dates"]))
        cols[t] = ser.resample("W-FRI").last()
    W = pd.DataFrame(cols).sort_index()
    W = W[W.index >= lo - pd.Timedelta(days=400)]
    sma = W.rolling(44, min_periods=44).mean()
    valid = sma.notna() & W.notna()
    above = (W > sma) & valid
    member = pd.DataFrame(False, index=W.index, columns=W.columns)
    for f in W.index:
        dd = f.date()
        member.loc[f] = [bool(ticker_in_index_on(t, dd, mem)) for t in W.columns]
    use = valid & member
    n = use.sum(axis=1)
    b = (above & use).sum(axis=1) / n.where(n >= 30)
    return b


def s3_scale(nifty: pd.Series, breadth: pd.Series, keys) -> tuple[dict, pd.Series]:
    med = breadth.rolling(26, min_periods=26).median()
    out = {}
    for k in keys:
        D = decision_date(nifty.index, k)
        f = week_label(D) if D is not None else None
        ok = f is not None and f in breadth.index and np.isfinite(breadth.loc[f]) and np.isfinite(med.loc[f])
        out[k] = 0.5 if (ok and breadth.loc[f] < med.loc[f]) else 1.0
    return out, med


def clairvoyant_scale(nifty: pd.Series, wk: pd.Series, keys, level: float) -> dict:
    out = {}
    pos = {d: i for i, d in enumerate(wk.index)}
    for k in keys:
        D = decision_date(nifty.index, k)
        f = week_label(D) if D is not None else None
        i = pos.get(f)
        hit = i is not None and i + 13 < len(wk) and wk.iloc[i + 13] / wk.iloc[i] - 1.0 < 0
        out[k] = level if hit else 1.0
    return out


class OwnResultsGate:
    """S4: book's own trailing-4-week result. Reads the run's own ledger / position log (PIT: only rows dated
    before the entry week's Monday). Scale 0 when mean({closed R in the prior 28d} + {MTM R of open names}) < 0."""

    def __init__(self, ledger: list, plog: list):
        self.ledger, self.plog, self.cache, self.metric = ledger, plog, {}, {}

    def _compute(self, key):
        mon = monday(key)
        vals = []
        for r in self.ledger:
            xd = r.get("exit_date")
            if xd is None:
                continue
            xd = pd.Timestamp(xd)
            if xd < mon and (mon - xd).days <= 28 and r.get("reason") != "eos":
                vals.append(float(r["R"]))
        last = None
        for row in reversed(self.plog):
            d = pd.Timestamp(row["date"])
            if d >= mon:
                continue
            if last is None:
                last = d
            if d != last:
                break
            vals.append((float(row["mark_px"]) - float(row["entry"])) / float(row["risk0"]))
        m = float(np.mean(vals)) if vals else float("nan")
        return m, (0.0 if (vals and m < 0) else 1.0)

    def get(self, key, default=1.0):
        if key not in self.cache:
            m, sc = self._compute(key)
            self.metric[key], self.cache[key] = m, sc
        return self.cache[key]


# ----------------------------------------------------------------------------- engine
def setup(cache: Path):
    R94, live, load_demerger_rows, corrected_universe = runs._engine()
    from nq.data.membership import load_membership
    cut = runs.cut_universe(corrected_universe())
    last = runs.assert_within_cut(cut)
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    as_of = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=None)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **{**live["LIVE_PREP"], "as_of": as_of})
    mem = load_membership()
    return R94, P, mem, events, last


def run_row(R94, P, mem, events, scale, label: str, desc: str, last) -> dict:
    cfg = runs.normalize_config(None)
    kw = runs.engine_kwargs(cfg)
    a_grade = R94.grade_a_entries(P)
    ledger, plog, elog = [], [], []
    lever = scale(ledger, plog) if callable(scale) else scale
    t0 = time.time()
    out = R94.backtest(P, mem, ledger=ledger, a_grade=a_grade, **kw, demerger_events=events, position_log=plog,
                       event_log=elog, entry_size_scale_by_week=lever)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    nav = nav[nav.index >= pd.Timestamp(cfg["start"])]
    assert nav.index.max() <= pd.Timestamp(runs.CUT)
    from nq.runner.manifest import build_manifest
    man = build_manifest({**kw, "grade_gate": True, "entry_size_scale_by_week": desc}, membership="pit",
                         data_vintage=str(last.date()), window=(cfg["start"], runs.CUT))
    return {"label": label, "nav": nav, "ledger": pd.DataFrame(ledger), "plog": pd.DataFrame(plog),
            "lever": lever, "manifest": {k: man[k] for k in ("label", "is_live_book", "differs_on", "membership",
                                                             "data_vintage", "window", "config_hash", "code_sha")},
            "seconds": round(time.time() - t0, 1), "a_grade": a_grade}


# ----------------------------------------------------------------------------- metrics
def slice_metrics(nav: pd.Series, s, e) -> dict:
    n = nav[(nav.index >= pd.Timestamp(s)) & (nav.index <= pd.Timestamp(e))]
    r = n.pct_change().dropna()
    yrs = (n.index[-1] - n.index[0]).days / 365.25
    cagr = float((n.iloc[-1] / n.iloc[0]) ** (1 / yrs) - 1)
    mdd = float((n / n.cummax() - 1).min())
    return {"first": str(n.index[0].date()), "last": str(n.index[-1].date()), "n": int(len(n)),
            "sharpe": float(r.mean() / r.std() * np.sqrt(TD)), "cagr": cagr, "maxdd": mdd,
            "calmar": float(cagr / abs(mdd)) if mdd < 0 else float("nan"),
            "total_return": float(n.iloc[-1] / n.iloc[0] - 1)}


def year_returns(nav: pd.Series) -> dict:
    out, base = {}, float(nav.iloc[0])
    for y in sorted(set(nav.index.year)):
        last = float(nav[nav.index.year == y].iloc[-1])
        out[str(y)] = last / base - 1.0
        base = last
    return out


def find_episodes(nifty: pd.Series, thr: float, lo, hi) -> list[dict]:
    dd = nifty / nifty.rolling(DD_LOOKBACK, min_periods=DD_LOOKBACK).max() - 1.0
    idx = nifty.index
    flag = (dd <= -thr) & (idx >= lo) & (idx <= hi)
    pos = np.flatnonzero(flag.to_numpy())
    if not len(pos):
        return []
    grp = [[pos[0], pos[0]]]
    for p in pos[1:]:
        if p - grp[-1][1] <= MERGE_GAP:
            grp[-1][1] = p
        else:
            grp.append([p, p])
    return [{"start": idx[a], "end": idx[b], "depth": float(dd.iloc[a:b + 1].min())} for a, b in grp]


def flagged_weeks(scale_map) -> set:
    return {k for k, v in scale_map.items() if v < 1.0}


def forgone(ctrl_ledger: pd.DataFrame, flagged: set) -> dict:
    if not len(ctrl_ledger):
        return {}
    led = ctrl_ledger[ctrl_ledger["reason"] != "eos"].copy()
    led["entry_date"] = pd.to_datetime(led["entry_date"])
    iso = led["entry_date"].dt.isocalendar()
    led["_k"] = list(zip(iso["year"].astype(int), iso["week"].astype(int)))
    hit = led[led["_k"].isin(flagged)]
    rest = led[~led["_k"].isin(flagged)]

    def st(t):
        return {"n": int(len(t)), "sum_R": float(t["R"].sum()), "mean_R": float(t["R"].mean()) if len(t) else None,
                "win_rate": float((t["R"] > 0).mean()) if len(t) else None}
    return {"control_trades_in_throttled_weeks": st(hit), "control_trades_in_open_weeks": st(rest)}


def grade(row: dict, ctrl: dict) -> dict:
    res, dd_ok_all, full_all = {}, True, True
    for name in SUBS:
        a, c = row["subs"][name], ctrl["subs"][name]
        d_dd, d_sh, d_cal = a["maxdd"] - c["maxdd"], a["sharpe"] - c["sharpe"], a["calmar"] - c["calmar"]
        dd_ok = d_dd >= 0.05
        full = (d_cal > 0) and dd_ok and (d_sh >= -0.10)
        res[name] = {"d_maxdd_pp": d_dd * 100, "d_sharpe": d_sh, "d_calmar": d_cal, "maxdd_cut_ge_5pp": bool(dd_ok),
                     "calmar_up": bool(d_cal > 0), "sharpe_ok": bool(d_sh >= -0.10), "all_three": bool(full)}
        dd_ok_all &= dd_ok
        full_all &= full
    res["reading"] = ("EARNS A TRIAL PROPOSAL" if full_all else "RISK DIAL" if dd_ok_all else "NO HELP")
    return res


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "p1_throttle_cache"))
    a = ap.parse_args()
    cd = Path(a.cache_dir)
    cd.mkdir(parents=True, exist_ok=True)
    led_txt = LEDGER.read_text(encoding="utf-8")
    n_screens = sum(1 for ln in led_txt.splitlines() if ln.startswith("| ") and ln.split("|")[1].strip().isdigit())
    ntr = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text())["cumulative_n_trials"]
    assert n_screens >= 24, "screen row 24 must be on the ledger BEFORE this runs"

    R94, P, mem, events, last = setup(cd)
    nifty = runs.load_nifty()
    wk = nifty.resample("W-FRI").last().dropna()
    lo, hi = pd.Timestamp(runs.MIN_START), pd.Timestamp(runs.CUT)
    keys = iso_weeks(lo, hi)
    t0 = time.time()
    breadth = breadth_series(P, mem, lo)
    print(f"breadth built {time.time() - t0:.0f}s: weeks {len(breadth)}, mean {breadth.mean():.3f}")

    S1 = s1_scale(nifty, wk, keys)
    S2 = s2_scale(nifty, keys)
    S3, med = s3_scale(nifty, breadth, keys)
    CV0 = clairvoyant_scale(nifty, wk, keys, 0.0)
    CVh = clairvoyant_scale(nifty, wk, keys, 0.5)

    rows_spec = [
        ("CONTROL", None, "CONTROL"),
        ("S1 Nifty<40w SMA -> 0", S1, "S1"), ("S2 Nifty 20d<0 & <50dSMA -> 0.5", S2, "S2"),
        ("S3 breadth<26w median -> 0.5", S3, "S3"), ("S4 own trailing-4w R<0 -> 0", OwnResultsGate, "S4"),
        ("CV0 clairvoyant 13w<0 -> 0", CV0, "CV0"), ("CVh clairvoyant 13w<0 -> 0.5", CVh, "CVh")]
    raw = {}
    for label, sc, desc in rows_spec:
        raw[desc] = run_row(R94, P, mem, events, sc, label, desc, last)
        print(f"ran {label} ({raw[desc]['seconds']}s)")

    # control must equal the lab's live-config replay exactly
    lab = runs.replay(None, cache_dir=cd, runs_path=cd / "lab_runs.jsonl")
    c_nav = raw["CONTROL"]["nav"]
    c_sh = float(c_nav.pct_change().dropna().mean() / c_nav.pct_change().dropna().std() * np.sqrt(TD))
    assert abs(c_sh - lab["sharpe"]) < 1e-9 and abs(float(c_nav.iloc[-1]) - float(lab["nav"].iloc[-1])) < 1e-6, \
        "CONTROL does not reproduce nq.lab.runs.replay"

    # S4 decisions: fill the state-reading gate for every week (post-hoc reads are the same PIT rows)
    gate4 = raw["S4"]["lever"]
    S4 = {k: gate4.get(k) for k in keys}
    maps = {"S1": S1, "S2": S2, "S3": S3, "S4": S4, "CV0": CV0, "CVh": CVh}

    ep = find_episodes(nifty, EP_THR, lo, c_nav.index.max())
    ctrl_ledger = raw["CONTROL"]["ledger"]
    a_dates = []
    for (t, e0) in raw["CONTROL"]["a_grade"]:
        dte = pd.Timestamp(P[t]["dates"][e0])
        if dte >= lo:
            iso = dte.isocalendar()
            a_dates.append((int(iso[0]), int(iso[1])))
    res_rows = {}
    for desc, r in raw.items():
        nav = r["nav"]
        rets = nav.pct_change().dropna()
        full = slice_metrics(nav, nav.index[0], nav.index[-1])
        dsr = runs.deflated_sharpe(full["sharpe"], len(rets), N_TRIALS)
        subs = {k: slice_metrics(nav, *v) for k, v in SUBS.items()}
        episodes = []
        for e in ep:
            s, w = e["start"], e["start"] + pd.Timedelta(days=LIVE_WINDOW_DAYS)
            sl = nav[(nav.index >= s) & (nav.index <= w)]
            episodes.append({"start": str(s.date()), "book_return": float(sl.iloc[-1] / sl.iloc[0] - 1),
                             "maxdd": float((sl / sl.cummax() - 1).min())})
        pl = r["plog"]
        cash_share = float("nan")
        if len(pl):
            cs = (pl.groupby("date")["cash"].first() / pl.groupby("date")["equity"].first())
            cs.index = pd.DatetimeIndex(cs.index).normalize()
            cash_share = float(cs.reindex(nav.index).fillna(1.0).mean())
        row = {"label": r["label"], "full": full, "dsr": dsr, "subs": subs, "year_returns": year_returns(nav),
               "episodes_8pct": episodes, "avg_cash_share": cash_share, "manifest": r["manifest"],
               "n_trades": int(len(r["ledger"])), "seconds": r["seconds"]}
        if desc in maps:
            fl = flagged_weeks(maps[desc])
            row["weeks_throttled"] = len(fl)
            row["weeks_total"] = len(keys)
            row["share_weeks_throttled"] = len(fl) / len(keys)
            row["share_gradeA_windows_hit"] = float(np.mean([k in fl for k in a_dates])) if a_dates else None
            row["forgone_control_trades"] = forgone(ctrl_ledger, fl)
        res_rows[desc] = row
    for desc, row in res_rows.items():
        if desc != "CONTROL":
            row["grade"] = grade(row, res_rows["CONTROL"])
            row["episode_delta_vs_control"] = [x["book_return"] - c["book_return"] for x, c in
                                               zip(row["episodes_8pct"], res_rows["CONTROL"]["episodes_8pct"])]

    # POST-HOC NULL CONTROLS (added after the first read showed the half-size rows hold LESS cash than CONTROL, i.e.
    # a sizing/redeployment confound; disclosed in the readout, not graded, not counted as ideas). H05 = half size
    # EVERY week; RND* = the same number of throttled weeks as a signal, placed at random (seeded). They separate
    # "when" from "how much / how often".
    rng = np.random.default_rng(20261102)
    nulls = {}

    def _null_metrics(nav):
        full = slice_metrics(nav, nav.index[0], nav.index[-1])
        s1 = slice_metrics(nav, *SUBS["2019-21"])
        s2 = slice_metrics(nav, *SUBS["2022-24H1"])
        return {"sharpe": full["sharpe"], "calmar": full["calmar"], "maxdd": full["maxdd"],
                "dd_2019_21": s1["maxdd"], "dd_2022_24H1": s2["maxdd"],
                "sh_2019_21": s1["sharpe"], "sh_2022_24H1": s2["sharpe"]}
    h05 = run_row(R94, P, mem, events, {k: 0.5 for k in keys}, "H05 half size every week", "H05", last)
    nulls["H05"] = _null_metrics(h05["nav"])
    nulls["H05"]["avg_cash_share"] = float((h05["plog"].groupby("date")["cash"].first()
                                            / h05["plog"].groupby("date")["equity"].first()).reindex(
        pd.DatetimeIndex(h05["nav"].index)).fillna(1.0).mean()) if len(h05["plog"]) else None
    nulls["H05"]["n_trades"] = int(len(h05["ledger"]))
    for tag, level, n_wk in (("RND0_n59", 0.0, len(flagged_weeks(S1))), ("RNDh_n76", 0.5, len(flagged_weeks(S2))),
                             ("RNDh_n126", 0.5, len(flagged_weeks(S3)))):
        draws = []
        for i in range(20):
            pick = set(rng.choice(len(keys), size=n_wk, replace=False).tolist())
            sc = {k: (level if j in pick else 1.0) for j, k in enumerate(keys)}
            r_ = run_row(R94, P, mem, events, sc, tag, tag, last)
            draws.append(_null_metrics(r_["nav"]))
        arr = {m: np.array([d_[m] for d_ in draws]) for m in draws[0]}
        nulls[tag] = {"n_draws": 20, "n_weeks": n_wk, "level": level,
                      **{m: {"mean": float(v.mean()), "p05": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)),
                             "draws": [float(x) for x in v]} for m, v in arr.items()}}
        print("null done", tag, flush=True)

    # breadth diagnostics + agreement between causal signals and the clairvoyant weeks
    fl = {d: flagged_weeks(m) for d, m in maps.items()}
    overlap = {d: {"flagged": len(fl[d]), "also_clairvoyant": len(fl[d] & fl["CV0"]),
                   "precision": (len(fl[d] & fl["CV0"]) / len(fl[d])) if fl[d] else None,
                   "recall_of_cv0_weeks": (len(fl[d] & fl["CV0"]) / len(fl["CV0"])) if fl["CV0"] else None}
               for d in ("S1", "S2", "S3", "S4")}
    res = {"standing_counts": {"screens": n_screens, "sealed_opens": 3, "n_trials": ntr},
           "cut": runs.CUT, "start": runs.MIN_START, "n_trials_for_dsr": N_TRIALS, "last_bar": str(last.date()),
           "control_check": {"sharpe_lab": lab["sharpe"], "sharpe_here": c_sh, "maxdd": lab["maxdd"],
                             "n_trades": lab["n_trades"]},
           "episodes_8pct": [{"start": str(e["start"].date()), "end": str(e["end"].date()), "depth": e["depth"]} for e in ep],
           "rows": res_rows, "overlap_with_clairvoyant": overlap, "post_hoc_null_controls": nulls,
           "breadth": {"mean": float(breadth.mean()), "weeks": int(breadth.notna().sum())}}
    OUT.write_text(json.dumps(res, indent=2, default=str, allow_nan=True), encoding="utf-8")

    def f(x, p=2):
        return "nan" if x is None or not np.isfinite(x) else f"{x:.{p}f}"
    print("\nrow | Sharpe | DSR-defl | CAGR | MaxDD | Calmar | worstYr | thr% | A-hit% | sub1 Sh/DD/Cal | sub2 Sh/DD/Cal | reading")
    for d, r in res_rows.items():
        fu, s1, s2 = r["full"], r["subs"]["2019-21"], r["subs"]["2022-24H1"]
        wy = min(r["year_returns"].values())
        print(f"{d:8s}| {f(fu['sharpe'])} | {f(r['dsr']['deflated_sharpe'])} | {f(fu['cagr'] * 100, 1)} | {f(fu['maxdd'] * 100, 1)} | "
              f"{f(fu['calmar'])} | {f(wy * 100, 1)} | {f(r.get('share_weeks_throttled', 0) * 100, 0)} | "
              f"{f((r.get('share_gradeA_windows_hit') or 0) * 100, 0)} | {f(s1['sharpe'])}/{f(s1['maxdd'] * 100, 1)}/{f(s1['calmar'])} | "
              f"{f(s2['sharpe'])}/{f(s2['maxdd'] * 100, 1)}/{f(s2['calmar'])} | {r.get('grade', {}).get('reading', '-')}")
    print("\nepisodes:", [e["start"] for e in res["episodes_8pct"]])
    for d, r in res_rows.items():
        print(d, [f(x["book_return"] * 100, 1) for x in r["episodes_8pct"]])


if __name__ == "__main__":
    main()
