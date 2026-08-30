#!/usr/bin/env python3
"""Fail the forward-wall job when the wall did not gain a row though sessions have closed.

WHY THIS EXISTS. `cron-forward-wall` already refuses to publish a run whose contracted artifacts are
MISSING ("the commit diff is the receipt — a green workflow that persisted nothing is red here").
It cannot see the other failure: every artifact present, unchanged, and a commit message announcing
a daily log that was never written.

That is what happened. Five scheduled runs, 2026-08-24 through 2026-08-28, each finished green,
printed `forward-wall: start 2026-08-12 | appended 0 row(s)`, and committed
"chore(wall): forward-wall daily log <date>" while `results/forward_wall.csv` still ended at
2026-08-21. The cause was upstream — `run_paper_cron` took the `min_bars` default on a 15-day
top-up, so the OHLCV cache never advanced (fixed in that script, and now checked at every call site
by `check_ohlcv_topup_contract.py`). The point of THIS file is that the cause does not matter: any
future reason the wall stops must stop the job too.

`forward/prereg.md` §3 registers the wall as a forward record, and the rows are hash-chained so a
later reader can trust that what was logged is what was known. A silent five-session hole is the one
thing that record cannot survive, because nothing downstream can tell a gap from a quiet market.

The doctrine is the repo's own, from `nq/paper/wall_cron._assert_veto_arm_live`: "A wall that stops
is a wall you fix; a wall that agrees with itself is a wall you believe." Refusing costs a re-run.

DELIBERATELY NOT FATAL ON: a same-day re-run or a holiday (no session has closed since the last row,
so there is nothing to advance to), and a cold start with no wall file yet. `--allow-stale` forces a
deliberate offline replay, matching `run_bhanushali_cron`'s flag of the same name.

    run with: python scripts/assert_wall_advanced.py [--state-dir results] [--allow-stale]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from config import NSE_HOLIDAYS, RESULTS_DIR, assert_calendar_covers  # noqa: E402


class WallStalledError(RuntimeError):
    """The wall gained no row although at least one NSE session has closed since its last."""


def sessions_after(day: str, upto: str) -> int:
    """NSE sessions strictly after ``day`` and up to ``upto``. Weekend- and holiday-aware."""
    lo, hi = pd.Timestamp(day), pd.Timestamp(upto)
    if hi <= lo:
        return 0
    hol = set(NSE_HOLIDAYS)
    return sum(1 for d in pd.bdate_range(lo + pd.Timedelta(days=1), hi)
               if d.date().isoformat() not in hol)


def last_wall_date(path: Path) -> str | None:
    """The date of the wall's last logged row, or None if there is no wall yet."""
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.reader(fh) if r and r[0][:1].isdigit()]
    return rows[-1][0][:10] if rows else None


def check(state_dir: Path, today: str, *, allow_stale: bool = False) -> str:
    """Return a one-line OK message, or raise WallStalledError."""
    wall = Path(state_dir) / "forward_wall.csv"
    last = last_wall_date(wall)
    if last is None:
        return f"no wall rows yet at {wall} — cold start, nothing to advance from"
    # Only the upper bound matters and only the calendar can answer it; past its coverage the
    # session count would be a guess, and this file exists to stop guesses being published.
    assert_calendar_covers(today, what="the forward-wall staleness check")
    elapsed = sessions_after(last, today)
    if elapsed <= 0:
        return f"wall at {last}; no NSE session has closed since — nothing to advance to"
    if allow_stale:
        return f"wall at {last}; {elapsed} session(s) elapsed — STALE, allowed by --allow-stale"
    raise WallStalledError(
        f"WALL DID NOT ADVANCE. results/forward_wall.csv still ends at {last}, but {elapsed} NSE "
        f"session(s) have closed since.\n"
        "Do NOT publish this run: it would commit a message naming a daily log it did not write, "
        "into a hash-chained record that forward/prereg.md SS3 registers as forward evidence.\n"
        "First suspect the OHLCV cache not advancing (nq.data.ohlcv.download_ohlcv drops names "
        "under `min_bars`; a top-up must pass min_bars=1 — "
        "`python scripts/check_ohlcv_topup_contract.py` checks every call site).\n"
        "Then check that data/ff_india_factors.parquet reaches the sessions being logged: past its "
        "last date the veto arm has no residual ranks and nq.paper.wall_cron refuses to log.\n"
        "--allow-stale forces a deliberate offline replay.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    ap.add_argument("--today", default=None, help="override today (tests/replay); default: today")
    ap.add_argument("--allow-stale", action="store_true", help="deliberate offline replay")
    args = ap.parse_args(argv)
    today = args.today or str(pd.Timestamp.today().date())
    try:
        print(f"wall freshness: {check(Path(args.state_dir), today, allow_stale=args.allow_stale)}")
    except WallStalledError as exc:
        print(f"::error::{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
