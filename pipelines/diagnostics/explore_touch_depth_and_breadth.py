"""EXPLORE (tier 0, docs/PROCESS_TIERS.md) -- 2026-10-20. No pre-registration, no screen row, no n_trials change.

ITEM 1  Rank the weekly top-5 by TOUCH DEPTH instead of CRS distance.
ITEM 4  Our own signal funnel as a breadth gauge (zero-trial count).

Everything is EXPLORATORY and TRAIN ONLY: every price series is cut at 2024-06-30 before the engine sees
it (asserted); the reported window is 2019-01-01..2024-06-30; the sealed 2024-07-01..2026-06-30 slice is
never loaded. The book is the LIVE configuration with PIT membership, driven exactly as nq/lab/runs.replay
drives it (engine_kwargs(DEFAULT_CONFIG), load_membership(), demerger events). The engine is NOT edited:
the alternative A-sets are built here and handed to R94.backtest(a_grade=...).

    python pipelines/diagnostics/explore_touch_depth_and_breadth.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.lab import runs as L                                   # noqa: E402

START, CUT = L.MIN_START, L.CUT
SUBPERIODS = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", CUT)}
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-10-20_touch_depth_and_breadth.json"
TOP_N = 5
DEEP = 0.05                                                    # the registry's deep/shallow cut (Q2)
LOOKBACK_WK = 8                                                # Q2 pullback window (weeks ending at the signal week)


# ----------------------------------------------------------------------------------------- stats
def curve_stats(nav: pd.Series, lo: str, hi: str) -> dict:
    """CONTINUOUS SLICE of the one full-run curve (never a fresh-capital re-run)."""
    e = nav[(nav.index >= pd.Timestamp(lo)) & (nav.index <= pd.Timestamp(hi))]
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25 if len(e) > 1 else float("nan")
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 2 and r.std() > 0 else None,
            "cagr_pct": float(((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100) if len(e) > 1 else None,
            "maxdd_pct": float((e / e.cummax() - 1).min() * 100) if len(e) else None}


def deflate(nav: pd.Series, n_trials: int) -> dict:
    r = nav.pct_change().dropna()
    sh = float(r.mean() / r.std() * np.sqrt(252))
    d = L.deflated_sharpe(sh, len(r), n_trials, skew=float(r.skew()), kurt=float(r.kurt() + 3.0))
    return {"sharpe_raw": sh, "n_trials_used": n_trials, "dsr_prob": d["dsr"],
            "sr0_annual": d["sr0_annual"], "sharpe_deflated": d["deflated_sharpe"]}


# ----------------------------------------------------------------------------------------- touch depth
def weekly_structure(s: dict):
    """Re-derive the engine's weekly groups / SMA from P[t] arrays EXACTLY as prep_weekly_rank does."""
    idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
    weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    c, lw = s["c"], s["l"]
    wlow = np.array([lw[dd].min() for dd in weeks]); wclose = np.array([c[dd[-1]] for dd in weeks])
    wsma = pd.Series(wclose).rolling(44).mean().to_numpy()
    return weeks, wlow, wclose, wsma


def build_signal_table(P) -> pd.DataFrame:
    """One row per entry window: ticker, e0, dates, band, CRS rank, and PIT touch-depth features.

    depth_sw = signal-week low / its 44w SMA - 1                     (from the entry_win tuple alone)
    depth_8w = MIN over the 8 weeks ending at the signal week of (weekly low / that week's own SMA - 1)
               (the Q2 'pullback low' extension of forward/prereg_signal_quality.md, low-based)
    Every input is known at the signal-week close, i.e. before the entry week. PIT by construction."""
    rows, n_mis = [], 0
    for t, s in P.items():
        if not s["entry_win"]:
            continue
        weeks, wlow, wclose, wsma = weekly_structure(s)
        wk_of_first = {dd[0]: j for j, dd in enumerate(weeks)}
        dates = s["dates"]
        for e0, (edays, lo, hi, crs, sma_sig, origin) in s["entry_win"].items():
            k = wk_of_first[e0] - 1                              # signal week = the week before the entry window
            assert origin == 0, "live prep emits touch-origin signals only"
            if abs(wlow[k] - lo) > 1e-9 * max(1.0, abs(lo)) or abs(wsma[k] - sma_sig) > 1e-9 * max(1.0, abs(sma_sig)):
                n_mis += 1
            a = max(k - LOOKBACK_WK + 1, 0)
            ext_w = wlow[a:k + 1] / wsma[a:k + 1] - 1.0
            ext_w = ext_w[np.isfinite(ext_w)]
            rows.append({"t": t, "e0": int(e0), "entry_date": pd.Timestamp(dates[e0]),
                         "lo": float(lo), "hi": float(hi), "crs": float(crs),
                         "depth_sw": float(lo / sma_sig - 1.0),
                         "depth_8w": float(ext_w.min()) if len(ext_w) else float("nan")})
    assert n_mis == 0, f"{n_mis} entry windows disagree with the re-derived weekly low/SMA"
    df = pd.DataFrame(rows)
    iso = df["entry_date"].dt.isocalendar()
    df["wk"] = list(zip(iso["year"].astype(int), iso["week"].astype(int)))
    df["wk_monday"] = (df["entry_date"] - pd.to_timedelta(df["entry_date"].dt.weekday, unit="D")).dt.normalize()
    return df


