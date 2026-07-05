"""Live / paper runner for the 0091 weekly-swing book (FORWARD-WATCH).

Self-sufficient: refreshes the live OHLCV cache itself, then re-runs the tested 0091 engine
(run_bhanushali_weekly_sma.prep_weekly_sma + run_bhanushali_weekly_full.backtest, finding 0034) from a
fixed inception, and serializes the CURRENT state to the dashboard envelope (results/*_weekly.json/.csv).
Live == backtest by construction: the same deterministic, PIT-clean engine that produced the +18.2% CAGR /
+0.87 Sharpe backtest generates the live signals — no re-implementation.

CADENCE — a weekly-swing book only changes after Friday's weekly close, so this runs on its OWN schedule:
**every Saturday 6 PM IST** (.github/workflows/cron-weekly-scanner.yml). Saturday's download picks up the
just-closed Friday bar; the signals it computes are actionable the following Mon/Tue (buy in the band).
Idempotent — recomputed from inception each run (see the known mutable-record caveat, finding-0035 TODO).

MODELED FILLS — the book models entries at the in-range open; live you place a limit order inside the
band. Forward-watch record, NOT a live broker ledger. Clean forward inception (owner choice): default
--start = go-live date, so the book only reflects trades from inception forward; empty until fresh
post-inception bars exist (valid, not an error).

    python scripts/run_weekly_paper_cron.py --start 2026-07-04            # cron (downloads)
    python scripts/run_weekly_paper_cron.py --start 2025-01-01 --no-download  # local/offline test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import RESULTS_DIR  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
import run_bhanushali_weekly_full as W89  # noqa: E402  (engine family; kept for imports)
import run_bhanushali_weekly_crs as CRS  # noqa: E402  (Nifty-50 CSV path + index plumbing)
import run_bhanushali_weekly_rank as R94  # noqa: E402  — LIVE strategy: 0093-N50 + ranked fill (finding 0038)

INCEPTION_DEFAULT = "2026-07-04"
TARGET_R = 2                     # 0091 books half at +2R -> the displayed target
HOLD_DAYS_DISPLAY = 65          # ~13-week cap in trading days, for the card's "hold ~N days"
# closed-trade exit reason -> the status vocabulary the frontend/history views already understand
_STATUS = {"target3": "HIT_TARGET", "trail": "HIT_STOP", "stop": "HIT_STOP", "stop_half": "HIT_STOP",
           "time": "EXPIRED", "eos": "EXPIRED"}


def _last(P, t, key):
    arr = P[t][key]
    return arr[-1]


def build_envelopes(P, out, ledger, generated_at, mem=None):
    """Map the 0091 live state to the same dashboard envelope shape the momentum book writes.

    Buy-signals come from the LATEST completed week's setup (P[t]['last_signal']) — inception-independent,
    so they always reflect last Friday's close. Held positions / NAV / closed trades come from the
    inception-gated paper book (out) — clean-forward, empty until the book has post-inception trades.
    """
    from nq.data.membership import ticker_in_index_on
    signals = []
    for t, s in P.items():
        ls = s.get("last_signal")
        if not ls:
            continue
        fri = pd.Timestamp(s["dates"][ls["fri_idx"]])
        if mem is not None and not ticker_in_index_on(t, fri.date(), mem):
            continue                                           # only currently-listed index members
        lo, hi = ls["lo"], ls["hi"]
        cur = float(_last(P, t, "c"))
        entry = round(cur if lo < cur < hi else (lo + hi) / 2.0, 2)   # buy inside the band
        stop = round(lo, 2)
        if entry <= stop:
            continue
        signals.append({
            "ticker": t, "entry": entry, "stop": stop,
            "target": round(entry + TARGET_R * (entry - stop), 2),
            "entry_low": round(lo, 2), "entry_high": round(hi, 2),
            "current_price": round(cur, 2), "close": round(cur, 2),
            "signal_date": str(fri.date()),                    # the just-closed setup week (stable)
            "hold_days": HOLD_DAYS_DISPLAY,
            # CRS-rank fill priority (finding 0038): fund strongest-first. A-grade = top 5 by rank.
            "crs_rank": round(float(ls.get("rank", 0.0)), 4),
            "grade": "B", "tier": "signal", "status": "FRESH",
            "buy_window": "buy Mon–Fri this week, at the open inside the band [low, high] — fund strongest CRS rank first",
        })
    # strongest-first on the page; top-5 flagged A so the grade filter surfaces the priority names
    signals.sort(key=lambda x: -x["crs_rank"])
    for j, sg in enumerate(signals):
        sg["grade"] = "A" if j < 5 else "B"

    # ── held positions ──
    positions = {}
    hist_active = []
    for t, p in out["open_positions"].items():
        cur = float(_last(P, t, "c"))
        entry = float(p["en"])
        stop = float(p["trail"] if p["half_done"] else p["stop"])
        shares = float(p["sh"])
        ed = str(p["rec"]["entry_date"])[:10] if "rec" in p else None
        pct = round((cur / entry - 1) * 100, 2) if entry else 0.0
        days = int(p["weeks"] * 5)
        positions[t] = {
            "entry_date": ed, "entry_price": round(entry, 2), "shares": round(shares, 2),
            "position_size": round(shares * entry, 2), "atr_stop": round(stop, 2),
            "target": round(float(p["tp2"]), 2), "current_price": round(cur, 2),
            "current_value": round(shares * cur, 2), "unrealised_pnl": round(shares * (cur - entry), 2),
            "unrealised_pnl_pct": pct, "days_held": days,
        }
        hist_active.append({
            "ticker": t, "signal_date": ed, "status": "ACTIVE", "entry": round(entry, 2),
            "stop": round(stop, 2), "target": round(float(p["tp2"]), 2), "current_price": round(cur, 2),
            "close_price": round(cur, 2), "pnl_pct": pct, "return_pct": pct,
            "days_since": days, "hold_days": days,
        })

    # ── closed trades -> history + analytics ──
    led = pd.DataFrame(ledger)
    hist_closed = []
    for _, r in led.iterrows():
        entry = float(r["entry"]); exitpx = float(r["exit_px"])
        ret_pct = round((exitpx / entry - 1) * 100, 2) if entry else 0.0
        hist_closed.append({
            "ticker": r["tkr"], "signal_date": str(r["entry_date"])[:10],
            "status": _STATUS.get(str(r["reason"]).replace("_half", ""), "EXPIRED"),
            "entry": round(entry, 2), "close_price": round(exitpx, 2),
            "close_date": str(r["exit_date"])[:10], "return_pct": ret_pct, "pnl_pct": ret_pct,
            "r_multiple": round(float(r["R"]), 2), "net_pnl": round(float(r["net_pnl"]), 2),
            "days_since": int(r["held_weeks"] * 5), "hold_days": int(r["held_weeks"] * 5),
            "exit_reason": str(r["reason"]),
        })
    sig_hist = hist_closed + hist_active
    n_closed = len(led)
    wins = int((led["R"] > 0).sum()) if n_closed else 0
    analytics = {
        "total_signals": len(sig_hist), "total_closed": n_closed, "active": len(positions),
        "win_rate": round(wins / n_closed * 100, 1) if n_closed else None,
        "avg_return_pct": round(float(pd.Series([h["return_pct"] for h in hist_closed]).mean()), 2) if n_closed else None,
        "avg_r": round(float(led["R"].mean()), 2) if n_closed else None,
    }

    # ── portfolio + NAV curve ──
    curve = out["curve"]
    nav = float(out["equity"])
    peak = float(curve.cummax().iloc[-1]) if len(curve) else nav
    portfolio = {"cash": round(float(out["cash"]), 2), "peak_value": round(peak, 2),
                 "total_value": round(nav, 2), "n_positions": len(positions),
                 "total_trades": n_closed, "positions": positions}
    hist_df = (curve.rename("total_value").rename_axis("date").reset_index()
               if len(curve) else pd.DataFrame({"date": [], "total_value": []}))

    envelope = {
        "generated_at": generated_at, "model": "weekly-swing-0094-rank", "signals": signals,
        "regime": {"status": "UNKNOWN", "strength": 0, "vix": 0, "breadth": 0},
        "n_positions": len(positions), "cash": round(float(out["cash"]), 2),
        "note": "forward-watch, modeled fills — 0094 weekly swing (0093-N50 signals, CRS-ranked fills; UNDERPOWERED DSR 0.89, not certified)",
    }
    return envelope, sig_hist, analytics, portfolio, hist_df


def _refresh_ohlcv(start: str, history_days: int, do_download: bool) -> dict:
    """Return the LIVE OHLCV cache, refreshed with recent bars unless --no-download.

    Self-sufficient so the weekly book can run in its OWN Saturday workflow (no momentum
    step to download first). Mirrors run_paper_cron's incremental logic: cold cache -> full
    history from (inception - history_days); warm cache -> last 15 days merged. Saturday runs
    pick up the just-closed Friday bar (NSE shut Sat, so yfinance returns through Friday).
    """
    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    if not do_download:
        return ohlcv
    from datetime import date, timedelta
    from nq.data.ohlcv import download_ohlcv, merge_ohlcv, save_ohlcv_cache
    from run_cpcv import build_universe
    universe = build_universe("current")
    hist_start = (pd.to_datetime(start) - pd.Timedelta(days=history_days)).date().isoformat()
    dl_start = hist_start if not ohlcv else (date.today() - timedelta(days=15)).isoformat()
    print(f"downloading OHLCV {dl_start}.. for {len(universe)} names ...", flush=True)
    try:
        fresh = download_ohlcv(universe, start=dl_start, end=date.today().isoformat())
        ohlcv = merge_ohlcv(ohlcv, fresh) if ohlcv else fresh
        save_ohlcv_cache(ohlcv, OHLCV_CACHE)
    except Exception as exc:  # noqa: BLE001 — a download hiccup must not lose the existing cache/book
        print(f"download failed ({type(exc).__name__}: {exc}); using cached bars", flush=True)
    return ohlcv


def _refresh_nifty50(do_download: bool) -> None:
    """Refresh the pinned Nifty-50 CSV (the CRS denominator) with recent bars. Non-fatal — a fetch
    hiccup falls back to the committed series so the book still runs."""
    if not do_download:
        return
    from datetime import date
    try:
        import yfinance as yf
        csv = CRS.NIFTY50_CSV
        existing = pd.read_csv(csv, parse_dates=["date"]) if Path(csv).exists() else pd.DataFrame(columns=["date", "nifty50_close"])
        d = yf.download("^NSEI", start="2015-01-01", end=date.today().isoformat(), progress=False, auto_adjust=False)
        close = d["Close"]; close = close.iloc[:, 0] if hasattr(close, "columns") else close
        fresh = pd.DataFrame({"date": pd.to_datetime(close.index).tz_localize(None),
                              "nifty50_close": close.values}).dropna()
        merged = pd.concat([existing, fresh]).drop_duplicates("date", keep="last").sort_values("date")
        merged.to_csv(csv, index=False)
        print(f"nifty-50 refreshed -> {merged['date'].max().date()} ({len(merged)} rows)", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"nifty-50 refresh failed ({type(exc).__name__}: {exc}); using committed CSV", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="weekly-swing (0093 + Nifty-50 CRS) forward-watch paper runner")
    ap.add_argument("--start", default=INCEPTION_DEFAULT, help="inception (clean forward start) YYYY-MM-DD")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    ap.add_argument("--no-download", action="store_true", help="use the cache as-is (test/offline)")
    ap.add_argument("--history-days", type=int, default=520, help="calendar days of history before inception for the 44-week-SMA warmup")
    args = ap.parse_args(argv)
    sd = Path(args.state_dir); sd.mkdir(parents=True, exist_ok=True)

    # LIVE data = data/ohlcv.pkl (self-refreshed here). NOT corrected_universe(): the backfill/alias
    # delisted names are a backtest-only survivorship tool, are not committed to the repo (would crash
    # the cron), and a forward book only ever trades currently-listed names. Empty -> valid empty book.
    ohlcv = _refresh_ohlcv(args.start, args.history_days, not args.no_download)
    _refresh_nifty50(not args.no_download)               # CRS denominator (finding 0037)
    mem = load_membership()
    # LIVE strategy = 0093 + Nifty-50 with CRS-ranked fills (finding 0038; supersedes arbitrary fill).
    P = R94.prep_weekly_rank(ohlcv)
    ledger: list = []
    out = R94.backtest(P, mem, ledger=ledger, start=args.start, return_state=True)
    # data's last date = the "as of" the book is current to
    last = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=pd.Timestamp(args.start))
    generated_at = str(last.date())

    envelope, sig_hist, analytics, portfolio, hist_df = build_envelopes(P, out, ledger, generated_at, mem)

    (sd / "signals_today_weekly.json").write_text(json.dumps(envelope, indent=2, default=str), encoding="utf-8")
    (sd / "signals_history_weekly.json").write_text(json.dumps(sig_hist, indent=2, default=str), encoding="utf-8")
    (sd / "signal_analytics_weekly.json").write_text(json.dumps(analytics, indent=2, default=str), encoding="utf-8")
    (sd / "paper_portfolio_weekly.json").write_text(json.dumps(portfolio, indent=2, default=str), encoding="utf-8")
    hist_df.to_csv(sd / "portfolio_history_weekly.csv", index=False)

    print(f"weekly paper cron: inception {args.start} | as-of {generated_at} | "
          f"{len(envelope['signals'])} buy-signals | held {portfolio['n_positions']} | "
          f"closed {analytics['total_closed']} | NAV {portfolio['total_value']:,.0f} -> {sd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
