"""How much does compounding the STCG drag actually cost?

Pre-registration 0001 §5.4 says "STCG is applied at 20% inside the compounding". The implementation
netted the whole tax bill off the FINAL value instead, and said so in its own docstring ("no path
compounding of the tax drag"). Those are different books: tax paid in 2018 is not available to earn
returns in 2019-2026, and the lump-sum version lets it earn for the whole window.

This measures the gap on the real 0001 book, so the corrected after-tax figure replaces the
optimistic one with a number rather than an assertion.

    python pipelines/diagnostics/diag_tax_compounding.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import after_tax_curve  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from nq.validation.metrics import TRADING_DAYS  # noqa: E402
from run_0001_xsec_momentum import BAND, END, START, add_signals, run  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

CAP = 1_000_000.0
STCG = 0.20


def main() -> int:
    print("=== STCG: lump-sum netting vs compounded drag ===\n")
    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    b = p[keep].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == BAND) & b["nms"].notna(),
                         b["nms"], np.nan)
    bt = run(b)

    ec, trades = bt["equity_curve"], bt["trades"]
    yrs = (pd.to_datetime(ec[-1]["date"]) - pd.to_datetime(ec[0]["date"])).days / 365.25
    gross_final = float(ec[-1]["equity"])

    by_yr: dict[int, float] = {}
    for t in trades:
        y = int(str(t["exit_date"])[:4])
        by_yr[y] = by_yr.get(y, 0.0) + float(t["pnl"])
    tax = sum(STCG * max(0.0, g) for g in by_yr.values())
    lump_final = CAP + sum(float(t["pnl"]) for t in trades) - tax
    comp_final = float(after_tax_curve(bt, stcg=STCG)[-1]["equity"])

    sess_yrs = len(ec) / TRADING_DAYS

    def cagr(x: float, y: float = sess_yrs) -> float:
        return ((x / CAP) ** (1.0 / y) - 1.0) * 100.0

    print(f"  window {ec[0]['date']} -> {ec[-1]['date']}")
    print(f"  {len(ec):,} sessions = {sess_yrs:.3f} 'years' at the 252 convention, "
          f"but {yrs:.3f} calendar years")
    print(f"  -> the panel runs {len(ec) / yrs:.1f} sessions per calendar year, not 252\n")
    print(f"  gross                  CAGR {cagr(gross_final):>6.2f}%   final Rs {gross_final:>14,.0f}")
    print(f"  after-tax, lump sum    CAGR {cagr(lump_final):>6.2f}%   final Rs {lump_final:>14,.0f}"
          f"   <- what was reported")
    print(f"  after-tax, compounded  CAGR {cagr(comp_final):>6.2f}%   final Rs {comp_final:>14,.0f}"
          f"   <- what the pre-reg specified")
    print(f"\n  OVERSTATEMENT          {cagr(lump_final) - cagr(comp_final):>6.2f}pp of CAGR"
          f"   Rs {lump_final - comp_final:,.0f} of final value")
    print(f"  total STCG paid        Rs {tax:,.0f}")

    print("\n=== tax by year (net realised gain -> bill) ===")
    for y in sorted(by_yr):
        g = by_yr[y]
        print(f"    {y}   realised Rs {g:>12,.0f}   tax Rs {STCG * max(0.0, g):>11,.0f}")

    print("\n  READING: the gap is the return the tax money would have earned had it stayed in the")
    print("  book, NET of the unrealised gains the old model dropped. The old figure carried two")
    print("  errors pointing opposite ways — no compounding (optimistic) and final value taken as")
    print("  'capital + realised' rather than actual equity (pessimistic).")

    print("\n=== SEPARATE ISSUE: the annualisation convention (programme-wide) ===")
    print(f"  gross CAGR @252-session 'year' {cagr(gross_final):>6.2f}%   <- every pinned result")
    print(f"  gross CAGR @calendar year      {cagr(gross_final, yrs):>6.2f}%")
    print(f"  overstatement                  {cagr(gross_final) - cagr(gross_final, yrs):>6.2f}pp")
    print("  A 'compound ANNUAL growth rate' should annualise by calendar time. Dividing sessions")
    print("  by 252 when the data supplies ~247.6 per year counts 9.32 years where 9.49 elapsed,")
    print("  and a shorter denominator inflates the rate. This affects baseline_v1 and every other")
    print("  pinned CAGR, so it is REPORTED, not silently fixed — changing it re-anchors the pin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
