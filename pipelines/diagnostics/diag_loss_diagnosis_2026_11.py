"""DIAGNOSTIC (tier 1, MEASURE): why the live strategy loses, and under what conditions it works.

Owner request 2026-11-13. Analysis only: no live change, no tuning, no trial, no screen row. Writes
diagnostics/research/2026-11_loss_diagnosis.md (+ .json).

Datasets, kept separate in every table:
  A  = training window: live configuration, entries 2019-01-01..2024-06-30, prices cut at 2024-06-30 (asserted).
       Per-trade = the uncapped book (every Grade-A signal, the same population as the live tracker);
       account = the ₹10L capped book.
  B  = the sealed 2024H2-2026H1 slice. OWNER DECISION 2026-11-13: NOT opened by this study (it would be a new sealed
       open, S5). Only a price-only data-integrity check is run on B (step 5); no trade outcome in B is read.
  C  = the 55 live trades since 2026-07-06 (results/signals_history_weekly.json): closed trades at exit, open trades at
       the latest close, labelled. Initial stops from results/cards_archive.jsonl. Prices from Yahoo (auto-adjusted),
       cached in the scratch directory. Account = the live paper book (results/portfolio_history_weekly.csv).

Fixed definitions (no threshold here was fitted):
  regime, at the signal Friday: Nifty weekly close vs its 40-week SMA; 40-week SMA vs its value 4 weeks earlier;
    Nifty 13-week return buckets (<-5, -5..0, 0..+5, >+5 %); midcap breadth (PIT Nifty-500 members ranked 101-250 by
    63-session median traded value - an approximation, there is no midcap index list - share closing above their own
    200-day SMA: <40, 40-60, >60 %); India VIX (<15, 15-20, >20).
  runner = a trade at or above +2R. winner = R > 0.
  entry features at the signal Friday: distance from the 52-week high, pullback depth (13-week high to signal-week low),
    extension of the entry over the 40-week SMA, signal-week volume vs the prior 20-session average, stop distance %,
    252-session beta to the Nifty, 26-week return minus the Nifty's, a results meeting announced by then and due within
    28 days (PIT), 63-session median traded value (₹ crore), sector (config.get_sector). Grade is A for every trade in
    both A and C by construction (the live tracker records Grade-A signals only).

    python pipelines/diagnostics/diag_loss_diagnosis_2026_11.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
import diag_giveback_ratchet_0148 as G  # noqa: E402
import diag_problem1_throttle_bound as T  # noqa: E402
from explore_plus1r_arms import path_stats  # noqa: E402

OUT_MD = ROOT / "diagnostics" / "research" / "2026-11_loss_diagnosis.md"
OUT_JSON = ROOT / "diagnostics" / "research" / "2026-11_loss_diagnosis.json"
CACHE = Path(os.environ.get("LOSS_DIAG_CACHE", ROOT / ".cache" / "loss_diag"))
TRADING_DAYS = 252


# ----------------------------------------------------------------------------------------------- helpers
def signal_friday(d) -> pd.Timestamp:
    d = pd.Timestamp(d).normalize()
    back = (d.weekday() - 4) % 7 or 7
    return d - pd.Timedelta(days=back)


def nav_stats(nav: pd.Series) -> dict:
    nav = nav.dropna().astype(float)
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    r = nav.pct_change().dropna()
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(TRADING_DAYS)) if r.std() > 0 else float("nan"),
            "cagr_pct": float(((nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1) * 100) if yrs > 0 else float("nan"),
            "maxdd_pct": float((nav / nav.cummax() - 1).min() * 100), "from": str(nav.index[0].date()),
            "to": str(nav.index[-1].date())}


def trade_metrics(d: pd.DataFrame) -> dict:
    c = d[d.closed]
    if not len(d):
        return {"n": 0}
    w, l = c[c.R > 0], c[c.R <= 0]
    return {"n": int(len(d)), "n_closed": int(len(c)), "n_open": int((~d.closed).sum()),
            "win_pct": round(float((c.R > 0).mean() * 100), 1) if len(c) else None,
            "avg_win_R": round(float(w.R.mean()), 2) if len(w) else None,
            "avg_loss_R": round(float(l.R.mean()), 2) if len(l) else None,
            "avg_R_closed": round(float(c.R.mean()), 3) if len(c) else None,
            "total_R": round(float(d.R.sum()), 1),
            "runner_pct": round(float((d.R >= 2).mean() * 100), 1),
            "hold_wk_winners": round(float(w.weeks.mean()), 1) if len(w) else None,
            "hold_wk_losers": round(float(l.weeks.mean()), 1) if len(l) else None,
            "full_stop_pct_closed": round(float((c.reason == "stop").mean() * 100), 1) if len(c) else None}


def md_table(rows: list[dict], cols: list[str], heads: list[str] | None = None) -> str:
    heads = heads or cols
    out = ["| " + " | ".join(heads) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("—" if r.get(c) is None or (isinstance(r.get(c), float) and np.isnan(r.get(c)))
                                     else (f"{r[c]:,.2f}" if isinstance(r.get(c), float) else str(r[c])) for c in cols) + " |")
    return "\n".join(out)


def features(t: str, entry_date, entry: float, stop: float, px: pd.DataFrame, nifty: pd.Series, events_by: dict,
             earn_until: pd.Timestamp) -> dict:
    f = signal_friday(entry_date)
    h = px[px.index <= f]
    out = {"signal_friday": f}
    if len(h) < 30:
        return out
    wk = h["Close"].resample("W-FRI").last().dropna()
    sma40 = wk.rolling(40, min_periods=40).mean()
    hi252 = h["High"].iloc[-252:].max()
    out["dist_52w_high_pct"] = (h["Close"].iloc[-1] / hi252 - 1) * 100
    wk_hi = h["High"].resample("W-FRI").max().dropna()
    wk_lo = h["Low"].resample("W-FRI").min().dropna()
    if len(wk_hi) > 13:
        hi13 = wk_hi.iloc[-14:-1].max()
        out["pullback_depth_pct"] = (1 - wk_lo.iloc[-1] / hi13) * 100
    if pd.notna(sma40.iloc[-1]):
        out["ext_40w_pct"] = (entry / sma40.iloc[-1] - 1) * 100
    last_week = h[h.index > f - pd.Timedelta(days=7)]
    prior = h[h.index <= f - pd.Timedelta(days=7)].iloc[-20:]
    if len(last_week) and len(prior) and prior["Volume"].mean() > 0:
        out["vol_vs_20d"] = float(last_week["Volume"].mean() / prior["Volume"].mean())
    out["stop_pct"] = (entry - stop) / entry * 100
    rs = h["Close"].pct_change()
    nr = nifty.reindex(h.index).pct_change()
    j = pd.concat([rs, nr], axis=1).dropna().iloc[-252:]
    if len(j) > 120 and j.iloc[:, 1].var() > 0:
        out["beta"] = float(j.cov().iloc[0, 1] / j.iloc[:, 1].var())
    n_f = nifty[nifty.index <= f]
    if len(wk) > 26 and len(n_f) > 130:
        nwk = n_f.resample("W-FRI").last().dropna()
        out["rs6m_pct"] = ((wk.iloc[-1] / wk.iloc[-27] - 1) - (nwk.iloc[-1] / nwk.iloc[-27] - 1)) * 100
    if f <= earn_until:
        g = events_by.get(t)
        out["results_4w"] = bool(g is not None and ((g.ann_ts <= f + pd.Timedelta(hours=23, minutes=59))
                                                   & (g.event_date > f) & (g.event_date <= f + pd.Timedelta(days=28))).any())
    tv = (h["Close"] * h["Volume"]).iloc[-63:].median()
    out["traded_value_cr"] = float(tv / 1e7)
    return out


def regime_tables(nifty: pd.Series, vix: pd.Series, breadth: pd.Series) -> pd.DataFrame:
    nwk = nifty.resample("W-FRI").last().dropna()
    sma = nwk.rolling(40, min_periods=40).mean()
    r = pd.DataFrame({"nifty": nwk, "sma40": sma})
    r["above_40w"] = r.nifty >= r.sma40
    r["sma40_rising"] = r.sma40 > r.sma40.shift(4)
    r["ret13_pct"] = (r.nifty / r.nifty.shift(13) - 1) * 100
    r["vix"] = vix.resample("W-FRI").last().reindex(r.index) if len(vix) else np.nan
    r["breadth_pct"] = breadth.reindex(r.index) * 100 if len(breadth) else np.nan
    return r


def tag(d: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    rr = reg.reindex(d.signal_friday.values)
    d = d.copy()
    d["nifty_vs_40w"] = np.where(rr.above_40w.values == True, "above", np.where(rr.above_40w.values == False, "below", None))  # noqa: E712
    d["sma40_slope"] = np.where(rr.sma40_rising.values == True, "rising", np.where(rr.sma40_rising.values == False, "falling", None))  # noqa: E712
    d["ret13_bucket"] = pd.cut(rr.ret13_pct.values, [-np.inf, -5, 0, 5, np.inf], labels=["<-5%", "-5..0%", "0..+5%", ">+5%"]).astype(str)
    d["breadth_bucket"] = pd.cut(rr.breadth_pct.values, [-np.inf, 40, 60, np.inf], labels=["<40%", "40-60%", ">60%"]).astype(str)
    d["vix_bucket"] = pd.cut(rr.vix.values, [-np.inf, 15, 20, np.inf], labels=["<15", "15-20", ">20"]).astype(str)
    return d


def midcap_breadth(px: dict, mem, fridays: pd.DatetimeIndex) -> pd.Series:
    from run_bhanushali_weekly_rank import ticker_in_index_on
    C = pd.DataFrame({t: df["Close"] for t, df in px.items()}).sort_index()
    V = pd.DataFrame({t: df["Close"] * df["Volume"] for t, df in px.items()}).sort_index()
    tv = V.rolling(63, min_periods=40).median()
    s200 = C.rolling(200, min_periods=200).mean()
    out = {}
    for f in fridays:
        i = C.index.searchsorted(f, side="right") - 1
        if i < 0:
            continue
        d = C.index[i]
        mem_ok = [t for t in C.columns if mem is None or ticker_in_index_on(t, f.date(), mem)]
        row = tv.loc[d, mem_ok].dropna().sort_values(ascending=False)
        mid = [t for t in row.index[100:250] if pd.notna(s200.at[d, t])]
        if len(mid) >= 30:
            out[f] = float((C.loc[d, mid] > s200.loc[d, mid]).mean())
    return pd.Series(out)


# ----------------------------------------------------------------------------------------------- dataset A
def build_A():
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    from nq.lab import runs as L
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(G.CUT)] for t, df in corrected_universe().items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    assert max(df.index.max() for df in cut.values()) <= pd.Timestamp(G.CUT), "sealed data reached the engine"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    ev = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem, A = load_membership(), R94.grade_a_entries(P)
    nifty = L.load_nifty()
    nifty = nifty[nifty.index <= pd.Timestamp(G.CUT)]
    kw = dict(**LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS, demerger_events=ev)

    def run(unc, scale=None):
        led: list = []
        k = dict(kw)
        if scale is not None:
            k["entry_size_scale_by_week"] = scale
        out = R94.backtest(P, mem, ledger=led, start=G.START, uncapped=unc, a_grade=A, **k)
        d = pd.DataFrame(led)
        d = d[(d.entry - d.stop0) / d.entry >= 0.005]
        return out, d
    return cut, P, mem, nifty, run


# ----------------------------------------------------------------------------------------------- dataset C
def yahoo(tickers: list[str], start: str, name: str) -> dict:
    import yfinance as yf
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}.pkl"
    if f.exists():
        return pd.read_pickle(f)
    out = {}
    for i in range(0, len(tickers), 80):
        chunk = tickers[i:i + 80]
        raw = yf.download(chunk, start=start, auto_adjust=True, progress=False, group_by="ticker", threads=True)
        for t in chunk:
            try:
                df = raw[t].dropna(subset=["Close"]) if len(chunk) > 1 else raw.dropna(subset=["Close"])
                if len(df):
                    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
                    out[t] = df[["Open", "High", "Low", "Close", "Volume"]]
            except Exception:
                pass
    pd.to_pickle(out, f)
    return out


def build_C():
    h = json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8"))
    H = h if isinstance(h, list) else h["signals"]
    C = [json.loads(x) for x in (ROOT / "results" / "cards_archive.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = []
    for r in H:
        m = sorted([c for c in C if c["ticker"] == r["ticker"] and c.get("stop")
                    and abs((pd.Timestamp(c["signal_date"]) - pd.Timestamp(r["signal_date"])).days) <= 3],
                   key=lambda c: c.get("as_of", ""))
        card = m[0]
        entry_date = pd.Timestamp(card.get("bought_date") or r["signal_date"])
        rows.append(dict(tkr=r["ticker"], signal_date=r["signal_date"], entry_date=entry_date, entry=float(r["entry"]),
                         stop0=float(card["stop"]), status=r["status"], reason=r.get("exit_reason") or "open",
                         R_rec=r.get("r_multiple"), close_price=r.get("close_price"), close_date=r.get("close_date"),
                         hold_days=r.get("hold_days")))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- main
def main() -> int:
    from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table
    import config
    events = build_event_table(pd.read_parquet(EARNINGS_RAW_PATH))
    events_by = {s: g for s, g in events.groupby("symbol")}
    earn_until = events.ann_ts.max().normalize()
    res: dict = {"note": "A = train 2019..2024-06; B not opened (owner, 2026-11-13); C = live since 2026-07-06",
                 "earnings_known_until": str(earn_until.date())}
    md: list[str] = []

    # ---------------- A
    cut, P, mem, niftyA, runA = build_A()
    outA_c, _ = runA(False)
    outA_u, ledA = runA(True)
    ledA = ledA.reset_index(drop=True)
    dA = pd.DataFrame({"tkr": ledA.tkr, "entry_date": pd.to_datetime(ledA.entry_date), "entry": ledA.entry,
                       "stop0": ledA.stop0, "exit_date": pd.to_datetime(ledA.exit_date), "reason": ledA.reason,
                       "R": ledA.R.astype(float), "weeks": ledA.held_weeks.astype(float), "exit_px": ledA.exit_px})
    dA["closed"] = dA.reason != "eos"
    macro = pd.read_parquet(ROOT / "data" / "macro_pit.parquet")
    vixA = macro.set_index(pd.to_datetime(macro["date"]))["vix_level"].dropna()
    vixA = vixA[vixA.index <= pd.Timestamp(G.CUT)]
    fridaysA = pd.date_range("2018-06-01", G.CUT, freq="W-FRI")
    breadthA = midcap_breadth(cut, mem, fridaysA)
    regA = regime_tables(niftyA, vixA, breadthA)
    featsA = [features(r.tkr, r.entry_date, r.entry, r.stop0, cut[r.tkr], niftyA, events_by, earn_until) for r in dA.itertuples()]
    dA = pd.concat([dA, pd.DataFrame(featsA)], axis=1)
    dA = tag(dA, regA)
    psA = path_stats(dA.assign(exit_date=dA.exit_date.where(dA.closed, pd.Timestamp(G.CUT))), cut)
    dA = dA.merge(psA[["tkr", "entry_date", "mfe_close", "mfe_high"]].assign(entry_date=lambda x: pd.to_datetime(x.entry_date)),
                  on=["tkr", "entry_date"], how="left")
    dA["sector"] = dA.tkr.map(config.get_sector)
    accA = nav_stats(pd.Series(outA_c["curve"], index=pd.DatetimeIndex(pd.Series(outA_c["curve"]).index)))

    # ---------------- C
    c0 = build_C()
    tick = sorted(c0.tkr.unique())
    pxC = yahoo([f"{t}.NS" for t in tick] + ["^NSEI", "^INDIAVIX"], "2024-06-01", "live_trades_prices")
    pxC = {k.replace(".NS", ""): v for k, v in pxC.items()}
    niftyC = pxC["^NSEI"]["Close"]
    vixC = pxC["^INDIAVIX"]["Close"] if "^INDIAVIX" in pxC else pd.Series(dtype=float)
    last_close = {t: float(pxC[t]["Close"].iloc[-1]) for t in tick if t in pxC}
    c0["closed"] = c0.status != "ACTIVE"
    c0["R"] = [float(r.R_rec) if r.closed and r.R_rec is not None else
               (last_close.get(r.tkr, np.nan) - r.entry) / (r.entry - r.stop0) for r in c0.itertuples()]
    c0["weeks"] = c0.hold_days.astype(float) / 5.0
    c0["exit_date"] = pd.to_datetime(c0.close_date.where(c0.closed, None))
    try:
        from nq.data.membership import load_membership as _lm
        memv2 = pd.read_csv(ROOT / "data" / "nifty500_membership_v2.csv", parse_dates=["from_date", "to_date"])
        uni = sorted(set(memv2[memv2.to_date >= pd.Timestamp("2026-06-01")].ticker.astype(str)))
        pxU = yahoo([f"{t}.NS" for t in uni], "2025-06-01", "n500_universe_prices")
        pxU = {k.replace(".NS", ""): v for k, v in pxU.items() if len(v) > 220}
        breadthC = midcap_breadth(pxU, _lm(), pd.date_range("2026-06-05", pd.Timestamp.today(), freq="W-FRI"))
        res["breadth_C_note"] = (f"live breadth: PIT Nifty-500 members (nifty500_membership_v2) with Yahoo prices, "
                                 f"{len(pxU)} names with enough history")
    except Exception as exc:                                                  # noqa: BLE001
        breadthC = pd.Series(dtype=float)
        res["breadth_C_note"] = f"live breadth unavailable: {type(exc).__name__}: {exc}"
    regC = regime_tables(niftyC, vixC, breadthC)
    featsC = [features(r.tkr, r.entry_date, r.entry, r.stop0, pxC[r.tkr], niftyC, events_by, earn_until) if r.tkr in pxC else {}
              for r in c0.itertuples()]
    dC = pd.concat([c0.reset_index(drop=True), pd.DataFrame(featsC)], axis=1)
    dC = tag(dC, regC)
    far = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    psC = path_stats(dC.assign(exit_date=dC.exit_date.fillna(far), R=dC.R), pxC)
    dC = dC.merge(psC[["tkr", "entry_date", "mfe_close", "mfe_high"]].assign(entry_date=lambda x: pd.to_datetime(x.entry_date)),
                  on=["tkr", "entry_date"], how="left")
    dC["sector"] = dC.tkr.map(config.get_sector)
    ph = pd.read_csv(ROOT / "results" / "portfolio_history_weekly.csv", parse_dates=["date"]).set_index("date")["total_value"]
    accC = nav_stats(ph)

    D = {"A": dA, "C": dC}
    # ---------------- 1. headline
    head = []
    for k, d in D.items():
        acc = accA if k == "A" else accC
        head.append({"dataset": k, **trade_metrics(d), "acct_sharpe": round(acc["sharpe"], 2),
                     "acct_cagr_pct": round(acc["cagr_pct"], 1), "acct_maxdd_pct": round(acc["maxdd_pct"], 1),
                     "acct_window": f'{acc["from"]}..{acc["to"]}'})
    res["headline"] = head
    hc = ["dataset", "n", "n_closed", "n_open", "win_pct", "avg_win_R", "avg_loss_R", "avg_R_closed", "total_R", "runner_pct",
          "hold_wk_winners", "hold_wk_losers", "full_stop_pct_closed", "acct_sharpe", "acct_cagr_pct", "acct_maxdd_pct", "acct_window"]
    md += ["## 1. Headline", "", md_table(head, hc), ""]

    # ---------------- 2. regime
    md += ["## 2. Market regime at entry (per-trade metrics; account metrics are whole-book only)", ""]
    res["regime"] = {}
    for dim in ("nifty_vs_40w", "sma40_slope", "ret13_bucket", "breadth_bucket", "vix_bucket"):
        rows = []
        for k, d in D.items():
            for b, g in d.groupby(dim, dropna=False):
                rows.append({"dataset": k, "bucket": str(b), **trade_metrics(g)})
        res["regime"][dim] = rows
        md += [f"### {dim}", "", md_table(rows, ["dataset", "bucket", "n", "n_closed", "win_pct", "avg_win_R", "avg_loss_R",
                                                 "avg_R_closed", "total_R", "runner_pct", "full_stop_pct_closed"]), ""]

    # ---------------- 3. anatomy
    md += ["## 3. Trade anatomy", ""]
    res["anatomy"] = {}
    bins = [-np.inf, 0, 0.5, 1, 1.5, 2, np.inf]
    labels = ["<0", "0-0.5", "0.5-1", "1-1.5", "1.5-2", ">=2"]
    rows = []
    for k, d in D.items():
        st = d[d.closed & (d.reason == "stop")]
        for basis in ("mfe_close", "mfe_high"):
            cnt = pd.cut(st[basis], bins, labels=labels).value_counts().reindex(labels).fillna(0).astype(int)
            rows.append({"dataset": k, "basis": basis, "n_full_stops": int(len(st)), **{f"peak {l}R": int(cnt[l]) for l in labels}})
    res["anatomy"]["peak_R_of_full_stops"] = rows
    md += ["### Peak R reached by trades that ended at the full stop", "",
           md_table(rows, ["dataset", "basis", "n_full_stops"] + [f"peak {l}R" for l in labels]), ""]
    rows = []
    for k, d in D.items():
        lo = d[d.closed & (d.R <= 0)]
        rows.append({"dataset": k, "losers": int(len(lo)),
                     "never_above_0.5R_intraweek_pct": round(float((lo.mfe_high < 0.5).mean() * 100), 1) if len(lo) else None,
                     "never_above_0.5R_friday_pct": round(float((lo.mfe_close < 0.5).mean() * 100), 1) if len(lo) else None})
    res["anatomy"]["failed_immediately"] = rows
    md += ["### Losers that never got above +0.5R (failed immediately)", "",
           md_table(rows, ["dataset", "losers", "never_above_0.5R_intraweek_pct", "never_above_0.5R_friday_pct"]), ""]
    feats = ["dist_52w_high_pct", "pullback_depth_pct", "ext_40w_pct", "vol_vs_20d", "stop_pct", "beta", "rs6m_pct",
             "traded_value_cr"]
    from scipy.stats import mannwhitneyu
    rows = []
    for ft in feats:
        r = {"feature": ft}
        dirs = {}
        for k, d in D.items():
            c = d[d.closed]
            w, l = c[c.R > 0][ft].dropna(), c[c.R <= 0][ft].dropna()
            r[f"{k}_win_median"] = round(float(w.median()), 2) if len(w) else None
            r[f"{k}_loss_median"] = round(float(l.median()), 2) if len(l) else None
            p = mannwhitneyu(w, l).pvalue if len(w) > 4 and len(l) > 4 else np.nan
            r[f"{k}_p"] = round(float(p), 3) if p == p else None
            dirs[k] = np.sign(w.median() - l.median()) if len(w) and len(l) else 0
        r["clear_in_A_same_sign_in_C"] = bool(r["A_p"] is not None and r["A_p"] < 0.05 and dirs["A"] == dirs["C"] and dirs["A"] != 0)
        rows.append(r)
    for k, d in D.items():
        c = d[d.closed & d.results_4w.notna()] if "results_4w" in d else d.iloc[:0]
        if len(c):
            rows.append({"feature": f"results_4w (share, {k})", f"{k}_win_median": round(float(c[c.R > 0].results_4w.mean() * 100), 1),
                         f"{k}_loss_median": round(float(c[c.R <= 0].results_4w.mean() * 100), 1)})
    res["anatomy"]["winners_vs_losers"] = rows
    md += ["### Winners vs losers at entry (closed trades; medians; Mann-Whitney p)", "",
           "B is not opened, so a 'clear in both' flag is read as: p < 0.05 in A and the same direction in C (C has few "
           "closed winners, so C alone cannot confirm anything). results_4w rows give the share (%) with results due.", "",
           md_table(rows, ["feature", "A_win_median", "A_loss_median", "A_p", "C_win_median", "C_loss_median", "C_p",
                           "clear_in_A_same_sign_in_C"]), ""]
    rows = []
    for k, d in D.items():
        g = d.groupby("sector")
        for s, x in g:
            rows.append({"dataset": k, "sector": s, **{m: trade_metrics(x)[m] for m in ("n", "n_closed", "win_pct", "avg_R_closed", "total_R")}})
    rows.sort(key=lambda r: (r["dataset"], -r["n"]))
    res["sector"] = rows

    # ---------------- 4. A vs C
    rows = []
    for k, d in D.items():
        wk = d.groupby(d.signal_friday).size()
        r = {"dataset": k, "trades_per_signal_week": round(float(wk.mean()), 2)}
        for ft in feats:
            r[ft] = round(float(d[ft].mean()), 2) if ft in d else None
        rows.append(r)
    res["A_vs_C_features"] = rows
    md += ["## 4. What changed: A (train) vs C (live). B was not opened, so the requested A-vs-B comparison is A-vs-C", "",
           md_table(rows, ["dataset", "trades_per_signal_week"] + feats), "",
           "Stop-out rate, runner share and runner size are in the section 1 table (full_stop_pct_closed, runner_pct, "
           "avg_win_R). Sector mix is in section 6.", ""]

    # ---------------- 5. execution and data
    md += ["## 5. Execution and data", ""]
    rows = []
    for k, d in D.items():
        st = d[d.closed & (d.reason == "stop")].copy()
        if k == "A":
            st["slip_R"] = (st.exit_px - st.stop0) / (st.entry - st.stop0)
        else:
            st["slip_R"] = (st.close_price.astype(float) - st.stop0) / (st.entry - st.stop0)
        rows.append({"dataset": k, "full_stops": int(len(st)), "mean_exit_vs_stop_R": round(float(st.slip_R.mean()), 2),
                     "median_exit_vs_stop_R": round(float(st.slip_R.median()), 2),
                     "worst_exit_vs_stop_R": round(float(st.slip_R.min()), 2),
                     "share_worse_than_-0.5R_beyond_stop": round(float((st.slip_R < -0.5).mean() * 100), 1)})
    res["stop_slippage"] = rows
    md += ["### Stop vs actual exit (the weekly-close stop fills at the next open), in R beyond the stop level", "",
           md_table(rows, ["dataset", "full_stops", "mean_exit_vs_stop_R", "median_exit_vs_stop_R", "worst_exit_vs_stop_R",
                           "share_worse_than_-0.5R_beyond_stop"]), "",
           "**Model entry vs your actual fill:** not measurable. The app's `execution_events` table has 0 rows (queried "
           "read-only 2026-11-13), so no real fill has been recorded. C's entries are the model's modelled fills.", ""]
    # B: price-only integrity check (no outcomes)
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    from run_bhanushali_weekly_rank import ticker_in_index_on
    full = corrected_universe()
    memB = load_membership()
    lo, hi = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")
    members = set()
    for f in pd.date_range(lo, hi, freq="QS"):
        members |= {t for t in full if ticker_in_index_on(t, f.date(), memB)}
    nob = sorted(t for t in members if not len(full[t][(full[t].index >= lo) & (full[t].index <= hi)]))
    ends = sorted(t for t in members if len(full[t]) and lo <= full[t].index.max() < pd.Timestamp("2026-06-01"))
    gaps = []
    for t in members:
        s = full[t][(full[t].index >= lo) & (full[t].index <= hi)]["Close"]
        if len(s) > 5:
            mv = s.pct_change().abs()
            for d_, v in mv[mv > 0.40].items():
                gaps.append(f"{t} {d_.date()} {v:.0%}")
    dem_path = ROOT / "data" / "corporate_actions_demergers.csv"
    dem_t = set()
    if dem_path.exists():
        for ln in dem_path.read_text(encoding="utf-8").splitlines():
            ln = ln.split("#", 1)[0].strip()
            if ln and not ln.lower().startswith("ticker"):
                dem_t.add(ln.split(",")[0].strip())
    res["B_price_integrity"] = {"members_seen": len(members), "members_with_no_bars": nob, "series_ending_before_2026-06": ends,
                                "one_day_moves_over_40pct": gaps,
                                "of_which_registered_demerger_tickers": sorted({g.split()[0] for g in gaps} & dem_t)}
    md += ["### B data integrity (prices only; no trade outcome read, so not a sealed open)", "",
           f"- PIT Nifty-500 members over 2024-07..2026-06 (quarterly sample): {len(members)}",
           f"- members with no bars at all in the slice: {len(nob)} {nob[:20]}",
           f"- series that stop before 2026-06 (possible delisting / suspension): {len(ends)} {ends[:20]}",
           f"- one-day moves above 40%: {len(gaps)} {gaps[:12]}",
           f"- of those tickers, registered demergers: {res['B_price_integrity']['of_which_registered_demerger_tickers']}", ""]

    # ---------------- 6. sector + concentration
    md += ["## 6. Sector and concentration", "", md_table(res["sector"], ["dataset", "sector", "n", "n_closed", "win_pct",
                                                                         "avg_R_closed", "total_R"]), ""]
    op = dC[~dC.closed]
    sc = op.sector.value_counts()
    rets = pd.DataFrame({t: pxC[t]["Close"].pct_change() for t in op.tkr if t in pxC}).iloc[-60:]
    cm = rets.corr()
    pairs = [(a, b, round(float(cm.at[a, b]), 2)) for i, a in enumerate(cm.columns) for b in cm.columns[i + 1:] if cm.at[a, b] > 0.6]
    off = cm.values[np.triu_indices_from(cm.values, k=1)]
    res["C_concentration"] = {"open_by_sector": sc.to_dict(), "mean_pairwise_corr_60d": round(float(np.nanmean(off)), 2),
                              "pairs_above_0.6": pairs}
    md += [f"**Live open trades ({len(op)}) by sector:** " + ", ".join(f"{k} {v}" for k, v in sc.items()),
           f"\n**60-session daily-return correlation among open trades:** mean {np.nanmean(off):.2f}; pairs above 0.6: "
           + (", ".join(f"{a}-{b} {c}" for a, b, c in pairs) or "none"), ""]

    # ---------------- 7. simple regime responses (A, plus C descriptive)
    md += ["## 7. Simple regime responses (fixed thresholds, descriptive only; A only, B not opened)", ""]
    nwk = niftyA.resample("W-FRI").last().dropna()
    keys = T.iso_weeks(pd.Timestamp("2019-01-01"), pd.Timestamp(G.CUT))
    s1 = T.s1_scale(niftyA, nwk, keys)
    sma = nwk.rolling(40, min_periods=40).mean()

    def by_week(rule):
        out = {}
        for k_ in keys:
            D_ = T.decision_date(niftyA.index, k_)
            f = T.week_label(D_) if D_ is not None else None
            out[k_] = rule(f) if f is not None else 1.0
        return out
    falling = by_week(lambda f: 0.0 if (f in sma.index and f - pd.Timedelta(weeks=4) in sma.index
                                        and sma[f] < sma[f - pd.Timedelta(weeks=4)]) else 1.0)
    br = by_week(lambda f: 0.0 if (len(breadthA[breadthA.index <= f]) and breadthA[breadthA.index <= f].iloc[-1] < 0.40) else 1.0)
    arms = {"live": None, "skip_below_40w": s1, "half_below_40w": {k: (0.5 if v == 0 else 1.0) for k, v in s1.items()},
            "skip_40w_falling": falling, "skip_breadth_lt_40": br}
    big = dA[dA.R >= 2]
    wkey = lambda d: tuple(pd.Timestamp(d).isocalendar()[:2])
    rows = []
    for name, sc_ in arms.items():
        o_c, _ = runA(False, sc_)
        o_u, d_u = runA(True, sc_)
        st = nav_stats(pd.Series(o_c["curve"], index=pd.DatetimeIndex(pd.Series(o_c["curve"]).index)))
        sizes = dA.entry_date.map(lambda d: (sc_ or {}).get(wkey(d), 1.0))
        R_eff = (dA.R * sizes)
        closed = dA.closed
        rows.append({"rule": name, "entries_at_full": int((sizes == 1).sum()), "entries_skipped": int((sizes == 0).sum()),
                     "entries_half": int((sizes == 0.5).sum()), "total_R_sized": round(float(R_eff.sum()), 1),
                     "avg_R_closed_sized": round(float(R_eff[closed].mean()), 3),
                     "acct_sharpe": round(st["sharpe"], 2), "acct_cagr_pct": round(st["cagr_pct"], 1),
                     "acct_maxdd_pct": round(st["maxdd_pct"], 1),
                     "big_winners_skipped": int((sizes[big.index] == 0).sum()),
                     "big_winners_halved": int((sizes[big.index] == 0.5).sum())})
    res["regime_responses_A"] = rows
    md += [md_table(rows, ["rule", "entries_at_full", "entries_skipped", "entries_half", "total_R_sized", "avg_R_closed_sized",
                           "acct_sharpe", "acct_cagr_pct", "acct_maxdd_pct", "big_winners_skipped", "big_winners_halved"]), "",
           "Per-trade R is the live A ledger re-weighted by each rule's size for the entry week (0 = skipped, 0.5 = half). "
           "Account columns are full engine runs of the capped book with the same rule (single path). Big winners = A trades "
           "at or above +2R.", ""]
    rowsC = []
    for dim, val in (("nifty_vs_40w", "below"), ("sma40_slope", "falling"), ("breadth_bucket", "<40%")):
        g = dC[dC[dim] == val]
        rowsC.append({"live trades in state": f"{dim} = {val}", "n": int(len(g)), "their_total_R": round(float(g.R.sum()), 1),
                      "of_all_live": int(len(dC))})
    res["regime_states_C"] = rowsC
    md += ["### Live trades (C) that each rule's state covered (descriptive; no rule was applied live)", "",
           md_table(rowsC, ["live trades in state", "n", "their_total_R", "of_all_live"]), ""]

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    (CACHE / "report_body.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for k, d in D.items():
        d.to_pickle(CACHE / f"trades_{k}.pkl")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
