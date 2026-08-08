"""Hybrid build on the ONE strategy that survived the train/holdout split.

The survey (`diag_swing_strategy_survey.py`) ranked nine swing strategies on TRAIN 2019-2023 and
then looked at HOLDOUT 2024-2026 once. Only Supertrend+Pivot (Rachana Ranade) was both selectable
on train (clearly above the random-entry null) and positive out of sample. This script builds the
"most hybrid" version the owner asked for, on that survivor.

The two overlays added are NOT swept parameters — each is a lever that showed an INDEPENDENT
drawdown benefit earlier in this same session, and each is added for its stated mechanism:

  R  Nifty > 200 DMA regime filter — published as part of the Bajaj RS55 system; measured in
     `diag_supertrend_bajaj.py` to cut MaxDD from -54.3% to -35.7% on a different entry.
  S  RS55 > 0 (55-bar outperformance vs Nifty) — the only relative-strength form in this session
     with a defensible published definition.

  H1 = survivor + R      H2 = survivor + S      H3 = survivor + R + S   (the full hybrid)

**HOLDOUT CONTAMINATION, stated plainly.** The 2024-2026 slice was already consumed once, to
adjudicate the nine survey cells. These hybrid holdout numbers are therefore a SECOND look at the
same data and are optimistically biased. They are reported because they were asked for; they are
NOT clean out-of-sample evidence and must not be quoted as such. After this, the only honest
certifier left for this family is forward data.

MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_swing_hybrid.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from diag_supertrend_system import supertrend  # noqa: E402
from diag_swing_strategy_survey import (HOLDOUT, TRAIN, build_base, ema,  # noqa: E402
                                        fresh, monthly_pivot, row, run)
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

_N50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
        .set_index("date")["nifty50_close"].sort_index())
_N50_OK = _N50 > _N50.rolling(200).mean()


def _survivor_core(d):
    """Supertrend(10,3) green + close > EMA200 + close crossing above the monthly pivot."""
    _, up = supertrend(d["h"], d["l"], d["c"], 10, 3.0)
    piv = monthly_pivot(d["idx"], d["h"], d["l"], d["c"])
    pc = np.concatenate([[np.nan], d["c"][:-1]])
    pp = np.concatenate([[np.nan], piv[:-1]])
    cross = np.nan_to_num((d["c"] > piv) & (pc <= pp), nan=False)
    return up & (d["c"] > ema(d["c"], 200)) & cross


def make(regime: bool, rs: bool):
    def f(d):
        ok = _survivor_core(d)
        if regime:
            ok = ok & _N50_OK.reindex(d["idx"], method="ffill").fillna(False).to_numpy().astype(bool)
        if rs:
            ok = ok & (np.nan_to_num(d["rs55"], nan=-9.0) > 0.0)
        return fresh(ok), d["c"] - 2.0 * d["atr"], 2.0, None, 252
    return f


CELLS = [
    ("BASE  Supertrend + Pivot (the survivor, unchanged)", make(False, False)),
    ("H1    + Nifty>200DMA regime filter", make(True, False)),
    ("H2    + RS55>0 relative-strength filter", make(False, True)),
    ("H3    + BOTH  = the full hybrid", make(True, True)),
]


def main() -> int:
    print("=== HYBRID on the train/holdout survivor: Supertrend + Pivot Points ===")
    print("    !! HOLDOUT 2024-2026 was already consumed by the 9-cell survey. The holdout column")
    print("    !! below is a SECOND look at the same data -> optimistically biased, NOT clean OOS.\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")
    res = []
    for tag, fn in CELLS:
        tr = run(P, fn, start=TRAIN[0], end=TRAIN[1])
        ho = run(P, fn, start=HOLDOUT[0], end=HOLDOUT[1])
        res.append((tag, tr, ho))
        print(f"  {tag}")
        print(f"      TRAIN    {row(tag, tr)}")
        print(f"      HOLDOUT* {row(tag, ho)}")
    print("\n=== what each overlay bought (train -> holdout*) ===")
    b = res[0]
    for tag, tr, ho in res[1:]:
        print(f"  {tag.split('  ')[0]:<6} dCAGR train {(tr['cagr']-b[1]['cagr'])*100:+6.2f}pp  "
              f"holdout* {(ho['cagr']-b[2]['cagr'])*100:+6.2f}pp   "
              f"dMaxDD train {(tr['dd']-b[1]['dd'])*100:+6.2f}pp  holdout* {(ho['dd']-b[2]['dd'])*100:+6.2f}pp")
    print("\n  reference: baseline_v1 CAGR 15.46% / Sharpe 0.667 / MaxDD -46.26% (2016-2026, "
          "different window — not a like-for-like comparison)")
    print("  standing counts: screens 17 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    print("  NOT a promote. The holdout is spent; only forward data can certify this family now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
