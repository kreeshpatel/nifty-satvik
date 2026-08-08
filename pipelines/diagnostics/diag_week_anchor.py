"""Week-anchor robustness diagnostic (Phase-0 census item; MEASUREMENT, 0 trials).

The whole weekly construction hardcodes ISO/W-FRI weeks. If headline results shift materially when the
week boundary rotates (a Thu-Wed week), the edifice is anchored-overfit; if stable, trust rises.
Implementation: shift every OHLCV index +2 calendar days (Fri->Sun stays in-week; Mon-Wed -> Wed-Fri),
which rotates the weekly partition to Thu..Wed without touching any price. Membership windows are real
dates (±2d slop — immaterial for a robustness read; stated caveat).

    python scripts/diag_week_anchor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402


def main() -> int:
    oh = corrected_universe(); mem = load_membership()
    base = backtest(prep_weekly_rank(oh), mem)
    sh = {t: g.set_axis(g.index + pd.Timedelta(days=2)) for t, g in oh.items()}
    anch = backtest(prep_weekly_rank(sh), mem)
    print("=== week-anchor robustness (Mon-Sun ISO vs rotated Thu-Wed) ===")
    for tag, m in (("ISO (record)", base), ("Thu-Wed", anch)):
        print(f"  {tag:<14} Sharpe {m['sharpe']:+.3f} | CAGR {m['cagr']*100:+.1f}% | DD {m['dd']*100:.1f}% "
              f"| trades {m['trades']} | win {m['wr']*100:.0f}%")
    d = anch["sharpe"] - base["sharpe"]
    print(f"\n  dSharpe {d:+.3f} -> {'STABLE (anchor-robust)' if abs(d) < 0.25 else 'FRAGILE — anchor-overfit red flag'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
