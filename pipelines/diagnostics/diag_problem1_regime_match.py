"""Problem 1 regime match (MEASURE tier): is the live 2026-07..10 loss a correction, or a defect?

Replays the LIVE book (nq.lab.runs DEFAULT_CONFIG: PIT membership, train window only, cut 2024-06-30,
start 2019-01-01) ONCE, finds Nifty correction episodes objectively, and reads each episode as a
CONTINUOUS SLICE of that one run (never a fresh-capital re-run). The uncapped Grade-A replay supplies the
signal population comparable to the live tracker. The live record is read from the committed live files
(all entries >= 2026-07-04; nothing sealed). The verdict rule is pre-committed in
diagnostics/research/diagnosis/2026-11-02_problem1_regime_match.md and applied here unchanged.

Run:  python pipelines/diagnostics/diag_problem1_regime_match.py [--cache-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nq.lab import runs                                   # noqa: E402
from nq.lab.stats import exclude_degenerate_stops         # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "diagnosis" / "2026-11-02_problem1_regime_match.json"
LIVE_WINDOW_DAYS = 116          # 2026-07-06 .. 2026-10-30
LIVE_START = pd.Timestamp("2026-07-06")
LIVE_BASE = 1_000_000.0
MERGE_GAP, DD_LOOKBACK = 21, 252
THRESHOLDS = (0.08, 0.10)
MIN_WR_TRADES = 10
STOP_REASONS = ("stop", "stop_part")


# ------------------------------------------------------------------ episodes
def find_episodes(nifty: pd.Series, thr: float, lo: pd.Timestamp, hi: pd.Timestamp) -> list[dict]:
    dd = nifty / nifty.rolling(DD_LOOKBACK, min_periods=DD_LOOKBACK).max() - 1.0
    idx = nifty.index
    flag = (dd <= -thr) & (idx >= lo) & (idx <= hi)
    pos = np.flatnonzero(flag.to_numpy())
    if not len(pos):
        return []
    runs_: list[list[int]] = [[pos[0], pos[0]]]
    for p in pos[1:]:
        if p - runs_[-1][1] <= MERGE_GAP:          # gap in sessions < MERGE_GAP+1 -> merge
            runs_[-1][1] = p
        else:
            runs_.append([p, p])
    eps = []
    for a, b in runs_:
        seg = dd.iloc[a:b + 1]
        trough = seg.idxmin()
        hi_win = nifty.iloc[max(0, a - DD_LOOKBACK):a + 1]
        eps.append({"start": idx[a], "end": idx[b], "trough_date": trough, "depth": float(seg.min()),
                    "peak_date": hi_win.idxmax(), "sessions": int(b - a + 1)})
    return eps


# ------------------------------------------------------------------ slice stats
def slice_stats(nav: pd.Series, nifty: pd.Series, s: pd.Timestamp, e: pd.Timestamp) -> dict:
    n = nav[(nav.index >= s) & (nav.index <= e)]
    m = nifty.reindex(nav.index).ffill()
    m = m[(m.index >= s) & (m.index <= e)]
    if len(n) < 3:
        return {"n_sessions": int(len(n))}
    r = n.pct_change().dropna()
    book, mkt = float(n.iloc[-1] / n.iloc[0] - 1), float(m.iloc[-1] / m.iloc[0] - 1)
    return {"first": str(n.index[0].date()), "last": str(n.index[-1].date()), "n_sessions": int(len(n)),
            "book_return": book, "maxdd": float((n / n.cummax() - 1).min()),
            "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan"),
            "nifty_return": mkt, "book_minus_nifty": book - mkt}


def trade_stats(t: pd.DataFrame) -> dict:
    n = int(len(t))
    if n == 0:
        return {"n": 0}
    R = t["R"].astype(float)
    stops = t[t["reason"] == "stop"]
    return {"n": n, "wins": int((R > 0).sum()), "win_rate": float((R > 0).mean()), "mean_R": float(R.mean()),
            "median_R": float(R.median()), "stop_exit_share": float(t["reason"].isin(STOP_REASONS).mean()),
            "share_below_m1.5R": float((R < -1.5).mean()),
            "mean_beyond_stop_R": float(np.maximum(0.0, -1.0 - stops["R"]).mean()) if len(stops) else float("nan"),
            "share_stops_beyond_1R": float((stops["R"] < -1.0).mean()) if len(stops) else float("nan")}


def prep_ledger(led: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    led = led.copy()
    led["entry_date"] = pd.to_datetime(led["entry_date"])
    led["exit_date"] = pd.to_datetime(led["exit_date"])
    n0 = len(led)
    led = exclude_degenerate_stops(led)
    n_deg = n0 - len(led)
    eos = led["reason"] == "eos"
    return led[~eos].copy(), {"rows": n0, "degenerate_excluded": int(n_deg), "eos_excluded": int(eos.sum())}


def window_trades(led: pd.DataFrame, s: pd.Timestamp, e: pd.Timestamp) -> dict:
    ent = led[(led["entry_date"] >= s) & (led["entry_date"] <= e)]
    return {"entered": trade_stats(ent), "closed_by_window_end": trade_stats(ent[ent["exit_date"] <= e])}


def pooled_unique(led: pd.DataFrame, windows: list[tuple[pd.Timestamp, pd.Timestamp]]) -> dict:
    """Pool the windows' trades, counting a signal once even where two episode windows overlap."""
    ent = [led[(led["entry_date"] >= s) & (led["entry_date"] <= e)].assign(_wend=e) for s, e in windows]
    ent = pd.concat(ent) if ent else led.iloc[0:0].assign(_wend=pd.NaT)
    closed = ent[ent["exit_date"] <= ent["_wend"]]
    key = ["tkr", "entry_date"]
    return {"entered": trade_stats(ent.drop_duplicates(key)), "closed_by_window_end": trade_stats(closed.drop_duplicates(key))}


