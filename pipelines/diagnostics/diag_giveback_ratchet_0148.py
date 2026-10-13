"""0148 — the giveback ratchet under the live scaled exit: activation bound.

Pre-registration: diagnostics/research/preregistry/0148-giveback-ratchet-bound.md (committed before this
file existed). Screen ledger row 21. No trial; nothing here changes the live config.

TRAIN ONLY: every price series is CUT at 2024-06-30 before the engine sees it, so the sealed 2024H2+
slice is never loaded. Trades still open at the cut close as `eos` at the cut and are counted separately.

    python pipelines/diagnostics/diag_giveback_ratchet_0148.py
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

START, CUT = "2019-01-01", "2024-06-30"
NOISE_FLOOR_R_PER_YR = 10.0          # 0109's path-noise floor
ARMS = {"base": {}, "primary_2.75_1.5": dict(lockin_mfe=2.75, lockin_at=1.5),
        "robust_2.50_1.5": dict(lockin_mfe=2.50, lockin_at=1.5)}
SUBPERIODS = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", CUT)}
OUT = ROOT / "diagnostics" / "research" / "giveback_ratchet" / "result.json"


def _curve_stats(curve: pd.Series, lo: str, hi: str) -> dict:
    """Sharpe / MaxDD on a CONTINUOUS SLICE of the one full-run curve — never a fresh-capital re-run."""
    e = curve[(curve.index >= pd.Timestamp(lo)) & (curve.index <= pd.Timestamp(hi))]
    r = e.pct_change().dropna()
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 2 and r.std() else None,
            "maxdd_pct": float((e / e.cummax() - 1).min() * 100) if len(e) else None}


def run_arm(P, events, R94, live: dict, extra: dict, *, uncapped: bool) -> tuple[dict, pd.DataFrame, int]:
    led, ev = [], []
    exit_cfg = {**live["LIVE_EXIT"], "scaled_exit": {**live["LIVE_EXIT"]["scaled_exit"], **extra}}
    # CORRECTED 2026-10-13: the first run passed mem=None, so its book could buy names outside the
    # Nifty-500 on the date; the live cron gates every fill on PIT membership, and this pre-registration
    # says "the live configuration exactly". `live["mem"]` is that gate. RESULT_MEMBERSHIP_OFF keeps the
    # original run's file for comparison.
    out = R94.backtest(P, live["mem"], ledger=led, start=START, uncapped=uncapped, a_grade=R94.grade_a_entries(P),
                       **live["LIVE_DISCIPLINE"], **exit_cfg, **live["LIVE_STALENESS"],
                       demerger_events=events, event_log=ev)
    fired = sum(1 for e in ev if e.get("event_type") == "stop_ratchet" and e.get("reason_code") == "lockin_at")
    return out, pd.DataFrame(led), fired


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe

    ohlcv = corrected_universe()
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(CUT)] for t, df in ohlcv.items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    last = max(df.index.max() for df in cut.values())
    assert last <= pd.Timestamp(CUT), f"sealed data reached the engine: {last}"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    from nq.data.membership import load_membership
    live = dict(LIVE_DISCIPLINE=LIVE_DISCIPLINE, LIVE_EXIT=LIVE_EXIT, LIVE_STALENESS=LIVE_STALENESS,
                mem=load_membership())

    res: dict = {"window": [START, CUT], "last_bar_seen": str(last.date()), "arms": {}}
    led_by: dict = {}
    for book, unc in (("capped", False), ("uncapped", True)):
        for name, extra in ARMS.items():
            out, led, fired = run_arm(P, events, R94, live, extra, uncapped=unc)
            led["year"] = pd.to_datetime(led["entry_date"]).dt.year
            closed = led[led["reason"] != "eos"]
            row = {"n_trades": int(len(led)), "n_open_at_cut": int((led["reason"] == "eos").sum()),
                   "ratchet_fired": fired, "mean_R": float(closed["R"].mean()),
                   "sum_R": float(closed["R"].sum()), "win_pct": float((closed["R"] > 0).mean() * 100),
                   # Red-team 2026-10-13: open-at-cut trades carry most of the R, and the ratchet closes trades
                   # the base leaves open, so a closed-only sum is censored differently per arm. The
                   # mark-inclusive sum is the PRIMARY R measure; the equity curve is primary overall.
                   "sum_R_incl_open_at_mark": float(led["R"].sum()),
                   "R_by_year": closed.groupby("year")["R"].sum().round(2).to_dict()}
            if book == "capped":
                row.update(cagr_pct=float(out["cagr"] * 100), full=_curve_stats(out["curve"], START, CUT),
                           sub={k: _curve_stats(out["curve"], *v) for k, v in SUBPERIODS.items()})
            res["arms"].setdefault(book, {})[name] = row
            led_by[(book, name)] = closed

    years = (pd.Timestamp(CUT) - pd.Timestamp(START)).days / 365.25
    res["bound"] = {}
    for book in ("capped", "uncapped"):
        b = res["arms"][book]["base"]
        for name in list(ARMS)[1:]:
            a = res["arms"][book][name]
            byy = {y: round(a["R_by_year"].get(y, 0.0) - b["R_by_year"].get(y, 0.0), 2)
                   for y in sorted(set(a["R_by_year"]) | set(b["R_by_year"]))}
            d_yr = (a["sum_R_incl_open_at_mark"] - b["sum_R_incl_open_at_mark"]) / years
            d_yr_closed_only = (a["sum_R"] - b["sum_R"]) / years
            sub = {k: round(sum(v for y, v in byy.items() if lo[:4] <= str(y) <= hi[:4]), 2)
                   for k, (lo, hi) in SUBPERIODS.items()}
            reading = ("ELIGIBLE for a pre-registered trial proposal at a review"
                       if d_yr >= NOISE_FLOOR_R_PER_YR and all(v > 0 for v in sub.values())
                       else "BOUND RECORDED — below the floor or wrong-signed; no trial")
            entry = {"delta_R_per_yr": round(d_yr, 2), "delta_R_per_yr_closed_only_censored": round(d_yr_closed_only, 2), "delta_mean_R": round(a["mean_R"] - b["mean_R"], 4),
                     "delta_R_by_year": byy, "delta_R_by_subperiod": sub, "reading": reading}
            if book == "capped":
                entry["delta_sharpe"] = round((a["full"]["sharpe"] or 0) - (b["full"]["sharpe"] or 0), 4)
                entry["delta_cagr_pp"] = round(a["cagr_pct"] - b["cagr_pct"], 2)
                entry["delta_maxdd_pp"] = round((a["full"]["maxdd_pct"] or 0) - (b["full"]["maxdd_pct"] or 0), 2)
            res["bound"][f"{book}:{name}"] = entry

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    for k, v in res["bound"].items():
        print(f"{k:<28} dR/yr {v['delta_R_per_yr']:+7.2f} | dMeanR {v['delta_mean_R']:+.4f} | "
              f"sub {v['delta_R_by_subperiod']} | {v.get('delta_sharpe', '')} | {v['reading']}")
    for book in ("capped", "uncapped"):
        for name, a in res["arms"][book].items():
            print(f"  {book:<9}{name:<18} n {a['n_trades']} open@cut {a['n_open_at_cut']} fired {a['ratchet_fired']} "
                  f"meanR {a['mean_R']:+.3f} sumR {a['sum_R']:+.1f} win {a['win_pct']:.1f}%"
                  + (f" Sharpe {a['full']['sharpe']:.3f} DD {a['full']['maxdd_pct']:.1f}%" if book == "capped" else ""))
    print(f"-> {OUT.relative_to(ROOT).as_posix()} (last bar seen {res['last_bar_seen']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
