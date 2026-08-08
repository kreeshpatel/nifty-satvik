"""The candidate through the REAL bar — first end-to-end run of the validated rig.

Everything the session's throwaway scripts did by hand is now done by tested first-party code:

  indicators   :mod:`nq.data.indicators`      (truncation-tested, hand-pinned pivots)
  weekly bars  :mod:`nq.data.weekly`          (ISO-week, byte-identical to the live book —
                                               NOT ``resample("W-FRI")``, which is what the
                                               session's weekly cells wrongly used)
  execution    :mod:`nq.engine.signal_book`   (two-engine parity-tested, ``simulate``'s cost model)
  data gate    :mod:`nq.data.integrity`       (unadjusted splits, thin-universe floor)
  adjudication :func:`nq.runner.research.adjudicate`  (block bootstrap + DSR + fail-closed gates)

CANDIDATE — weekly Supertrend(10,3) + EMA40w trend + monthly-pivot cross; stop 2 x weekly ATR(14);
target 2R; signal on a completed weekly bar, entry at the next daily open, managed on daily bars.

BASE — a **matched random-entry null**: the same number of signals per name, the same stop rule,
the same book, random dates on a fixed seed. That is the right comparator for ``adjudicate``,
whose turnover gate assumes both arms trade; a passive benchmark trades ~never and would fail that
gate for a reason unrelated to the strategy. Passive is reported separately as context, since 0136
established it as the binding economic benchmark.

Nothing here can PROMOTE anything — every window has been read many times. The point is to find out
what the candidate looks like when the numbers are produced by code that is tested.

    python scripts/run_candidate_gate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from nq.data.indicators import atr, ema, fresh, period_pivot, supertrend  # noqa: E402
from nq.data.integrity import assert_min_universe, integrity_report, split_suspects  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.weekly import build_weekly_panel  # noqa: E402
from nq.engine.signal_book import SignalBookConfig, simulate_signal_book  # noqa: E402
from nq.runner.research import adjudicate  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
SEED = 20260807
BOOK = SignalBookConfig(max_positions=10, risk_pct=2.0, max_position_pct=10.0)


def build_panel(ohlcv, membership) -> pd.DataFrame:
    """Tidy long panel, PIT-membership masked, with the ADV sidecar the cost model needs."""
    frames = []
    for tkr, df in ohlcv.items():
        if len(df) < 300 or not membership.get(tkr.upper()):
            continue
        idx = pd.DatetimeIndex(df.index)
        mem = np.zeros(len(idx), dtype=bool)
        for a, b in membership[tkr.upper()]:
            mem |= (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(b))
        if not mem.any():
            continue
        v = df["Volume"].to_numpy(float) if "Volume" in df.columns else np.zeros(len(idx))
        adv = pd.Series(df["Close"].to_numpy(float) * v).rolling(20).mean().to_numpy()
        frames.append(pd.DataFrame({
            "date": idx, "ticker": tkr,
            "open": df["Open"].to_numpy(float), "high": df["High"].to_numpy(float),
            "low": df["Low"].to_numpy(float), "close": df["Close"].to_numpy(float),
            "adv_rupees_20d": np.nan_to_num(adv), "member": mem}))
    p = pd.concat(frames, ignore_index=True)
    p = p[p["member"] & (p["date"] >= START) & (p["date"] <= END)].drop(columns=["member"])
    return p.reset_index(drop=True)


def candidate_signals(ohlcv, panel, weekly) -> pd.DataFrame:
    """Weekly Supertrend + EMA40w + monthly-pivot cross -> one row per fresh signal."""
    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    eligible = set(panel["ticker"].unique())
    rows = []
    for tkr, w in weekly.groupby("ticker"):
        if tkr not in eligible or len(w) < 60:
            continue
        w = w.sort_values("week_end")
        wh, wl, wc = (w[c].to_numpy(float) for c in ("h", "l", "c"))
        wend = pd.DatetimeIndex(w["week_end"])
        _, up = supertrend(wh, wl, wc, 10, 3.0)
        trend = wc > ema(wc, 40)
        # pivot from DAILY bars ("use daily-based values"), read at each week's close
        d = ohlcv[tkr]
        didx = pd.DatetimeIndex(d.index)
        piv_d = pd.Series(period_pivot(didx, d["High"].to_numpy(float), d["Low"].to_numpy(float),
                                       d["Close"].to_numpy(float), freq="M", level="P"), index=didx)
        piv = piv_d.reindex(wend, method="ffill").to_numpy(float)
        prev_c, prev_p = np.roll(wc, 1), np.roll(piv, 1)
        prev_c[0] = prev_p[0] = np.nan
        cross = np.nan_to_num((wc > piv) & (prev_c <= prev_p), nan=False)
        sig = fresh(up & np.nan_to_num(trend, nan=False) & cross)
        watr = atr(wh, wl, wc, 14)
        rs = (d["Close"].to_numpy(float) /
              n50.reindex(didx, method="ffill").to_numpy(float))
        rs55 = pd.Series(rs).pct_change(55).reindex(range(len(didx))).to_numpy()
        rs_at_week = pd.Series(rs55, index=didx).reindex(wend, method="ffill").to_numpy()
        for k in np.flatnonzero(sig):
            stop = wc[k] - 2.0 * watr[k]
            if not np.isfinite(stop) or stop <= 0 or not np.isfinite(rs_at_week[k]):
                continue
            rows.append({"date": wend[k], "ticker": tkr, "stop": stop,
                         "target_r": 2.0, "max_hold": 252, "priority": float(rs_at_week[k])})
    return pd.DataFrame(rows)


def matched_null(signals: pd.DataFrame, panel: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Same signal COUNT per ticker, same stop rule, random dates. The honest comparator."""
    rng = np.random.default_rng(seed)
    dates_by_ticker = {t: g["date"].to_numpy() for t, g in panel.groupby("ticker")}
    close_by = {t: dict(zip(g["date"], g["close"])) for t, g in panel.groupby("ticker")}
    rows = []
    for tkr, g in signals.groupby("ticker"):
        pool = dates_by_ticker.get(tkr)
        if pool is None or len(pool) < 80:
            continue
        picks = rng.choice(pool[60:-5], size=min(len(g), max(len(pool) - 70, 1)), replace=False)
        med_stop_frac = float(np.median(1.0 - g["stop"].to_numpy() /
                                        np.array([close_by[tkr].get(d, np.nan) for d in g["date"]])))
        for d in picks:
            c = close_by[tkr].get(pd.Timestamp(d))
            if c is None or not np.isfinite(med_stop_frac):
                continue
            rows.append({"date": pd.Timestamp(d), "ticker": tkr, "stop": c * (1 - med_stop_frac),
                         "target_r": 2.0, "max_hold": 252, "priority": float(rng.random())})
    return pd.DataFrame(rows)


