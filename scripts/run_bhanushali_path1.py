"""Pre-reg 0025 Path-1 runner: the 4×ATR initial-stop geometry as the ONLY change to the practitioner
config, on the 2×2 {geometry} × {universe} grid. Survivor-only cells run against the pinned cache;
corrected cells add data/ohlcv_backfill.pkl + the validated alias map (aliases materialized as the old
symbol pointing at the successor's series, honoring valid_until). Gross + net every cell.

Usage: python scripts/run_bhanushali_path1.py [--corrected]
Without --corrected only the survivor-only cells run (pre-backfill).
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_practitioner import backtest, prep, _row, _slices  # noqa: E402


def corrected_universe():
    """Pinned cache + backfill series + alias materialization (old symbol -> successor series)."""
    ohlcv = dict(load_ohlcv_cache(OHLCV_CACHE))
    bf = pickle.load(open(ROOT / "data" / "ohlcv_backfill.pkl", "rb"))
    for t, df in bf.items():
        ohlcv.setdefault(t, df)                                   # never overwrite the pinned series
    amap = json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"]
    for old, spec in amap.items():                                # aliases OVERRIDE any bhavcopy series for
        src = ohlcv.get(spec["to"])                               # the same old symbol (dividend-adjusted,
        if src is None:                                           # identity-validated — the better source)
            continue
        df = src
        if "valid_until" in spec:
            df = df[df.index <= pd.Timestamp(spec["valid_until"])]
        ohlcv[old] = df
    return ohlcv


def run_cells(ohlcv, label):
    P = prep(ohlcv)
    mem = load_membership()
    print(f"===== UNIVERSE: {label} ({len(P)} names) =====")
    for geom in ("candle", "atr4"):
        for cost_off, tag in ((True, "GROSS"), (False, "NET")):
            m = backtest(P, mem, stop_geom=geom, cost_off=cost_off)
            print(_row(f"{geom:<6} {tag}", m))
            if not cost_off:
                print(_slices(m))
    print()


def main() -> int:
    run_cells(load_ohlcv_cache(OHLCV_CACHE), "survivor-only (pinned f8625a8f)")
    if "--corrected" in sys.argv:
        run_cells(corrected_universe(), "corrected (pinned + backfill + aliases)")
    else:
        print("(corrected-universe cells deferred: run with --corrected after finalize_bhavcopy_backfill)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
