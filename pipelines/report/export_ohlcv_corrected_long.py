"""Regenerate research/exports/ohlcv_corrected_long.{csv,parquet} — a DERIVED artifact.

These two files are a long-format dump of the corrected universe (pinned `ohlcv.pkl` +
`ohlcv_backfill.pkl`, alias-aware) at 4-decimal precision: 814 tickers, 1,594,575 rows,
columns [ticker, Date, Open, High, Low, Close, Volume].

They are NOT mortal and are NOT committed (see .gitignore). They are a byte-deterministic
function of committed code over pinned inputs, and at ~100 MB + ~48 MB they are also too large
for git (the CSV sits within a rounding error of GitHub's 100 MB hard limit). Verified
2026-07-30: the previously-untracked working copies matched this builder's output exactly —
same shape, same tickers, same dates, and numerically identical once the 4dp rounding is applied.

Inputs (fetch and verify first — do not trust local data/):
  data/ohlcv.pkl           f8625a8f…  gh release download dataset-pin-20260701 --pattern 'ohlcv.pkl' --dir data
  data/ohlcv_backfill.pkl  9ebbe448…  gh release download dataset-pin-20260729 --pattern 'ohlcv_backfill.pkl' --dir data

    python scripts/export_ohlcv_corrected_long.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from run_bhanushali_path1 import corrected_universe  # noqa: E402

OUT_DIR = ROOT / "research" / "exports"
DECIMALS = 4


def build() -> pd.DataFrame:
    parts = []
    for ticker, df in corrected_universe().items():
        x = df.reset_index()
        x.columns = ["Date"] + list(df.columns)
        x.insert(0, "ticker", ticker)
        parts.append(x)
    long = pd.concat(parts, ignore_index=True)
    long["Date"] = pd.to_datetime(long["Date"]).dt.strftime("%Y-%m-%d")
    num = ["Open", "High", "Low", "Close", "Volume"]
    long[num] = long[num].astype(float).round(DECIMALS)
    return long.sort_values(["ticker", "Date"]).reset_index(drop=True)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    long = build()
    long.to_csv(OUT_DIR / "ohlcv_corrected_long.csv", index=False)
    long.to_parquet(OUT_DIR / "ohlcv_corrected_long.parquet", index=False)
    print(f"{len(long):,} rows · {long['ticker'].nunique()} tickers -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
