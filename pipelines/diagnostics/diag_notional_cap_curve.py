"""The notional-cap CONCENTRATION-vs-COLLECTION curve — population arithmetic only.

**VERIFICATION CLASS. Zero trials, zero screens. Counts frozen: screens 15 · sealed opens 1 ·
n_trials 138.** No book is re-run. No Sharpe, no MaxDD, no worst year, no ranking, no recommended
arm. This is the FREE half of the max_notional_pct question: what each cap does to deployed capital
on the EXISTING trade population.

WHAT THIS CANNOT DO — stated first because it is the binding limitation
----------------------------------------------------------------------
It cannot show **which trades a different cap would fund**. Position size feeds the cash path, the
cash path decides which later signals are affordable, and that is inseparable from a book re-run.
Every number here holds the funded set FIXED at the one the substrate actually produced. So this
curve prices the cap's effect on *capital deployment across the trades we took*, never its effect
on *trade selection*.

WHY THERE IS NO RETURN COLUMN — deliberate, not an omission
-----------------------------------------------------------
Sharpe / MaxDD / worst-year per cap is trial-class (arm-level: 5 configs on the honest base) and was
declined. Independently, finding **0113** measured what such a column would be worth: **PBO 46.2%**
over 924 IS/OOS combinations on this exact cfg-lever family, with the in-sample-best config landing
at the OOS **median** (IS 1.239 -> OOS 0.843 vs median 0.835). Within this family, picking the
in-sample-best confers **no OOS selection skill** — so a per-cap return ranking would arrive
pre-discounted to roughly zero decision weight while permanently deflating every future DSR bar.

THE ARITHMETIC (engine-exact, read from the committed sizing line)
------------------------------------------------------------------
`run_bhanushali_weekly_rank.py:868-874`:  sh = min(eq*RISK/(en-st),  eq*cap/en)

  risk_frac   = (entry - stop)/entry, clipped at LIVE max_risk_pct = 0.10 (the live stop cap)
  equity risked = eq * min(RISK, cap * risk_frac)          -> weight w = that / RISK
  notional      = eq * min(RISK / risk_frac, cap)          -> implied single-name exposure

Second approximation, stated: R is held at the UNCAPPED book's realized R. `max_risk_pct` is
modelled on the SIZING side only (it clips risk_frac); a real 10% stop cap would also change each
trade's R and exit path. So the recovery ratio answers "what does the book's realized R translate
to in deployed rupees under each cap", not "what would the book have earned".

Reproduce:
    python scripts/diag_notional_cap_curve.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

START = pd.Timestamp("2019-01-01")          # the programme trusts >=2019 only
RISK = 0.02                                  # run_bhanushali_sixstep.RISK
LIVE_MAX_RISK = 0.10                         # run_bhanushali_cron.LIVE_DISCIPLINE
CAPS = [0.15, 0.20, 0.25, 0.30, None]        # None = unbounded (LIVE minus the notional cap)
EXT_SPLIT = 5.0                              # the ext_band_census <5% core cohort

OUT_JSON = ROOT / "diagnostics" / "research" / "notional_cap_curve.json"
OUT_MD = ROOT / "diagnostics" / "research" / "notional_cap_curve.md"


def weights(risk_frac: np.ndarray, cap: float | None) -> np.ndarray:
    """w = effective equity risked / nominal RISK. Unbounded -> 1.0 everywhere."""
    if cap is None:
        return np.ones_like(risk_frac)
    return np.minimum(RISK, cap * risk_frac) / RISK


def exposure(risk_frac: np.ndarray, cap: float | None) -> np.ndarray:
    """Implied single-name notional as a fraction of sizing equity."""
    risk_sized = RISK / risk_frac
    return risk_sized if cap is None else np.minimum(risk_sized, cap)


def main() -> None:
    print("VERIFICATION CLASS — 0 trials, 0 screens. Counts frozen: 15 / 1 / 138.")
    tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    tr["entry_date"] = pd.to_datetime(tr["entry_date"])
    d = tr[tr["entry_date"] >= START].dropna(subset=["risk_pct", "R", "ext_vs_sma"]).copy()

    rf = (d["risk_pct"] / 100.0).clip(upper=LIVE_MAX_RISK).to_numpy(float)
    R = d["R"].to_numpy(float)
    lo = (d["ext_vs_sma"] < EXT_SPLIT).to_numpy()

    res: dict = {
        "_doc": "Notional-cap concentration-vs-collection curve — population arithmetic, 0 trials.",
        "class": "VERIFICATION — no book re-run, no Sharpe/MaxDD/worst-year, no recommended arm",
        "counts": "screens 15 · sealed opens 1 · n_trials 138 (frozen)",
        "LIMITATION": "cannot show WHICH TRADES a different cap would fund — the funded set is held "
                      "fixed at the substrate's; cap->cash-path->selection is inseparable from a "
                      "book re-run and was declined as trial-class",
        "return_column_absent_because": "0113 PBO 46.2% — within this cfg-lever family the "
                                        "in-sample-best config lands at the OOS median (1.239 -> "
                                        "0.843 vs 0.835), so a per-cap return ranking carries ~zero "
                                        "OOS decision weight and would deflate every future DSR bar",
        "approximation": "R held at the uncapped book's realized R; max_risk_pct=0.10 modelled on "
                         "the SIZING side only (clips risk_frac), not on R or the exit path",
        "population": f"uncapped Stage-1 substrate, entry_date >= {START.date()}, all setups",
        "n_trades": int(len(d)),
        "n_ext_below_5": int(lo.sum()), "n_ext_at_or_above_5": int((~lo).sum()),
        "sizing_constants": {"RISK": RISK, "live_max_risk_pct": LIVE_MAX_RISK,
                             "bind_condition": "cap * risk_frac < RISK  <=>  stop width < RISK/cap"},
        "curve": [],
    }

    for cap in CAPS:
        w = weights(rf, cap)
        ex = exposure(rf, cap)
        row = {
            "cap": "unbounded" if cap is None else round(cap, 2),
            "binds_below_stop_width_pct": (None if cap is None else round(100.0 * RISK / cap, 2)),
            "share_binding_pct": round(100.0 * float((w < 1.0 - 1e-12).mean()), 1),
            # COLLECTION side
            "weight_ext_below_5": round(float(w[lo].mean()), 3),
            "weight_ext_at_or_above_5": round(float(w[~lo].mean()), 3),
            "weight_book_mean": round(float(w.mean()), 3),
            "realized_R_recovery": round(float((R * w).sum() / R.sum()), 3),
            # CONCENTRATION side
            "max_single_name_exposure_pct": round(100.0 * float(ex.max()), 1),
            # the decisive one: how often does the CAP set the position size rather than risk-sizing?
            "share_sized_BY_THE_CAP_pct": (
                0.0 if cap is None
                else round(100.0 * float((np.isclose(ex, cap)).mean()), 1)),
            "p99_single_name_exposure_pct": round(100.0 * float(np.percentile(ex, 99)), 1),
            "share_exposure_over_30pct": round(100.0 * float((ex > 0.30).mean()), 1),
            "share_exposure_over_50pct": round(100.0 * float((ex > 0.50).mean()), 1),
            "concentration_cols_degenerate": (
                None if cap is None else
                f"max/p99 = the cap itself and >30%/>50% = 0 BY CONSTRUCTION (cap <= 0.30); the "
                f"informative column for a bounded cap is share_sized_BY_THE_CAP_pct"),
        }
        res["curve"].append(row)

    res["reading_note"] = (
        "COLLECTION rises and CONCENTRATION rises together — that is the whole tradeoff and it has "
        "no interior optimum visible in these columns, by construction. The unbounded arm's max "
        "exposure is the sizing rule's IMPLIED notional, not a position the book could ever fund: "
        "cash binds first (H5 — cash is the only capacity constraint). It is reported because it "
        "is exactly the runaway the 2026-07-16 guardrail was adopted against.")
    res["structural_finding"] = (
        "The notional cap is not a rare guardrail on this book — it is the POSITION SIZER. With the "
        "live max_risk_pct=0.10 in force, every stop is at most 10% wide, so risk-sizing always "
        "wants at least RISK/0.10 = 20% of equity per name. Any cap at or below 0.20 therefore sets "
        "the size of 100% of positions and the 2%-risk rule never binds. Two different quantities "
        "are easy to confuse here and both statements are true at cap 0.20: the cap sets NOTIONAL "
        "for 100% of trades, while equity RISKED falls below the nominal 2% for the 53.4% whose "
        "stop is narrower than 10% (a trade with an exactly-10% stop sits at the cap AND at full "
        "risk simultaneously).")

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    hdr = ["cap", "risk-sizing under-sized for", "**weight ext<5%**", "weight ext>=5%",
           "book weight", "**realized-R recovery**", "positions sized BY the cap", "max exposure"]
    lines = ["| " + " | ".join(hdr) + " |", "|" + "|".join(["---"] * len(hdr)) + "|"]
    for r in res["curve"]:
        lines.append("| " + " | ".join([
            f"**{r['cap']}**", f"{r['share_binding_pct']}% of trades",
            f"**{r['weight_ext_below_5']}**", f"{r['weight_ext_at_or_above_5']}",
            f"{r['weight_book_mean']}", f"**{r['realized_R_recovery']}**",
            f"{r['share_sized_BY_THE_CAP_pct']}%",
            f"{r['max_single_name_exposure_pct']}%"]) + " |")

    md = ["# Notional-cap curve — concentration vs collection", "",
          "**VERIFICATION CLASS — 0 trials, 0 screens. Counts frozen: screens 15 · sealed opens 1 · "
          "n_trials 138.** No book re-run. No Sharpe/MaxDD/worst-year. **No arm is recommended.**", "",
          f"**LIMITATION (first, because it binds):** {res['LIMITATION']}.", "",
          f"**No return column, deliberately:** {res['return_column_absent_because']}.", "",
          f"Population: {res['population']} — **{res['n_trades']} trades** "
          f"({res['n_ext_below_5']} with ext<5%, {res['n_ext_at_or_above_5']} with ext>=5%).", "",
          "\n".join(lines), "",
          "*(`max exposure` and the >30%/>50% tails are the cap itself / zero **by construction** "
          "for any bounded cap <= 0.30 — see the JSON. The informative concentration column is "
          "`positions sized BY the cap`.)*", "",
          f"**Structural finding.** {res['structural_finding']}", "",
          f"**Reading note.** {res['reading_note']}", "",
          "Reproduce: `python scripts/diag_notional_cap_curve.py`", ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write("\n".join(md).encode(enc, "replace").decode(enc, "replace") + "\n")


if __name__ == "__main__":
    main()
