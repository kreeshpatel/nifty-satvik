"""B-1 IMPACT CENSUS (read-only) — has a held name ever gone bar-less mid-hold?

Constitution bug B-1: ``run_bhanushali_weekly_rank.backtest`` skips ALL exit logic for a held
name that has no bar on the current date (``i is None -> continue``), and the NAV sum marks such
a name at its **entry price** (``… if d in didx[t] else p["en"]``). A holding that suspends or
delists mid-hold therefore (a) can never exit, and (b) is carried at cost regardless of its last
traded price — silently flattering NAV, which the Oct-1 scorecard's Sharpe/MaxDD gates read.

This script QUANTIFIES the exposure to date. It reads only:
  * ``results/signals_history_weekly.json``  (closed + active signal records)
  * ``results/paper_portfolio_weekly.json``  (the ₹10L book's open positions)
  * ``data/ohlcv.pkl``                        (the live cache — bar availability per name)

It does NOT read the forward-wall books/logs, does not run the engine, and changes nothing.

For every position that is/was open, it asks: does the name's bar series END before the book's
as-of date? If so it reports the gap in trading days, the entry mark vs the last traded close,
and the resulting rupee NAV flattery (shares x (entry - last_close)) for still-open cases.

Also reports the same census over the FULL live universe cache: names whose series is stale
while the rest of the universe has advanced (the population B-1 could bite in future).

    python scripts/diag_b1_absent_bar_census.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from config import RESULTS_DIR  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

STALE_SESSIONS_FLAG = 10        # the momentum engine's STALE_ABSENT_DAYS, used here as the yardstick


def _read(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except Exception:
        return default


def census(results_dir: Path, ohlcv: dict) -> dict:
    hist = _read(results_dir / "signals_history_weekly.json", [])
    port = _read(results_dir / "paper_portfolio_weekly.json", {})
    env = _read(results_dir / "signals_today_weekly.json", {})
    as_of = env.get("generated_at")

    last_bar: dict[str, pd.Timestamp] = {}
    last_close: dict[str, float] = {}
    for t, df in (ohlcv or {}).items():
        if df is None or len(df) == 0 or "Close" not in df.columns:
            continue
        last_bar[t] = pd.Timestamp(df.index[-1])
        try:
            last_close[t] = float(df["Close"].iloc[-1])
        except Exception:
            pass

    # universe-wide freshness reference: the newest bar anywhere in the cache
    universe_last = max(last_bar.values()) if last_bar else None

    def _stale_days(t: str) -> int | None:
        lb = last_bar.get(t)
        if lb is None or universe_last is None:
            return None
        return int(len(pd.bdate_range(lb, universe_last)) - 1)

    # ── 1. positions the book currently holds (the live NAV exposure) ──
    open_rows = []
    for t, p in (port.get("positions") or {}).items():
        sd = _stale_days(t)
        entry = float(p.get("entry_price") or 0.0)
        shares = float(p.get("shares") or 0.0)
        lc = last_close.get(t)
        row = {
            "ticker": t, "entry_date": p.get("entry_date"), "entry_price": round(entry, 2),
            "shares": round(shares, 4), "book_current_price": p.get("current_price"),
            "cache_last_bar": str(last_bar[t].date()) if t in last_bar else None,
            "cache_last_close": None if lc is None else round(lc, 2),
            "stale_sessions": sd, "in_cache": t in last_bar,
        }
        if sd is not None and sd > 0 and lc is not None:
            row["nav_flattery_rs"] = round(shares * (entry - lc), 2)
            row["nav_flattery_pct_of_position"] = (
                round((entry - lc) / entry * 100, 2) if entry else None)
        open_rows.append(row)

    # ── 2. every name that ever appeared in the signal history (closed round-trips too) ──
    hist_rows = []
    for h in hist if isinstance(hist, list) else []:
        t = h.get("ticker")
        if not t:
            continue
        sd = _stale_days(t)
        if t not in last_bar:
            hist_rows.append({"ticker": t, "status": h.get("status"),
                              "signal_date": h.get("signal_date"),
                              "close_date": h.get("close_date"),
                              "issue": "absent from the live OHLCV cache entirely",
                              "stale_sessions": None})
        elif sd is not None and sd >= STALE_SESSIONS_FLAG:
            hist_rows.append({"ticker": t, "status": h.get("status"),
                              "signal_date": h.get("signal_date"),
                              "close_date": h.get("close_date"),
                              "issue": f"series ends {sd} sessions before the universe",
                              "stale_sessions": sd})

    # ── 3. the population at risk: stale names anywhere in the live cache ──
    pop = []
    for t in sorted(last_bar):
        sd = _stale_days(t)
        if sd is not None and sd >= STALE_SESSIONS_FLAG:
            pop.append({"ticker": t, "last_bar": str(last_bar[t].date()), "stale_sessions": sd})

    affected_open = [r for r in open_rows if (r.get("stale_sessions") or 0) > 0 or not r["in_cache"]]
    total_flattery = round(sum(r.get("nav_flattery_rs", 0.0) for r in affected_open), 2)

    return {
        "book_as_of": as_of,
        "universe_last_bar": str(universe_last.date()) if universe_last is not None else None,
        "stale_yardstick_sessions": STALE_SESSIONS_FLAG,
        "n_open_positions": len(open_rows),
        "n_open_positions_affected": len(affected_open),
        "nav_flattery_rs_total": total_flattery,
        "book_nav": port.get("total_value"),
        "nav_flattery_pct_of_nav": (
            round(total_flattery / float(port["total_value"]) * 100, 4)
            if port.get("total_value") else None),
        "open_positions": open_rows,
        "history_names_flagged": hist_rows,
        "n_history_names_flagged": len(hist_rows),
        "universe_stale_names": pop,
        "n_universe_stale_names": len(pop),
        "n_universe_names": len(last_bar),
        "verdict": ("NO INSTANCE TO DATE" if not affected_open and not hist_rows
                    else "INSTANCES FOUND — see rows"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="B-1 absent-bar impact census (read-only)")
    ap.add_argument("--results-dir", default=str(RESULTS_DIR))
    ap.add_argument("--json", default=str(ROOT / "diagnostics" / "research" / "b1_absent_bar_census.json"))
    args = ap.parse_args(argv)

    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    rep = census(Path(args.results_dir), ohlcv)

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, default=str) + "\n", encoding="utf-8")

    print("=== B-1 absent-bar census (read-only) ===")
    print(f"book as-of {rep['book_as_of']} | universe last bar {rep['universe_last_bar']} | "
          f"{rep['n_universe_names']} cached names")
    print(f"open positions: {rep['n_open_positions']} | affected: {rep['n_open_positions_affected']}")
    print(f"NAV flattery to date: Rs {rep['nav_flattery_rs_total']:,.2f} "
          f"({rep['nav_flattery_pct_of_nav']}% of NAV {rep['book_nav']})")
    print(f"history names flagged: {rep['n_history_names_flagged']}")
    print(f"universe names stale >= {STALE_SESSIONS_FLAG} sessions: {rep['n_universe_stale_names']}")
    print(f"VERDICT: {rep['verdict']}")
    for r in rep["open_positions"]:
        print(f"  {r['ticker']:<12} entry {r['entry_price']:>10} | last bar {r['cache_last_bar']} "
              f"| stale {r['stale_sessions']} | flattery Rs {r.get('nav_flattery_rs', 0.0)}")
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
