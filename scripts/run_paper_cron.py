"""Stage-E block 3 — the daily paper-trading cron.

One session per run: refresh OHLCV incrementally → build today's ranked panel → step the persistent
PaperBook forward for any new sessions since its last step → save state + today's BUY signals. The book
tracks FORWARD from an inception date (it does NOT replay the backtest); it accumulates the ≥30 paper
trades that gate Stage F (live). Live ≡ backtest by construction (PaperBook reuses the engine kernels;
parity-gated). The vol-target (O-009) is read from config.json → live_overlays.

    python scripts/run_paper_cron.py --start 2026-05-30                 # daily (downloads recent bars)
    python scripts/run_paper_cron.py --start 2026-05-30 --cache data/ohlcv.pkl --no-download   # test/offline
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import RESULTS_DIR, load_frozen_cfg  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from scripts.run_cpcv import build_universe  # noqa: E402

CONFIG_JSON = ROOT / "models" / "long_horizon" / "config.json"


def _live_vol_target() -> dict | None:
    """The O-009 vol-target from config.json → live_overlays (None if disabled)."""
    try:
        lo = json.loads(CONFIG_JSON.read_text(encoding="utf-8")).get("live_overlays", {})
        return lo if float(lo.get("vol_target_annual", 0.0)) > 0 else None
    except Exception:
        return None


# ── forward-wall registered start (S-F1) ─────────────────────────────────────
# The wall may not begin before its own pre-registration existed. `forward/prereg.md` was registered
# 2026-07-02; any anchor earlier than that is a bug, not a start date.
WALL_PREREG_DATE = "2026-07-02"


def _wall_gap_report(state_dir: Path, book, *, wall_start: str | None) -> list[str]:
    """The sessions this run will mark as `gap` rather than log — the stall, made visible.

    `forward/prereg.md` SS3 rule 4 is what decides their fate: "a missed day is a gap, never
    reconstructed." `wall_cron.update_wall` enforces it structurally — only the most recent session
    becomes an `ok` row and the ones before it become hash-chained gaps — so nothing here can change
    the outcome. This exists so the outcome is not silent.

    That matters because the stall it was written for WAS silent: five runs (2026-08-24 .. 08-28)
    printed "appended 0 row(s)" and committed a daily-log message, and nothing in the run log said a
    session had been lost. A gap is the honest record, but a gap nobody is told about is still a
    surprise for whoever reads the wall next.
    """
    from nq.paper.forward_wall import _load
    existing = _load(state_dir / "forward_wall.csv")
    if not existing or not book.equity_curve:
        return []                                # cold wall: `wall_start` is the bound that applies
    last_wall = existing[-1]["date"]
    todo = [str(e["date"])[:10] for e in book.equity_curve
            if str(e["date"])[:10] > last_wall
            and (wall_start is None or str(e["date"])[:10] >= str(wall_start)[:10])]
    return todo[:-1]                             # the last one is logged; the rest are the gap


def _wall_start(state_dir: str | Path, last_session: str) -> str:
    """The wall's REGISTERED START — read from `<state_dir>/forward_wall_start.json`, written once.

    The paper book steps from its own inception, so a cold start already holds months of sessions in
    its equity curve. Logging those would enter recomputed history into the wall as `ok` rows that
    pass the hash chain (dates strictly increase) and misstate when they were known. So the wall
    starts on the day it first actually runs: the anchor is written once, committed, and read back
    by every later run.

    **The path is STATE-DIR-RELATIVE on purpose.** An earlier version anchored it to the repo root,
    and the test suite promptly wrote one: `tests/test_stagee_paper_cron.py` runs the cron against a
    2016 fixture, so the repo acquired an anchor of `2016-12-30`. Committed, that would have left the
    bound silently inert — every real session is after 2016, so nothing would ever have been skipped
    and the first live run would have backfilled the whole wall anyway. A guard that a test can write
    is not a guard, hence both the relocation and the sanity floor below.
    """
    f = Path(state_dir) / "forward_wall_start.json"
    if f.exists():
        return str(json.loads(f.read_text(encoding="utf-8"))["wall_start"])[:10]
    if last_session < WALL_PREREG_DATE:
        raise ValueError(
            f"refusing to anchor the forward wall at {last_session}, which predates its own "
            f"pre-registration ({WALL_PREREG_DATE}). This is a fixture or a stale cache, not a "
            f"start date — see forward/prereg.md §3.")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({
        "wall_start": last_session,
        "registered": "written by the first run of scripts/run_paper_cron.py that reached the wall",
        "why": "forward/prereg.md §3 — no session before this date may enter the wall as an `ok` "
               "row; the paper book's pre-existing curve is recomputed history, not forward "
               "evidence. Append-only: never edit this file.",
    }, indent=1) + "\n", encoding="utf-8")
    return last_session


# ── signal memory ────────────────────────────────────────────────────────────
# pending is re-selected at every session close, so stamping `end` on every run
# made a continuing signal look brand-new each day: its issue date walked forward,
# status stayed FRESH, and the T+1..T+3 buy window never closed on the dashboard.
# Instead, carry the ORIGINAL issue date for a name still pending from a prior run;
# a carried signal older than its buy window is re-issued fresh (the book
# re-selected it at the latest close — a new entry episode).

BUY_WINDOW_TRADING_DAYS = 3


def _load_prev_signal_dates(state_dir: str | Path) -> dict[str, str]:
    """ticker → signal_date from the previous run's signals_today.json ({} if none)."""
    try:
        prev = json.loads((Path(state_dir) / "signals_today.json").read_text(encoding="utf-8"))
        sigs = prev.get("signals", []) if isinstance(prev, dict) else (prev or [])
        return {str(s["ticker"]): str(s["signal_date"])
                for s in sigs if s.get("ticker") and s.get("signal_date")}
    except Exception:
        return {}


