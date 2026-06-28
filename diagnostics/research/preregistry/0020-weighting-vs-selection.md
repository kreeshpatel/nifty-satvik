# 0020 — Weighting-vs-selection diagnostic (does the sizing layer add value?)

- **ID:** 0020 (diagnostic, not a sleeve). Prompted by the owner: "selection features may
  be good but the *weightage* that selects/sizes the trades may be bad — then stacking more
  selection signals is pointless."
- **Registered:** 2026-06-09 (BEFORE the run; the question + arms + decision rule fixed first).
- **Holdout:** walk-forward on the locked-base model; RELATIVE arm comparison (same
  selection, varied weighting) so survivorship common-mode cancels → local read trustworthy.
- **Type:** measurement/ablation (no new signal). n_trials unaffected (no promotion claim).

## Question

Hold SELECTION fixed (same model, same gated signals); vary ONLY the weighting/sizing/
ranking layer. Does it ADD value or DESTROY it? If weighting is the bottleneck, fixing it
beats adding selection sleeves; if weighting is neutral, the bottleneck is selection (the
breadth program is the right lever).

## Wiring finding (resolved from code, important)

**The live 0.7–2.0x confidence-sizing multiplier was NEVER active in ANY walk-forward.**
`_simulate` sizes only via a `grade_fn`; `make_backtest_fn` / `run_multihorizon_walkforward`
only ever built bear/vix grade_fns, never `confidence_size_grade_fn`. So every locked-base
number (incl. the 0.81 yardstick) ran **flat-risk** — i.e. the locked base ≈ Arm B, and the
live weighting had **never been validated**. Hook added: `make_backtest_fn(...,
apply_confidence_sizing=True)` (`diagnostics/run_walk_forward.py`).

## Arms (selection fixed; weighting varied)

- **A_live** — conf×return ranking, cap=3/day, + the live 0.7–2.0x confidence multiplier ON.
- **B_flat** — same ranking+cap, multiplier OFF (flat risk_per_trade) = the locked-base config.
- **C_nocap** — flat risk, lift `max_signals_per_day` (take every gated signal).

Decomposition: weighting value-add = A−B; ranking-cap cost = C−B. Primary metric = median
per-fold Sharpe (CAGR reported alongside). Decision: A−B ≤ 0 within paired bootstrap CI →
weighting adds no value.

## Result (run 2026-06-09, `weighting_ablation_local.json`; single-model 14d, embargo-45,
2019–2025, local universe, reproducible)

| arm | med Sharpe | mean Sharpe | med CAGR | WR | trades |
|---|---|---|---|---|---|
| A_live | +0.083 | −0.047 | +0.3% | 49% | 323 |
| B_flat | +0.083 | −0.047 | +0.3% | 49% | 323 |
| C_nocap | +0.415 | −0.005 | +2.3% | 49% | 346 |

- **WEIGHTING value-add (A−B) = +0.000, CI [0.000, 0.000] — IDENTICAL, every fold.** The
  confidence-sizing multiplier adds **exactly nothing**: within the gated band (conf
  0.92–1.0) it is ~uniform (1.79–2.0x), a cosmetic no-op. → **Actionable: the live confidence
  multiplier is a complexity liability with zero benefit; it can be dropped.**
- **RANKING-CAP cost (C−B):** median Sharpe +0.415 vs +0.083 and +2.3% vs +0.3% CAGR look
  better with the cap lifted, BUT the paired per-fold Sharpe CI is +0.042 [−0.05, +0.15] —
  includes 0, NOT significant. Mildly-maybe-helpful; revisit on the corrected universe.

**Verdict: the weighting/sizing layer is roughly NEUTRAL — not a hidden value source being
wasted, and not sabotaging good selection.** It does not gate the program's advantage. →
**The bottleneck is SELECTION, not weighting.** This validates focusing research on the base
selection's strength (0021) rather than the sizing layer, and confirms the breadth program
(adding orthogonal selection) is the right class of lever (not weighting tuning).

**Caveat:** this run's ABSOLUTE Sharpe (~0.08 median) is softened by a short 2-yr initial
training window (vs the locked base's longer window → 0.81). The A−B/C−B RELATIVE deltas are
window-independent and robust; the absolute level here is NOT the true base level.

**Prior weighting kills corroborate** (all rejected): 0016 MV/HRP optimizer (−15.7% CAGR),
0013 regime/vol overlay, B3 percentile sizing, dispersion sizing. Every weighting scheme —
smarter OR the current multiplier — fails to beat flat-risk equal-weight. Weighting is a
solved/neutral problem; the edge is in selection.
