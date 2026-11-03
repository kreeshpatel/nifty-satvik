"""EXPLORE (tier 0): does raising the stop once a trade has run up stop the 'profit, then full loss' pattern?

Owner question 2026-11-03: trades go into profit, never reach the 2R target, and come back to a full stop.
Reuses the 0148 lever (scaled_exit lockin_mfe / lockin_at: once the peak reaches lockin_mfe R, the stop
rises to entry + lockin_at R, fired on the weekly close like the base stop). 0148 measured 2.75/2.50 -> 1.5
(BOUND); breakeven arms were never run. No screen row, no n_trials change, nothing changes live.
Live book with PIT membership; prices CUT at 2024-06-30 and asserted; single path per arm (~0.2 Sharpe noise).

    python pipelines/diagnostics/explore_giveback_breakeven.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipelines" / "diagnostics"))
sys.path.insert(0, str(ROOT / "scripts"))
import diag_giveback_ratchet_0148 as G  # noqa: E402

ARMS = {"base": {}, "be_at_1.0": dict(lockin_mfe=1.0, lockin_at=0.0), "be_at_1.5": dict(lockin_mfe=1.5, lockin_at=0.0),
        "be_after_2.0": dict(lockin_mfe=2.0, lockin_at=0.0), "lock1_after_2.0": dict(lockin_mfe=2.0, lockin_at=1.0)}
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-03_giveback_breakeven.json"


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(G.CUT)] for t, df in corrected_universe().items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    last = max(df.index.max() for df in cut.values())
    assert last <= pd.Timestamp(G.CUT), f"sealed data reached the engine: {last}"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    live = dict(LIVE_DISCIPLINE=LIVE_DISCIPLINE, LIVE_EXIT=LIVE_EXIT, LIVE_STALENESS=LIVE_STALENESS, mem=load_membership())
    res: dict = {"window": [G.START, G.CUT], "last_bar_seen": str(last.date()), "tier": "EXPLORE", "arms": {}}
    for book, unc in (("capped", False), ("uncapped", True)):
        for name, extra in ARMS.items():
            out, led, fired = G.run_arm(P, events, R94, live, extra, uncapped=unc)
            led = led[(led["entry"] - led["stop0"]) / led["entry"] >= 0.005]      # degenerate-stop rule (nq.lab.stats)
            closed = led[led["reason"] != "eos"]
            row = {"n": int(len(led)), "fired": fired, "win_pct": round(float((closed["R"] > 0).mean() * 100), 1),
                   "mean_R_closed": round(float(closed["R"].mean()), 3), "sum_R_incl_open": round(float(led["R"].sum()), 1)}
            if book == "capped":
                row.update(cagr_pct=round(out["cagr"] * 100, 1), full=G._curve_stats(out["curve"], G.START, G.CUT),
                           sub={k: G._curve_stats(out["curve"], *v) for k, v in G.SUBPERIODS.items()})
            res["arms"].setdefault(book, {})[name] = row
            print(book, name, json.dumps(row, default=lambda x: round(x, 3)))
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