# ------------------------------------------------------------------ live record
def live_record() -> dict:
    h = pd.read_csv(ROOT / "results" / "portfolio_history_weekly.csv", parse_dates=["date"]).set_index("date")["total_value"]
    sig = pd.DataFrame(json.load(open(ROOT / "results" / "signals_history_weekly.json")))
    closed = sig[sig["status"] != "ACTIVE"]
    R = closed["r_multiple"].astype(float)
    r = h.pct_change().dropna()
    peak = float(max(LIVE_BASE, h.cummax().max()))
    return {"first": str(h.index[0].date()), "last": str(h.index[-1].date()), "n_sessions": int(len(h)),
            "book_return": float(h.iloc[-1] / LIVE_BASE - 1),
            "maxdd": float((pd.concat([pd.Series([LIVE_BASE]), h.reset_index(drop=True)]).pipe(lambda x: x / x.cummax() - 1)).min()),
            "sharpe": float(r.mean() / r.std() * np.sqrt(252)),
            "n_closed": int(len(closed)), "wins": int((R > 0).sum()), "win_rate": float((R > 0).mean()),
            "mean_R": float(R.mean()), "median_R": float(R.median()),
            "share_below_m1.5R": float((R < -1.5).mean()), "n_below_m1.5R": int((R < -1.5).sum()),
            "stop_exit_share": float(closed["exit_reason"].isin(STOP_REASONS).mean()),
            "n_open": int((sig["status"] == "ACTIVE").sum())}


def binom_cdf(k: int, n: int, p: float) -> float:
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1)))


def pct_rank(live: float, hist: list[float]) -> float:
    """Share of historical episodes that did WORSE than live (lower value)."""
    return float(np.mean([h < live for h in hist])) if hist else float("nan")


