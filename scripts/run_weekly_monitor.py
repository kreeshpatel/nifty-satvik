"""Daily OBSERVATIONAL monitor for the Weekly-Swing forward-watch book.

Why this exists: the weekly-swing engine only recomputes on Saturday (run_weekly_paper_cron.py),
so all week the dashboard's weekly cards carry SATURDAY's price / P&L / distance-to-stop. This job
re-prices those FROZEN cards against fresh daily bars and flags intra-week events so the owner can
act on resting broker orders without watching the screen all day.

STRICTLY observational — it is the weekly book's analogue of the intraday shadow scan:
  * It NEVER recomputes the weekly signal set. Re-running the weekly engine daily would risk
    emitting/retracting signals off a PARTIAL current-week bar and break the weekly decision
    cadence the forward paper record is certified on.
  * It NEVER changes the frozen entry / stop / target — those are decided only at the Friday
    weekly close. It only reports live price vs those fixed lines.
  * It NEVER touches the paper book, NAV, ledger, wall log, or kill state.

Reads : results/signals_today_weekly.json   (the frozen weekly envelope: buy signals + held cards)
Writes: results/weekly_monitor.json         (fresh current_price + per-ticker event flags)

The dashboard backend (routers/signals.py) overlays this file's current_price and flags onto the
frozen weekly cards, so prices/P&L stay live all week for every viewer — Kite-connected or not —
without a second signal engine.

    python scripts/run_weekly_monitor.py               # cron (refreshes recent daily bars)
    python scripts/run_weekly_monitor.py --no-download # offline / local test (cache as-is)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import RESULTS_DIR  # noqa: E402
from nq.data.ohlcv import (  # noqa: E402
    OHLCV_CACHE,
    download_ohlcv,
    load_ohlcv_cache,
    merge_ohlcv,
    save_ohlcv_cache,
)

TRAIL_PCT = 0.04          # the runner's ratchet trail = 20-day SMA x (1 - 4%); shown as info only
NEAR_PCT = 2.0            # "approaching" band for stop / target proximity flags (percent)
CAP_WEEKS = 13            # ~3-month time cap; flag when a held position nears it
IST = timezone(timedelta(hours=5, minutes=30))


def _last_close_open_sma(df: pd.DataFrame) -> tuple[float, float, float, pd.Timestamp] | None:
    """(last_close, last_open, 20-day SMA of close, last-bar date) from a raw OHLCV frame."""
    if df is None or len(df) == 0 or "Close" not in df.columns:
        return None
    c = df["Close"].astype(float)
    o = df["Open"].astype(float) if "Open" in df.columns else c
    sma20 = float(c.tail(20).mean()) if len(c) >= 1 else float("nan")
    return float(c.iloc[-1]), float(o.iloc[-1]), sma20, pd.Timestamp(df.index[-1])


def _refresh(tickers: list[str], do_download: bool) -> dict:
    """Return the OHLCV cache, refreshed with the last ~20 days for just the envelope's tickers.

    Cheap by design — only the handful of names on the weekly cards, not the whole universe. A
    download hiccup is non-fatal: we fall back to whatever the cache already holds."""
    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    if not do_download or not tickers:
        return ohlcv
    dl_start = (date.today() - timedelta(days=20)).isoformat()
    try:
        fresh = download_ohlcv(tickers, start=dl_start, end=date.today().isoformat())
        ohlcv = merge_ohlcv(ohlcv, fresh) if ohlcv else fresh
        save_ohlcv_cache(ohlcv, OHLCV_CACHE)
        print(f"refreshed {len(fresh)}/{len(tickers)} tickers from {dl_start}", flush=True)
    except Exception as exc:  # noqa: BLE001 — never lose the cache over a fetch hiccup
        print(f"download failed ({type(exc).__name__}: {exc}); using cached bars", flush=True)
    return ohlcv


def build_monitor(envelope: dict, ohlcv: dict) -> dict:
    """Re-price the frozen weekly cards and flag intra-week events. Pure — reads, never mutates."""
    monitors: list[dict] = []
    flags: list[dict] = []
    as_of: pd.Timestamp | None = None

    for sig in envelope.get("signals", []):
        t = sig.get("ticker")
        px = _last_close_open_sma(ohlcv.get(t))
        if px is None:
            continue
        last_close, last_open, sma20, bar_dt = px
        as_of = bar_dt if as_of is None or bar_dt > as_of else as_of
        frozen_price = float(sig.get("current_price") or sig.get("close") or last_close)
        is_held = bool(sig.get("bought_date"))

        rec = {
            "ticker": t,
            "kind": "hold" if is_held else "buy",
            "current_price": round(last_close, 2),
            "frozen_price": round(frozen_price, 2),
            "sma20": round(sma20, 2) if pd.notna(sma20) else None,
            "as_of": str(bar_dt.date()),
        }

        if is_held:
            entry = float(sig.get("entry") or 0.0)
            stop = float(sig.get("stop") or 0.0)
            target = float(sig.get("target") or 0.0)
            pnl_pct = round((last_close / entry - 1) * 100, 2) if entry else None
            dist_stop = round((last_close / stop - 1) * 100, 2) if stop else None
            dist_tgt = round((target / last_close - 1) * 100, 2) if last_close and target else None
            stop_breach = bool(stop and last_close <= stop)
            target_hit = bool(target and last_close >= target)
            rec.update({
                "entry": round(entry, 2), "stop": round(stop, 2), "target": round(target, 2),
                "pnl_pct": pnl_pct, "dist_to_stop_pct": dist_stop, "dist_to_target_pct": dist_tgt,
                "stop_breached": stop_breach, "target_reached": target_hit,
                # informational: where next Saturday's ratchet trail would sit if it recomputed now.
                # NOT an active level — the trail only moves at the weekly close.
                "implied_trail_sma20": round(sma20 * (1 - TRAIL_PCT), 2) if pd.notna(sma20) else None,
            })
            if stop_breach:
                flags.append({"ticker": t, "event": "STOP_BREACH", "severity": "high",
                              "message": f"{t} closed {last_close:.2f} at/under its stop {stop:.2f} — weekly close will confirm the exit"})
            elif target_hit:
                flags.append({"ticker": t, "event": "TARGET_2R", "severity": "info",
                              "message": f"{t} reached +2R target {target:.2f} (last {last_close:.2f}) — sell half is due at the weekly close"})
            elif dist_stop is not None and dist_stop <= NEAR_PCT:
                flags.append({"ticker": t, "event": "NEAR_STOP", "severity": "warn",
                              "message": f"{t} is {dist_stop:.1f}% above its stop {stop:.2f}"})
        else:
            lo = float(sig.get("entry_low") or 0.0)
            hi = float(sig.get("entry_high") or 0.0)
            bw = sig.get("buy_window_until")
            in_range = bool(lo and hi and lo <= last_open <= hi)
            window_open = bool(bw and str(as_of.date()) <= bw) if as_of else None
            expired = bool(bw and str(as_of.date()) > bw) if as_of else False
            rec.update({
                "entry_low": round(lo, 2), "entry_high": round(hi, 2),
                "buy_window_until": bw, "buy_window_open": window_open,
                "filled_today": in_range, "expired": expired,
                "today_open": round(last_open, 2),
            })
            if window_open and in_range:
                flags.append({"ticker": t, "event": "FILLED_TODAY", "severity": "action",
                              "message": f"{t} opened {last_open:.2f} inside the band [{lo:.2f}, {hi:.2f}] — buyable at today's open"})
            elif expired:
                flags.append({"ticker": t, "event": "WINDOW_EXPIRED", "severity": "info",
                              "message": f"{t} buy-window closed {bw} with no in-range open — signal expired, no trade"})
        monitors.append(rec)

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generated_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "as_of": str(as_of.date()) if as_of is not None else None,
        "model": envelope.get("model", "weekly-swing-0094-rank"),
        "source": "signals_today_weekly.json",
        "note": ("OBSERVATIONAL re-pricing of the frozen Saturday weekly signals — live current_price + "
                 "intra-week event flags. Does NOT recompute signals or move any frozen level; the paper "
                 "record is untouched and the weekly decision cadence is unchanged."),
        "n_monitored": len(monitors),
        "n_flags": len(flags),
        "monitors": monitors,
        "flags": flags,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="daily observational monitor for the weekly-swing book")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    ap.add_argument("--no-download", action="store_true", help="use the cache as-is (offline/test)")
    args = ap.parse_args(argv)
    sd = Path(args.state_dir)

    env_path = sd / "signals_today_weekly.json"
    if not env_path.exists():
        print(f"no frozen weekly envelope at {env_path} — nothing to monitor (run the weekly cron first)")
        return 0
    envelope = json.loads(env_path.read_text(encoding="utf-8"))
    tickers = sorted({s.get("ticker") for s in envelope.get("signals", []) if s.get("ticker")})
    if not tickers:
        print("weekly envelope has no signals — nothing to monitor")
        return 0

    ohlcv = _refresh(tickers, not args.no_download)
    monitor = build_monitor(envelope, ohlcv)

    (sd / "weekly_monitor.json").write_text(json.dumps(monitor, indent=2, default=str), encoding="utf-8")
    fired = ", ".join(f"{f['event']}:{f['ticker']}" for f in monitor["flags"]) or "none"
    print(f"weekly monitor: as-of {monitor['as_of']} | {monitor['n_monitored']} cards re-priced | "
          f"{monitor['n_flags']} flags [{fired}] -> {sd / 'weekly_monitor.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
