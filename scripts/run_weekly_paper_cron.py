"""Live / paper runner for the 0091 weekly-swing book (FORWARD-WATCH).

Re-runs the tested 0091 engine (run_bhanushali_weekly_sma.prep_weekly_sma + run_bhanushali_weekly_full.
backtest, finding 0034) from a fixed inception over the freshly-updated corrected universe, then serializes
the CURRENT state to the dashboard envelope (results/*_weekly.json/.csv). Live == backtest by construction:
the same deterministic, PIT-clean engine that produced the +18.2% CAGR / +0.87 Sharpe backtest generates
the live signals — no re-implementation, no persisted-state drift (recomputed from inception each run).

MODELED FILLS — the book models entries at the in-range open; live you place a limit order inside the
band. This is a forward-watch record, NOT a live broker ledger. 0091 signals refresh weekly (Mondays,
after Friday's weekly close); this runs daily and is idempotent.

Clean forward inception (owner choice): default --start = the go-live date, so the book only reflects
trades from inception forward. Until fresh post-inception bars exist the book is legitimately empty (valid,
not an error); it fills as the daily cron adds bars.

    python scripts/run_weekly_paper_cron.py --start 2026-07-04
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
import run_bhanushali_weekly_full as W89  # noqa: E402
import run_bhanushali_weekly_sma as S91  # noqa: E402

INCEPTION_DEFAULT = "2026-07-04"
TARGET_R = 2                     # 0091 books half at +2R -> the displayed target
HOLD_DAYS_DISPLAY = 65          # ~13-week cap in trading days, for the card's "hold ~N days"
# closed-trade exit reason -> the status vocabulary the frontend/history views already understand
_STATUS = {"target3": "HIT_TARGET", "trail": "HIT_STOP", "stop": "HIT_STOP", "stop_half": "HIT_STOP",
           "time": "EXPIRED", "eos": "EXPIRED"}


def _last(P, t, key):
    arr = P[t][key]
    return arr[-1]


def build_envelopes(P, out, ledger, generated_at):
    """Map the 0091 live state to the same dashboard envelope shape the momentum book writes."""
    # ── this week's actionable "buy in range" signals (active entry windows) ──
    signals = []
    for t, o_ in out["active_orders"].items():
        lo, hi = float(o_["lo"]), float(o_["hi"])
        cur = float(_last(P, t, "c"))
        entry = round(cur if lo < cur < hi else (lo + hi) / 2.0, 2)   # buy inside the band
        stop = round(lo, 2)
        target = round(entry + TARGET_R * (entry - stop), 2)
        # signal_date = the SETUP week's last day (the green-bounce week that just closed) — the day
        # before the entry window opened. STABLE across daily re-runs; NOT today's date (which would
        # walk forward every run, the glitch fixed earlier on the momentum book).
        first_day = min(o_["days"])
        sig_idx = max(0, first_day - 1)
        signals.append({
            "ticker": t, "entry": entry, "stop": stop, "target": target,
            "entry_low": round(lo, 2), "entry_high": round(hi, 2),
            "current_price": round(cur, 2), "close": round(cur, 2),
            "signal_date": str(pd.Timestamp(P[t]["dates"][sig_idx]).date()),
            "hold_days": HOLD_DAYS_DISPLAY, "grade": "B", "tier": "signal", "status": "FRESH",
            "buy_window": "this week — buy the open inside the band [low, high]",
        })

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
        "generated_at": generated_at, "model": "weekly-swing-0091", "signals": signals,
        "regime": {"status": "UNKNOWN", "strength": 0, "vix": 0, "breadth": 0},
        "n_positions": len(positions), "cash": round(float(out["cash"]), 2),
        "note": "forward-watch, modeled fills — 0091 all-SMA weekly swing (UNDERPOWERED, not certified)",
    }
    return envelope, sig_hist, analytics, portfolio, hist_df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="0091 weekly-swing forward-watch paper runner")
    ap.add_argument("--start", default=INCEPTION_DEFAULT, help="inception (clean forward start) YYYY-MM-DD")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    args = ap.parse_args(argv)
    sd = Path(args.state_dir); sd.mkdir(parents=True, exist_ok=True)

    # LIVE data = the fresh cache the momentum cron just refreshed (data/ohlcv.pkl). NOT
    # corrected_universe(): the backfill/alias delisted names are a backtest-only survivorship
    # tool, they are not committed to the repo (would crash the cron), and a forward book only
    # ever trades currently-listed names anyway. Empty cache -> valid empty book, never a crash.
    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    mem = load_membership()
    P = S91.prep_weekly_sma(ohlcv)
    ledger: list = []
    out = W89.backtest(P, mem, ledger=ledger, start=args.start, return_state=True)
    # data's last date = the "as of" the book is current to
    last = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=pd.Timestamp(args.start))
    generated_at = str(last.date())

    envelope, sig_hist, analytics, portfolio, hist_df = build_envelopes(P, out, ledger, generated_at)

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
