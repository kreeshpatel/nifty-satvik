"""M2 — hold-age distribution under the LIVE no-cap exit (descriptive, no tuning, no gate).

Constitution G6 / B-2 substance: under the live config-P exit the weekly branch decides stop /
blow-off pattern / 44w-SMA runner and returns BEFORE any cap check, so neither the 13-week cap nor
the 52-week backstop the P2 exit carried is reachable. Holds are unbounded above. The card still
shows "hold ~65 days".

This answers the menu question — *how old do positions actually get?* — by running the LIVE
configuration (LIVE_DISCIPLINE + LIVE_EXIT + LIVE_STALENESS) and reading out the realised
holding-period distribution. It is DESCRIPTIVE: no parameter is searched, no arm is compared, no
gate is evaluated, nothing is promoted or killed. It spends no trial and no screen.

Reference cell: the same engine with the frozen defaults (13-week cap ON) is reported alongside, so
the no-cap tail is visible as a difference in distribution rather than an absolute number.

    python scripts/diag_m2_hold_age.py [--corrected] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, file_sha256, load_ohlcv_cache  # noqa: E402

import run_bhanushali_weekly_rank as R94  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_STALENESS  # noqa: E402

CAP_WEEKS_REF = 13          # the cap the frozen config applies and the live config does not
P2_BACKSTOP_WEEKS = 52      # the backstop the P2 exit carried, unreachable under config P


def _stats(weeks: list[float]) -> dict:
    if not weeks:
        return {"n": 0}
    a = np.asarray(weeks, dtype=float)
    return {
        "n": int(a.size),
        "median_weeks": round(float(np.median(a)), 1),
        "mean_weeks": round(float(a.mean()), 1),
        "p75_weeks": round(float(np.percentile(a, 75)), 1),
        "p90_weeks": round(float(np.percentile(a, 90)), 1),
        "p99_weeks": round(float(np.percentile(a, 99)), 1),
        "max_weeks": round(float(a.max()), 1),
        "median_days": round(float(np.median(a)) * 5, 0),
        "max_days": round(float(a.max()) * 5, 0),
        "pct_over_13w": round(float((a > CAP_WEEKS_REF).mean() * 100), 1),
        "pct_over_26w": round(float((a > 26).mean() * 100), 1),
        "pct_over_52w": round(float((a > P2_BACKSTOP_WEEKS).mean() * 100), 1),
        "n_over_52w": int((a > P2_BACKSTOP_WEEKS).sum()),
    }


def _run(P, mem, label: str, **kw) -> dict:
    led: list = []
    out = R94.backtest(P, mem, ledger=led, **kw)
    weeks = [float(r["held_weeks"]) for r in led if r.get("held_weeks") is not None]
    rep = {"label": label, "hold": _stats(weeks),
           "exit_reasons": {k: int(v) for k, v in sorted(out["reasons"].items())}}
    if weeks:
        df = pd.DataFrame({"w": weeks, "R": [float(r.get("R", np.nan)) for r in led],
                           "reason": [r.get("reason") for r in led]})
        bins = [0, 4, 13, 26, 52, 104, 10_000]
        labels = ["0-4w", "5-13w", "14-26w", "27-52w", "53-104w", ">104w"]
        df["bucket"] = pd.cut(df["w"], bins=bins, labels=labels, right=True)
        g = df.groupby("bucket", observed=False).agg(n=("w", "size"), mean_R=("R", "mean"))
        rep["by_bucket"] = {str(k): {"n": int(v["n"]),
                                     "mean_R": (None if pd.isna(v["mean_R"]) else round(float(v["mean_R"]), 3))}
                            for k, v in g.iterrows()}
        # what the runners contribute: share of total R earned by the longest-held decile
        cut = float(np.percentile(df["w"], 90))
        tail = df[df["w"] >= cut]
        tot = float(df["R"].sum())
        rep["longest_decile"] = {
            "min_weeks": round(cut, 1), "n": int(len(tail)),
            "share_of_total_R_pct": (round(float(tail["R"].sum()) / tot * 100, 1) if tot else None),
        }
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="M2 hold-age distribution (descriptive)")
    ap.add_argument("--corrected", action="store_true",
                    help="use the corrected (backfilled + alias) universe if available")
    ap.add_argument("--json", default=str(ROOT / "diagnostics" / "research" / "m2_hold_age.json"))
    args = ap.parse_args(argv)

    if args.corrected:
        from run_bhanushali_path1 import corrected_universe
        ohlcv, uni = corrected_universe(), "corrected (pinned + backfill + aliases)"
    else:
        ohlcv, uni = load_ohlcv_cache(OHLCV_CACHE), f"pinned survivor-only ({file_sha256()[:8]})"
    mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    a_set = R94.grade_a_entries(P)

    live = _run(P, mem, "LIVE config P (no time cap, Grade-A, discipline)",
                a_grade=a_set, **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)
    frozen = _run(P, mem, "frozen 0094 defaults (13-week cap ON, all grades)")

    rep = {"universe": uni, "n_names": len(P),
           "note": ("DESCRIPTIVE readout of realised holding periods — no parameter searched, no "
                    "arm compared, no gate evaluated. Spends no trial and no screen."),
           "live": live, "frozen_reference": frozen}
    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"=== M2 hold-age distribution === universe: {uni} ({len(P)} names)")
    for cell in (live, frozen):
        h = cell["hold"]
        print(f"\n{cell['label']}  ({h.get('n', 0)} closed trades)")
        if h.get("n"):
            print(f"  median {h['median_weeks']}w ({h['median_days']:.0f}d) | mean {h['mean_weeks']}w | "
                  f"p90 {h['p90_weeks']}w | max {h['max_weeks']}w ({h['max_days']:.0f}d)")
            print(f"  over 13w {h['pct_over_13w']}% | over 26w {h['pct_over_26w']}% | "
                  f"over 52w {h['pct_over_52w']}% ({h['n_over_52w']} trades)")
            print(f"  buckets: {cell.get('by_bucket')}")
            print(f"  longest decile: {cell.get('longest_decile')}")
        print(f"  exits: {cell['exit_reasons']}")
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