def topn_set(df: pd.DataFrame, mem, tii, key) -> set:
    """Top-5 per ISO week by `key(row)` ascending, among BUYABLE signals (D6-style: band exists, PIT member)."""
    out = set()
    for _wk, g in df.groupby("wk"):
        ok = []
        for r in g.itertuples(index=False):
            if not r.hi > r.lo:
                continue
            if not tii(r.t, r.entry_date.date(), mem):
                continue
            k = key(r)
            if not np.isfinite(k[0]):
                continue
            ok.append((k, r.t, r.e0))
        ok.sort(key=lambda x: x[0])
        out.update((t, e0) for _k, t, e0 in ok[:TOP_N])
    return out


# ----------------------------------------------------------------------------------------- runs
def run_book(R94, P, mem, events, kw, a_grade, *, uncapped: bool):
    led, plog, elog = [], [], []
    out = R94.backtest(P, mem, ledger=led, a_grade=a_grade, **{**kw, "uncapped": uncapped},
                       demerger_events=events, position_log=plog, event_log=elog)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    nav = nav[nav.index >= pd.Timestamp(START)]
    return nav, pd.DataFrame(led)


def trade_stats(led: pd.DataFrame) -> dict:
    if led.empty:
        return {"n_trades": 0}
    closed = led[led["reason"] != "eos"]
    ed = pd.to_datetime(closed["entry_date"])
    sub = {k: float(closed[(ed >= pd.Timestamp(lo)) & (ed <= pd.Timestamp(hi))]["R"].mean()) for k, (lo, hi) in SUBPERIODS.items()}
    return {"n_trades": int(len(led)), "n_open_at_cut_eos": int((led["reason"] == "eos").sum()),
            "mean_R_closed": float(closed["R"].mean()), "median_R_closed": float(closed["R"].median()),
            "win_pct_closed": float((closed["R"] > 0).mean() * 100),
            "mean_R_incl_eos_mark": float(led["R"].mean()), "mean_R_closed_by_subperiod": sub,
            # R is heavy-tailed (gap/data events); report the tail so a mean is never read alone
            "min_R": float(closed["R"].min()), "n_R_below_minus5": int((closed["R"] < -5).sum()),
            "mean_R_closed_excl_below_minus5": float(closed[closed["R"] >= -5]["R"].mean()),
            "worst3": closed.nsmallest(3, "R")[[c for c in ("ticker", "entry_date", "R", "reason") if c in closed.columns]]
                      .astype(str).to_dict("records")}


# ----------------------------------------------------------------------------------------- item 4
def asof(s: pd.Series, d: pd.Timestamp):
    pos = s.index.searchsorted(d, side="right") - 1
    return float(s.iloc[pos]) if pos >= 0 else float("nan")


def fwd_ret(s: pd.Series, anchor: pd.Timestamp, weeks: int):
    end = anchor + pd.Timedelta(weeks=weeks)
    if end > pd.Timestamp(CUT):                                  # never look past the cut
        return float("nan")
    a, b = asof(s, anchor), asof(s, end)
    return b / a - 1.0 if a > 0 and b > 0 else float("nan")


