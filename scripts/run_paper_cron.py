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
        # incremental: refresh recent bars (or full history on a cold cache) and merge
        dl_start = hist_start if not ohlcv else (date.today() - timedelta(days=15)).isoformat()
        print(f"downloading OHLCV {dl_start}..{end} for {len(universe)} names ...", flush=True)
        fresh = download_ohlcv(universe, start=dl_start, end=end)
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
    book.save(args.state_dir)

    # today's BUY signals = the pending names to fill at the next session's open (indicative entry)
    last_day = df[df["date"] == df["date"].max()].set_index("ticker") if not df.empty else None
    signals = []
    for tkr in book.pending:
        if last_day is not None and tkr in last_day.index:
            row = last_day.loc[tkr]
            signals.append({"ticker": tkr, "indicative_close": round(float(row["close"]), 2),
                            "buy_window": "T+1..T+3 at open"})
    Path(args.state_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.state_dir) / "signals_today.json").write_text(
        json.dumps({"as_of": end, "n_positions": len(book.positions), "cash": round(book.cash, 2),
                    "buy_signals": signals, "kill_state": book.kill_flags()}, indent=2, default=str),
        encoding="utf-8")

    nav = book.equity_curve[-1]["equity"] if book.equity_curve else args.initial_capital
    print(f"paper cron: stepped {stepped} session(s) | NAV {nav} | held {len(book.positions)} | "
          f"pending {len(book.pending)} | trades {len(book.trades)} -> {args.state_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
