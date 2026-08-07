"""Build ``data/raw_close_reference.parquet`` — the raw exchange closes the adjustment guard probes.

The guard in ``nq.data.adjustment_guard`` needs an UNADJUSTED reference to compute
``adj(t) = cache(t) / raw(t)``. That reference must be exchange-sourced (the vendor cannot audit
itself) and it must be committed, because a guard that needs the network to run is a guard that
gets skipped on the day the network is flaky.

The probe grid is deliberately two-part:

* **Quarterly**, 2019Q1 onward — broad coverage, catches a seam anywhere in the history.
* **Every year boundary** (the last session of each year and the first of the next) — the 2026Q3
  foundation audit localised five of seven seams to 1 January, so the boundary is probed on both
  sides at full density rather than relying on the quarterly grid to bracket it.

Both are already harvested by the foundation audit; this script consolidates them into one small
artifact under ``data/`` (whitelisted in ``.gitignore``) so the guard has a single stable input.

    python scripts/build_raw_close_reference.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = ROOT / "data" / "raw_close_reference.parquet"


def main() -> int:
    frames = []
    for name in ("bhavcopy_sample.parquet", "bhavcopy_events.parquet"):
        p = AUDIT / name
        if p.exists():
            frames.append(pd.read_parquet(p)[["symbol", "date", "close", "series"]])
    if not frames:
        print("no harvested bhavcopy found — run scripts/audit_foundation_bhavcopy_2026Q3.py first")
        return 1
    df = pd.concat(frames, ignore_index=True)
    # EQ before BE when a symbol printed both on a session: EQ is the rolling-settlement series the
    # cache tracks. Deterministic, so the artifact is byte-stable across rebuilds.
    df["_pref"] = (df["series"] != "EQ").astype(int)
    df = (df.sort_values(["symbol", "date", "_pref"])
            .drop_duplicates(["symbol", "date"], keep="first")
            .drop(columns=["_pref", "series"]))
    df = df[df["close"].astype(float) > 0].reset_index(drop=True)
    df.to_parquet(OUT, index=False, compression="zstd")
    print(f"wrote {OUT}  rows={len(df)}  symbols={df['symbol'].nunique()}  "
          f"dates={df['date'].nunique()}  "
          f"span={str(df['date'].min())[:10]}..{str(df['date'].max())[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