def passive_benchmark(panel: pd.DataFrame) -> dict:
    """Equal-weight daily-rebalanced ownership of the eligible universe — 0136's binding gate.

    Annualised on **bars/252**, matching ``nq.engine.portfolio.compute_metrics``. Using calendar
    days/365.25 here instead (9.49 vs 9.32 years on this window) silently understated passive by
    ~0.3pp of CAGR and made the comparison unfair to the benchmark — caught by noticing the
    candidate and passive printed an identical 17.62%.
    """
    r = panel.pivot_table(index="date", columns="ticker", values="close").sort_index().pct_change()
    daily = r.mean(axis=1).fillna(0.0)
    eq = (1 + daily).cumprod()
    yrs = len(eq) / 252.0
    return {"cagr_pct": round((eq.iloc[-1] ** (1 / yrs) - 1) * 100, 3),
            "sharpe": round(daily.mean() / daily.std() * np.sqrt(252), 3),
            "max_drawdown_pct": round((eq / eq.cummax() - 1).min() * 100, 2),
            "years": round(yrs, 2), "note": "EW daily rebalance carries a rebalancing premium"}


def concentration(trades: list[dict]) -> dict:
    """backtest-rigor §C4 — is the result carried by a handful of trades?"""
    if not trades:
        return {}
    pnl = np.array([t["pnl"] for t in trades], dtype=float)
    tot = pnl.sum()
    order = np.argsort(-pnl)
    top = {f"top{k}_share_pct": (round(pnl[order[:k]].sum() / tot * 100, 1) if tot else None)
           for k in (5, 10, 25)}
    by_name: dict[str, float] = {}
    for t in trades:
        by_name[t["ticker"]] = by_name.get(t["ticker"], 0.0) + float(t["pnl"])
    top3 = sorted(by_name.values(), reverse=True)[:3]
    return {**top, "top3_names_share_pct": round(sum(top3) / tot * 100, 1) if tot else None,
            "n_trades": len(trades)}


