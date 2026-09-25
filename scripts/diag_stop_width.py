#!/usr/bin/env python3
"""Stop width and the R denominator — MEASUREMENT, zero trials.

Implements `diagnostics/research/stop_width/SPEC.md`, committed before this script existed.

Is the live book losing more money per trade than the research book, or the same money measured in
smaller units? R is a ratio and its denominator is the stop width; the live book's stops are a median
5.6% wide against roughly 13% in the reconstruction.

    python scripts/diag_stop_width.py --run-date 2026-09-25

Outputs `diagnostics/research/stop_width/<run-date>/{summary.json, trades.csv}`. Nothing is adopted:
the stop axis is closed in both directions (0105 tighten, 0106 widen, 0109 floor) and the arithmetic
re-expression in §4 is a unit conversion, never a simulation of a wider stop.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.brain import portfolio as PF  # noqa: E402

# ── copied from SPEC.md ─────────────────────────────────────────────────────────────────────────────
HIST_START, HIST_END = "2019-01-01", "2024-06-30"
# SPEC A1.3: `max_risk_pct = 0.10` pins a stop at 10% exactly, and float noise then splits identical
# trades across a 10% band edge. Capped trades are their own cell; the bands cover uncapped widths.
CAP_PCT, CAP_TOL = 10.0, 0.05
BANDS = ((0.0, 3.0, "<3%"), (3.0, 6.0, "3-6%"), (6.0, CAP_PCT - CAP_TOL, "6-10% (uncapped)"))
N_BOOT, SEED = 2000, 20260925
MIN_TRADES = 30

OUT_BASE = ROOT / "diagnostics" / "research" / "stop_width"
LEDGER = ROOT / "results" / "attribution_ledger.csv"


def band_of(width_pct: float) -> str | None:
    if width_pct is None or not np.isfinite(width_pct):
        return None
    if abs(width_pct - CAP_PCT) <= CAP_TOL:
        return "at the 10% cap"
    for lo, hi, name in BANDS:
        if lo <= width_pct < hi:
            return name
    return ">10% (uncapped)"


def historical_trades() -> pd.DataFrame:
    """Population A — the 0142 reconstruction's ledger, one row per closed trade.

    The corporate-action HOLD stays OFF: it waits for an owner to resolve a freeze, and in a 5.5-year
    reconstruction nobody does (0142 amendment A1).
    """
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe

    ohlcv = corrected_universe()
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(HIST_END)] for t, df in ohlcv.items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    led: list = []
    R94.backtest(P, None, ledger=led, start=HIST_START, return_state=True,
                 a_grade=R94.grade_a_entries(P), **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS,
                 demerger_events=events)
    d = pd.DataFrame(led)
    if d.empty:
        return d
    d["stop_width_pct"] = (d["entry"] - d["stop0"]) / d["entry"] * 100.0
    d["return_pct"] = (d["exit_px"] / d["entry"] - 1.0) * 100.0
    d = d.rename(columns={"tkr": "ticker", "R": "r_multiple"})
    return d[["ticker", "entry_date", "stop_width_pct", "r_multiple", "return_pct", "reason"]]


def live_trades() -> pd.DataFrame:
    """Population B — the committed attribution ledger's closed trades."""
    d = pd.read_csv(LEDGER)
    d = d[d["exit_reason"].notna()].copy()
    # SPEC A1.1: the ENGINE basis (return% / R) is the denominator R was actually measured against. The
    # card's stop is a different object and disagrees by >5% on 3 of 11 closed trades.
    d["stop_width_pct"] = d["stop_width_pct_engine"].fillna(d["stop_width_pct_card"])
    return d[["ticker", "signal_date", "stop_width_pct", "stop_width_pct_card", "stop_width_pct_engine",
              "width_gap_pct", "r_multiple", "return_pct", "exit_reason", "beyond_stop_r", "designed_r"]
             ].rename(columns={"signal_date": "entry_date", "exit_reason": "reason"})


def _cell(d: pd.DataFrame, label: str) -> dict:
    """SPEC measures 1 and 2 for one slice, with the cluster bootstrap on the two means."""
    cell: dict = {"label": label, "n": int(len(d)), "informative": len(d) >= MIN_TRADES}
    if d.empty:
        return cell
    q = d["stop_width_pct"].quantile([0.25, 0.5, 0.75]).round(3)
    cell["stop_width_pct"] = {"median": float(q[0.5]), "iqr": [float(q[0.25]), float(q[0.75])],
                              "min": round(float(d["stop_width_pct"].min()), 3),
                              "max": round(float(d["stop_width_pct"].max()), 3)}
    pt, lo, hi = PF.cluster_bootstrap_mean(d["r_multiple"], d["ticker"], n_boot=N_BOOT, seed=SEED)
    cell["mean_R"] = {"pt": round(pt, 3), "ci": [round(lo, 3), round(hi, 3)]}
    cell["median_R"] = round(float(d["r_multiple"].median()), 3)
    if "return_pct" in d:
        pt2, lo2, hi2 = PF.cluster_bootstrap_mean(d["return_pct"], d["ticker"], n_boot=N_BOOT, seed=SEED)
        cell["mean_return_pct"] = {"pt": round(pt2, 3), "ci": [round(lo2, 3), round(hi2, 3)]}
        cell["median_return_pct"] = round(float(d["return_pct"].median()), 3)
    return cell


