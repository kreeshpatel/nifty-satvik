"""0130 — the SIZING-EXCLUSION BOUND: what the funding bias costs, or saves.

Pre-registration: `diagnostics/research/preregistry/0130-sizing-exclusion-bound.md`
(owner sign-off 2026-08-06; amendments A1-A3 written before this file was run).
**MEASUREMENT class** — screen-ledger row 16, appended before the run. `n_trials` stays 138.

## What this prices

The trade-population census found the funded book is not a representative sample of its own signal
population: `shares = sizing_eq x 2% / (entry - stop)`, so notional is inversely proportional to stop
width, and **0 of the 1,249 tightest-stop signals were funded in 9.5 years**. Per trade the excluded
quintile dominates (+0.972R vs +0.224R) — but ~6 wide-stop positions fit where 1 tight-stop position
consumes 70% of the book, and 6 x 0.224 > 0.972. Armchair arithmetic flips sign. This measures it.

**Per amendment A1 the deliverable is a PRICE, not a verdict.** The headline is the magnitude and
its CI in % of equity per year. The escalation floor (+-20%/yr, derived in the pre-reg §4) is
four-fifths of a 24.69%/yr book, so almost nothing clears it and a below-floor result was expected
before this file existed. It decides whether the result escalates to the owner, not whether it is
real.

## The two arms, and the one thing that must not happen

* **Arm A — actual.** The 255 funded trades exactly as the record produced them.
* **Arm B — equal-notional comparator.** Same weekly candidate queue, same CRS fill priority, but
  size taken from the engine's *existing* stop-width-INDEPENDENT term (`sizing_eq x cap / entry`,
  `R94:873-874`) at the frozen live cap **0.20**. Tight-stop signals thereby become affordable.
  Affordability is evaluated at **full deployment — 5 concurrent seats** — and **not** by simulating
  the cash carry path.
* **Clairvoyant leg.** The same 5 seats filled with perfect foresight instead of by CRS: a ceiling
  no real rule can reach.

**The binding constraint (pre-reg §1.4).** No equity curve, no cash path, no portfolio Sharpe /
CAGR / MaxDD for any arm. Producing one would flip this study to trial class and require an
`n_trials` increment first. Both arms are therefore priced on a FIXED reference equity of EQ0 with
no compounding, which is what keeps them commensurable and keeps this a bound.

## Units — both, because R is not comparable across these arms

Arm A is risk-parity, so the engine's own assert makes **1R exactly 2% of equity** (`R94:884, 889`).
Arm B is notional-parity, so 1R is worth a different amount of money depending on stop width — which
is precisely binder section 8.2's named exception, and why the pre-registered gate is stated in % of
equity rather than in R.

* **R** is price-based, gross of costs: `(exit - entry) / (entry - stop)`.
* **% of equity** is net of costs: `net_pnl / EQ0`, where `net_pnl` already carries both cost legs.

Reporting only R would reproduce the exact trap the census documented.

Output: `diagnostics/research/foundation_audit_2026Q3/sizing_exclusion_bound_0130.json`
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
OUTDIR = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = OUTDIR / "sizing_exclusion_bound_0130.json"

EQ0 = 1_000_000.0          # fixed reference equity; no compounding, by design (pre-reg §1.4)
CAP = 0.20                 # frozen: the live LIVE_DISCIPLINE value. No sweep, no second value.
SEATS = int(1 / CAP)       # 5 — "full deployment", the stated approximation
YEARS = 9.4867             # 2017-01-02 .. 2026-06-29, the record's own span
FLOOR_PCT = 20.0           # the escalation floor, % of equity per year (pre-reg §4 derivation)
BOOT, SEED = 5000, 20260806


def _slot_select(pop: pd.DataFrame, seats: int, key: str, ascending: bool) -> pd.DataFrame:
    """Fill `seats` concurrent slots from the signal population, in date order.

    A slot frees on its trade's exit date. When several signals arrive the same day, they are
    ordered by `key`. This is occupancy accounting, NOT a cash simulation: no equity is tracked, no
    curve is produced, and every position is the same fraction of a fixed reference equity.
    """
    df = pop.sort_values(["entry_date", key], ascending=[True, ascending]).reset_index(drop=True)
    busy: list[pd.Timestamp] = []            # exit dates of currently-held slots
    taken = np.zeros(len(df), dtype=bool)
    for i, (ed, xd) in enumerate(zip(df["entry_date"], df["exit_date"])):
        busy = [b for b in busy if b >= ed]  # free every slot whose trade has closed
        if len(busy) < seats:
            busy.append(xd)
            taken[i] = True
    return df[taken].copy()


def _arm_stats(d: pd.DataFrame, weight_pct: pd.Series, label: str) -> dict:
    """Both units. `weight_pct` is each trade's contribution in % of EQ0."""
    R = d["R"].astype(float)
    eq = weight_pct.astype(float)
    yr = d.groupby(d["entry_date"].dt.year)
    return {
        "arm": label,
        "n_trades": int(len(d)),
        "trades_per_year": round(len(d) / YEARS, 2),
        "sum_R": round(float(R.sum()), 2),
        "R_per_year": round(float(R.sum()) / YEARS, 3),
        "mean_R": round(float(R.mean()), 4),
        "win_rate": round(float((R > 0).mean()), 4),
        "equity_pct_total": round(float(eq.sum()), 3),
        "equity_pct_per_year": round(float(eq.sum()) / YEARS, 4),
        "mean_equity_pct_per_trade": round(float(eq.mean()), 4),
        "median_stop_width_pct": round(float(d["risk_pct"].median()), 3),
        "median_ext_pct": round(float(d["ext_pct"].median()), 3),
        "disaster_n": int((R <= -1.5).sum()),
        "disaster_share_pct": round(100.0 * float((R <= -1.5).mean()), 2),
        "worst_single_equity_pct": round(float(eq.min()), 4),
        "disaster_equity_pct_total": round(float(eq[R <= -1.5].sum()), 3),
        "per_year_equity_pct": {str(y): round(float(v), 3)
                                for y, v in eq.groupby(d["entry_date"].dt.year).sum().items()},
        "per_year_n": {str(y): int(len(g)) for y, g in yr},
    }


