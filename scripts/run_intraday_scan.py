"""Intraday 14:30-IST SHADOW scan (cron job #2) — see the same-day trend before the close.

What it does, every trading day at ~14:30 IST:
  1. Downloads ~2y daily OHLCV for current PIT Nifty-500 members (+ ^NSEI). At 14:30 the latest bar is
     TODAY'S PARTIAL candle (open/high/low/last so far + volume so far).
  2. Rebuilds this week's frozen top-50 practitioner watchlist from COMPLETED bars only (strictly before
     this ISO week's first session — identical PIT semantics to the backtest).
  3. Checks each watchlist name's FORMING setup on the partial candle: touch-and-hold of the rising
     44-SMA, currently green with the last price in the upper half of today's range, and volume PACE
     >= 1.5x the 20d average (volume-so-far scaled by elapsed session fraction).
  4. Emits results/intraday_scan/YYYY-MM-DD.json: regime state, watchlist, forming setups with their
     would-be trigger (today's high so far x1.001) and would-be 4xATR stop. OBSERVATIONAL ONLY.
  5. Appends to results/intraday_scan/confirmation_log.csv: for YESTERDAY's forming list, did the
     completed candle confirm the signal by the close? This accrues the partial->final SURVIVAL RATE —
     the statistic that decides whether same-day entries are ever proposed as a real (pre-registered)
     trial. Until then, nothing here touches the paper book, the wall log, or any traded state.

Honesty notes (why this is a shadow, not a buying job):
  - Every backtest in the 0022-0025 arc validated signals on COMPLETED candles. A 14:30 signal can
    un-form by 15:30 (candle turns red / volume pace fades) — same-day buying is therefore an UNTESTED
    entry timing, not a faster version of the tested one.
  - The volume-pace scaling (elapsed fraction of the 09:15-15:30 session) is an assumption; it is
    recorded in every JSON so the survival stats can be re-based later if needed.
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from run_bhanushali_practitioner import build_watchlist, prep  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
OUTDIR = ROOT / "results" / "intraday_scan"
SESSION_MIN = (15 * 60 + 30) - (9 * 60 + 15)                     # 375 trading minutes


def session_fraction(now_ist: datetime) -> float:
    mins = (now_ist.hour * 60 + now_ist.minute) - (9 * 60 + 15)
    return float(np.clip(mins / SESSION_MIN, 0.05, 1.0))


def main() -> int:
    import yfinance as yf
    now = datetime.now(IST)
    today = pd.Timestamp(now.date())
    mem = load_membership()
    universe = sorted(t for t in mem if ticker_in_index_on(t, now.date(), mem))
    print(f"intraday scan {now:%Y-%m-%d %H:%M} IST | universe {len(universe)}", flush=True)

    start = (today - pd.Timedelta(days=750)).date().isoformat()
    raw = yf.download([t + ".NS" for t in universe] + ["^NSEI"], start=start, progress=False,
                      group_by="ticker", auto_adjust=True, threads=True)
    frames, partial = {}, {}
    for t in universe:
        try:
            df = raw[t + ".NS"].dropna(how="all")
        except Exception:
            continue
        if len(df) < 320:
            continue
        if df.index[-1].normalize() == today:                     # split off today's PARTIAL bar
            partial[t] = df.iloc[-1]
            df = df.iloc[:-1]
        frames[t] = df[["Open", "High", "Low", "Close", "Volume"]]
    if not partial:
        print("no partial bar for today (holiday / pre-open / data lag) — nothing to scan")
        return 0

    P = prep(frames)                                              # indicators from COMPLETED bars only
    # regime: NIFTY above its rising 44-SMA (completed bars)
    nse = raw["^NSEI"].dropna(how="all")["Close"]
    nse = nse[nse.index.normalize() < today]
    nsma = nse.rolling(44).mean()
    regime_ok = bool(nse.iloc[-1] > nsma.iloc[-1] and nsma.iloc[-1] > nsma.iloc[-11])

    # this week's frozen watchlist: data strictly before the ISO week's first session
    week_first = today - pd.Timedelta(days=now.weekday())
    prev_i = {}
    for t, s in P.items():
        j = s["dates"].searchsorted(week_first) - 1
        if j >= 0:
            prev_i[t] = j
    watch = build_watchlist(P, mem, now.date(), prev_i)

    frac = session_fraction(now)
    forming = []
    for rank, t in enumerate(watch):
        if t not in partial or t not in P:
            continue
        s, b = P[t], partial[t]
        i = len(s["c"]) - 1                                       # last completed bar
        dsma, atr = s["dsma"][i], s["atr"][i]
        if not np.isfinite(dsma) or not s["strong"][i]:
            continue
        o_, h_, l_, last, v = float(b["Open"]), float(b["High"]), float(b["Low"]), float(b["Close"]), float(b["Volume"])
        rng = h_ - l_
        cond = dict(
            touch_hold_44sma=bool(l_ <= dsma * 1.02 and last >= dsma),
            green_upper_half=bool(last > o_ and rng > 0 and (last - l_) >= 0.5 * rng),
            vol_pace=round(v / max(frac * s_vavg20(frames[t]), 1.0), 2),
        )
        cond["hvc_pace_ok"] = cond["vol_pace"] >= 1.5
        if cond["touch_hold_44sma"] and cond["green_upper_half"] and cond["hvc_pace_ok"]:
            forming.append(dict(
                ticker=t, rank=rank, last=round(last, 2), dist_to_44sma_pct=round((last / dsma - 1) * 100, 2),
                slope66_pct=round(s["slope66"][i] * 100, 1), atr_pct=round(atr / last * 100, 2),
                would_be_trigger=round(h_ * 1.001, 2), would_be_stop_4atr=round(last - 4 * atr, 2),
                conditions=cond))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = dict(generated_utc=datetime.now(timezone.utc).isoformat(), ist=f"{now:%Y-%m-%d %H:%M}",
               session_fraction=round(frac, 3), regime_ok=regime_ok, n_watchlist=len(watch),
               watchlist=watch, n_forming=len(forming), forming=forming,
               caveats=dict(shadow_only=True, partial_candle=True,
                            volume_pace_scaling="volume_so_far / (elapsed_session_fraction * 20d_avg)"))
    (OUTDIR / f"{today.date()}.json").write_text(json.dumps(out, indent=1))
    print(f"regime {'OK' if regime_ok else 'OFF'} | watchlist {len(watch)} | forming setups {len(forming)}"
          f" -> results/intraday_scan/{today.date()}.json")

    # confirmation follow-up: did yesterday's forming signals survive to the completed close?
    _confirm(P, today)
    return 0


def s_vavg20(df: pd.DataFrame) -> float:
    return float(df["Volume"].tail(20).mean())


def _confirm(P, today) -> None:
    files = sorted(OUTDIR.glob("2*.json"))
    prev = [f for f in files if f.stem < str(today.date())]
    if not prev:
        return
    last = json.loads(prev[-1].read_text())
    rows = []
    for f_ in last.get("forming", []):
        t = f_["ticker"]
        if t not in P:
            continue
        s = P[t]
        j = s["dates"].searchsorted(pd.Timestamp(last["ist"][:10]))
        if j >= len(s["dates"]) or s["dates"][j] != pd.Timestamp(last["ist"][:10]):
            continue
        confirmed = bool(s["strong"][j] and s["hold44"][j] and s["qgreen"][j] and s["hvc"][j])
        rows.append(dict(scan_date=last["ist"][:10], ticker=t, confirmed_at_close=confirmed))
    if rows:
        log = OUTDIR / "confirmation_log.csv"
        df = pd.DataFrame(rows)
        df.to_csv(log, mode="a", header=not log.exists(), index=False)
        full = pd.read_csv(log)
        print(f"confirmation log: +{len(df)} rows | lifetime partial->close survival "
              f"{full['confirmed_at_close'].mean()*100:.0f}% over {len(full)} signals")


if __name__ == "__main__":
    raise SystemExit(main())
