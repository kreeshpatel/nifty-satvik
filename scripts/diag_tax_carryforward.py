"""Quantify the deterministic tax win: FY-based STCG with STCL carry-forward vs the current
per-calendar-year, no-carry-forward after-tax approximation. Reproducible basis for ADR-0007.

All long-horizon holds are < 12 months (max 63d) -> every realized gain is STCG (20%). India taxes
per FISCAL year (Apr-Mar) and lets short-term capital LOSSES offset STCG/LTCG, carried forward 8
years. The repo's `_after_tax_cagr` approximates tax per CALENDAR year with NO carry-forward, so a
losing year pays 0 tax but gives no credit against a later winning year. This script sizes the gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

INIT, STCG = 1_000_000.0, 0.20
L = 1e5


def main() -> int:
    tl = pd.read_csv(ROOT / "research" / "exports" / "tradelog.csv",
                     parse_dates=["entry_date", "exit_date"])
    gross = float(tl["pnl"].sum())
    span = (tl["exit_date"].max() - tl["entry_date"].min()).days / 365.25

    def cagr(final: float) -> float:
        return ((final / INIT) ** (1.0 / span) - 1.0) * 100.0

    # (a) current approximation: per CALENDAR year, tax 20% of max(0, net pnl), no carry-forward
    tax_cal = sum(STCG * max(0.0, v) for v in tl.groupby(tl["exit_date"].dt.year)["pnl"].sum())

    # (b) proper FY (Apr-Mar) with STCL carry-forward (all holds < 12mo => all STCG)
    tl["fy"] = tl["exit_date"].dt.year - (tl["exit_date"].dt.month < 4).astype(int)
    carry, tax_fy = 0.0, 0.0
    for _fy, v in tl.groupby("fy")["pnl"].sum().sort_index().items():
        net = float(v) + carry
        if net > 0:
            tax_fy += STCG * net
            carry = 0.0
        else:
            carry = net

    print(f"span {span:.2f}y   gross pnl {gross / L:+.1f}L   gross CAGR {cagr(INIT + gross):.2f}%")
    print(f"(a) calendar-year, NO carry-forward : tax {tax_cal / L:.1f}L -> after-tax {cagr(INIT + gross - tax_cal):.2f}%")
    print(f"(b) FY + STCL carry-forward         : tax {tax_fy / L:.1f}L -> after-tax {cagr(INIT + gross - tax_fy):.2f}%")
    print(f"deterministic tax win (b - a): {(tax_cal - tax_fy) / L:.1f}L saved = "
          f"{cagr(INIT + gross - tax_fy) - cagr(INIT + gross - tax_cal):+.2f}pp after-tax CAGR")
    print("per-FY net pnl (L):",
          {int(k): round(v / L, 1) for k, v in tl.groupby("fy")["pnl"].sum().sort_index().items()})
    print("\nRead: the deterministic loss-set-off win is small (~+0.35pp) because a <63d-hold book "
          "rarely straddles FY boundaries. The larger after-tax uplift some overlays show is the "
          "UNCERTIFIABLE return edge, not free tax money (ADR-0007).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
