"""UNIT RESOLUTION — which unit is money for this book, established from the identity.

Verification/measurement class. Zero trials, no new hypothesis. Reads committed artifacts only.

## The question

Binder §6/§7/§8 and the trade-population census both circle the same worry: R divides by each
trade's own stop width, so is the R-measured edge a denominator artifact? This settles it by
establishing the arithmetic identity rather than by argument.

## The identity

Under risk-parity sizing the engine solves `shares = sizing_eq x risk / (entry - stop)` and asserts
the result (`R94:884, 889`). Multiply through by the price move:

    gross P&L = shares x (exit - entry)
              = sizing_eq x risk x (exit - entry) / (entry - stop)
              = sizing_eq x risk x R

so **gross equity return = R x risk_fraction, exactly.** R is not a ratio that needs converting to
money; under this sizer it IS money, at 2% of equity per R.

## The one place it does not hold, and why that is a finding

The engine credits the booked +2R half at a **notional 2.0R** rather than at the price it actually
filled (`R94:487-490`). The half is triggered by a weekly CLOSE at or above the target and filled at
the NEXT session's open, so in a trending week it routinely fills well above the target. That makes
the identity exact on trades that never book the half and approximate on those that do — and it
makes published R **conservative**, not inflated.

Outputs `diagnostics/research/foundation_audit_2026Q3/unit_resolution.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = D / "unit_resolution.json"

EQ0, RISK, YEARS = 1_000_000.0, 0.02, 9.4867


def main() -> int:
    U = pd.read_parquet(D / "trade_population.parquet")
    half = U["half_px"].notna()

    # gross P&L, correctly accounting for the half leg (this is why half_px must be carried)
    U["gross_pnl"] = U["shares"] * (U["exit_px"] - U["entry"])
    U.loc[half, "gross_pnl"] = (
        0.5 * U.loc[half, "shares"] * (U.loc[half, "half_px"] - U.loc[half, "entry"])
        + 0.5 * U.loc[half, "shares"] * (U.loc[half, "exit_px"] - U.loc[half, "entry"]))
    U["gross_eq_pct"] = 100.0 * U["gross_pnl"] / EQ0
    U["net_eq_pct"] = 100.0 * U["net_pnl"] / EQ0
    U["R_x_risk_pct"] = 100.0 * U["R"] * RISK
    U["net_pct_of_position"] = 100.0 * U["net_pnl"] / U["gross_in"]

    ident = {}
    for label, g in (("no_half_booked", U[~half]), ("half_booked", U[half]), ("all", U)):
        d = (g["gross_eq_pct"] - g["R_x_risk_pct"]).abs()
        ident[label] = {
            "n": int(len(g)),
            "corr_gross_equity_pct_vs_R_x_2pct": round(float(
                g["gross_eq_pct"].corr(g["R_x_risk_pct"])), 10),
            "max_abs_diff_pp": round(float(d.max()), 8),
            "mean_abs_diff_pp": round(float(d.mean()), 8),
            "corr_net_equity_pct_vs_R_x_2pct": round(float(
                g["net_eq_pct"].corr(g["R_x_risk_pct"])), 10),
        }

    h = U[half].copy()
    h["half_R_actual"] = (h["half_px"] - h["entry"]) / h["risk0"]
    conservatism = {
        "n_half_booked": int(half.sum()),
        "share_of_population_pct": round(100 * float(half.mean()), 2),
        "credited_R_for_the_half": 2.0,
        "actual_half_R_mean": round(float(h["half_R_actual"].mean()), 4),
        "actual_half_R_median": round(float(h["half_R_actual"].median()), 4),
        "understatement_R_per_half_booked_trade": round(
            0.5 * float(h["half_R_actual"].mean() - 2.0), 4),
        "_reading": "published R UNDERSTATES realised money on the 34% of trades that book the "
                    "half; the engine is conservative on winners, not flattering",
    }

    F = U[U["funded"]]
    cross = {
        "funded_sum_R": round(float(F["R"].sum()), 2),
        "funded_R_per_year": round(float(F["R"].sum()) / YEARS, 3),
        "implied_gross_equity_pct_per_year": round(100 * RISK * float(F["R"].sum()) / YEARS, 3),
        "measured_net_equity_pct_per_year_0130": 26.546,
        "difference_is_cost_drag_pp": round(
            100 * RISK * float(F["R"].sum()) / YEARS - 26.546, 3),
    }

    # ── the three lenses ──────────────────────────────────────────────────────────────────────
    U["band"] = pd.cut(U["ext_pct"], [-1e9, 0, 5, 10, 20, 1e9],
                       labels=["<0", "0-5", "5-10", "10-20", ">20"])
    rows = []
    for b, g in U.groupby("band", observed=True):
        rows.append({"ext_band": str(b), "N": int(len(g)),
                     "mean_R": round(float(g["R"].mean()), 4),
                     "mean_net_pct_of_POSITION": round(float(g["net_pct_of_position"].mean()), 4),
                     "mean_net_pct_of_EQUITY": round(float(g["net_eq_pct"].mean()), 4),
                     "median_stop_width_pct": round(float(g["risk_pct"].median()), 2)})
    T = pd.DataFrame(rows)
    for c in ("mean_R", "mean_net_pct_of_POSITION", "mean_net_pct_of_EQUITY"):
        T["rank_" + c] = T[c].rank(ascending=False).astype(int)

    lens = {
        "table": T.to_dict("records"),
        "band_rank_spearman": {
            "R_vs_equity_pct": round(float(T["mean_R"].corr(
                T["mean_net_pct_of_EQUITY"], method="spearman")), 4),
            "R_vs_position_pct": round(float(T["mean_R"].corr(
                T["mean_net_pct_of_POSITION"], method="spearman")), 4),
            "equity_pct_vs_position_pct": round(float(T["mean_net_pct_of_EQUITY"].corr(
                T["mean_net_pct_of_POSITION"], method="spearman")), 4),
        },
        "trade_level_pearson_vs_R": {
            "equity_pct": round(float(U["net_eq_pct"].corr(U["R"])), 4),
            "position_pct": round(float(U["net_pct_of_position"].corr(U["R"])), 4),
        },
    }

    res = {
        "_class": "VERIFICATION — unit resolution. Zero trials; counts unchanged 16 / 1 / 138.",
        "identity": {
            "statement": "under risk-parity sizing, gross equity return = R x risk_fraction EXACTLY",
            "derivation": "shares = sizing_eq*risk/(entry-stop)  =>  shares*(exit-entry) = "
                          "sizing_eq*risk*R",
            "engine_assert": "R94:884, 889 pin risk at 2.00% +- 0.02% of sizing equity on every fill",
            "by_cohort": ident,
        },
        "half_credit_conservatism": conservatism,
        "cross_check_vs_0130": cross,
        "three_lenses": lens,
        "conclusion": {
            "record_uncapped": "R IS the money unit. 1R = 2% of equity, exactly.",
            "live_capped": "% of POSITION is the money unit only under equal-notional sizing; the "
                           "two diverge ONLY where the notional cap binds — live, on 53.4% of trades",
            "proof_that_equal_notional_is_worse": "finding 0130: -10.83% of equity/yr, "
                                                  "CI [-26.33, +4.74], 7/10 years same sign",
        },
    }
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")

    print("IDENTITY")
    for k, v in ident.items():
        print(f"  {k:<16} n={v['n']:>5}  corr(gross eq%, R*2%) = "
              f"{v['corr_gross_equity_pct_vs_R_x_2pct']:.10f}  max|d| = {v['max_abs_diff_pp']:.4f}pp")
    print("\nHALF CREDIT:", json.dumps(conservatism, indent=2))
    print("\nCROSS-CHECK:", json.dumps(cross, indent=2))
    print("\nTHREE LENSES")
    print(T.to_string(index=False))
    print("\nband-rank spearman:", json.dumps(lens["band_rank_spearman"]))
    print("trade-level pearson vs R:", json.dumps(lens["trade_level_pearson_vs_R"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