def _boot_delta(a_eq: np.ndarray, b_eq: np.ndarray) -> dict:
    """CI on the per-year equity difference, by resampling TRADES within each arm.

    The arms are not paired — Arm B contains trades Arm A never took — so the difference is
    bootstrapped as a difference of two independent sums, each divided by the same span.
    """
    rng = np.random.default_rng(SEED)
    d = np.empty(BOOT)
    for i in range(BOOT):
        sa = rng.choice(a_eq, size=len(a_eq), replace=True).sum()
        sb = rng.choice(b_eq, size=len(b_eq), replace=True).sum()
        d[i] = (sb - sa) / YEARS
    return {"point": round(float((b_eq.sum() - a_eq.sum()) / YEARS), 4),
            "ci95_low": round(float(np.percentile(d, 2.5)), 4),
            "ci95_high": round(float(np.percentile(d, 97.5)), 4),
            "p_sign_positive": round(float((d > 0).mean()), 4),
            "draws": BOOT}


def main() -> int:
    pop = pd.read_parquet(OUTDIR / "trade_population.parquet")
    pop["entry_date"] = pd.to_datetime(pop["entry_date"])
    pop["exit_date"] = pd.to_datetime(pop["exit_date"])

    # ── Arm A — the record's own funded trades, priced on the fixed reference equity ───────────
    A = pop[pop["funded"]].copy()
    a_eq = 100.0 * A["net_pnl"] / EQ0                     # each trade's % of EQ0, net of costs

    # ── Arm B — equal notional, CRS priority, 5 seats ─────────────────────────────────────────
    # Every position is CAP of equity, so a trade's contribution is CAP x its own net return.
    B = _slot_select(pop, SEATS, key="rank", ascending=False)
    # a position is CAP of equity, so its contribution in % of equity is CAP x its own return %
    b_eq = CAP * B["net_pct"]

    # ── Clairvoyant leg — same seats, perfect foresight instead of CRS ─────────────────────────
    C = _slot_select(pop, SEATS, key="net_pct", ascending=False)
    c_eq = CAP * C["net_pct"]

    armA = _arm_stats(A, a_eq, "A_actual_risk_parity")
    armB = _arm_stats(B, b_eq, "B_equal_notional_cap0.20")
    armC = _arm_stats(C, c_eq, "C_clairvoyant_ceiling")

    delta = _boot_delta(a_eq.to_numpy(float), b_eq.to_numpy(float))
    delta_clair = round(float((c_eq.sum() - a_eq.sum()) / YEARS), 4)

    # concurrency actually deployed, per arm (max simultaneous holdings)
    def _max_conc(d: pd.DataFrame) -> dict:
        ev = ([(t, 1) for t in d["entry_date"]] + [(t, -1) for t in d["exit_date"]])
        ev.sort()
        cur = mx = 0
        for _, s in ev:
            cur += s
            mx = max(mx, cur)
        span = pd.date_range(d["entry_date"].min(), d["exit_date"].max(), freq="W")
        occ = [int(((d["entry_date"] <= w) & (d["exit_date"] >= w)).sum()) for w in span]
        return {"max_concurrent": mx, "mean_concurrent": round(float(np.mean(occ)), 2),
                "median_concurrent": float(np.median(occ))}

    for arm, d in ((armA, A), (armB, B), (armC, C)):
        arm.update(_max_conc(d))

    per_year_delta = {}
    ay = a_eq.groupby(A["entry_date"].dt.year).sum()
    by = b_eq.groupby(B["entry_date"].dt.year).sum()
    for y in sorted(set(ay.index) | set(by.index)):
        per_year_delta[str(y)] = round(float(by.get(y, 0.0) - ay.get(y, 0.0)), 3)
    signs = [v for v in per_year_delta.values()]
    n_pos = sum(1 for v in signs if v > 0)

    res = {
        "_class": "MEASUREMENT — 0130 sizing-exclusion bound. Screen row 16. n_trials unchanged 138.",
        "_framing": "PER AMENDMENT A1 THE DELIVERABLE IS A PRICE, NOT A VERDICT. The headline is the "
                    "magnitude and its CI in % of equity per year. The escalation floor is "
                    "four-fifths of the book, so a below-floor result was expected before this ran; "
                    "it decides escalation, not reality.",
        "config": {"EQ0": EQ0, "cap": CAP, "seats_full_deployment": SEATS, "years": YEARS,
                   "escalation_floor_pct_equity_per_year": FLOOR_PCT,
                   "approximation": "affordability at full deployment; NO cash-path simulation, no "
                                    "equity curve, no Sharpe/CAGR/MaxDD (pre-reg §1.4)"},
        "population": {"n_signals": int(len(pop)), "n_funded": int(len(A))},

        "HEADLINE": {
            "_statement": "difference in % of equity per year, Arm B (equal-notional) minus "
                          "Arm A (actual risk-parity). POSITIVE = the funding bias COSTS the book; "
                          "NEGATIVE = the bias SAVES the book.",
            "delta_equity_pct_per_year": delta["point"],
            "ci95": [delta["ci95_low"], delta["ci95_high"]],
            "p_positive": delta["p_sign_positive"],
            "clairvoyant_delta_equity_pct_per_year": delta_clair,
            "escalation_floor_pct": FLOOR_PCT,
            "above_escalation_floor": bool(abs(delta["point"]) >= FLOOR_PCT),
        },

        "arms": {"A": armA, "B": armB, "C_clairvoyant": armC},
        "per_year_delta_equity_pct": per_year_delta,
        "per_year_sign_consistency": f"{n_pos}/{len(signs)} years positive",
        "units_note": "R is price-based and GROSS of costs; % of equity is NET of costs. In Arm A "
                      "1R == 2% of equity exactly (engine assert R94:884,889). In Arm B it does "
                      "not, which is why the gate is stated in % of equity.",
        "seat_check_vs_more_slots": {
            "arm_B_max_concurrent": armB["max_concurrent"],
            "arm_B_mean_concurrent": armB["mean_concurrent"],
            "more_slots_non_diluting_band": "4-5 names (22-26 slice Sharpe 1.21); 7 -> 0.97; 10 -> 0.81",
            "_note": "pre-reg §2.1 / amendment A2: a CLEAR is NOT evidence for a sizer change "
                     "unless it holds at a seat count inside the non-diluting band",
        },
    }
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps(res["HEADLINE"], indent=2))
    print("\nARMS")
    for k in ("A", "B", "C_clairvoyant"):
        a = res["arms"][k]
        print(f"  {a['arm']:<30} n={a['n_trades']:>4} ({a['trades_per_year']:>5.1f}/yr) "
              f"sumR={a['sum_R']:>8.1f} ({a['R_per_year']:>6.2f} R/yr) "
              f"eq%/yr={a['equity_pct_per_year']:>7.3f} "
              f"conc max={a['max_concurrent']} mean={a['mean_concurrent']:.2f} "
              f"medstop={a['median_stop_width_pct']:.2f}% dis={a['disaster_n']}")
    print("\nper-year delta (eq %/yr):", res["per_year_delta_equity_pct"])
    print("sign consistency:", res["per_year_sign_consistency"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