def main() -> int:
    print("=== CANDIDATE THROUGH THE VALIDATED RIG ===\n")
    ohlcv, membership = corrected_universe(), load_membership()
    panel = build_panel(ohlcv, membership)
    print(f"  panel {len(panel):,} rows · {panel['ticker'].nunique()} names · "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}")

    counts = assert_min_universe(panel, floor=100, context="candidate gate")
    print(f"  universe floor OK — min yearly mean {counts.min():.0f} names")

    weekly = build_weekly_panel({t: ohlcv[t] for t in panel['ticker'].unique() if t in ohlcv})
    print(f"  weekly panel {len(weekly):,} rows (ISO-week, canonical)")

    cand_sig = candidate_signals(ohlcv, panel, weekly)
    null_sig = matched_null(cand_sig, panel)
    print(f"  candidate signals {len(cand_sig):,} · matched-null signals {len(null_sig):,}\n")

    cand = simulate_signal_book(panel, cand_sig, cfg=BOOK, start=START, end=END)
    null = simulate_signal_book(panel, null_sig, cfg=BOOK, start=START, end=END)

    print("=== ARMS (full continuous window — no fresh-capital sub-runs) ===")
    for tag, bt in (("CANDIDATE", cand), ("RANDOM NULL", null)):
        m = bt["metrics"]
        print(f"  {tag:<12} CAGR {m['cagr_pct']:>7.2f}%  Sharpe {m['sharpe']:>6.3f}  "
              f"MaxDD {m['max_drawdown_pct']:>7.2f}%  Calmar {m['calmar']:>5.2f}  "
              f"trades {m['n_trades']:>4}  win {m['win_rate_pct']:>5.1f}%")
    pb = passive_benchmark(panel)
    print(f"  {'PASSIVE EW':<12} CAGR {pb['cagr_pct']:>7.2f}%  Sharpe {pb['sharpe']:>6.3f}  "
          f"MaxDD {pb['max_drawdown_pct']:>7.2f}%   [0136's binding benchmark]")

    print("\n=== THE MECHANIZED BAR (nq.runner.research.adjudicate) ===")
    verdict = adjudicate(null, cand, end=END, initial_capital=1_000_000.0)
    for k, v in verdict["gates"].items():
        print(f"  {'PASS' if v else 'FAIL':<5} {k}")
    print(f"\n  dSharpe {verdict['dSharpe']:+.3f}  CI {verdict['dSharpe_ci']}  "
          f"DSR {verdict['dsr_candidate']}  n_eff {verdict['n_eff_windows']}  "
          f"n_trials {verdict['n_trials']}")
    print(f"  dCalmar {verdict['dCalmar']}  2022-26 dCAGR {verdict['subperiod_2022_dCAGR']}  "
          f"fold-pass {verdict['fold_pass_frac']} ({verdict['n_folds']} folds)  "
          f"turnover_d {verdict['turnover_delta']}")
    print(f"\n  VERDICT: {verdict['verdict']}")

    print("\n=== backtest-rigor C4 — concentration ===")
    con = concentration(cand["trades"])
    for k, v in con.items():
        print(f"  {k:<24} {v}")

    print("\n=== data integrity ===")
    rep = integrity_report(ohlcv, trades=cand["trades"], panel=panel, floor=100)
    print(f"  overall {rep['overall']} · events {rep['n_events']} {rep['by_kind']}")
    print(f"  trades spanning unadjusted splits: {rep['trades_spanning_suspects']} "
          f"(P&L {rep['pnl_in_spanning_trades']:,.0f})")
    if rep["trades_spanning_suspects"]:
        print("  ** RED: at least one trade's R is a corporate-action artefact")

    out = ROOT / "diagnostics" / "research" / "candidate_gate.json"
    out.write_text(json.dumps({"candidate": cand["metrics"], "null": null["metrics"],
                               "passive": pb, "verdict": verdict, "concentration": con,
                               "integrity": {k: v for k, v in rep.items() if k != "suspects"}},
                              indent=2, default=str))
    print(f"\n  -> {out}")
    print("  standing counts: screens 19 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
