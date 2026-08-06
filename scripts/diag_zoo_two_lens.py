"""THE ZOO QUESTION — STAGE1's per-origin table, re-expressed in BOTH units with CIs.

Verification/measurement class. Zero trials, zero screens. **NO PROPOSAL IS MADE.** This delivers
numbers and confounds; whether any of it becomes a candidate is the owner's call, and would require
a fresh, population-primary pre-registration.

## Why it could only be done now

The substrate carried `R` but not `net_pnl` / `stt_paid` / `half_px`, so the per-origin table could
only ever be read in R. With those columns carried through (`build_substrate.py`, 2026-08-06) the
same trades can be read in **% of equity** — and the unit resolution showed that on this sizer the
two are the same variable, while % of *position* is not.

## Confounds — read before the numbers

1. **The substrate runs `P2_EXIT`, not the frozen ladder.** `no_time_cap=True`,
   `wk20_trail_pct=0.04`, `blowoff_arm_r=2.5`. The run of record uses the 13-week time cap and the
   default ladder. **These are not the record's engine**, and a per-origin ranking under one exit
   does not transfer to the other.
2. **The substrate's `box` / `sr_pivot` are a different construction from E10's ad-hoc run.** Any
   comparison to E10's numbers is comparing two different detectors.
3. **Origins are assigned by masking priority, not independently.** The zoo detectors are additive
   with `& ~wsig`, so `touch44` has first claim on every name-week and each later origin sees only
   what the earlier ones did not take. The cohorts are therefore not exchangeable.
4. **This is the UNCAPPED per-signal population.** The per-trade-does-not-equal-portfolio wall has
   already been measured on exactly this question: STAGE4 found no sleeve config beats touch-only
   under the cap, and ROUTER found per-branch exits lose (0.71 vs 1.29 on the 2022-26 slice). A
   population-level gap here is **not** evidence of a portfolio-level gap, and the programme has two
   trial-priced results saying so.

Output: `diagnostics/research/foundation_audit_2026Q3/zoo_two_lens.json`
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3" / "zoo_two_lens.json"
EQ0, BOOT, SEED = 1_000_000.0, 10_000, 20260806
STT = 0.001


def _ci(x: np.ndarray, rng) -> tuple[float, float]:
    idx = rng.integers(0, len(x), size=(BOOT, len(x)))
    m = x[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def _ci_delta(a: np.ndarray, b: np.ndarray, rng) -> tuple[float, float, float]:
    """CI on mean(a) - mean(b), independent resampling (the cohorts are disjoint)."""
    ia = rng.integers(0, len(a), size=(BOOT, len(a)))
    ib = rng.integers(0, len(b), size=(BOOT, len(b)))
    d = a[ia].mean(axis=1) - b[ib].mean(axis=1)
    return (float(np.mean(a) - np.mean(b)), float(np.percentile(d, 2.5)),
            float(np.percentile(d, 97.5)))


def main() -> int:
    t = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    for c in ("net_pnl", "stt_paid", "half_px"):
        if c not in t.columns:
            raise SystemExit(f"substrate lacks `{c}` — rebuild with scripts/build_substrate.py")

    # the substrate is built uncapped off a FIXED EQ0, so net_pnl / EQ0 IS % of equity
    t["equity_pct"] = 100.0 * t["net_pnl"] / EQ0
    # % of POSITION needs the share count, which needs half_px (34-40% of trades book the half)
    legs = t["entry"] + np.where(t["half_px"].notna(),
                                 0.5 * t["half_px"].fillna(0) + 0.5 * t["exit_px"], t["exit_px"])
    t["shares"] = t["stt_paid"] / (STT * legs)
    t["position_pct"] = 100.0 * t["net_pnl"] / (t["shares"] * t["entry"])

    t = t[t["R"].notna() & t["equity_pct"].notna()].copy()
    rng = np.random.default_rng(SEED)

    base = t[t["setup"] == "touch44"]
    bR, bE = base["R"].to_numpy(float), base["equity_pct"].to_numpy(float)

    rows = []
    for setup, g in t.groupby("setup"):
        R, E = g["R"].to_numpy(float), g["equity_pct"].to_numpy(float)
        if len(g) < 20:
            rows.append({"setup": setup, "N": int(len(g)), "_note": "N<20, not bootstrapped"})
            continue
        rlo, rhi = _ci(R, rng)
        elo, ehi = _ci(E, rng)
        row = {"setup": setup, "N": int(len(g)),
               "mean_R": round(float(R.mean()), 4), "R_ci95": [round(rlo, 4), round(rhi, 4)],
               "mean_equity_pct": round(float(E.mean()), 4),
               "equity_pct_ci95": [round(elo, 4), round(ehi, 4)],
               "mean_position_pct": round(float(g["position_pct"].mean()), 4),
               "win_rate": round(float((R > 0).mean()), 4),
               "median_stop_width_pct": round(float(g["risk_pct"].median()), 2)}
        if setup != "touch44":
            dR, dRlo, dRhi = _ci_delta(R, bR, rng)
            dE, dElo, dEhi = _ci_delta(E, bE, rng)
            row.update({
                "dR_vs_touch44": round(dR, 4), "dR_ci95": [round(dRlo, 4), round(dRhi, 4)],
                "dR_excludes_zero": bool(dRlo > 0 or dRhi < 0),
                "dEq_vs_touch44": round(dE, 4), "dEq_ci95": [round(dElo, 4), round(dEhi, 4)],
                "dEq_excludes_zero": bool(dElo > 0 or dEhi < 0),
                "both_lenses_agree_and_powered": bool(
                    (dRlo > 0 and dElo > 0) or (dRhi < 0 and dEhi < 0)),
            })
        rows.append(row)

    rows.sort(key=lambda r: -(r.get("mean_equity_pct") or -1e9))
    named = [r for r in rows if r["setup"] in
             ("cup_handle", "box", "double_bottom", "ascending_base")]
    verdict = {
        "question": "do cup / box / double_bottom / ascending_base beat touch44 at POPULATION level, "
                    "with adequate power, in BOTH units?",
        "answer_per_setup": {r["setup"]: {
            "dR": r.get("dR_vs_touch44"), "dR_ci": r.get("dR_ci95"),
            "dEq": r.get("dEq_vs_touch44"), "dEq_ci": r.get("dEq_ci95"),
            "powered_in_both_and_same_sign": r.get("both_lenses_agree_and_powered")}
            for r in named},
        "n_powered_in_both": sum(1 for r in named if r.get("both_lenses_agree_and_powered")),
    }

    res = {
        "_class": "MEASUREMENT — zoo two-lens re-expression. Zero trials, zero screens. NO PROPOSAL.",
        "_confounds": [
            "the substrate runs P2_EXIT (no time cap, 20wk trail, blowoff arm), NOT the frozen "
            "13-week ladder of the run of record",
            "the substrate's box / sr_pivot are a DIFFERENT construction from E10's ad-hoc run",
            "origins are assigned by masking priority (touch44 has first claim), so the cohorts are "
            "not exchangeable",
            "this is the UNCAPPED per-signal population; STAGE4 and ROUTER already measured that the "
            "zoo does not survive the capital cap",
        ],
        "config": {"EQ0": EQ0, "bootstrap_draws": BOOT, "seed": SEED},
        "per_setup": rows,
        "verdict": verdict,
    }
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"{'setup':<16}{'N':>6}{'meanR':>9}{'R CI95':>22}{'eq%':>9}{'eq% CI95':>22}"
          f"{'dR':>9}{'dR excl0':>10}{'dEq':>9}{'dEq excl0':>11}{'BOTH':>7}")
    for r in rows:
        if "mean_R" not in r:
            print(f"{r['setup']:<16}{r['N']:>6}   (N<20, not bootstrapped)")
            continue
        print(f"{r['setup']:<16}{r['N']:>6}{r['mean_R']:>9.3f}"
              f"{str(r['R_ci95']):>22}{r['mean_equity_pct']:>9.3f}{str(r['equity_pct_ci95']):>22}"
              f"{r.get('dR_vs_touch44', 0):>9.3f}{str(r.get('dR_excludes_zero', '—')):>10}"
              f"{r.get('dEq_vs_touch44', 0):>9.3f}{str(r.get('dEq_excludes_zero', '—')):>11}"
              f"{str(r.get('both_lenses_agree_and_powered', '—')):>7}")
    print("\nsetups beating touch44, powered in BOTH lenses:", verdict["n_powered_in_both"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
