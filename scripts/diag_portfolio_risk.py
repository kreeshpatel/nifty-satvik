#!/usr/bin/env python3
"""Portfolio risk decomposition — MEASUREMENT, zero trials.

Implements `diagnostics/research/portfolio_risk/SPEC.md`, committed before this script existed. How much
of the book is the market, and how much of its diversification is real?

    python scripts/diag_portfolio_risk.py --live-end 2026-09-23      # historical + live book
    python scripts/diag_portfolio_risk.py --offline                  # historical only, no network

Population A is the live configuration re-run on prices ending **2024-06-30**, so the sealed validation
slice stays shut. Population B is the live forward book (description only). Outputs
`diagnostics/research/portfolio_risk/<run-date>/{summary.json, daily.csv.gz}`. Nothing is adopted: a
de-gross, hedge or seat-count change is a live rule and needs a pre-registration, a trial and the
quarterly review.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.brain import portfolio as PF  # noqa: E402

# ── copied from SPEC.md ─────────────────────────────────────────────────────────────────────────────
HIST_START, HIST_END = "2019-01-01", "2024-06-30"      # ends before the sealed slice
CORR_WINDOW = 63
DD_THRESHOLD, DD_LOOKBACK = 0.10, 252
N_BOOT, SEED, BLOCK = 2000, 20260924, 63
MIN_SESSIONS, MIN_TRADES = 100, 30
BAD_DROP, BAD_JUMP = -0.45, 0.90                        # same integrity rule as 0141
INCEPTION = "2026-07-04"

OUT_BASE = ROOT / "diagnostics" / "research" / "portfolio_risk"


def _returns_panel(ohlcv: dict, demergers: dict) -> pd.DataFrame:
    """Daily returns by ticker, with split-size moves and registered demerger days removed (integrity)."""
    cols = {}
    for t, df in ohlcv.items():
        if df is None or len(df) < 2:
            continue
        c = pd.Series(df["Close"].to_numpy(float), index=pd.DatetimeIndex(df.index).normalize())
        r = c.pct_change()
        r[(r <= BAD_DROP) | (r >= BAD_JUMP)] = np.nan
        for d in demergers.get(t, ()):                   # the day a spin-off re-bases is not a return
            if d in r.index:
                r.loc[d] = np.nan
        cols[t] = r
    return pd.DataFrame(cols).sort_index()


def _held_by_day(ledger: pd.DataFrame, sessions: pd.DatetimeIndex) -> dict[pd.Timestamp, list[str]]:
    """Names held on each session: entry_date <= d <= exit_date (the exit fills at that day's open)."""
    held: dict[pd.Timestamp, list[str]] = {d: [] for d in sessions}
    for t in ledger.itertuples(index=False):
        a, b = pd.Timestamp(t.entry_date).normalize(), pd.Timestamp(t.exit_date).normalize()
        for d in sessions[(sessions >= a) & (sessions <= b)]:
            held[d].append(t.tkr)
    return held


def _togetherness(held: dict, rets: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Per session: seats, average pairwise correlation, effective bets, diversification ratio, PC1 share.

    Correlations use the trailing CORR_WINDOW sessions up to and including that day (point-in-time).
    """
    sessions = sorted(held)
    idx = rets.index
    rows = []
    for d in sessions:
        names = [n for n in held[d] if n in rets.columns]
        row = {"date": d, "n_held": len(names)}
        if len(names) >= 2:
            end = idx.searchsorted(d, side="right")
            win = rets.iloc[max(0, end - CORR_WINDOW):end][names].dropna(axis=1, thresh=CORR_WINDOW // 2)
            if win.shape[1] >= 2 and len(win) >= CORR_WINDOW // 2:
                rho = PF.average_pairwise_correlation(win)
                cov = win.cov().to_numpy(float)
                w = np.array([weights[d].get(n, 0.0) for n in win.columns]) if weights else None
                if w is None or not np.isfinite(w).all() or w.sum() <= 0:
                    w = np.full(win.shape[1], 1.0 / win.shape[1])
                else:
                    w = w / w.sum()
                row.update(rho_bar=rho, n_eff=PF.effective_bets(win.shape[1], rho),
                           div_ratio=PF.diversification_ratio(w, cov),
                           pc1_share=PF.top_eigenvalue_share(win), n_corr=win.shape[1])
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")


def _series_cell(x: pd.Series, label: str) -> dict:
    s = pd.Series(x, dtype=float).dropna()
    cell = {"n_sessions": int(len(s)), "informative": len(s) >= MIN_SESSIONS}
    if len(s):
        pt, lo, hi = PF.block_bootstrap_ci(s.to_numpy(), lambda a: float(a.mean()),
                                           block=BLOCK, n_boot=N_BOOT, seed=SEED)
        cell.update({f"mean_{label}": round(pt, 4), "ci": [round(lo, 4), round(hi, 4)],
                     "median": round(float(s.median()), 4),
                     "p10": round(float(s.quantile(0.10)), 4), "p90": round(float(s.quantile(0.90)), 4)})
    return cell


def _episodes(mask: pd.Series, min_sessions: int = 30) -> list[tuple[str, pd.Series]]:
    """Contiguous runs of a regime mask, longest first (SPEC A2).

    The red-team read showed why this is needed: 90 of the 171 index-drawdown sessions are the COVID
    crash, and the whole "correlation rises in drawdowns" effect lived in that one episode. A regime
    cell built from stitched episodes is one observation dressed as many.
    """
    m = pd.Series(mask, dtype=bool)
    grp = (m != m.shift()).cumsum()[m]
    runs = [(str(g.index[0].date()) + ".." + str(g.index[-1].date()), g)
            for _, g in m[m].groupby(grp) if len(g) >= min_sessions]
    return sorted(runs, key=lambda kv: -len(kv[1]))


def _trade_cell(d: pd.DataFrame, r_col: str = "R") -> dict:
    """Per-exit-reason cell with the SPEC's cluster-bootstrap CI on the mean (it promised one; the first
    implementation shipped none — red-team, 2026-09-24)."""
    pt, lo, hi = PF.cluster_bootstrap_mean(d[r_col], d["tkr"] if "tkr" in d else d.index.astype(str),
                                           n_boot=N_BOOT, seed=SEED)
    return {"n": int(len(d)), "mean_R": round(pt, 3), "mean_R_ci": [round(lo, 3), round(hi, 3)],
            "median_R": round(float(d[r_col].median()), 3), "skew_R": round(PF.sample_skew(d[r_col]), 3),
            "sum_R": round(float(d[r_col].sum()), 2), "informative": len(d) >= MIN_TRADES}


def _exit_cells(ledger: pd.DataFrame, reason_col: str = "reason", r_col: str = "R") -> dict:
    if ledger.empty or reason_col not in ledger:
        return {}
    d = ledger.dropna(subset=[reason_col, r_col])
    total = float(d[r_col].sum())
    out = {}
    for reason, g in d.groupby(reason_col):
        cell = _trade_cell(g, r_col)
        cell["share_of_total_R"] = round(float(g[r_col].sum()) / total, 4) if total > 0 else None
        out[str(reason)] = cell
    out["_note"] = ("share_of_total_R is None when the book's total R is not positive — the ratio inverts "
                    "sign and a losing family reads as a contribution. Read sum_R in R units.")
    return out


def _exposure(book_r: pd.Series, mkt_r: pd.Series) -> dict:
    m = PF.market_model(book_r, mkt_r)
    out = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in m.items()}
    out["informative"] = m["n"] >= MIN_SESSIONS
    both = pd.concat([book_r, mkt_r], axis=1, join="inner").dropna()
    if len(both) >= BLOCK:
        both.columns = ["b", "m"]
        _, lo, hi = PF.block_bootstrap_paired(both["m"], both["b"], PF.beta_of,
                                              block=BLOCK, n_boot=N_BOOT, seed=SEED)
        out["beta_block_ci"] = [round(lo, 4), round(hi, 4)]
    return out


def _vol_at_exit_vs_entry(ledger: pd.DataFrame, rets: pd.DataFrame) -> dict:
    """SPEC measure 8: sigma_63(exit) / sigma_63(entry) per closed trade, by exit reason."""
    vol = rets.rolling(CORR_WINDOW, min_periods=CORR_WINDOW // 2).std()
    rows = []
    for t in ledger.itertuples(index=False):
        if t.tkr not in vol.columns:
            continue
        try:
            a = vol[t.tkr].asof(pd.Timestamp(t.entry_date))
            b = vol[t.tkr].asof(pd.Timestamp(t.exit_date))
        except KeyError:
            continue
        if a and b and np.isfinite(a) and np.isfinite(b) and a > 0:
            rows.append({"reason": str(t.reason), "ratio": float(b / a)})
    d = pd.DataFrame(rows)
    if d.empty:
        return {}
    g = d.groupby("reason")["ratio"].agg(n="size", median="median", mean="mean")
    g["informative"] = g["n"] >= MIN_TRADES
    return {r: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}
            for r, row in g.round(4).to_dict("index").items()}


def _curve_stats(curve: pd.Series) -> dict:
    """Headline stats of the reconstructed book — for `/plausibility-check`, not for promotion.

    NOT A GATE NUMBER. This is a FRESH-CAPITAL run from HIST_START, so the equity peak resets at the
    window start and the drawdown is measured from a 2019 peak. CLAUDE.md requires sub-period GATES to be
    a continuous slice of one full run; this is a descriptive reconstruction of the book being described,
    and nothing is judged against a threshold here.
    """
    c = pd.Series(curve, dtype=float).dropna()
    if len(c) < 2:
        return {}
    r = c.pct_change().dropna()
    years = (c.index[-1] - c.index[0]).days / 365.25
    dd = float((c / c.cummax() - 1.0).min())
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(252)) if r.std(ddof=1) > 0 else float("nan")
    return {"start_equity": round(float(c.iloc[0]), 2), "final_equity": round(float(c.iloc[-1]), 2),
            "years": round(years, 2), "cagr_pct": round(((float(c.iloc[-1]) / float(c.iloc[0])) ** (1 / years) - 1) * 100, 2),
            "sharpe_gross_daily_ann": round(sharpe, 3), "max_drawdown_pct": round(dd * 100, 2)}


def historical(ohlcv: dict, demergers: dict, index_close: pd.Series) -> tuple[dict, pd.DataFrame]:
    """Population A — the live configuration on prices ending HIST_END."""
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)

    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(HIST_END)] for t, df in ohlcv.items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    led: list = []
    # SPEC A1: the corporate-action HOLD is deliberately OFF here. It waits for an owner to resolve a
    # frozen position; with no owner in a 5.5-year reconstruction it never resolves, the loss is never
    # realised, and the book reads 52.8% CAGR instead of 39.4% (4 positions frozen on circuit-limit
    # crash days). Registered demerger events stay on — those are facts, not a review.
    out = R94.backtest(P, None, ledger=led, start=HIST_START, return_state=True,
                       a_grade=R94.grade_a_entries(P), **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS,
                       demerger_events=events)
    ledger = pd.DataFrame(led)
    curve = pd.Series(out["curve"], dtype=float)
    curve.index = pd.DatetimeIndex(curve.index).normalize()
    curve = curve[~curve.index.duplicated(keep="last")]
    book_r = PF.daily_returns(curve)
    mkt_r = PF.daily_returns(index_close)

    rets = _returns_panel(cut, demergers)
    sessions = pd.DatetimeIndex([d for d in curve.index if d >= pd.Timestamp(HIST_START)])
    tog = _togetherness(_held_by_day(ledger, sessions), rets)
    # .astype(bool) matters: a reindexed+filled mask is object dtype, and `~mask` on object dtype gives
    # Python's bitwise-not of the bools (-1 / -2), which pandas then reads as LABELS, not a filter.
    dd = (PF.drawdown_regime(index_close, threshold=DD_THRESHOLD, lookback=DD_LOOKBACK)
          .reindex(tog.index).fillna(False).astype(bool))

    summ = {
        "window": f"{HIST_START}..{HIST_END}", "n_trades": int(len(ledger)),
        "book": _curve_stats(curve),      # so the book being described can be checked against the anchors
        "market_exposure": _exposure(book_r, mkt_r),
        "togetherness": {k: _series_cell(tog[k], k) for k in ("rho_bar", "n_eff", "div_ratio", "pc1_share")
                         if k in tog},
        "seats": {"mean": round(float(tog["n_held"].mean()), 2), "median": float(tog["n_held"].median()),
                  "max": int(tog["n_held"].max())},
        "regime_split": {},
        "exit_reasons": _exit_cells(ledger),
        "vol_at_exit_over_entry": _vol_at_exit_vs_entry(ledger, rets),
    }
    def _regime_cell(sub: pd.DataFrame) -> dict:
        cell = {k: _series_cell(sub[k], k) for k in ("rho_bar", "n_eff", "div_ratio") if k in sub}
        cell["mean_n_held"] = round(float(sub["n_held"].mean()), 2)     # n_eff falls with seats alone
        idx = book_r.index.intersection(sub.index)
        cell["market_exposure"] = _exposure(book_r.reindex(idx), mkt_r)
        cell["book_return_per_day_pct"] = round(float(book_r.reindex(idx).mean()) * 100, 4)
        return cell

    for name, mask in (("index_drawdown_ge_10pct", dd), ("calm", ~dd)):
        summ["regime_split"][name] = _regime_cell(tog[mask])
    # SPEC A2 — the drawdown cell episode by episode, and with its largest episode removed. One crash
    # must not be able to carry a regime claim.
    eps = _episodes(dd)
    summ["regime_split"]["_episodes"] = {name: _regime_cell(tog.loc[g.index]) for name, g in eps}
    if eps:
        summ["regime_split"]["index_drawdown_ex_largest_episode"] = _regime_cell(
            tog[dd & ~tog.index.isin(eps[0][1].index)])
        summ["regime_split"]["_largest_episode"] = eps[0][0]
    return summ, tog.assign(population="historical")


def _index_live(end: str) -> pd.Series:
    """Nifty-50 closes for the live window, fetched directly.

    The committed `benchmark_nifty50.csv` is refreshed by the weekly cron at RUNTIME, so the file in the
    repo ends before the live book starts (2026-07-03 against an inception of 2026-07-04) and a beta
    computed from it would have had zero overlapping sessions. Found on the first run of this study.
    """
    import yfinance as yf
    end_excl = str((pd.Timestamp(end) + pd.Timedelta(days=1)).date())
    df = yf.download("^NSEI", start="2026-01-01", end=end_excl, auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    s = pd.Series(df["Close"].to_numpy(float), index=pd.DatetimeIndex(df.index).normalize())
    return s[~s.index.duplicated(keep="last")].sort_index()


def live(end: str) -> tuple[dict, pd.DataFrame]:
    """Population B — the live forward book. Description only; every cell carries n."""
    from diag_excursions_null import download_raw

    nav = pd.read_csv(ROOT / "results" / "portfolio_history_weekly.csv", parse_dates=["date"])
    nav = nav.set_index("date")["total_value"].astype(float)
    nav_end = str(nav.index.max().date())      # the NAV, not the requested price end, bounds this window
    book_r = PF.daily_returns(nav)
    snaps: dict[pd.Timestamp, dict] = {}
    for f in sorted(glob.glob(str(ROOT / "results" / "archive" / "*" / "paper_portfolio_weekly.json"))):
        d = pd.Timestamp(Path(f).parent.name[:10])
        pos = json.loads(Path(f).read_text(encoding="utf-8")).get("positions", {})
        if pos:
            snaps[d] = {t: float(p.get("current_value") or 0.0) for t, p in pos.items()}
    names = sorted({t for s in snaps.values() for t in s})
    px = download_raw(names, start="2026-01-01", end=end) if names else {}
    rets = _returns_panel(px, {})
    held = {d: [t for t, v in s.items() if v > 0] for d, s in snaps.items()}
    weights = {d: {t: v for t, v in s.items() if v > 0} for d, s in snaps.items()}
    tog = _togetherness(held, rets, weights=weights)

    hist = json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8"))
    closed = pd.DataFrame([{"reason": h.get("exit_reason"), "R": h.get("r_multiple")}
                           for h in hist if h.get("exit_reason")])
    shares = {}
    if snaps:
        last = max(snaps)
        cols = [t for t in weights[last] if t in rets.columns]
        win = rets.loc[:last, cols].tail(CORR_WINDOW).dropna(axis=1, thresh=CORR_WINDOW // 2)
        if win.shape[1] >= 2:
            w = np.array([weights[last][t] for t in win.columns], dtype=float)
            vs = PF.variance_shares(w / w.sum(), win.cov().to_numpy(float))
            vs.index = list(win.columns)
            shares = {"as_of": str(last.date()),
                      "shares": json.loads(vs.round(4).to_json(orient="index"))}
    return {
        "inception": INCEPTION, "nav_window_end": nav_end, "prices_fetched_to": end,
        "n_snapshots": len(snaps),
        "_status": "forward-wall description; n is small by construction",
        "market_source": "^NSEI via yfinance (the committed CSV ends before inception)",
        "market_exposure": _exposure(book_r, PF.daily_returns(_index_live(end))),
        "togetherness": {k: _series_cell(tog[k], k) for k in ("rho_bar", "n_eff", "div_ratio", "pc1_share")
                         if k in tog},
        "seats": ({"mean": round(float(tog["n_held"].mean()), 2), "max": int(tog["n_held"].max())}
                  if len(tog) else {}),
        "variance_shares_latest": shares,
        "exit_reasons": _exit_cells(closed.assign(tkr=[h.get("ticker") for h in hist if h.get("exit_reason")])),
        "n_closed_trades": int(len(closed)),
    }, tog.assign(population="live")


def assert_completed_session(end: str, today: date | None = None) -> None:
    today = today or date.today()
    if date.fromisoformat(end) >= today:
        raise SystemExit(f"--live-end {end} is not a completed session (today is {today}); use the last closed one")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--live-end", help="last COMPLETED session for the live book's prices")
    ap.add_argument("--offline", action="store_true", help="historical only; no network")
    ap.add_argument("--run-date", default=str(date.today()))
    args = ap.parse_args(argv)
    if not args.offline and not args.live_end:
        ap.error("--live-end is required unless --offline")

    import run_bhanushali_weekly_crs as CRS
    from diag_excursions_null import demerger_dates
    from run_bhanushali_path1 import corrected_universe

    n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
    n50.index = pd.DatetimeIndex(n50.index).normalize()
    n50 = n50[~n50.index.duplicated(keep="last")].sort_index()   # the CSV can carry a repeated session
    counts = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    summary: dict = {
        "spec": "diagnostics/research/portfolio_risk/SPEC.md", "class": "MEASUREMENT (zero trials)",
        "n_trials_at_run": counts["cumulative_n_trials"], "run_date": args.run_date,
        "constants": {"corr_window": CORR_WINDOW, "dd_threshold": DD_THRESHOLD, "block": BLOCK,
                      "n_boot": N_BOOT, "seed": SEED, "min_sessions": MIN_SESSIONS, "min_trades": MIN_TRADES},
        "book_stats_caveat": ("The historical book's CAGR/Sharpe/DD are a FRESH-CAPITAL sub-window run "
                              "(peak resets at 2019-01-01), NOT gate numbers. On this window frozen-0094 "
                              "defaults give 30.3%/1.225; the live config's lift is the config-P runner "
                              "exit (24.0%/1.153 -> 39.4%/1.666), the owner-adopted fat-tail exit."),
        "reading": ("Exposure description only. Nothing here authorises a de-gross, a hedge or a seat-count "
                    "change: 0095 killed the one de-gross measured on this book (ΔSharpe −0.398) and "
                    "FINDING_more_slots shows concentration is load-bearing."),
    }
    ohlcv = corrected_universe()
    dem = demerger_dates()
    summary["historical"], daily_a = historical(ohlcv, dem, n50)
    frames = [daily_a]
    if not args.offline:
        assert_completed_session(args.live_end)
        summary["live"], daily_b = live(args.live_end)
        frames.append(daily_b)

    out = OUT_BASE / args.run_date
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    pd.concat(frames).to_csv(out / "daily.csv.gz", compression="gzip")
    print(f"portfolio risk -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
