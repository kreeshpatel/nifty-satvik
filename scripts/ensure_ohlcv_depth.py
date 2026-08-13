#!/usr/bin/env python3
"""Deepen the OHLCV cache head so the forward wall's veto arm can regress.

Why this exists
---------------
The veto-0.1 arm regresses each name's returns on the FF-India factors over a trailing window
(`nq.research.residual`: REG_WIN 252 + SKIP 21 + 5 = **278 joined bars** per name before the first
score). The factor panel is built from the live OHLCV cache. But the daily paper cron only tops up
the **last ~15 days** on a warm cache (`run_paper_cron.py`: `dl_start = ... if not ohlcv else
today-15`), so on the CI runner the cache never deepens past its original ~520-day warmup. The
factor panel then spans <278 sessions, `residual_ranks` returns zero rows, `pd.concat([])` raises
"No objects to concatenate", and the wall SKIPS its row — the contracted `results/forward_wall.csv`
never appears and the commit guard goes RED.

This script deepens the cache HEAD to ``--start`` when it does not already reach that far, then the
factor build has enough history for the regression. It is GATED on the cache's earliest date, so it
does a full deep fetch at most once per monthly ``actions/cache`` key roll (a uniformly shallow
runner cache), and is a no-op on a cache that already runs deep (a local dev machine). It never
touches the RECENT tail — the paper cron owns that — so the base book of record is unaffected.

Idempotent: merge_ohlcv unions on the date index; re-running with the same ``--start`` changes
nothing once the cache reaches back that far.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nq.data.ohlcv import (OHLCV_CACHE, download_ohlcv, load_ohlcv_cache,  # noqa: E402
                           merge_ohlcv, save_ohlcv_cache)
from scripts.run_cpcv import build_universe  # noqa: E402


def _earliest(ohlcv: dict[str, pd.DataFrame]) -> pd.Timestamp | None:
    """The earliest date ANY name carries — i.e. how far back the cache reaches at all.

    min-over-names (not max) on purpose: a deep cache that has just added one freshly-listed name
    still reaches back via its long-lived names, so this stays a no-op there. A uniformly shallow
    runner cache (every name downloaded from the same warmup start) reports that shallow start and
    triggers the deepen.
    """
    mins = [df.index.min() for df in ohlcv.values() if len(df.index)]
    return min(mins) if mins else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deepen the OHLCV cache head for the wall's veto arm")
    ap.add_argument("--start", required=True, help="target earliest date YYYY-MM-DD the cache must reach")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--cache", default=None, help="OHLCV pickle cache path (default data/ohlcv.pkl)")
    ap.add_argument("--end", default=None, help="deep-fetch end (default: today)")
    args = ap.parse_args(argv)

    cache = Path(args.cache) if args.cache else OHLCV_CACHE
    target = pd.to_datetime(args.start)
    ohlcv = load_ohlcv_cache(cache)
    have = _earliest(ohlcv)

    if have is not None and have <= target:
        print(f"ohlcv-depth: cache already reaches {have.date()} <= {target.date()}; no deep fetch", flush=True)
        return 0

    universe = build_universe(args.mode)
    end = args.end or date.today().isoformat()
    print(f"ohlcv-depth: cache earliest {have.date() if have is not None else 'EMPTY'} > {target.date()}; "
          f"deep-fetching {args.start}..{end} for {len(universe)} names ...", flush=True)
    fresh = download_ohlcv(universe, start=args.start, end=end)
    merged = merge_ohlcv(ohlcv, fresh) if ohlcv else fresh
    save_ohlcv_cache(merged, cache)
    now = _earliest(merged)
    print(f"ohlcv-depth: cache earliest now {now.date() if now is not None else 'EMPTY'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
