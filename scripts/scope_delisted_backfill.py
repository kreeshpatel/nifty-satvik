"""Scope the delisted-price backfill (the survivor-only-cache data debt, CLAUDE.md / prereg v1.5 §3).
Inventories the PIT Nifty-500 members with NO price series in data/ohlcv.pkl: membership windows, days of
backtest exposure lost, and a per-year exposure profile. Writes the work-list to
diagnostics/research/delisted_backfill_scope.csv. Read-only; no cache mutation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

START, END = pd.Timestamp("2017-01-01"), pd.Timestamp("2026-06-29")


def main() -> int:
    cache = set(load_ohlcv_cache(OHLCV_CACHE))
    mem = load_membership()
    rows = []
    for t, spans in mem.items():
        if t in cache:
            continue
        days = 0
        lo, hi = None, None
        for a, b in spans:
            a, b = pd.Timestamp(a), pd.Timestamp(b if b is not None else END)
            a2, b2 = max(a, START), min(b, END)
            if a2 <= b2:
                days += (b2 - a2).days
                lo = a2 if lo is None else min(lo, a2)
                hi = b2 if hi is None else max(hi, b2)
        if days > 0:
            rows.append(dict(ticker=t, member_days_in_window=days,
                             first=lo.date(), last=hi.date()))
    df = pd.DataFrame(rows).sort_values("member_days_in_window", ascending=False)
    out = ROOT / "diagnostics" / "research" / "delisted_backfill_scope.csv"
    df.to_csv(out, index=False)
    print(f"missing members with in-window membership: {len(df)} (written to {out.relative_to(ROOT)})")
    print(f"total lost member-days 2017-2026: {df['member_days_in_window'].sum():,}")
    # per-year exposure: how many missing names were members in each year
    for yr in range(2017, 2027):
        y0, y1 = pd.Timestamp(f"{yr}-01-01"), pd.Timestamp(f"{yr}-12-31")
        n = sum(1 for _, r in df.iterrows()
                if pd.Timestamp(r["first"]) <= y1 and pd.Timestamp(r["last"]) >= y0)
        print(f"  {yr}: {n} missing members active")
    print("\ntop 20 by lost exposure:")
    print(df.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
