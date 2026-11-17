"""DIAGNOSTIC (tier 1, MEASURE): system inventory and common scorecard, Phase 1-2 of the redesign study.

Owner request 2026-11-13. Analysis only: no live config, engine or trial-counter change; nothing tuned; every
strategy runs exactly as its own pre-registration or spec defines it. The sealed slice B (2024-07-01..2026-06-30) is
NOT read for the live swing book or its all-grades variant: their prices are cut at 2024-06-30 and the cut is asserted.
The momentum (0001), long-horizon (baseline_v1) and low-vol (0081/0107) books were each validated on windows that
already ran to 2026-06-30, so their published period is re-run as published.

Writes diagnostics/research/2026-11_system_inventory.json and the table body of the .md report. TRI benchmark
histories are fetched once from niftyindices.com and committed under diagnostics/research/benchmarks/tri/.

    INVENTORY_CACHE=<dir> python pipelines/diagnostics/diag_system_inventory_2026_11.py

Conventions (the same for every strategy, blend and benchmark):
  capital ₹10L; CAGR by calendar time (ADR-0014); Sharpe and Sortino on daily returns x sqrt(252), rf 0;
  worst drawdown on the daily curve; longest drawdown = longest peak-to-recovery spell, in weeks; Calmar = CAGR / |MaxDD|;
  every window is a CONTINUOUS SLICE of one full run, re-based at the window start, never a fresh-capital re-run.
  Costs are each engine's own coded stack (all three read the same config brokerage / STT / tiered-slippage constants).
  Turnover = cost basis of all lots opened, per year, as a multiple of mean equity. Positions = mean names held per session.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"), str(ROOT / "pipelines" / "diagnostics")]

OUT_JSON = ROOT / "diagnostics" / "research" / "2026-11_system_inventory.json"
TRI_DIR = ROOT / "diagnostics" / "research" / "benchmarks" / "tri"
CACHE = Path(os.environ.get("INVENTORY_CACHE", ROOT / ".cache" / "system_inventory"))
CAPITAL = 1_000_000.0
COMMON = ("2019-03-01", "2024-06-28")          # longest window every runnable strategy supports (see report)
EXTENDED = ("2019-03-01", "2026-06-29")        # books whose own validation already ran to 2026-06-30
SWING_CUT = "2024-06-30"
EXPENSE = 0.004                                # index-fund expense ratio assumed, per year (0.3-0.5% range)
CASH_RATE = 0.06
N_PATHS = 20
BENCH = {"Nifty 50": "NIFTY 50", "Nifty 500": "NIFTY 500", "Nifty Midcap 150": "NIFTY MIDCAP 150",
         "Nifty Midcap150 Momentum 50": "NIFTY MIDCAP150 MOMENTUM 50", "Nifty 200 Momentum 30": "NIFTY200 MOMENTUM 30",
         "Nifty Alpha Low-Volatility 30": "NIFTY ALPHA LOW-VOLATILITY 30"}


# ------------------------------------------------------------------------------------------------ metrics
def to_nav(curve) -> pd.Series:
    if isinstance(curve, pd.Series):
        s = curve.astype(float)
    elif isinstance(curve, dict):
        s = pd.Series(curve, dtype=float)
    else:
        s = pd.Series([float(e["equity"]) for e in curve], index=[e["date"] for e in curve], dtype=float)
    s.index = pd.DatetimeIndex(pd.to_datetime(s.index)).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()


def window(nav: pd.Series, lo: str, hi: str) -> pd.Series:
    s = nav[(nav.index >= pd.Timestamp(lo)) & (nav.index <= pd.Timestamp(hi))]
    return s / s.iloc[0] * CAPITAL if len(s) else s


def metrics(nav: pd.Series) -> dict:
    nav = nav.dropna()
    if len(nav) < 5:
        return {}
    r = nav.pct_change().dropna()
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")
    dd = nav / nav.cummax() - 1
    under = dd < 0
    longest, start = 0, None
    for d, u in under.items():
        if u and start is None:
            start = d
        if not u and start is not None:
            longest = max(longest, (d - start).days)
            start = None
    if start is not None:
        longest = max(longest, (nav.index[-1] - start).days)
    down = r[r < 0]
    mdd = float(dd.min())
    return {"cagr_pct": round(cagr * 100, 2), "sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 3) if r.std() > 0 else None,
            "sortino": round(float(r.mean() / down.std() * np.sqrt(252)), 3) if len(down) > 1 and down.std() > 0 else None,
            "maxdd_pct": round(mdd * 100, 2), "longest_dd_weeks": round(longest / 7, 1),
            "calmar": round(cagr / abs(mdd), 2) if mdd < 0 else None,
            "from": str(nav.index[0].date()), "to": str(nav.index[-1].date())}


def annual(nav: pd.Series) -> dict:
    out = {}
    for y, g in nav.groupby(nav.index.year):
        prev = nav[nav.index < g.index[0]]
        base = prev.iloc[-1] if len(prev) else g.iloc[0]
        out[int(y)] = round(float(g.iloc[-1] / base - 1) * 100, 1)
    return out


def band(vals) -> dict:
    v = np.array([x for x in vals if x is not None and x == x], dtype=float)
    return {"median": round(float(np.median(v)), 3), "p5": round(float(np.percentile(v, 5)), 3),
            "p95": round(float(np.percentile(v, 95)), 3)} if len(v) else {}


def cached(name: str, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}.pkl"
    if f.exists():
        return pd.read_pickle(f)
    out = fn()
    pd.to_pickle(out, f)
    return out


# ------------------------------------------------------------------------------------------------ strategies
def run_swing() -> dict:
    """Live swing (Grade A) and the all-grades base-swing, 20 paired paths + one unperturbed run. Prices cut 2024-06-30."""
    from nq.lab import ensemble as E
    from nq.lab import runs as L
    ctx = E.prepare_context()
    assert pd.Timestamp(ctx.last_bar) <= pd.Timestamp(SWING_CUT), "sealed data reached the swing engine"
    R94 = L._engine()[0]
    draws = E.draw_perturbations(N_PATHS, E.DEFAULT_SEED)
    out = {"last_bar": str(pd.Timestamp(ctx.last_bar).date())}
    for name, over in (("swing_live", {}), ("base_swing", {"grade_gate": False})):
        def one(start, cost_delta, plog=None):
            cfg = {**L.normalize_config(over), "start": str(start)}
            kw = L.engine_kwargs(cfg)
            led: list = []
            with E.cost_jitter(float(cost_delta)):
                o = R94.backtest(ctx.P, ctx.mem, ledger=led, position_log=plog,
                                 a_grade=ctx.a_grade("default") if cfg["grade_gate"] else None, **kw, demerger_events=ctx.events)
            return to_nav(o["curve"]), led
        plog: list = []
        nav0, led0 = one("2019-01-01", 0.0, plog)
        pl = pd.DataFrame(plog)
        first = pl.sort_values("date").groupby(["tkr", "entry"]).head(1)
        yrs = (nav0.index[-1] - nav0.index[0]).days / 365.25
        paths = [one(d["start"], d["cost_delta"])[0] for _, d in draws.iterrows()]
        out[name] = {"nav": nav0, "paths": paths, "n_trades": len(led0),
                     "turnover_x": float(first.notional.sum() / nav0.mean() / yrs),
                     "avg_positions": float(pl.groupby("date").tkr.nunique().reindex(nav0.index).fillna(0).mean())}
        print(name, "done", flush=True)
    return out


def run_momentum(ohlcv, mem, start: str, end: str, uni_start: str | None = None) -> dict:
    import run_0001_xsec_momentum as M
    from nq.universe import build_universe
    u = build_universe(ohlcv, mem, start=uni_start or start, end=end)   # replay: universe warm-up starts earlier than the book
    p = M.add_signals(u)
    keep = p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())
    b = p[keep].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
    from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
    bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**M.BOOK), start=start, end=end, initial_capital=CAPITAL)
    nav = to_nav(bt["equity_curve"])
    tr = pd.DataFrame(bt["trades"])
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25 if len(nav) > 1 else float("nan")
    npos = pd.Series([e.get("n_positions", np.nan) for e in bt["equity_curve"]], dtype=float)
    return {"nav": nav, "metrics_engine": bt["metrics"], "n_trades": int(len(tr)),
            "turnover_x": float((tr["entry"] * tr["qty"]).sum() / nav.mean() / yrs) if len(tr) and yrs == yrs else None,
            "avg_positions": float(npos.mean())}


def run_lh_and_lowvol(ohlcv, mem, start: str, end: str) -> dict:
    from config import load_frozen_cfg
    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.engine.panel import compose_ranked_panel
    from nq.runner.research import run_backtest
    cfg = load_frozen_cfg()
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv, fund_store=load_fund_store(), membership=mem)
    panel["date"] = pd.to_datetime(panel["date"])
    out = {}
    rv = pd.concat([pd.DataFrame({"date": pd.to_datetime(g.index), "ticker": t,
                                  "rvol": g["Close"].pct_change().rolling(63).std().to_numpy()}) for t, g in ohlcv.items()],
                   ignore_index=True)
    lv = panel.merge(rv, on=["date", "ticker"], how="left").copy()
    lv["trend_rank"] = (-lv["rvol"]).groupby(lv["date"]).rank(pct=True)
    for name, pn in (("long_horizon", panel), ("lowvol_sleeve", lv)):
        res = run_backtest(pn, cfg, start=start, end=end)
        nav = to_nav(res["equity_curve"])
        tr = pd.DataFrame(res["trades"])
        yrs = (nav.index[-1] - nav.index[0]).days / 365.25 if len(nav) > 1 else float("nan")
        qty = next((c for c in ("qty", "shares", "quantity") if c in tr.columns), None)
        ent = next((c for c in ("entry", "entry_price") if c in tr.columns), None)
        npos = [e.get("n_positions") for e in res["equity_curve"] if isinstance(e, dict) and "n_positions" in e]
        out[name] = {"nav": nav, "metrics_engine": res.get("metrics", {}), "n_trades": int(len(tr)),
                     "turnover_x": float((tr[ent] * tr[qty]).sum() / nav.mean() / yrs) if qty and ent and len(tr) else None,
                     "avg_positions": float(np.mean(npos)) if npos else res.get("metrics", {}).get("avg_positions_held")}
        print(name, "done", flush=True)
    return out


# ------------------------------------------------------------------------------------------------ data
def yahoo(tickers: list[str], start: str, name: str) -> dict:
    import yfinance as yf

    def fetch():
        out = {}
        for i in range(0, len(tickers), 80):
            chunk = tickers[i:i + 80]
            raw = yf.download(chunk, start=start, auto_adjust=True, progress=False, group_by="ticker", threads=True)
            for t in chunk:
                try:
                    df = raw[t].dropna(subset=["Close"])
                    if len(df):
                        df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
                        out[t.replace(".NS", "")] = df[["Open", "High", "Low", "Close", "Volume"]]
                except Exception:                                             # noqa: BLE001
                    pass
            time.sleep(1)
        return out
    return cached(name, fetch)


def fetch_tri() -> dict:
    """Total-return index histories from niftyindices.com, cached as committed CSVs."""
    import requests
    TRI_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    h = {"User-Agent": "Mozilla/5.0 (research script)", "Accept": "application/json, text/javascript, */*; q=0.01",
         "Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest",
         "Origin": "https://www.niftyindices.com", "Referer": "https://www.niftyindices.com/reports/historical-data"}
    s = None
    for label, api in BENCH.items():
        f = TRI_DIR / (label.lower().replace(" ", "_").replace("-", "_") + "_tri.csv")
        if not f.exists():
            if s is None:
                s = requests.Session()
                s.get("https://www.niftyindices.com/reports/historical-data", headers=h, timeout=30)
            rows = []
            for y in range(2016, 2027):
                cinfo = "{'name':'%s','startDate':'01-Jan-%d','endDate':'31-Dec-%d','indexName':'%s'}" % (api, y, y, api)
                r = s.post("https://www.niftyindices.com/BackPage/getTotalReturnIndexString", headers=h,
                           data=json.dumps({"cinfo": cinfo}), timeout=60)
                try:
                    rows += json.loads(r.text)
                except Exception:                                             # noqa: BLE001
                    pass
                time.sleep(0.5)
            d = pd.DataFrame(rows)
            if not len(d):
                out[label] = None
                continue
            d = pd.DataFrame({"date": pd.to_datetime(d["Date"], format="%d %b %Y"),
                              "tri": pd.to_numeric(d["TotalReturnsIndex"], errors="coerce")}).dropna()
            d = d.drop_duplicates("date").sort_values("date")
            d.to_csv(f, index=False)
        d = pd.read_csv(f, parse_dates=["date"])
        out[label] = d.set_index("date")["tri"].astype(float)
    return out


def net_of_fee(tri: pd.Series, fee: float = EXPENSE) -> pd.Series:
    days = pd.Series(tri.index, index=tri.index).diff().dt.days.fillna(0)
    return tri * np.exp(-fee * days.cumsum() / 365.25)


# ------------------------------------------------------------------------------------------------ main
def main() -> int:
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    res: dict = {"capital": CAPITAL, "common_window": COMMON, "extended_window": EXTENDED, "expense_ratio": EXPENSE,
                 "cash_rate": CASH_RATE, "n_paths": N_PATHS}
    full = corrected_universe()
    mem = load_membership()
    res["data"] = {"tickers": len(full), "first_bar": str(min(d.index.min() for d in full.values()).date()),
                   "last_bar": str(max(d.index.max() for d in full.values()).date())}

    sw = cached("swing", run_swing)
    mom = cached("momentum", lambda: run_momentum(full, mem, "2017-01-01", "2026-06-30"))
    lh = cached("lh_lowvol", lambda: run_lh_and_lowvol(full, mem, "2017-01-01", "2026-06-30"))
    S = {"swing_live": sw["swing_live"], "base_swing": sw["base_swing"], "xsec_momentum_0001": mom,
         "long_horizon": lh["long_horizon"], "lowvol_sleeve": lh["lowvol_sleeve"]}
    res["reproduction_check"] = {
        "xsec_momentum_0001": {"published": {"cagr_pct": 21.73, "sharpe": 1.130, "maxdd_pct": -37.17},
                               "this_run_full_window": metrics(mom["nav"])},
        "long_horizon": {"published_pin": {"cagr_pct": 15.46, "sharpe": 0.667, "maxdd_pct": -46.26},
                         "published_after_calendar_fix": {"cagr_pct": 14.88, "sharpe": 0.647},
                         "this_run_full_window": metrics(lh["long_horizon"]["nav"])},
        "swing_last_bar_seen": sw["last_bar"]}

    # blend-hybrid 0.60 swing / 0.40 low-vol (0107, owner-fixed weight), daily-rebalanced like the logger
    def blend(parts: dict, lo, hi) -> pd.Series:
        navs = {k: window(S[k]["nav"], lo, hi) for k in parts}
        idx = None
        for n in navs.values():
            idx = n.index if idx is None else idx.intersection(n.index)
        r = sum(w * navs[k].reindex(idx).pct_change().fillna(0) for k, w in parts.items())
        return CAPITAL * (1 + r).cumprod()

    # ---------------- Step 2: common scorecard
    score = {}
    for k, v in S.items():
        w = window(v["nav"], *COMMON)
        row = {"window": "common", **metrics(w), "annual_pct": annual(w), "turnover_x_per_year": None if v.get("turnover_x") is None else round(v["turnover_x"], 2),
               "avg_positions": None if v.get("avg_positions") is None else round(float(v["avg_positions"]), 1),
               "n_trades_full_run": v.get("n_trades")}
        if "paths" in v:
            pm = [metrics(window(p, *COMMON)) for p in v["paths"]]
            row["ensemble"] = {m: band([x.get(m) for x in pm]) for m in ("cagr_pct", "sharpe", "sortino", "maxdd_pct", "calmar", "longest_dd_weeks")}
            row["ensemble_supported"] = True
        else:
            row["ensemble_supported"] = False
        if k not in ("swing_live", "base_swing"):
            e = window(v["nav"], *EXTENDED)
            row["extended"] = {**metrics(e), "annual_pct": annual(e)}
        score[k] = row
    bh = blend({"swing_live": 0.60, "lowvol_sleeve": 0.40}, *COMMON)
    score["blend_hybrid_60_40"] = {"window": "common", **metrics(bh), "annual_pct": annual(bh), "ensemble_supported": False,
                                   "note": "0.60 swing / 0.40 low-vol, daily-rebalanced fixed weights (0107 owner weight)"}
    res["scorecard"] = score

    # ---------------- Step 5: benchmarks
    tri = fetch_tri()
    bench = {}
    missing = [k for k, v in tri.items() if v is None]
    for k, s in tri.items():
        if s is None:
            continue
        net = net_of_fee(s)
        row = {"first_date": str(s.index[0].date()), "last_date": str(s.index[-1].date())}
        for tag, (lo, hi) in (("common", COMMON), ("extended", EXTENDED)):
            w = window(net, lo, hi)
            g = window(s, lo, hi)
            row[tag] = {**metrics(w), "annual_pct": annual(w), "gross_cagr_pct": metrics(g).get("cagr_pct")}
        bench[k] = row
    res["benchmarks"] = bench
    res["benchmarks_missing"] = missing

    # ---------------- Step 4: correlation and fixed blends
    nav_c = {k: window(v["nav"], *COMMON) for k, v in S.items()}
    wk = pd.DataFrame({k: n.resample("W-FRI").last().pct_change() for k, n in nav_c.items()}).dropna()
    from nq.lab import runs as L
    nifty = L.load_nifty()
    nw = nifty.resample("W-FRI").last().dropna()
    below = (nw < nw.rolling(40, min_periods=40).mean()).shift(1).reindex(wk.index).fillna(False).astype(bool)
    res["correlation"] = {"weeks": int(len(wk)), "weeks_nifty_below_40w": int(below.sum()),
                          "overall": wk.corr().round(2).to_dict(), "nifty_below_40w": wk[below].corr().round(2).to_dict(),
                          "regime_rule": "a week counts as 'below' when the PRIOR Friday's Nifty close was under its 40-week SMA"}
    blends = {}
    for name, parts in (("70_momentum_30_swing", {"xsec_momentum_0001": 0.70, "swing_live": 0.30}),
                        ("50_momentum_50_swing", {"xsec_momentum_0001": 0.50, "swing_live": 0.50})):
        b = blend(parts, *COMMON)
        blends[name] = {**metrics(b), "annual_pct": annual(b)}
    b = blend({"xsec_momentum_0001": 0.70, "swing_live": 0.30}, *COMMON)
    r = b.pct_change().fillna(0)
    vol = r.rolling(20).std().shift(1) * np.sqrt(252)
    expo = (0.15 / vol).clip(upper=1.0).fillna(1.0)
    rv = expo * r + (1 - expo) * (CASH_RATE / 252)
    bv = CAPITAL * (1 + rv).cumprod()
    blends["70_30_vol_target_15"] = {**metrics(bv), "annual_pct": annual(bv), "mean_exposure": round(float(expo.mean()), 2),
                                     "min_exposure": round(float(expo.min()), 2)}
    res["blends"] = blends
    res["blend_rules"] = ("fixed weights re-set daily, no cost charged for moving money between sleeves; vol target uses the "
                          "20-session realised volatility of the combined book up to the prior session, exposure = "
                          "min(1, 15% / vol), the rest in cash at 6% a year")

    # ---------------- Step 3: forward records
    fwd = {}
    ph = pd.read_csv(ROOT / "results" / "portfolio_history_weekly.csv", parse_dates=["date"]).set_index("date")["total_value"]
    hist = json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8"))
    hist = hist if isinstance(hist, list) else hist["signals"]

    def roll_pct(nav: pd.Series, days: int, realised: float) -> dict:
        w = nav.resample("W-FRI").last().dropna()
        n = max(1, round(days / 7))
        rr = (w / w.shift(n) - 1).dropna() * 100
        return {"horizon_weeks": n, "backtest_median_pct": round(float(rr.median()), 1), "backtest_p5_pct": round(float(rr.quantile(.05)), 1),
                "backtest_p95_pct": round(float(rr.quantile(.95)), 1),
                "realised_percentile": round(float((rr < realised).mean() * 100), 0)}
    real = float(ph.iloc[-1] / CAPITAL - 1) * 100
    fwd["swing_live"] = {"record": "results/portfolio_history_weekly.csv (paper book, rebuilt by the scan each week)",
                         "start": str(ph.index[0].date()), "end": str(ph.index[-1].date()), "return_pct": round(real, 2),
                         "maxdd_pct": round(float((ph / ph.cummax() - 1).min() * 100), 2), "n_trades": len(hist),
                         "n_closed": sum(1 for h in hist if h.get("status") != "ACTIVE"),
                         "vs_backtest": roll_pct(window(S["swing_live"]["nav"], *COMMON), (ph.index[-1] - ph.index[0]).days, real),
                         "note": "the record IS the engine run on live data, so a dated replay equals it by construction; the "
                                 "comparison is against the distribution of same-length windows in the 2019-2024H1 backtest"}
    bs = json.loads((ROOT / "results" / "base_swing_forward.json").read_text(encoding="utf-8"))
    fwd["base_swing"] = {"record": "results/base_swing_forward.json", "start": bs.get("inception"), "end": bs.get("as_of"),
                         "cagr_pct": bs.get("cagr_pct"), "maxdd_pct": bs.get("maxdd_pct"), "n_closed": bs.get("n_closed"),
                         "note": "identical positions and NAV to the Grade-A book so far (forward/prereg_swing.md §12)"}
    wall = pd.read_csv(ROOT / "results" / "forward_wall.csv", parse_dates=["date"])
    wall = wall[wall.status == "ok"]
    lh_start_eq = float(wall.base_equity.iloc[0] / (1 + wall.base_ret.iloc[0]))
    lh_real = float(wall.base_equity.iloc[-1] / lh_start_eq - 1) * 100
    eq = pd.concat([pd.Series([lh_start_eq]), wall.base_equity.reset_index(drop=True)])
    pp = json.loads((ROOT / "results" / "paper_portfolio.json").read_text(encoding="utf-8"))
    fwd["long_horizon"] = {"record": "results/forward_wall.csv (base arm) + results/paper_portfolio.json", "start": str(wall.date.iloc[0].date()),
                           "end": str(wall.date.iloc[-1].date()), "return_pct": round(lh_real, 2),
                           "maxdd_pct": round(float((eq / eq.cummax() - 1).min() * 100), 2), "n_trades_paper_book_total": pp.get("total_trades"),
                           "arms": {a: round(float(wall[f"{a}_equity"].iloc[-1] / (wall[f"{a}_equity"].iloc[0] / (1 + wall[f"{a}_ret"].iloc[0])) - 1) * 100, 2)
                                    for a in ("base", "veto", "drift")},
                           "vs_backtest": roll_pct(window(S["long_horizon"]["nav"], *EXTENDED), (wall.date.iloc[-1] - wall.date.iloc[0]).days, lh_real)}
    bl = json.loads((ROOT / "results" / "blend_hybrid_paper.json").read_text(encoding="utf-8"))
    fwd["blend_hybrid_60_40"] = {"record": "results/blend_hybrid_paper.json", "start": bl.get("inception"), "end": bl.get("asof"),
                                 "return_pct": round((bl["blend_nav"] / CAPITAL - 1) * 100, 2),
                                 "swing_leg_pct": round((bl["swing_nav"] / CAPITAL - 1) * 100, 2),
                                 "lowvol_leg_pct": round((bl["lowvol_nav"] / CAPITAL - 1) * 100, 2), "n_points": bl.get("n_points")}
    b50 = json.loads((ROOT / "results" / "breadth50_forward.json").read_text(encoding="utf-8"))
    fwd["breadth50_watched"] = {"record": "results/breadth50_forward.json", "start": b50.get("inception"), "end": b50.get("asof"),
                                "weeks": b50.get("n_points"),
                                "return_pct": {a: round(float(np.prod([1 + x[1] for x in b50["weekly_returns"][a]]) - 1) * 100, 2)
                                               for a in b50.get("arms", [])},
                                "note": "forward-only by construction; its spec forbids any in-sample performance evaluation"}

    # momentum: no forward record; replay 2026-08-07 -> latest on Yahoo prices (labelled a replay)
    try:
        memv2 = pd.read_csv(ROOT / "data" / "nifty500_membership_v2.csv", parse_dates=["from_date", "to_date"])
        uni = sorted(set(memv2[memv2.to_date >= pd.Timestamp("2026-06-01")].ticker.astype(str)))
        ypx = yahoo([f"{t}.NS" for t in uni], "2024-10-01", "yahoo_n500_from_2024_10")
        ypx = {k: v for k, v in ypx.items() if len(v) > 300}
        last = max(v.index.max() for v in ypx.values())
        rp = run_momentum(ypx, mem, "2026-08-07", str(last.date()), uni_start="2024-10-01")
        n = rp["nav"]
        fwd["xsec_momentum_0001"] = {"forward_record": "NONE. No model-wall log exists for 0001; the forward wall that would carry it was "
                                                       "blocked by the veto arm's factor data (audit 2026-08-11/12).",
                                     "REPLAY_not_a_record": {"start": str(n.index[0].date()), "end": str(n.index[-1].date()),
                                                             "return_pct": round(float(n.iloc[-1] / n.iloc[0] - 1) * 100, 2),
                                                             "maxdd_pct": round(float((n / n.cummax() - 1).min() * 100), 2),
                                                             "n_trades": rp["n_trades"], "avg_positions": round(rp["avg_positions"], 1),
                                                             "data": f"Yahoo auto-adjusted, {len(ypx)} current PIT Nifty-500 members, fresh ₹10L on 2026-08-07"},
                                     "vs_backtest": roll_pct(window(S["xsec_momentum_0001"]["nav"], *EXTENDED), (n.index[-1] - n.index[0]).days,
                                                             float(n.iloc[-1] / n.iloc[0] - 1) * 100)}
        nif = yahoo(["^NSEI"], "2026-08-01", "yahoo_nsei_2026")
        ns = list(nif.values())[0]["Close"]
        fwd["nifty50_price_same_dates_pct"] = {
            "2026-07-06..latest": None,
            "2026-08-07..latest": round(float(ns.iloc[-1] / ns[ns.index >= pd.Timestamp("2026-08-07")].iloc[0] - 1) * 100, 2)}
    except Exception as exc:                                                  # noqa: BLE001
        fwd["xsec_momentum_0001"] = {"forward_record": "NONE", "replay_error": f"{type(exc).__name__}: {exc}"}
    res["forward"] = fwd

    # ---------------- Step 6
    res["execution"] = {"execution_events_rows": 0, "queried": "2026-11-13, read-only, production database",
                        "meaning": "no real fill has ever been recorded in the app"}

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items() if k not in ("nav", "paths")}
        if isinstance(o, (list, tuple)):
            return [clean(x) for x in o]
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        return o
    OUT_JSON.write_text(json.dumps(clean(res), indent=2, default=str) + "\n", encoding="utf-8")
    sys.stdout.buffer.write((json.dumps(clean({k: res[k] for k in ("reproduction_check", "benchmarks_missing")}), indent=1, default=str) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