def _issue_date(prev_dates: dict[str, str], tkr: str, end: str,
                window: int = BUY_WINDOW_TRADING_DAYS) -> str:
    """Issue date for a pending signal: carried from the prior run while its buy
    window is open, else today (`end`)."""
    issued = prev_dates.get(tkr, end)
    if issued == end:
        return end
    import pandas as pd
    try:
        age_bdays = max(0, len(pd.bdate_range(issued, end)) - 1)
    except Exception:
        return end
    return end if age_bdays > window else issued


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Daily paper-trading cron (PaperBook step)")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="current")
    ap.add_argument("--start", required=True, help="paper inception date YYYY-MM-DD (book trades from here)")
    ap.add_argument("--end", default=None, help="default: today")
    ap.add_argument("--cache", default=None, help="OHLCV pickle cache path (default data/ohlcv.pkl)")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR), help="where paper state persists")
    ap.add_argument("--initial-capital", type=float, default=1_000_000.0)
    ap.add_argument("--no-download", action="store_true", help="use the cache as-is (test/offline)")
    ap.add_argument("--history-days", type=int, default=520, help="calendar days of history before inception for warmup")
    ap.add_argument("--allow-wall-backfill", action="store_true",
                    help="log every missed session as an `ok` row instead of a `gap` marker. "
                         "forward/prereg.md SS3 rule 4 says a missed day is a gap, never "
                         "reconstructed — this overrides that, and is an owner decision")
    args = ap.parse_args(argv)

    import pandas as pd

    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import (OHLCV_CACHE, download_ohlcv, load_ohlcv_cache, merge_ohlcv,
                               save_ohlcv_cache)
    from nq.engine.panel import compose_ranked_panel
    from nq.paper.book import PaperBook

    cfg = load_frozen_cfg()
    universe = build_universe(args.mode)
    end = args.end or date.today().isoformat()
    cache = Path(args.cache) if args.cache else OHLCV_CACHE
    hist_start = (pd.to_datetime(args.start) - pd.Timedelta(days=args.history_days)).date().isoformat()

    ohlcv = load_ohlcv_cache(cache)
    if not args.no_download:
        # Cold cache -> full history. Warm cache -> a 15-day top-up. The two need DIFFERENT
        # `min_bars`, and that is the whole point of splitting them.
        #
        # `download_ohlcv` drops any name returning fewer than `min_bars` usable bars. The default
        # of 50 is right for the full pull, where a name with a handful of bars cannot warm up the
        # features. It is fatal for the top-up: 15 calendar days is ~11 sessions, so EVERY name is
        # discarded, `merge_ohlcv` folds an empty dict into the cache, and the job prints a success
        # line over data that did not move.
        #
        # That is exactly what froze the forward wall. Five green runs, 2026-08-24 to 2026-08-28,
        # each downloaded nothing, left the cache at 2026-08-21, rebuilt a byte-identical factor
        # panel (619 days, 2024-02-15..2026-08-21) and appended 0 rows to results/forward_wall.csv
        # — while committing "chore(wall): forward-wall daily log 2026-08-28". A pre-registered
        # forward record (forward/prereg.md §3) lost five sessions and reported success.
        #
        # The failure was already known and already written down: nq.data.ohlcv.download_ohlcv's
        # docstring ends "Callers doing a top-up must pass ``min_bars=1``", after the same bug held
        # the live swing book at 2026-07-31 through a successful 2026-08-10 run. That fix updated
        # one caller. The test that guarded it asserted a literal line of that one file, so this
        # caller could — and did — repeat the defect with the guard green. tests/test_ohlcv_topup.py
        # now checks the contract at every call site instead.
        if not ohlcv:
            print(f"downloading OHLCV {hist_start}..{end} for {len(universe)} names "
                  f"(full history) ...", flush=True)
            fresh = download_ohlcv(universe, start=hist_start, end=end)
        else:
            topup_start = (date.today() - timedelta(days=15)).isoformat()
            print(f"downloading OHLCV {topup_start}..{end} for {len(universe)} names "
                  f"(top-up) ...", flush=True)
            fresh = download_ohlcv(universe, start=topup_start, end=end, min_bars=1)
        # A top-up that comes back empty is the signature of the bug above, not a quiet no-op:
        # a weekday run after a session always has bars to fetch. Say so rather than composing a
        # panel from an unchanged cache and letting the wall report "appended 0 row(s)".
        if ohlcv and not fresh:
            print(f"::warning::OHLCV top-up returned 0 of {len(universe)} names through {end} "
                  f"— the cache did not advance; downstream panel/wall will not move", flush=True)
        ohlcv = merge_ohlcv(ohlcv, fresh) if ohlcv else fresh
        save_ohlcv_cache(ohlcv, cache)
    if not ohlcv:
        print("ERROR: no OHLCV (empty cache and --no-download)", flush=True)
        return 1

    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1

    book = PaperBook(cfg, initial_capital=args.initial_capital, vol_target=_live_vol_target())
    book.load(args.state_dir)
    last = pd.to_datetime(book.equity_curve[-1]["date"]) if book.equity_curve else None
    inception = pd.to_datetime(args.start)

    df = panel.copy(); df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= inception) & (df["date"] <= pd.to_datetime(end))]
    stepped = 0
    for d, g in df.groupby("date", sort=True):
        if last is not None and d <= last:
            continue                                    # already processed this session
        book.step(d, g.set_index("ticker"))
        stepped += 1

    # Refresh each held position's mark to the LATEST session close for a live MTM display.
    # step() leaves a position filled on the last session marked at its ENTRY (it skips the
    # fill-day close-mark so it doesn't age/exit on the fill day), so per-position P&L would read
    # 0 until the next session. Mark to the latest close so the dashboard's position P&L agrees
    # with the NAV. Display-only: the equity curve already marks to close via _mark, so this never
    # touches the parity-gated step()/simulate() path.
    last_day = df[df["date"] == df["date"].max()].set_index("ticker") if not df.empty else None
    if last_day is not None:
        for _tkr, _p in book.positions.items():
            if _tkr in last_day.index:
                _p.last_mark = float(last_day.loc[_tkr, "close"])
    book.save(args.state_dir)

    # forward-wall (forward/prereg.md §3): append the atomic 3-book (base/veto-0.1/drift) hash-chained
    # row for the newly-stepped sessions. Isolated + non-fatal so a wall error never breaks the paper job.
    try:
        from nq.paper.wall_cron import update_wall
        ws = (_wall_start(args.state_dir, str(book.equity_curve[-1]["date"])[:10])
              if book.equity_curve else None)
        gapped = _wall_gap_report(Path(args.state_dir), book, wall_start=ws)
        if gapped and not args.allow_wall_backfill:
            print(f"::warning::forward-wall: {len(gapped)} missed session(s) "
                  f"({gapped[0]} .. {gapped[-1]}) will be logged as `gap`, not reconstructed "
                  f"(forward/prereg.md SS3 rule 4). --allow-wall-backfill overrides.", flush=True)
        wrote = update_wall(book, panel, cfg, state_dir=args.state_dir,
                            vol_target=_live_vol_target(), wall_start=ws,
                            backfill=args.allow_wall_backfill)
        print(f"forward-wall: start {ws} | appended {wrote} row(s) "
              f"-> {args.state_dir}/forward_wall.csv", flush=True)
    except Exception as exc:  # noqa: BLE001 -- the wall must never break the paper cron
        print(f"forward-wall: SKIPPED ({type(exc).__name__}: {exc})", flush=True)

    # today's BUY signals = the pending names to fill at the next session's open (indicative entry/
    # stop/target). signals_today.json uses the niftyquant backend's envelope shape.
    from nq.engine.portfolio import leg_slippage
    hold_days = int(cfg["max_hold_days"]); target_pct = float(cfg["target_pct"])
    prev_dates = _load_prev_signal_dates(args.state_dir)   # signal memory (see helpers above)
    signals = []
    for tkr in book.pending:
        if last_day is not None and tkr in last_day.index:
            row = last_day.loc[tkr]
            close = float(row["close"]); atr = float(row.get("atr_pct_63", 0) or 0)
            entry = round(close * (1 + leg_slippage(float(row.get("adv_rupees_20d", 0) or 0))), 2)
            stop = round(entry * (1 - float(cfg["stop_atr_mult"]) * atr / 100.0), 2) if atr > 0 else None
            # field names match the frontend contract (SignalsV3.enrichSignal + SignalCard):
            # entry/stop/target/current_price drive the numbers; tier/grade/signal_date/hold_days
            # drive the chips. indicative_* kept as legacy aliases.
            issued = _issue_date(prev_dates, tkr, end)
            signals.append({
                "ticker": tkr, "entry": entry, "stop": stop,
                "target": round(entry * (1 + target_pct / 100.0), 2), "target_pct": round(target_pct, 2),
                "current_price": round(close, 2), "close": round(close, 2),
                "signal_date": issued, "hold_days": hold_days, "grade": "B", "tier": "signal",
                "status": "FRESH" if issued == end else "ACTIVE",
                "buy_window": "T+1..T+3 at open",
                "indicative_close": round(close, 2), "indicative_entry": entry,
            })
    Path(args.state_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.state_dir) / "signals_today.json").write_text(json.dumps({
        "generated_at": end, "signals": signals,
        "regime": {"status": "UNKNOWN", "strength": 0, "vix": 0, "breadth": 0},
        "n_positions": len(book.positions), "cash": round(book.cash, 2),
        "kill_state": book.kill_flags(),
    }, indent=2, default=str), encoding="utf-8")

    nav = book.equity_curve[-1]["equity"] if book.equity_curve else args.initial_capital
    print(f"paper cron: stepped {stepped} session(s) | NAV {nav} | held {len(book.positions)} | "
          f"pending {len(book.pending)} | trades {len(book.trades)} -> {args.state_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
