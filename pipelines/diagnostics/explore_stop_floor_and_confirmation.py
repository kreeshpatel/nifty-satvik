"""EXPLORE (tier 0): regime cross-tab, a minimum stop distance, a confirmation entry, why live stops are tighter.

Owner request 2026-11-13. Exploration only: no trial, no screen row, nothing live changes, the sealed 2024H2+ slice is
not read. Dataset A = the live configuration on 2019-01-01..2024-06-30 (prices cut at 2024-06-30, asserted), closed
trades and trades open at the cut reported separately. C = the 55 live trades (replay only).

Inputs reused from the loss diagnosis (pipelines/diagnostics/diag_loss_diagnosis_2026_11.py, run first):
  $LOSS_DIAG_CACHE/trades_A.pkl (A per-trade table with regime tags) and live_trades_prices.pkl (Yahoo prices for C).

  1  cross-tab: Nifty vs its 40-week SMA x VIX bucket x midcap-breadth bucket, by year.
  2  minimum stop distance (engine levers min_stop_pct / min_stop_atr20 / min_stop_mode): skip or widen below 6/7/8/9%
     or 1.0/1.5/2.0 x the daily 20-session ATR. Per-trade (uncapped) and capped single path for every setting; the
     20-path paired ensemble for the best setting and its neighbours.
  3  confirmation entry: enter only at the next open after a Friday close above the signal week's high, within 1/2/3
     weeks; a Friday close at or below the stop first, or no confirmation in time, drops the signal. The engine cannot
     re-time entries, so this is simulated per trade with the live-exit replay (explore_live_replay_plus1r.simulate),
     against the same replay of the current rule (sim-base) so both arms share every assumption. No account result.
  4  why live stops are tighter: decomposition of stop distance for A vs C, and the code history of the stop rule.
  5  rules 2 and 3 replayed on the 55 live trades.

    LOSS_DIAG_CACHE=<dir> python pipelines/diagnostics/explore_stop_floor_and_confirmation.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
import diag_giveback_ratchet_0148 as G  # noqa: E402
from explore_live_replay_plus1r import LIVE_SE, load_trades, simulate  # noqa: E402

CACHE = Path(os.environ["LOSS_DIAG_CACHE"])
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-13_stop_floor_and_confirmation.json"
OUT_MD = CACHE / "stopfloor_body.md"
BIG = 2.0
PCTS = (0.06, 0.07, 0.08, 0.09)
ATRS = (1.0, 1.5, 2.0)


def md_table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c)
            cells.append("—" if v is None or (isinstance(v, float) and np.isnan(v)) else (f"{v:,.2f}" if isinstance(v, float) else str(v)))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def per_trade(d: pd.DataFrame) -> dict:
    c = d[d.closed]
    st = c[c.reason == "stop"]
    slip = ((st.exit_px - st.stop0) / (st.entry - st.stop0)) if "exit_px" in st and len(st) else pd.Series(dtype=float)
    return {"n_closed": int(len(c)), "n_open_at_cut": int((~d.closed).sum()),
            "avg_R_closed": round(float(c.R.mean()), 3) if len(c) else None,
            "total_R_closed": round(float(c.R.sum()), 1), "total_R_open_marked": round(float(d[~d.closed].R.sum()), 1),
            "runner_pct": round(float((d.R >= BIG).mean() * 100), 1),
            "full_stop_pct_closed": round(float((c.reason == "stop").mean() * 100), 1) if len(c) else None,
            "mean_slip_beyond_stop_R": round(float(slip.mean()), 2) if len(slip) else None}


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    res: dict = {"tier": "EXPLORE", "window_A": [G.START, G.CUT]}
    md: list[str] = []

    # ------------------------------------------------------------------ 1. cross-tab (from the diagnosis table)
    A = pd.read_pickle(CACHE / "trades_A.pkl")
    A["year"] = pd.to_datetime(A.entry_date).dt.year
    A["cell"] = A.nifty_vs_40w.astype(str) + " | VIX " + A.vix_bucket.astype(str) + " | breadth " + A.breadth_bucket.astype(str)
    rows = []
    for cell, g in A.groupby("cell"):
        c = g[g.closed]
        by_year = c.groupby("year").R.agg(["count", "sum"])
        tot = float(c.R.sum())
        top_year = by_year["sum"].abs().idxmax() if len(by_year) else None
        share = float(by_year.loc[top_year, "sum"] / tot) if top_year is not None and tot else float("nan")
        rows.append({"cell": cell, "n_closed": int(len(c)), "avg_R_closed": round(float(c.R.mean()), 2) if len(c) else None,
                     "total_R_closed": round(tot, 1), "runner_pct": round(float((g.R >= BIG).mean() * 100), 1),
                     "n_open_at_cut": int((~g.closed).sum()), "open_R_marked": round(float(g[~g.closed].R.sum()), 1),
                     "by_year (n:R)": " ".join(f"{int(y)}:{int(r['count'])}:{r['sum']:+.1f}" for y, r in by_year.iterrows()),
                     "top_year": int(top_year) if top_year is not None else None,
                     "top_year_share_of_R": round(share, 2) if share == share else None})
    rows.sort(key=lambda r: -r["n_closed"])
    res["crosstab"] = rows
    md += ["## 1. Regime cross-tab (A): Nifty vs 40-week SMA × VIX × midcap breadth", "",
           "Closed trades and trades open at the 2024-06-30 cut are separate columns. `by_year` lists year:closed trades:R. "
           "`top_year_share_of_R` is the share of the cell's closed-trade R that its single largest year contributes "
           "(above 1 or below 0 means the other years net the opposite way).", "",
           md_table(rows, ["cell", "n_closed", "avg_R_closed", "total_R_closed", "runner_pct", "n_open_at_cut", "open_R_marked",
                           "top_year", "top_year_share_of_R", "by_year (n:R)"]), ""]

    # ------------------------------------------------------------------ engine context for 2
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(G.CUT)] for t, df in corrected_universe().items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    assert max(df.index.max() for df in cut.values()) <= pd.Timestamp(G.CUT), "sealed data reached the engine"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    ev = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem, Aset = load_membership(), R94.grade_a_entries(P)
    kw0 = dict(**LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS, demerger_events=ev)

    def run(unc, extra):
        led: list = []
        out = R94.backtest(P, mem, ledger=led, start=G.START, uncapped=unc, a_grade=Aset, **kw0, **extra)
        d = pd.DataFrame(led)
        d = d[(d.entry - d.stop0) / d.entry >= 0.005].copy()
        d["closed"] = d.reason != "eos"
        d["R"] = d.R.astype(float)
        return out, d

    out_c, _ = run(False, {})
    _, base = run(True, {})
    base_key = base.assign(k=base.tkr + "|" + pd.to_datetime(base.entry_date).dt.strftime("%Y-%m-%d"))
    big = base_key[base_key.R >= BIG]
    imm = A[A.closed & (A.R <= 0) & (A.mfe_high < 0.5)]
    imm_keys = set(imm.tkr + "|" + pd.to_datetime(imm.entry_date).dt.strftime("%Y-%m-%d"))

    # ------------------------------------------------------------------ 2. minimum stop distance
    arms = {"live": {}}
    for mode in ("skip", "widen"):
        for p in PCTS:
            arms[f"{mode}_pct_{int(p * 100)}"] = dict(min_stop_pct=p, min_stop_mode=mode)
        for a in ATRS:
            arms[f"{mode}_atr_{a}"] = dict(min_stop_atr20=a, min_stop_mode=mode)
    rows = []
    for name, extra in arms.items():
        oc, d = (out_c, base) if name == "live" else (run(False, extra)[0], run(True, extra)[1])
        st = G._curve_stats(oc["curve"], G.START, G.CUT)
        keys = set(d.tkr + "|" + pd.to_datetime(d.entry_date).dt.strftime("%Y-%m-%d"))
        rmap = dict(zip(d.tkr + "|" + pd.to_datetime(d.entry_date).dt.strftime("%Y-%m-%d"), d.R))
        lost = [k for k in big.k if k not in keys or rmap.get(k, 0) < BIG]
        rows.append({"arm": name, **per_trade(d), "big_winners_lost": len(lost),
                     "immediate_failures_avoided": len(imm_keys - keys),
                     "capped_sharpe": round(st["sharpe"], 3), "capped_maxdd_pct": round(st["maxdd_pct"], 1),
                     "capped_cagr_pct": round(oc["cagr"] * 100, 1)})
        print("stopfloor", rows[-1], flush=True)
    res["stop_floor"] = rows
    md += ["## 2. Minimum stop distance (A)", "",
           "Per-trade = uncapped book (the live tracker's population). Capped = ₹10L book, one path. `big_winners_lost` = live "
           "A trades at or above +2R that the arm drops or that end below +2R under it. `immediate_failures_avoided` = live "
           "losers that never traded above +0.5R intraweek and that the arm does not take.", "",
           md_table(rows, ["arm", "n_closed", "n_open_at_cut", "avg_R_closed", "total_R_closed", "total_R_open_marked",
                           "runner_pct", "full_stop_pct_closed", "mean_slip_beyond_stop_R", "big_winners_lost",
                           "immediate_failures_avoided", "capped_sharpe", "capped_maxdd_pct", "capped_cagr_pct"]), ""]

    # best by capped single-path Sharpe, then its neighbours in the same family, on 20 paths
    cand = [r for r in rows if r["arm"] != "live"]
    best = max(cand, key=lambda r: r["capped_sharpe"])["arm"]
    mode, kind, val = best.split("_")
    fam = [f"{mode}_pct_{int(p * 100)}" for p in PCTS] if kind == "pct" else [f"{mode}_atr_{a}" for a in ATRS]
    i = fam.index(best)
    pick = ["live"] + fam[max(0, i - 1): i + 2]
    from nq.lab import ensemble as E
    from nq.lab import runs as L
    ctx = E.prepare_context()
    draws = E.draw_perturbations(20, E.DEFAULT_SEED)

    def epath(extra, d_):
        cfg = {**L.normalize_config({}), "start": str(d_["start"])}
        k = L.engine_kwargs(cfg)
        k.update(extra)
        led: list = []
        with E.cost_jitter(float(d_["cost_delta"])):
            o = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ctx.a_grade("default"), **k, demerger_events=ctx.events)
        nav = pd.Series(o["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        return E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)
    paths = {k: [epath(arms[k], d_) for _, d_ in draws.iterrows()] for k in pick}
    q = lambda v: {"median": round(float(np.median(v)), 3), "p5": round(float(np.percentile(v, 5)), 3),
                   "p95": round(float(np.percentile(v, 95)), 3)}
    ens = []
    for k in pick[1:]:
        ds = np.array([a["sharpe"] - b["sharpe"] for a, b in zip(paths[k], paths["live"])])
        dd = np.array([(a["maxdd"] - b["maxdd"]) * 100 for a, b in zip(paths[k], paths["live"])])
        ens.append({"arm": k, "dSharpe": q(ds), "paths_better": int((ds > 0).sum()), "dMaxDD_pp": q(dd),
                    "verdict": "robustly better" if np.percentile(ds, 5) > 0 else ("robustly worse" if np.percentile(ds, 95) < 0 else "inside path noise")})
    res["stop_floor_ensemble"] = {"best_single_path": best, "arms": ens,
                                  "live_band": {m: q([p[m] for p in paths["live"]]) for m in ("sharpe", "maxdd")}}
    md += [f"### 20 paired paths: the best single-path setting (`{best}`) and its neighbours", "",
           md_table([{"arm": e["arm"], "dSharpe median": e["dSharpe"]["median"], "p5": e["dSharpe"]["p5"], "p95": e["dSharpe"]["p95"],
                      "paths better": e["paths_better"], "dMaxDD pp median": e["dMaxDD_pp"]["median"], "verdict": e["verdict"]}
                     for e in ens], ["arm", "dSharpe median", "p5", "p95", "paths better", "dMaxDD pp median", "verdict"]), ""]

    # ------------------------------------------------------------------ 3. confirmation entry (per-trade simulation)
    def sim_set(trades, bars, weeks=None):
        out = []
        for t in trades:
            df = bars.get(t["tkr"])
            if df is None:
                continue
            en_d = pd.Timestamp(t.get("bought") or t["sig"])
            if weeks is None:
                r = simulate(t, df, LIVE_SE)
                out.append({**t, **r, "entry_used": t["en"], "taken": True})
                continue
            prior = df[df.index < en_d]
            if not len(prior):
                continue
            last = prior.index[-1]
            wk = prior[prior.index.to_period("W-FRI") == last.to_period("W-FRI")]
            H = float(wk["High"].max())
            after = df[df.index >= en_d]
            fridays = after.groupby(after.index.to_period("W-FRI")).tail(1)
            taken = False
            for j, (d_, row) in enumerate(fridays.iterrows()):
                if j >= weeks:
                    break
                if row["Close"] <= t["stop0"]:
                    break
                if row["Close"] > H:
                    nxt = df[df.index > d_]
                    if len(nxt) and float(nxt["Open"].iloc[0]) > t["stop0"]:
                        t2 = {**t, "en": float(nxt["Open"].iloc[0]), "bought": str(nxt.index[0].date())}
                        r = simulate(t2, df, LIVE_SE)
                        out.append({**t, **r, "entry_used": t2["en"], "taken": True, "confirm_date": str(d_.date())})
                        taken = True
                    break
            if not taken:
                out.append({**t, "R": np.nan, "reason": "dropped", "taken": False})
        return pd.DataFrame(out)

    trA = [{"tkr": r.tkr, "en": float(r.entry), "stop0": float(r.stop0), "sig": pd.Timestamp(r.entry_date),
            "bought": str(pd.Timestamp(r.entry_date).date()), "status": "", "R_rec": float(r.R),
            "key": f"{r.tkr}|{pd.Timestamp(r.entry_date).date()}"} for r in base.itertuples()]
    simA = {"sim_base": sim_set(trA, cut)}
    for w in (1, 2, 3):
        simA[f"confirm_{w}w"] = sim_set(trA, cut, w)
    rows = []
    sb = simA["sim_base"]
    big_keys = set(big.k)
    for name, d in simA.items():
        tk = d[d.taken]
        closed = tk[tk.reason != "open"]
        fs = closed[closed.reason == "stop"]
        lost = [k for k in big_keys if k not in set(tk.key) or float(tk.set_index("key").R.get(k, 0)) < BIG]
        rows.append({"arm": name, "taken": int(len(tk)), "dropped": int((~d.taken).sum()), "n_closed": int(len(closed)),
                     "avg_R_closed": round(float(closed.R.mean()), 3), "total_R_closed": round(float(closed.R.sum()), 1),
                     "total_R_open_marked": round(float(tk[tk.reason == "open"].R.sum()), 1),
                     "runner_pct": round(float((tk.R >= BIG).mean() * 100), 1),
                     "full_stop_pct_closed": round(float((closed.reason == "stop").mean() * 100), 1),
                     "mean_slip_beyond_stop_R": round(float((fs.R + 1).mean()), 2) if len(fs) else None,
                     "big_winners_lost": len(lost), "immediate_failures_avoided": len(imm_keys - set(tk.key))})
    agree = sb.dropna(subset=["R"])
    res["confirmation"] = rows
    res["sim_base_vs_engine"] = {"sim_total_R": round(float(agree.R.sum()), 1), "engine_total_R": round(float(base.R.sum()), 1),
                                 "corr": round(float(np.corrcoef(agree.R, agree.R_rec)[0, 1]), 3)}
    md += ["## 3. Confirmation entry (A, per-trade simulation)", "",
           f"Simulated with the live-exit replay. `sim_base` is the same replay of the current entry, so the comparison is "
           f"like for like. The replay vs the engine on A: total R {res['sim_base_vs_engine']['sim_total_R']} vs "
           f"{res['sim_base_vs_engine']['engine_total_R']}, per-trade correlation {res['sim_base_vs_engine']['corr']}. The "
           "engine cannot re-time an entry, so there is no capped-book or 20-path result for this rule.", "",
           md_table(rows, ["arm", "taken", "dropped", "n_closed", "avg_R_closed", "total_R_closed", "total_R_open_marked",
                           "runner_pct", "full_stop_pct_closed", "mean_slip_beyond_stop_R", "big_winners_lost",
                           "immediate_failures_avoided"]), ""]

    # ------------------------------------------------------------------ 4. why live stops are tighter
    pxC = {k.replace(".NS", ""): v for k, v in pd.read_pickle(CACHE / "live_trades_prices.pkl").items()}
    trC = load_trades()

    def decomp(rows_, bars):
        out = []
        for t in rows_:
            df = bars.get(t["tkr"])
            if df is None:
                continue
            en_d = pd.Timestamp(t.get("bought") or t["sig"])
            prior = df[df.index < en_d]
            if len(prior) < 25:
                continue
            last = prior.index[-1]
            wk = prior[prior.index.to_period("W-FRI") == last.to_period("W-FRI")]
            H, Lo = float(wk["High"].max()), float(wk["Low"].min())
            h, l, c = prior["High"].iloc[-20:], prior["Low"].iloc[-20:], prior["Close"].shift(1).iloc[-20:]
            atr = float(pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1).mean())
            en, st = t["en"], t["stop0"]
            out.append({"stop_pct": (en - st) / en * 100, "week_range_pct": (H - Lo) / Lo * 100,
                        "entry_pos_in_week_range": (en - Lo) / (H - Lo) if H > Lo else np.nan,
                        "atr20_pct": atr / en * 100, "stop_in_atr20": (en - st) / atr if atr > 0 else np.nan,
                        "stop_capped_at_10pct": bool(abs((en - st) / en - 0.10) < 0.002),
                        "stop_below_week_low": bool(st < Lo - 1e-6), "entry_below_week_low": bool(en < Lo)})
        return pd.DataFrame(out)
    dA, dC = decomp(trA, cut), decomp(trC, pxC)
    rows = []
    for k, d in (("A", dA), ("C", dC)):
        rows.append({"dataset": k, "n": int(len(d)), **{f"median_{m}": round(float(d[m].median()), 2) for m in
                     ("stop_pct", "week_range_pct", "entry_pos_in_week_range", "atr20_pct", "stop_in_atr20")},
                     "share_capped_at_10pct": round(float(d.stop_capped_at_10pct.mean() * 100), 1)})
    res["stop_decomposition"] = rows
    log = subprocess.run(["git", "log", "--since=2024-01-01", "--format=%h %ad %s", "--date=short", "--",
                          "scripts/run_bhanushali_weekly_rank.py"], capture_output=True, text=True, cwd=ROOT).stdout
    stop_commits = [ln for ln in log.splitlines() if any(w in ln.lower() for w in ("stop", "risk", "band", "entry", "fill"))]
    res["engine_commits_touching_stop_or_entry"] = stop_commits
    md += ["## 4. Why live stops are tighter", "",
           "Stop = the signal week's low, raised to entry × 0.90 when that is further than 10% (`max_risk_pct = 0.10`). "
           "So stop distance = entry position above the week's low, as a share of entry. It is driven by how wide the signal "
           "week was (`week_range_pct`) and where in that range the fill landed (`entry_pos_in_week_range`, 0 = at the low, "
           "1 = at the high). `atr20_pct` is the stock's daily volatility before entry.", "",
           md_table(rows, ["dataset", "n", "median_stop_pct", "median_week_range_pct", "median_entry_pos_in_week_range",
                           "median_atr20_pct", "median_stop_in_atr20", "share_capped_at_10pct"]), "",
           f"Engine commits since 2024 whose subject mentions stop, risk, band, entry or fill ({len(stop_commits)}):", ""]
    md += [f"- `{ln}`" for ln in stop_commits[:30]] + [""]

    # ------------------------------------------------------------------ 5. live replay of 2 and 3
    def atr20_at(df, d_):
        prior = df[df.index < pd.Timestamp(d_)]
        h, l, c = prior["High"].iloc[-20:], prior["Low"].iloc[-20:], prior["Close"].shift(1).iloc[-20:]
        return float(pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1).mean())
    live_rows = []
    simC = {"sim_base": sim_set(trC, pxC)}
    best_extra = arms[best]
    floor_arms = {best: best_extra, **{k: arms[k] for k in pick[1:] if k != best}}
    for name, extra in floor_arms.items():
        out = []
        for t in trC:
            df = pxC.get(t["tkr"])
            if df is None:
                continue
            en, st = t["en"], t["stop0"]
            fl = extra.get("min_stop_pct", 0) * en
            if extra.get("min_stop_atr20"):
                fl = max(fl, extra["min_stop_atr20"] * atr20_at(df, t.get("bought") or t["sig"]))
            if en - st >= fl:
                out.append({**t, **simulate(t, df, LIVE_SE), "taken": True})
            elif extra.get("min_stop_mode") == "widen":
                t2 = {**t, "stop0": en - fl}
                out.append({**t, **simulate(t2, df, LIVE_SE), "taken": True, "widened": True})
            else:
                out.append({**t, "R": np.nan, "reason": "skipped", "taken": False})
        simC[name] = pd.DataFrame(out)
    for w in (1, 2, 3):
        simC[f"confirm_{w}w"] = sim_set(trC, pxC, w)
    for name, d in simC.items():
        tk = d[d.taken] if "taken" in d else d
        live_rows.append({"arm": name, "taken": int(len(tk)), "skipped_or_dropped": int(len(d) - len(tk)),
                          "total_R_all_marked": round(float(tk.R.sum()), 1),
                          "total_R_closed": round(float(tk[tk.reason != "open"].R.sum()), 1),
                          "skipped": ", ".join(sorted(d[~d.taken].tkr)) if "taken" in d and (~d.taken).any() else ""})
    res["live_replay"] = live_rows
    md += ["## 5. Rules 2 and 3 replayed on the 55 live trades", "",
           "Same replay as `sim_base` (it reproduces the closed live record within about 1R). Open trades are marked at the "
           "latest close in the price cache. Skipped or dropped trades count as zero.", "",
           md_table(live_rows, ["arm", "taken", "skipped_or_dropped", "total_R_all_marked", "total_R_closed", "skipped"]), ""]

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
