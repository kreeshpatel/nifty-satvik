"""Pivot-spec disambiguation for the Ranade Supertrend+Pivot strategy.

Sources describe the pivot leg two different ways, and they are not the same trigger:

  (a) "price must cross above a pivot point"  — pivot unspecified
  (b) "you can take an entry when the DAILY CANDLE CLOSES ABOVE THE R1 (Resistance) level",
      where "pivot points calculate key price levels based on THE PREVIOUS DAY'S high, low and
      close" -> P = (H+L+C)/3 of the prior day, R1 = 2P - L(prior)
  (c) a stated conservative variant: "enter only when the bullish candle surpasses the high of
      the previous candle"

The survey implemented the pivot leg as a cross above the MONTHLY central pivot. That is one
reading of (a) and it is NOT reading (b). This script prices all of them so the strategy is
tested as published rather than as guessed.

This is a SPEC CORRECTION, not a parameter search — the same class as discovering the Bajaj system
uses RS55 rather than RS14. No threshold is being tuned; four documented readings of one rule are
being disambiguated.

**Every window is now used.** Train and holdout were consumed by the survey; 2016-2018 was consumed
by the deep dive. All three are reported here for completeness and NONE of them is clean evidence
any more. This is characterisation. Only forward data can certify this family.

MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_ranade_pivot_variants.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from diag_ranade_deepdive import EARLY, HOLD, TRAIN, engine, show  # noqa: E402
from diag_supertrend_system import supertrend  # noqa: E402
from diag_swing_strategy_survey import build_base, ema, fresh, monthly_pivot  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402


def daily_pivots(h, l, c):
    """Classic pivots from the PRIOR day's bar: P=(H+L+C)/3, R1=2P-L, S1=2P-H."""
    ph = np.concatenate([[np.nan], h[:-1]])
    pl = np.concatenate([[np.nan], l[:-1]])
    pc = np.concatenate([[np.nan], c[:-1]])
    p = (ph + pl + pc) / 3.0
    return p, 2 * p - pl, 2 * p - ph


def _common(d):
    _, up = supertrend(d["h"], d["l"], d["c"], 10, 3.0)
    return up & (d["c"] > ema(d["c"], 200))


def v_monthly_p(d):                                  # what the survey ran
    piv = monthly_pivot(d["idx"], d["h"], d["l"], d["c"])
    pc = np.concatenate([[np.nan], d["c"][:-1]])
    pp = np.concatenate([[np.nan], piv[:-1]])
    return fresh(_common(d) & np.nan_to_num((d["c"] > piv) & (pc <= pp), nan=False))


def v_daily_p(d):
    p, _, _ = daily_pivots(d["h"], d["l"], d["c"])
    return fresh(_common(d) & np.nan_to_num(d["c"] > p, nan=False))


def v_daily_r1(d):                                   # the sourced reading (b)
    _, r1, _ = daily_pivots(d["h"], d["l"], d["c"])
    return fresh(_common(d) & np.nan_to_num(d["c"] > r1, nan=False))


def v_daily_r1_conservative(d):                      # (b) + the stated confirmation (c)
    _, r1, _ = daily_pivots(d["h"], d["l"], d["c"])
    ph = np.concatenate([[np.nan], d["h"][:-1]])
    ok = _common(d) & np.nan_to_num((d["c"] > r1) & (d["c"] > d["o"]) & (d["h"] > ph), nan=False)
    return fresh(ok)


VARIANTS = [
    ("(survey)  monthly central pivot P", v_monthly_p),
    ("(a)       daily central pivot P", v_daily_p),
    ("(b)       daily R1  <- SOURCED", v_daily_r1),
    ("(c)       daily R1 + prior-high confirm", v_daily_r1_conservative),
]


def main() -> int:
    print("=== Ranade pivot-spec disambiguation — four documented readings of one rule ===")
    print("    ALL windows are now used. Nothing below is clean evidence; this is characterisation.\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")
    import diag_ranade_deepdive as DD
    for tag, fn in VARIANTS:
        DD.legs = lambda d, **kw: fn(d)          # swap the signal, keep the identical book
        print(f"  {tag}")
        for wtag, (s, e) in (("2016-18*", EARLY), ("train  ", TRAIN), ("holdout", HOLD)):
            m, _ = engine(P, start=s, end=e)
            show(f"    {wtag}", m)
    print("\n  * 2016-18 membership back-extended -> optimistic")
    print("  standing counts: screens 17 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
