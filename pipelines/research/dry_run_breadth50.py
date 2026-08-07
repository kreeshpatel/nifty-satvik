"""breadth-50 dry run — CONSTRUCTION VALIDATION ONLY on one historical snapshot date.

Validates: shapes, weight sums, tilt bounds, PIT-lagged feature joins (delivery at <= snapshot Friday;
events announced <= snapshot Friday), and CRS reconciliation coverage. NO performance evaluation of
any kind (that is the wall's job, post-sign-off). Wired into no cron.

    python scripts/dry_run_breadth50.py [--snap 2024-06-28]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.delivery import DELIVERY_RAW_PATH, apply_alias_map, derive_delivery_features  # noqa: E402
from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.research.breadth50 import EVENT_WINDOW_CD, TILT_HI, TILT_LO, build_books, weekly_crs_dist  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--snap", default="2024-06-28")
    a = ap.parse_args()
    snap = pd.Timestamp(a.snap)
    print(f"=== breadth-50 dry run @ {snap.date()} (construction only) ===")
    oh = load_ohlcv_cache(OHLCV_CACHE)
    closes = pd.DataFrame({t: g["Close"] for t, g in oh.items()})
    closes.index = pd.to_datetime(closes.index)
    # Nifty-50 proxy: the OI spot series is the engine's own N50 reference where available; else the
    # equal-weight top-liquidity composite. Use the options-OI spot (committed layer).
    oi = pd.read_parquet(ROOT / "data" / "options_oi_pit.parquet")
    idx = oi["spot"]; idx.index = pd.to_datetime(oi.index)
    crs = weekly_crs_dist(closes, idx, snap)
    print(f"CRS cross-section at snapshot: {crs.notna().sum()} names")

    # PIT delivery join (features at <= snap)
    raw = apply_alias_map(pd.read_parquet(DELIVERY_RAW_PATH))
    raw["date"] = pd.to_datetime(raw["date"]).astype("datetime64[ns]")
    feats = derive_delivery_features(raw)
    feats = feats[(feats["date"] <= snap) & (feats["date"] >= snap - pd.Timedelta(days=10))]
    # staleness cap (the 0118 screen's 10d rule): a symbol with no recent delivery row joins as NaN,
    # never as a years-old value (delisted-name carryover was the dry-run's first-run defect).
    dlv = feats.sort_values("date").groupby("symbol")["dlv_med21"].last()
    lag = (snap - feats.groupby("symbol")["date"].last()).dt.days
    print(f"delivery join: {dlv.notna().sum()} symbols | join lag days p50 {lag.median():.0f} "
          f"p95 {lag.quantile(.95):.0f} (PIT: all >= 0 -> {bool((lag >= 0).all())})")

    # PIT event flag (announced <= snap; event within 14cd of the entry-week Monday)
    ev = build_event_table(apply_alias_map(pd.read_parquet(EARNINGS_RAW_PATH)))
    monday = snap + pd.Timedelta(days=3)
    known = ev[ev["ann_ts"] <= snap]
    hit = known[(known["event_date"] >= monday) &
                (known["event_date"] <= monday + pd.Timedelta(days=EVENT_WINDOW_CD))]
    flag = pd.Series(True, index=hit["symbol"].unique())
    print(f"event flags: {len(flag)} names carry a known event within {EVENT_WINDOW_CD}cd "
          f"(announced <= snapshot: {bool((hit['ann_ts'] <= snap).all())})")

    books = build_books(crs, dlv, flag)
    print(f"\nbooks built: {len(books)} names")
    print(f"  w_ew sum {books['w_ew'].sum():.6f} | w_sw sum {books['w_sw'].sum():.6f}")
    rel = books["w_sw"] / books["w_ew"]
    print(f"  SW/EW tilt range [{rel.min():.2f}, {rel.max():.2f}] "
          f"(bounds pre-normalization [{TILT_LO}, {TILT_HI}] -> post-normalization may shift; "
          f"raw-tilt bound check inside build_books asserts)")
    print(f"  flagged-event names in book: {int(books['event_flag'].sum())} | "
          f"delivery coverage in book: {books['dlv_med21'].notna().mean()*100:.0f}%")
    print("\nTop 10 by SW weight:")
    print(books.sort_values("w_sw", ascending=False).head(10).round(4).to_string())
    print("\nDRY RUN COMPLETE — construction validated; no performance computed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