def spearman(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 8:
        return {"n": int(m.sum()), "rho": None}
    xr = pd.Series(x[m]).rank().to_numpy(); yr = pd.Series(y[m]).rank().to_numpy()
    return {"n": int(m.sum()), "rho": float(np.corrcoef(xr, yr)[0, 1]), "pearson": float(np.corrcoef(x[m], y[m])[0, 1])}


def quintile_table(x, y, label_y):
    m = np.isfinite(x) & np.isfinite(y)
    d = pd.DataFrame({"x": x[m], "y": y[m]})
    if len(d) < 25:
        return []
    d["q"] = pd.qcut(d["x"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    g = d.groupby("q", observed=True).agg(n=("y", "size"), x_lo=("x", "min"), x_hi=("x", "max"),
                                          mean_y=("y", "mean"), median_y=("y", "median"))
    return [{"quintile": int(q), "n": int(r.n), "x_range": [float(r.x_lo), float(r.x_hi)],
             f"mean_{label_y}": float(r.mean_y), f"median_{label_y}": float(r.median_y)} for q, r in g.iterrows()]


def boot_diff(a: np.ndarray, b: np.ndarray, n=4000, seed=7):
    if len(a) < 5 or len(b) < 5:
        return None
    rng = np.random.default_rng(seed)
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def mondays_of(led: pd.DataFrame) -> pd.DataFrame:
    c = led[led["reason"] != "eos"].copy()
    ed = pd.to_datetime(c["entry_date"])
    c["wk_monday"] = (ed - pd.to_timedelta(ed.dt.weekday, unit="D")).dt.normalize()
    return c[c["wk_monday"] >= pd.Timestamp(START)]


def breadth_study(sig, P, mem, tii, nifty, nav_live, led_live, led_unc_a):
    all_mondays = pd.date_range(START, CUT, freq="W-MON")
    didx = {t: pd.DatetimeIndex(s["dates"]) for t, s in P.items()}
    alive, members = {}, {}
    for mon in all_mondays:
        fri = mon - pd.Timedelta(days=3)
        n_a = n_m = 0
        for t, di in didx.items():
            pos = di.searchsorted(fri, side="right") - 1
            if pos >= 0 and (fri - di[pos]).days <= 7:
                n_a += 1
                n_m += bool(tii(t, fri.date(), mem))
        alive[mon], members[mon] = n_a, n_m
    sig_m = sig[[bool(tii(t, d.date(), mem)) for t, d in zip(sig["t"], sig["entry_date"])]]
    wk = pd.DataFrame(index=all_mondays)
    wk["n_sig"] = sig.groupby("wk_monday").size().reindex(all_mondays).fillna(0)
    wk["n_sig_member"] = sig_m.groupby("wk_monday").size().reindex(all_mondays).fillna(0)
    wk["n_alive"] = pd.Series(alive); wk["n_members"] = pd.Series(members)
    wk["pct_names"] = wk["n_sig"] / wk["n_alive"] * 100
    wk["pct_members"] = wk["n_sig_member"] / wk["n_members"] * 100
    wk["anchor"] = wk.index - pd.Timedelta(days=3)               # signal-week Friday close
    wk = wk[wk["anchor"] >= pd.Timestamp(START)].copy()
    for h in (4, 13):
        wk[f"nifty_fwd{h}"] = [fwd_ret(nifty, a, h) for a in wk["anchor"]]
        wk[f"book_fwd{h}"] = [fwd_ret(nav_live, a, h) for a in wk["anchor"]]
    gl = mondays_of(led_live).groupby("wk_monday")["R"].agg(["mean", "size"])
    gu = mondays_of(led_unc_a).groupby("wk_monday")["R"].agg(["mean", "size"])
    wk["meanR_live_book"] = gl["mean"].reindex(wk.index); wk["nR_live_book"] = gl["size"].reindex(wk.index)
    wk["meanR_A_uncapped"] = gu["mean"].reindex(wk.index); wk["nR_A_uncapped"] = gu["size"].reindex(wk.index)

    res = {"n_weeks": int(len(wk)),
           "signals_per_week": {"mean": float(wk["n_sig"].mean()), "median": float(wk["n_sig"].median()),
                                "p10": float(wk["n_sig"].quantile(.1)), "p90": float(wk["n_sig"].quantile(.9)),
                                "max": int(wk["n_sig"].max()), "zero_weeks": int((wk["n_sig"] == 0).sum())},
           "pct_names_per_week": {"mean": float(wk["pct_names"].mean()), "p90": float(wk["pct_names"].quantile(.9))},
           "universe_alive_mean": float(wk["n_alive"].mean()), "members_mean": float(wk["n_members"].mean())}
    targets = ["nifty_fwd4", "nifty_fwd13", "book_fwd4", "book_fwd13", "meanR_live_book", "meanR_A_uncapped"]
    for xname in ("n_sig", "pct_names", "n_sig_member", "pct_members"):
        res[f"corr_{xname}"], res[f"quintiles_{xname}"] = {}, {}
        for col in targets:
            x = wk[xname].to_numpy(float); y = wk[col].to_numpy(float)
            c = spearman(x, y)
            h = 13 if col.endswith("13") else (4 if col.endswith("4") else 1)
            c["n_eff_overlap_adj"] = round(c["n"] / h, 1)
            res[f"corr_{xname}"][col] = c
            res[f"quintiles_{xname}"][col] = quintile_table(x, y, col)
    res["subperiod_spearman_n_sig"] = {k: {col: spearman(wk[(wk.index >= lo) & (wk.index <= hi)]["n_sig"].to_numpy(float),
                                                         wk[(wk.index >= lo) & (wk.index <= hi)][col].to_numpy(float))
                                           for col in targets} for k, (lo, hi) in SUBPERIODS.items()}
    thr = wk["n_sig"].quantile(.9)
    flood = set(wk.index[wk["n_sig"] >= thr])
    pooled = {}
    for name, led in (("live_book_trades", led_live), ("A_uncapped_trades", led_unc_a)):
        c = mondays_of(led)
        fl = c[c["wk_monday"].isin(flood)]["R"]; rest = c[~c["wk_monday"].isin(flood)]["R"]
        pooled[name] = {"flood_decile_threshold_signals": float(thr), "n_flood": int(len(fl)),
                        "mean_R_flood": float(fl.mean()) if len(fl) else None, "n_rest": int(len(rest)),
                        "mean_R_rest": float(rest.mean()) if len(rest) else None,
                        "diff": float(fl.mean() - rest.mean()) if len(fl) and len(rest) else None,
                        "boot95_diff_trade_level": boot_diff(fl.to_numpy(), rest.to_numpy())}
    res["flood_vs_rest_trade_R"] = pooled
    out = wk.drop(columns=["anchor"]).reset_index(names="wk_monday")
    out["wk_monday"] = out["wk_monday"].dt.strftime("%Y-%m-%d")
    return res, out


def standing_counts() -> dict:
    nt = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    led = (ROOT / "diagnostics" / "research" / "label_screen_ledger.md").read_text(encoding="utf-8")
    screens = [int(m.group(1)) for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*20\d\d-", led, re.M)]
    sealed = {m.group(1) for m in re.finditer(r"^\|\s*(S\d+)\s*\|", led, re.M)}
    return {"screens": max(screens) if screens else None, "sealed_opens": len(sealed),
            "n_trials": nt["cumulative_n_trials"], "source": "n_trials.json + label_screen_ledger.md (parsed)"}


# ----------------------------------------------------------------------------------------- main
def main() -> int:
    t0 = time.time()
    R94, live, load_demerger_rows, corrected_universe = L._engine()
    from nq.data.membership import load_membership, ticker_in_index_on

    cut = L.cut_universe(corrected_universe())                   # TRAIN ONLY: cut BEFORE the engine, asserted
    last = L.assert_within_cut(cut)
    assert last <= pd.Timestamp(CUT), f"sealed data reached the engine: {last}"
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    events = R94.build_demerger_events(cut, load_demerger_rows(), **live["LIVE_PREP"])
    mem = load_membership()
    cfg = L.normalize_config(L.DEFAULT_CONFIG)
    kw = L.engine_kwargs(cfg)
    manifest = L._manifest(cfg, str(last.date()))
    nifty = L.load_nifty()

    sig = build_signal_table(P)
    print(f"signals {len(sig)} over {sig['wk'].nunique()} weeks; prep {time.time()-t0:.0f}s; {manifest['label']}", flush=True)

    A = {
        "a_live_CRS": R94.grade_a_entries(P),
        "b_D6_filter_before_rank": R94.grade_a_entries(P, mem=mem, filter_before_rank=True),
        "c_depth8w_buyable": topn_set(sig, mem, ticker_in_index_on, lambda r: (r.depth_8w,)),
        "d_deepbucket_then_CRS": topn_set(sig, mem, ticker_in_index_on, lambda r: (0 if r.depth_8w < DEEP else 1, -r.crs)),
        "c0_signalweek_low_ext_buyable": topn_set(sig, mem, ticker_in_index_on, lambda r: (r.depth_sw,)),
    }
    n_trials_dsr = L.n_configs_tried() + len(A)
    base_a, base_b = A["a_live_CRS"], A["b_D6_filter_before_rank"]
    overlap = {k: {"size": len(v), "jaccard_vs_a": len(v & base_a) / len(v | base_a),
                   "jaccard_vs_b": len(v & base_b) / len(v | base_b)} for k, v in A.items()}
    print("set sizes", {k: len(v) for k, v in A.items()}, flush=True)

    res = {"tier": "EXPLORE (tier 0) -- EXPLORATORY; adopts nothing; no pre-reg / screen row / n_trials change",
           "window": [START, CUT], "last_bar_seen": str(last.date()),
           "manifest_engine_kwargs_and_membership": manifest,
           "a_grade_note": "the manifest describes engine kwargs + PIT membership; each arm swaps ONLY the a_grade set",
           "standing_counts": standing_counts(), "dsr_n_trials_used": n_trials_dsr,
           "dsr_n_trials_note": f"lab n_configs_tried()={L.n_configs_tried()} (lab_runs.jsonl is gitignored) + {len(A)} arms run here, each counted as a distinct config; lab ledger NOT written",
           "touch_depth_defs": {
               "depth_8w": "min over the 8 weeks ending at the signal week of (weekly low / that week's own 44w SMA - 1), PIT. Q2 of prereg_signal_quality is on dist_to_sma_pct (close-based in the cron); the engine does not carry weekly closes per entry, and the 'pullback low' wording is what the registry edge was about, so the low-based form is used.",
               "depth_sw": "signal-week low / its 44w SMA - 1 (exact from the entry_win tuple)",
               "d_rank": "bucket (8w depth < 5% first) then CRS distance descending within bucket",
               "buyable": "hi > lo and PIT Nifty-500 member on the entry date (the D6 rule)"},
           "set_overlap": overlap, "arms": {}}
    leds = {}
    for name, aset in A.items():
        nav, led = run_book(R94, P, mem, events, kw, aset, uncapped=False)
        _navu, ledu = run_book(R94, P, mem, events, kw, aset, uncapped=True)
        leds[name] = (nav, led, ledu)
        row = {"a_set_size": len(aset),
               "capped_book": {"full": curve_stats(nav, START, CUT),
                               "sub": {k: curve_stats(nav, *v) for k, v in SUBPERIODS.items()},
                               "deflation": deflate(nav, n_trials_dsr), "trades": trade_stats(led)},
               "uncapped_A_set_per_trade": trade_stats(ledu)}
        res["arms"][name] = row
        f = row["capped_book"]["full"]; u = row["uncapped_A_set_per_trade"]
        print(f"{name:<32} Sh {f['sharpe']:.3f} CAGR {f['cagr_pct']:.1f} DD {f['maxdd_pct']:.1f} n {len(led)} | "
              f"unc meanR {u.get('mean_R_closed', float('nan')):+.3f} n {u.get('n_trades')} | {time.time()-t0:.0f}s", flush=True)

    arms = res["arms"]; cmp = {}
    for cand in ("c_depth8w_buyable", "d_deepbucket_then_CRS", "c0_signalweek_low_ext_buyable"):
        cmp[cand] = {k: {"d_sharpe_vs_b": arms[cand]["capped_book"]["sub"][k]["sharpe"] - arms["b_D6_filter_before_rank"]["capped_book"]["sub"][k]["sharpe"],
                         "d_cagr_pp_vs_b": arms[cand]["capped_book"]["sub"][k]["cagr_pct"] - arms["b_D6_filter_before_rank"]["capped_book"]["sub"][k]["cagr_pct"]}
                     for k in SUBPERIODS}
        cmp[cand]["beats_b_on_sharpe_in_both_subperiods"] = all(cmp[cand][k]["d_sharpe_vs_b"] > 0 for k in SUBPERIODS)
    res["compare_vs_b"] = cmp

    nav_a, led_a, ledu_a = leds["a_live_CRS"]
    b4, wk_tbl = breadth_study(sig, P, mem, ticker_in_index_on, nifty, nav_a, led_a, ledu_a)
    res["item4_breadth"] = b4
    res["seconds"] = round(time.time() - t0, 1)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    wk_tbl.to_csv(OUT_JSON.with_name("2026-10-20_touch_depth_and_breadth_weekly.csv"), index=False)
    print(f"-> {OUT_JSON.relative_to(ROOT).as_posix()} ({res['seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
