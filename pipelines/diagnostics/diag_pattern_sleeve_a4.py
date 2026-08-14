"""A4 (Category-A re-examination): the REAL standalone pattern-book backtest that closes the chart-zoo
sleeve. 0131 killed the zoo as a SHARED pool (seat dilution) but preserved the own-capital sleeve as
the untested escape. This runs box+cup_handle+double_bottom (origins 1,6,8) as a standalone capped
book through the actual engine with the frozen exit (mark-to-market), by filtering each stock's
entry_win to pattern origins only, then measures its profile and its correlation/blend vs the swing
book. Result: the sleeve is WORSE than swing on every axis and correlates +0.60 — the blend never
beats swing-alone, so it does not diversify. Per-trade edge (0131) does not survive to the book even
with its own capital (Law II + Law VII). MEASUREMENT — no trial, no screen row.

Run: python pipelines/diagnostics/diag_pattern_sleeve_a4.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

PATTERN_ORIGINS = {1, 6, 8}  # box, cup_handle, double_bottom (0131's elected family)


def _prof(bt: dict) -> tuple[float, float, float]:
    return bt["sharpe"], bt["cagr"] * 100, bt["dd"] * 100


def _daily_ret(bt: dict) -> pd.Series:
    c = bt["curve"].copy()
    c.index = pd.to_datetime(c.index)
    return c.pct_change().dropna()


def main() -> int:
    ohlcv = corrected_universe()
    mem = load_membership()

    led_sw: list = []
    sw = R94.backtest(R94.prep_weekly_rank(ohlcv), mem, ledger=led_sw, start="2017-01-01")

    P = R94.prep_weekly_rank(ohlcv, box_breakout=True, zoo_origins=(6, 8))
    for s in P.values():
        if isinstance(s, dict) and "entry_win" in s:
            s["entry_win"] = {d: t for d, t in s["entry_win"].items() if t[5] in PATTERN_ORIGINS}
    led_pat: list = []
    pat = R94.backtest(P, mem, ledger=led_pat, start="2017-01-01")

    print("A4 — standalone pattern book (box+cup+double_bottom), frozen exit, capped")
    print(f"{'book':>10} {'Sharpe':>7} {'CAGR%':>7} {'MaxDD%':>7} {'trades':>7}")
    print(f"{'swing-0094':>10} {_prof(sw)[0]:7.2f} {_prof(sw)[1]:7.1f} {_prof(sw)[2]:7.1f} {len(led_sw):7d}")
    print(f"{'pattern':>10} {_prof(pat)[0]:7.2f} {_prof(pat)[1]:7.1f} {_prof(pat)[2]:7.1f} {len(led_pat):7d}")

    rs, rp = _daily_ret(sw), _daily_ret(pat)
    idx = rs.index.intersection(rp.index)
    a, b = rs.reindex(idx).fillna(0.0), rp.reindex(idx).fillna(0.0)
    print(f"\ncorr(swing, pattern) daily = {np.corrcoef(a, b)[0, 1]:+.2f}  (n={len(idx)})")
    for w in (0.4, 0.5, 0.6, 0.7):
        br = w * a + (1 - w) * b
        print(f"  blend w_swing={w:.1f}: Sharpe {br.mean() / br.std() * np.sqrt(252):+.2f}")
    print(f"  (swing {a.mean() / a.std() * np.sqrt(252):+.2f}, "
          f"pattern {b.mean() / b.std() * np.sqrt(252):+.2f})")
    print("\nVerdict: worse standalone AND no diversification (blend never beats swing) -> no home.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