# ------------------------------------------------------------------ main
def analyse(thr: float, nav, nifty, led_c, led_u, live, lo, hi) -> dict:
    eps = find_episodes(nifty, thr, lo, hi)
    rows = []
    for ep in eps:
        s, e = ep["start"], ep["end"]
        wend = s + pd.Timedelta(days=LIVE_WINDOW_DAYS)
        rows.append({
            "start": str(s.date()), "peak_date": str(ep["peak_date"].date()), "trough_date": str(ep["trough_date"].date()),
            "end": str(e.date()), "depth": ep["depth"], "sessions": ep["sessions"],
            "window_end": str(wend.date()),
            "full_episode": {"slice": slice_stats(nav, nifty, s, e), "capped": window_trades(led_c, s, e),
                             "uncapped_gradeA": window_trades(led_u, s, e)},
            "live_shaped_window": {"slice": slice_stats(nav, nifty, s, wend), "capped": window_trades(led_c, s, wend),
                                   "uncapped_gradeA": window_trades(led_u, s, wend)}})
    out = {"threshold": thr, "n_episodes": len(rows), "episodes": rows}
    br = [r["live_shaped_window"]["slice"].get("book_return") for r in rows]
    br = [x for x in br if x is not None]
    wr = [(r["start"], r["live_shaped_window"]["uncapped_gradeA"]["closed_by_window_end"]) for r in rows]
    wr_q = [(d, x["win_rate"]) for d, x in wr if x.get("n", 0) >= MIN_WR_TRADES]
    pooled = pooled_unique(led_u, [(ep["start"], ep["start"] + pd.Timedelta(days=LIVE_WINDOW_DAYS)) for ep in eps])
    out["pooled_uncapped_gradeA_unique"] = pooled
    pool_n, pool_w = pooled["closed_by_window_end"].get("n", 0), pooled["closed_by_window_end"].get("wins", 0)
    p = pool_w / pool_n if pool_n else float("nan")
    pe_n, pe_w = pooled["entered"].get("n", 0), pooled["entered"].get("wins", 0)
    out["range"] = {
        "book_return_min": min(br) if br else None, "book_return_max": max(br) if br else None,
        "live_book_return": live["book_return"],
        "live_inside_book_return": bool(br and live["book_return"] >= min(br)),
        "pct_episodes_worse_than_live_book_return": pct_rank(live["book_return"], br),
        "winrate_qualifying_episodes": [{"start": d, "win_rate": w} for d, w in wr_q],
        "winrate_min": min(w for _, w in wr_q) if wr_q else None,
        "winrate_max": max(w for _, w in wr_q) if wr_q else None,
        "live_win_rate": live["win_rate"],
        "live_inside_win_rate": bool(wr_q and live["win_rate"] >= min(w for _, w in wr_q)),
        "pct_episodes_worse_than_live_win_rate": pct_rank(live["win_rate"], [w for _, w in wr_q]),
        "pooled_closed_by_window_end": {"n": pool_n, "wins": pool_w, "win_rate": p},
        "pooled_entered_eventual": {"n": pe_n, "wins": pe_w, "win_rate": (pe_w / pe_n if pe_n else None)},
        "binom_P_le_1_win_in_32": binom_cdf(1, 32, p) if pool_n else None,
        "binom_P_le_1_win_in_32_eventual_secondary": binom_cdf(1, 32, pe_w / pe_n) if pe_n else None}
    r_ = out["range"]
    if len(rows) < 3 or len(wr_q) < 3:
        verdict = "INCONCLUSIVE"
    elif r_["live_inside_book_return"] and r_["live_inside_win_rate"] and r_["binom_P_le_1_win_in_32"] >= 0.05:
        verdict = "REGIME"
    else:
        verdict = "WORSE THAN REGIME"
    out["verdict"] = verdict
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "p1_lab_cache"))
    a = ap.parse_args()
    cd = Path(a.cache_dir)
    rp = cd / "lab_runs.jsonl"                    # keep the repo's multiplicity ledger untouched
    capped = runs.replay(None, cache_dir=cd, runs_path=rp)
    uncapped = runs.replay({"uncapped": True}, cache_dir=cd, runs_path=rp)
    assert pd.Timestamp(capped["last_bar"]) <= pd.Timestamp(runs.CUT)
    assert pd.Timestamp(uncapped["last_bar"]) <= pd.Timestamp(runs.CUT)
    nav, nifty = capped["nav"], runs.load_nifty()
    assert nav.index.max() <= pd.Timestamp(runs.CUT) and nifty.index.max() <= pd.Timestamp(runs.CUT)
    led_c, meta_c = prep_ledger(capped["ledger"])
    led_u, meta_u = prep_ledger(uncapped["ledger"])
    live = live_record()
    lo, hi = pd.Timestamp(runs.MIN_START), nav.index.max()
    res = {"standing_counts": {"screens": 23, "sealed_opens": 3, "n_trials": 2},
           "run": {"config": capped["config"], "config_hash": capped["config_hash"], "sharpe": capped["sharpe"],
                   "maxdd": capped["maxdd"], "cagr": capped["cagr"], "n_trades_capped": capped["n_trades"],
                   "n_trades_uncapped": uncapped["n_trades"], "last_bar": capped["last_bar"],
                   "ledger_capped": meta_c, "ledger_uncapped": meta_u},
           "train_baseline": {"capped_all": trade_stats(led_c), "uncapped_all": trade_stats(led_u)},
           "live": live,
           "analysis": {f"dd_{int(t * 100)}pct": analyse(t, nav, nifty, led_c, led_u, live, lo, hi) for t in THRESHOLDS}}
    res["verdict_primary_8pct"] = res["analysis"]["dd_8pct"]["verdict"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str, allow_nan=True), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("run", "train_baseline", "live", "verdict_primary_8pct")}, indent=1, default=str))
    for k, v in res["analysis"].items():
        print(f"\n== {k}: {v['n_episodes']} episodes, verdict {v['verdict']}")
        for e in v["episodes"]:
            s = e["live_shaped_window"]["slice"]
            u = e["live_shaped_window"]["uncapped_gradeA"]["closed_by_window_end"]
            print(e["start"], e["trough_date"], e["end"], f"depth {e['depth']:.3f}",
                  f"| win book {s.get('book_return', float('nan')):.3f} nifty {s.get('nifty_return', float('nan')):.3f}",
                  f"| uncapped closed n={u.get('n')} wr={u.get('win_rate')}")
        print(json.dumps(v["range"], indent=1, default=str))


if __name__ == "__main__":
    main()
