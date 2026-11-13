"""EXPLORE (tier 0): round-trip losers and the +1R management arms on the live exit, 2019-01-01..2024-06-30.

Owner request 2026-11-13. Part 1 measures trades that reached +1R (on a Friday close, and separately on an intraweek
high) and still exited at the full stop, and how many big winners dipped back near entry before running.
Part 2 runs the +1R management arms on the current live rules (uncapped per-trade book and the capped book,
single path). Path robustness is in explore_ensemble_plus1r_arms.py. No screen row, no n_trials change.
PIT membership, prices cut at 2024-06-30 and asserted.

    python pipelines/diagnostics/explore_plus1r_arms.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
import diag_giveback_ratchet_0148 as G  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-13_plus1r_arms.json"


def _trail(lag: float, start: float = 1.0, top: float = 12.0) -> tuple:
    """Stop-ladder steps that trail the peak by `lag` R once the peak reaches `start` R (whole-R steps)."""
    steps, m = [], start
    while m <= top + 1e-9:
        steps.append((round(m, 2), round(m - lag, 2)))
        m += 1.0
    return tuple(steps)


# name -> scaled_exit overrides on top of the live exit (all levers already exist in the engine, off by default)
ARMS = {
    "live": {},
    "breakeven_at_1R": dict(lockin_mfe=1.0, lockin_at=0.0),
    "stop_-0.5R_at_1R": dict(lockin_mfe=1.0, lockin_at=-0.5),
    "partial_20pct_at_1R": dict(tp1_r=1.0, tp1_frac=0.20, tp2_r=2.0, tp2_frac=0.20),
    "first_40pct_at_1R": dict(tp1_r=1.0),
    "trail_1R_behind_after_1R": dict(lockin_ladder=_trail(1.0)),
    "trail_1.5R_behind_after_1.5R": dict(lockin_ladder=_trail(1.5, start=1.5)),
}

# The same ratchet arms armed from the week's full high (engine lever `ratchet_peak`, 2026-11-13). The engine's
# default peak is the max of week-END-session highs, which understates how often a +1R rule would arm in practice.
ARMS_WH = {f"{k}|week_high": {**v, "ratchet_peak": "week_high"} for k, v in ARMS.items()
           if any(x in v for x in ("lockin_mfe", "lockin_ladder"))}


def path_stats(led: pd.DataFrame, bars: dict) -> pd.DataFrame:
    """Per closed trade: peak R on a Friday close and on an intraweek high, and the post-+1R dips."""
    rows = []
    for r in led.itertuples():
        df = bars.get(r.tkr)
        risk = r.entry - r.stop0
        if df is None or risk <= 0 or pd.isna(r.exit_date):
            continue
        w = df[(df.index >= pd.Timestamp(r.entry_date)) & (df.index < pd.Timestamp(r.exit_date))]
        if not len(w):
            continue
        fri = w["Close"].resample("W-FRI").last().dropna()
        fri = fri[fri.index < pd.Timestamp(r.exit_date)]
        hi_r = (w["High"] - r.entry) / risk
        lo_r = (w["Low"] - r.entry) / risk
        cl_r = (fri - r.entry) / risk
        after1 = hi_r[hi_r >= 1.0]
        dip_low = dip_close0 = dip_close_m05 = False
        if len(after1):
            t1 = after1.index[0]
            dip_low = bool((lo_r[lo_r.index > t1] <= 0.25).any())
            later_c = cl_r[cl_r.index >= t1]
            dip_close0 = bool((later_c <= 0.0).any())
            dip_close_m05 = bool((later_c <= -0.5).any())
        rows.append(dict(tkr=r.tkr, entry_date=str(pd.Timestamp(r.entry_date).date()), reason=r.reason, R=r.R,
                         mfe_close=float(cl_r.max()) if len(cl_r) else float("nan"), mfe_high=float(hi_r.max()),
                         dip_low_0p25_after_1R=dip_low, close_at_or_below_entry_after_1R=dip_close0,
                         close_at_or_below_m0p5_after_1R=dip_close_m05))
    return pd.DataFrame(rows)


def summarise(ps: pd.DataFrame) -> dict:
    full_stop = ps[ps.reason == "stop"]
    out = {"closed": int(len(ps)), "full_stops": int(len(full_stop))}
    for basis in ("mfe_close", "mfe_high"):
        rt = full_stop[full_stop[basis] >= 1.0]
        out[f"round_trip_{basis}"] = {"count": int(len(rt)), "share_of_full_stops_pct": round(100 * len(rt) / max(len(full_stop), 1), 1),
                                      "sum_R": round(float(rt.R.sum()), 1), "mean_R": round(float(rt.R.mean()), 2) if len(rt) else None,
                                      "giveback_from_peak_R": round(float((rt[basis] - rt.R).sum()), 1)}
    big = ps[ps.R >= 2.0]
    out["big_winners_R_ge_2"] = {"count": int(len(big)), "sum_R": round(float(big.R.sum()), 1),
                                 "low_back_to_+0.25R_after_+1R": int(big.dip_low_0p25_after_1R.sum()),
                                 "friday_close_at_or_below_entry_after_+1R": int(big.close_at_or_below_entry_after_1R.sum()),
                                 "friday_close_at_or_below_-0.5R_after_+1R": int(big.close_at_or_below_m0p5_after_1R.sum())}
    return out


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(G.CUT)] for t, df in corrected_universe().items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    assert max(df.index.max() for df in cut.values()) <= pd.Timestamp(G.CUT), "sealed data reached the engine"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    ev = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem, A = load_membership(), R94.grade_a_entries(P)
    res: dict = {"tier": "EXPLORE", "window": [G.START, G.CUT], "arms_def": {k: str(v) for k, v in ARMS.items()}, "arms": {}}
    for name, extra in {**ARMS, **ARMS_WH}.items():
        exit_cfg = {**LIVE_EXIT, "scaled_exit": {**LIVE_EXIT["scaled_exit"], **extra}}
        for book, unc in (("uncapped", True), ("capped", False)):
            led: list = []
            out = R94.backtest(P, mem, ledger=led, start=G.START, uncapped=unc, a_grade=A, **LIVE_DISCIPLINE,
                               **exit_cfg, **LIVE_STALENESS, demerger_events=ev)
            d = pd.DataFrame(led)
            d = d[(d.entry - d.stop0) / d.entry >= 0.005]               # degenerate-stop rule (nq.lab.stats)
            c = d[d.reason != "eos"]
            row = {"n": int(len(c)), "win_pct": round(float((c.R > 0).mean() * 100), 1),
                   "mean_R": round(float(c.R.mean()), 3), "sum_R_incl_open": round(float(d.R.sum()), 1),
                   "full_stop_pct": round(float((c.reason == "stop").mean() * 100), 1)}
            if book == "capped":
                st = G._curve_stats(out["curve"], G.START, G.CUT)
                row.update(cagr_pct=round(out["cagr"] * 100, 1), sharpe=round(st["sharpe"], 3), maxdd_pct=round(st["maxdd_pct"], 1))
            if name == "live" and unc:
                res["round_trip_history"] = summarise(path_stats(c, cut))
            res["arms"].setdefault(name, {})[book] = row
            print(name, book, row, flush=True)
    print(json.dumps(res["round_trip_history"], indent=1))
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
