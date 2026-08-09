"""MEASUREMENT (no trial): what does the r94 golden fixture actually exercise, and what can it not?

A 2026-08-09 audit called the golden master's coverage "the largest single test gap in the repo",
on two grounds: its worst overnight gap is -0.20% so the gap surface is untested, and `targets` and
`pattern` -- the live book's two profit tranches -- never appear in its exit reasons. The planned fix
(Track A3) was to build a gapping, halting, losing fixture cell.

Probing before building found the premise wrong on both counts.

**1. There is no gap surface to test.** The only two gap-aware branches are `hard_stop`
(`run_bhanushali_weekly_rank.py:545`) and `disaster_floor_pct` (`:573`). Neither is passed by the
live configuration, so both sit at their defaults of False and 0.0. Injecting -15% overnight gaps
into three held names changes the exit mix by exactly nothing: same 42 trades under defaults, same
50 under config P, identical reasons. The live book decides on WEEKLY closes and fills at the next
Monday open, so an intraweek gap is not something it can respond to. Both gap branches were killed by
measurement anyway -- 0105 hard stop at dSharpe -0.477 and 0109 disaster floor at -0.071.

That is not a coverage gap. It is a design property, and the honest statement of it is that **the
live book concedes the whole gap by construction** -- which is a risk fact the owner should hold,
not a test to write.

**2. The profit tranches fire on every single trade.** They cannot appear as exit REASONS because
config P sets `tp2_frac = 0.0`, so the 40%-at-2R and 40%-blow-off bookings are always PARTIAL and the
20% runner always determines the final reason. The ledger's `half_date` field is the tell: it is set
on 50 of 50 rows. 43 of 50 trades reach +2R and the maximum is +38R. The tranche machinery is among
the best-exercised code in the fixture; the reason vocabulary simply cannot show it.

**What genuinely survives the audit**, and is smaller than it looked: the `frozen_defaults` cell has
`win_rate 1.0` and no losing trade at all. That is worth fixing. But it is the frozen 0094 research
cell, not the live path -- the live cells already exercise `stop`, `sma_break`, `stale`, `eos` and the
tp1 partial on every trade.

    python pipelines/diagnostics/diag_golden_exit_coverage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_r94_golden_fixture as B  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_STALENESS  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "golden_exit_coverage.json"
GAP_DAYS = {"ALPHA": [900, 1100, 1300], "BRAVO": [950, 1150], "DELTA": [1000, 1250]}
GAP_SIZE = -0.15


class _IndexProvider:
    """prep_weekly_rank's CRS denominator, pinned to the fixture's own index series."""

    def __init__(self, s: pd.Series) -> None:
        self.s = s

    def __call__(self, *a, **k) -> pd.Series:
        return self.s


def worst_gap(df: pd.DataFrame) -> float:
    o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
    return float(np.min(o[1:] / c[:-1] - 1.0))


def inject_gaps(df: pd.DataFrame, days: list[int], size: float) -> pd.DataFrame:
    d = df.copy()
    o = d["Open"].to_numpy(float).copy()
    c = d["Close"].to_numpy(float)
    for i in days:
        if 0 < i < len(o):
            o[i] = c[i - 1] * (1.0 + size)
            d.iloc[i, d.columns.get_loc("Low")] = min(d["Low"].iloc[i], o[i] * 0.995)
            d.iloc[i, d.columns.get_loc("Close")] = min(d["Close"].iloc[i], o[i] * 1.002)
    d["Open"] = o
    return d


def run(ohlcv: dict, index: pd.Series, live: bool) -> tuple[dict, list]:
    P = R94.prep_weekly_rank(ohlcv, index_provider=_IndexProvider(index))
    a = R94.grade_a_entries(P)
    led: list = []
    kw = {**LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS} if live else {}
    m = R94.backtest(P, None, ledger=led, a_grade=a, **kw)
    return m, led


def main() -> int:
    oh, index = B.synth_universe()
    base_gap = min(worst_gap(d) for d in oh.values())

    m_def, _ = run(oh, index, live=False)
    m_live, led = run(oh, index, live=True)

    gapped = {**oh, **{k: inject_gaps(oh[k], v, GAP_SIZE) for k, v in GAP_DAYS.items()}}
    g_gap = min(worst_gap(d) for d in gapped.values())
    m_def_g, _ = run(gapped, index, live=False)
    m_live_g, _ = run(gapped, index, live=True)

    R = [float(r["R"]) for r in led if r.get("R") is not None]
    halves = [r for r in led if r.get("half_date") is not None]

    out = {
        "_doc": "MEASUREMENT, no trial. What the r94 golden fixture exercises.",
        "reproduce": "python pipelines/diagnostics/diag_golden_exit_coverage.py",
        "gap_insensitivity": {
            "fixture_worst_overnight_gap_pct": round(base_gap * 100, 3),
            "injected_worst_overnight_gap_pct": round(g_gap * 100, 3),
            "defaults_before": m_def["reasons"], "defaults_after_gaps": m_def_g["reasons"],
            "live_before": m_live["reasons"], "live_after_gaps": m_live_g["reasons"],
            "unchanged": (m_def["reasons"] == m_def_g["reasons"]
                          and m_live["reasons"] == m_live_g["reasons"]),
            "reading": ("hard_stop and disaster_floor_pct are the only gap-aware branches and both "
                        "are off in the live config, so a -15% overnight gap changes nothing. The "
                        "live book concedes the whole gap by construction."),
        },
        "tranche_coverage": {
            "live_exit_reasons": m_live["reasons"],
            "ledger_rows": len(led),
            "rows_with_partial_booking": len(halves),
            "trades_reaching_2R": sum(1 for x in R if x >= 2.0),
            "max_R": round(max(R), 2) if R else None,
            "tp2_frac": LIVE_EXIT["scaled_exit"]["tp2_frac"],
            "reading": ("tp2_frac = 0.0, so a position can never be FULLY closed by targets; the 20% "
                        "runner always sets the final reason. `targets` and `pattern` are therefore "
                        "absent from the reason vocabulary while firing as partials on every trade."),
        },
        "what_survives": ("The frozen_defaults cell has win_rate 1.0 and no losing trade. That is "
                          "real and worth fixing, but it is the frozen 0094 research cell, not the "
                          "live path."),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"fixture worst overnight gap {base_gap*100:+.2f}% -> injected {g_gap*100:+.2f}%")
    print(f"  defaults  before {m_def['reasons']}  after {m_def_g['reasons']}")
    print(f"  live      before {m_live['reasons']}  after {m_live_g['reasons']}")
    print(f"  UNCHANGED: {out['gap_insensitivity']['unchanged']}")
    print(f"\npartial bookings recorded on {len(halves)} of {len(led)} rows | "
          f"{sum(1 for x in R if x >= 2.0)} trades reach +2R | max R {max(R):+.2f}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
