"""ENG-01 — no-trade band on rebalance drift trims, measured against frozen 0001.

The expectation was written to `research/0001-xsec-momentum/eng-01-no-trade-band.md` BEFORE this
ran. The band is 0.20 of target, derived from the cost structure there. **One value, one run.**
Sweeping a second value would turn this into a search and forfeit the right to call it engineering.

    python pipelines/research/run_eng01_no_trade_band.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import _after_tax_cagr  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from nq.validation.montecarlo import resample_equity_curve  # noqa: E402
from run_0001_xsec_momentum import BAND, END, START, add_signals, run  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

CAP = 1_000_000.0
BAND_WIDTH = 0.20
OUT = ROOT / "research" / "0001-xsec-momentum"


def summarise(tag: str, bt: dict) -> dict:
    m = bt["metrics"]
    mix = Counter(t["reason"] for t in bt["trades"])
    at = _after_tax_cagr(bt, CAP)
    print(f"  {tag:<16} CAGR {m['cagr_pct']:>7.2f}%  after-tax {at:>6.2f}%  "
          f"Sharpe {m['sharpe']:>6.3f}  MaxDD {m['max_drawdown_pct']:>7.2f}%  "
          f"turnover {m['turnover_per_year']:>6.1f}")
    print(f"                   trades {m['n_trades']:>5}  "
          f"trim {mix['rebalance_trim']:>5}  exit {mix['rebalance_exit']:>4}  "
          f"avg positions {m['avg_positions_held']:.2f}")
    return {"metrics": m, "mix": dict(mix), "after_tax_cagr": at}


def main() -> int:
    print("=== ENG-01 — no-trade band vs frozen 0001 ===")
    print("    expectation pre-stated in eng-01-no-trade-band.md · ONE band, ONE run, no sweep\n")

    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    band = p[keep].copy()
    band["rank"] = np.where(band["eligible"] & (band["size_band"] == BAND) & band["nms"].notna(),
                            band["nms"], np.nan)

    base = run(band)
    banded = run(band, rebalance_band=BAND_WIDTH)

    print("=== ARMS ===")
    b = summarise("frozen 0001", base)
    n = summarise(f"band {BAND_WIDTH:.0%}", banded)

    bm, nm = base["metrics"], banded["metrics"]
    d_cagr = nm["cagr_pct"] - bm["cagr_pct"]
    d_at = n["after_tax_cagr"] - b["after_tax_cagr"]
    trim_drop = 1 - n["mix"].get("rebalance_trim", 0) / max(b["mix"].get("rebalance_trim", 1), 1)

    print("\n=== VS THE PRE-STATED EXPECTATION ===")
    checks = [
        ("trim count falls >=50%", trim_drop >= 0.50, f"fell {trim_drop:.1%}"),
        ("turnover falls", nm["turnover_per_year"] < bm["turnover_per_year"],
         f"{bm['turnover_per_year']:.1f} -> {nm['turnover_per_year']:.1f}"),
        ("CAGR +0.3 to +0.7pp", 0.3 <= d_cagr <= 0.7, f"{d_cagr:+.2f}pp"),
        ("Sharpe ~flat (+-0.05)", abs(nm["sharpe"] - bm["sharpe"]) <= 0.05,
         f"{bm['sharpe']:.3f} -> {nm['sharpe']:.3f}"),
        ("MaxDD ~unchanged (+-3pp)", abs(nm["max_drawdown_pct"] - bm["max_drawdown_pct"]) <= 3.0,
         f"{bm['max_drawdown_pct']:.2f} -> {nm['max_drawdown_pct']:.2f}"),
    ]
    for name, ok, detail in checks:
        print(f"  {'MET    ' if ok else 'MISSED '} {name:<26} {detail}")
    print(f"\n  after-tax CAGR {b['after_tax_cagr']:.2f}% -> {n['after_tax_cagr']:.2f}%  ({d_at:+.2f}pp)")
    print("  (after-tax is the number this change exists to move — STCG is 5x the friction)")

    if d_cagr < 0:
        print("\n  ** CAGR FELL. Per the pre-statement that is a finding, not a tuning signal:")
        print("     the rebalancing premium exceeded the costs saved. Revert the band; do NOT")
        print("     try a second width — that would make this a sweep after the fact.")

    mc = resample_equity_curve(banded["equity_curve"], n_paths=5000, seed=20260807)
    print(f"\n=== PLANNING DRAWDOWN ===\n  block {mc.block}d · observed {mc.dd_observed*100:.2f}% · "
          f"p99 {mc.dd_p99*100:.2f}%")

    (OUT / "eng01_results.json").write_text(json.dumps({
        "band": BAND_WIDTH, "base": b, "banded": n,
        "delta_cagr_pp": d_cagr, "delta_after_tax_pp": d_at, "trim_drop": trim_drop,
        "expectation_checks": {k: bool(v) for k, v, _ in checks},
        "planning_dd_p99": mc.dd_p99}, indent=2, default=str), encoding="utf-8")
    print(f"\n  -> {OUT / 'eng01_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
