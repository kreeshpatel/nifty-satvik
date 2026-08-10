"""Build the point-in-time equity F&O membership panel from NSE bhavcopies.

The intraday store is scoped to the F&O universe (the reset rationale in
`diagnostics/research/n_trials.json`), because F&O membership is the liquidity screen the exchange
itself maintains. That list did not exist here: `harvest_fo_bhavcopy.py` keeps only the NIFTY
index-option rows and discards every single-stock row.

This walks the same bhavcopies through `nq.data.fo_universe.parse_fo_members` and accumulates a
DATED (date, symbol) panel to `data/fo_membership.parquet`. Dated is the whole point — names enter
and leave the segment on exchange review, and a universe pinned to today's list silently deletes
every leaver.

Restartable: dates already in the parquet are skipped, so an interrupted run resumes. It shares the
downloader with the OI harvester (`nq.data.nse_bhavcopy`), so a NSE path change is fixed once.

    python pipelines/build/build_fo_universe.py                    # 2017-01-01 .. today
    python pipelines/build/build_fo_universe.py --start 2024-01-01
    python pipelines/build/build_fo_universe.py --report           # summarise what exists, no fetch
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.fo_universe import build_membership, members_on, membership_spans  # noqa: E402
from nq.data.nse_bhavcopy import fetch_for_date  # noqa: E402

OUT = ROOT / "data" / "fo_membership.parquet"
CHECKPOINT_EVERY = 100


def _report(panel: pd.DataFrame) -> int:
    if not len(panel):
        print(f"{OUT.relative_to(ROOT)} is empty or absent — nothing to report")
        return 0
    dates = pd.to_datetime(panel["date"])
    spans = membership_spans(panel)
    last_session = dates.max()
    leavers = spans[spans["last"] < last_session]
    print(f"sessions {dates.nunique():,} | {dates.min().date()} .. {last_session.date()}")
    print(f"symbols ever in the segment: {panel['symbol'].nunique()}")
    print(f"in force on the last session: {len(members_on(panel, last_session))}")
    print(f"LEFT the segment before it:   {len(leavers)}  <- the names a today-pinned list would drop")
    if len(leavers):
        show = leavers.sort_values("last").tail(10)
        for _, r in show.iterrows():
            print(f"    {r['symbol']:<14s} {str(r['first'].date())} .. {str(r['last'].date())} "
                  f"({r['n_sessions']} sessions)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=str(pd.Timestamp.today().normalize().date()))
    ap.add_argument("--report", action="store_true", help="summarise the existing panel, no fetch")
    args = ap.parse_args()

    have = pd.read_parquet(OUT) if OUT.exists() else pd.DataFrame(columns=["date", "symbol"])
    if args.report:
        return _report(have)

    done = set(pd.to_datetime(have["date"]).dt.normalize().unique()) if len(have) else set()
    all_days = list(pd.bdate_range(args.start, args.end))
    days = [d for d in all_days if d.normalize() not in done]
    print(f"days {args.start}..{args.end}: total {len(all_days)} | have {len(done)} | "
          f"to fetch {len(days)}", flush=True)

    sess = requests.Session()
    parts = [have] if len(have) else []
    n_ok = n_miss = 0
    for k, d in enumerate(days):
        df = fetch_for_date(sess, d)
        # A miss is the normal case on a holiday. It is counted, never written as an empty marker:
        # this panel says where a name WAS, and a holiday is an absence of evidence, not evidence
        # that the segment was empty.
        day_panel = build_membership({d: df}) if df is not None else None
        if day_panel is not None and len(day_panel):
            parts.append(day_panel)
            n_ok += 1
        else:
            n_miss += 1
        if k % CHECKPOINT_EVERY == CHECKPOINT_EVERY - 1 or k == len(days) - 1:
            pd.concat(parts, ignore_index=True).drop_duplicates().to_parquet(OUT, index=False)
            print(f"  {k+1}/{len(days)} | sessions ok {n_ok} miss {n_miss} | last {d.date()}",
                  flush=True)
        time.sleep(0.25)

    if parts:
        panel = pd.concat(parts, ignore_index=True).drop_duplicates()
        panel = panel.sort_values(["date", "symbol"], kind="mergesort").reset_index(drop=True)
        panel.to_parquet(OUT, index=False)
    print(f"\nDONE -> {OUT.relative_to(ROOT)}")
    return _report(pd.read_parquet(OUT) if OUT.exists() else have)


if __name__ == "__main__":
    raise SystemExit(main())