def _by_band(d: pd.DataFrame) -> dict:
    """SPEC measure 3 — how much of a loss is fill past the stop, by stop-width band."""
    out: dict = {}
    losses = d[d["r_multiple"] < 0].copy()
    if losses.empty:
        return out
    losses["band"] = losses["stop_width_pct"].map(band_of)
    for band, g in losses.groupby("band"):
        beyond = g["r_multiple"].clip(upper=-1.0) + 1.0        # the part past the designed −1R
        designed = g["r_multiple"] - beyond
        out[str(band)] = {
            "n": int(len(g)), "informative": len(g) >= MIN_TRADES,
            "median_stop_width_pct": round(float(g["stop_width_pct"].median()), 3),
            "median_R": round(float(g["r_multiple"].median()), 3),
            "median_return_pct": round(float(g["return_pct"].median()), 3),
            "sum_R": round(float(g["r_multiple"].sum()), 2),
            "sum_designed_R": round(float(designed.sum()), 2),
            "sum_beyond_stop_R": round(float(beyond.sum()), 2),
            "share_beyond_stop": (round(float(beyond.sum() / g["r_multiple"].sum()), 4)
                                  if g["r_multiple"].sum() < 0 else None),
            "gap_through_rate": round(float((g["r_multiple"] < -1.0).mean()), 4),
        }
    return out


def _reexpress(live: pd.DataFrame, hist_median_width: float) -> dict:
    """SPEC measure 4 — the live losses restated at the historical median stop width.

    A UNIT CONVERSION: the same price move divided by a different denominator. It is NOT a simulation of
    a wider stop — 0106 measured that and killed it (ΔSharpe −0.347) — and must never be quoted as one.
    """
    losses = live[live["r_multiple"] < 0]
    if losses.empty or not hist_median_width > 0:
        return {}
    restated = losses["return_pct"] / hist_median_width
    return {"_what_this_is": ("arithmetic re-expression of the SAME price moves at population A's median "
                             "stop width; not a wider-stop simulation (0106 KILL) and not a proposal"),
            "hist_median_stop_width_pct": round(float(hist_median_width), 3),
            "live_sum_R_as_measured": round(float(losses["r_multiple"].sum()), 2),
            "live_sum_R_at_hist_width": round(float(restated.sum()), 2),
            "live_median_R_as_measured": round(float(losses["r_multiple"].median()), 3),
            "live_median_R_at_hist_width": round(float(restated.median()), 3)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-date", default=str(date.today()))
    args = ap.parse_args(argv)

    counts = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    hist, live = historical_trades(), live_trades()
    hist_loss, live_loss = hist[hist["r_multiple"] < 0], live[live["r_multiple"] < 0]
    hist_med_w = float(hist_loss["stop_width_pct"].median()) if len(hist_loss) else float("nan")

    def _diff(col: str, a: pd.DataFrame, b: pd.DataFrame) -> dict:
        """SPEC A1.2 — the between-population difference with its own interval, not two eyeballed ones."""
        pt, lo, hi = PF.cluster_bootstrap_two_sample(a[col], a["ticker"], b[col], b["ticker"],
                                                     n_boot=N_BOOT, seed=SEED)
        return {"live_minus_historical": round(pt, 3), "ci": [round(lo, 3), round(hi, 3)],
                "excludes_zero": bool(lo > 0 or hi < 0)}

    summary = {
        "spec": "diagnostics/research/stop_width/SPEC.md", "class": "MEASUREMENT (zero trials)",
        "n_trials_at_run": counts["cumulative_n_trials"], "run_date": args.run_date,
        "constants": {"hist_window": f"{HIST_START}..{HIST_END}", "n_boot": N_BOOT, "seed": SEED,
                      "min_trades": MIN_TRADES},
        "reading": ("Nothing is adopted. The stop axis is closed in both directions (0105, 0106, 0109); "
                    "measure 4 is a unit conversion, never a wider-stop simulation."),
        "historical": {"all": _cell(hist, "A all"), "losses": _cell(hist_loss, "A losses"),
                       "by_band": _by_band(hist)},
        "live": {"all": _cell(live, "B all"), "losses": _cell(live_loss, "B losses"),
                 "by_band": _by_band(live)},
        "differences_live_minus_historical (losses)": {
            "stop_width_pct": _diff("stop_width_pct", hist_loss, live_loss),
            "return_pct": _diff("return_pct", hist_loss, live_loss),
            "r_multiple": _diff("r_multiple", hist_loss, live_loss),
        },
        "live_width_basis": {
            "n_card_vs_engine_gap_gt_5pct": int((live["width_gap_pct"] > 5.0).sum()),
            "tickers": sorted(live.loc[live["width_gap_pct"] > 5.0, "ticker"].astype(str)),
            "_note": "widths here are the ENGINE basis (return%/R); the card's stop is a different object",
        },
        "_live_bootstrap_caveat": ("11 trades on 11 distinct tickers: the cluster bootstrap degenerates to "
                                   "an ordinary percentile bootstrap at n=11 and is anti-conservative"),
        "reexpression": _reexpress(live, hist_med_w),
    }
    out = OUT_BASE / args.run_date
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    pd.concat([hist.assign(population="historical"), live.assign(population="live")],
              ignore_index=True).to_csv(out / "trades.csv", index=False)
    print(f"stop width -> {out}  | A n={len(hist)} ({len(hist_loss)} losses) | B n={len(live)} ({len(live_loss)} losses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
