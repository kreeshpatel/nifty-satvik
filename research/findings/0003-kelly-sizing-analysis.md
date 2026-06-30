# 0003 — Kelly criterion for long-horizon sizing: useful as a ceiling, not as a sizer

- Status: **DECIDED — do NOT build a Kelly sizer.** Kelly endorses the current scheme + re-derives the
  planned C3 tilt (and predicts it underpowered). Recorded so "add Kelly sizing" is not re-litigated.
- Date: 2026-07-01   Prompted by: owner question ("is the Kelly criterion useful here?").
- Method: 9-agent adversarial analysis (theory / empirical / program-history / conviction-connection
  lenses → 4 adversarial critics → synthesis), grounded in config.json, portfolio.py (base_risk_qty),
  baseline_v1.json, overlay_registry.md. All Kelly numbers are upper bounds on an edge ~25% likely real.

## Bottom line
Kelly is useful here only as a **discipline and a ceiling**, not a sizing formula. Run honestly
(continuous payoff, covariance-aware, edge-uncertainty-shrunk) it says the book already sits at
**~quarter-Kelly** (`k = deployed-vol ÷ Sharpe ≈ 0.18–0.22`) — exactly right for an edge whose
block-bootstrap Sharpe CI [−0.02, 1.43] straddles zero (DSR 0.246) at an already-accepted −46% maxDD.
The only thing literal Kelly adds is a growth-optimal *size-up*, which our DD ceiling + mean-preserved
Stage-D charter + fiduciary duty all forbid.

## Why (the load-bearing facts)
- The binary `f*≈12.8%` is an artifact (collapses a continuous, trailing-dominated payoff onto two
  points; it is in loss-units, not notional). The honest objects: continuous single-bet full Kelly
  ~70–130% notional/name; portfolio full Kelly ~2.9–4.0× gross. Both absurd as literal targets.
- The 3%-risk knob is largely **inert** — the 15% cap binds for ~every name; we run a 15%-notional-cap
  book at ~1.0× gross (cash-capped). The no-borrow cash cap is a robust covariance haircut that can't
  blow up the way an estimated `Σ⁻¹μ` would (infeasible PIT on 13×13 non-stationary, μ of uncertain sign).
- **Correlation, not per-trade edge, governs safe size.** Naive per-name Kelly summed over ~12.87
  correlated names over-bets >5× (each name's Kelly weight is only `1/(1+(n−1)ρ)` of independent).
- Four decisive objections: estimation error (over-bets a maybe-phantom edge; penalty one-sided to
  ruin), correlation (handled by cash cap + O-009 vol-target), drawdown/fiduciary (full Kelly → ~50%
  chance of 50% DD; unacceptable for ~10 clients), redundancy (STRATEGY_FULL §8: "the v1 Kelly/quality
  sizer is not used"; 0020 conviction-size multiplier = +0.000, CI [0,0] every fold).

## Connection to Stage-C/C3 (conviction sizing)
Stage-D's mean-preserved quintile tilt **is** conviction-scaled fractional Kelly (redistribute the
fixed Kelly budget, don't lever up). So Kelly = a re-derivation of the planned C3 trial, not a new
lever. With C2 IC 0.056 (≪ ~0.3 tradeable), sizing IR ≈ IC·√breadth ≈ 0.20 (overstated — trades
correlated), and a tilt that cannot lift the mean by construction, Kelly **predicts UNDERPOWERED →
SHADOW/KILL**, mirroring 0020. The variance-reduction it could buy overlaps the already-promoted O-009.

## Recommendation (acted/decided)
- **DO** keep the frozen kernel as-is; Kelly endorses quarter-Kelly for this edge/DD.
- **DO** (new) adopt `k = deployed-vol ÷ Sharpe` as a **governance ceiling**: never exceed half-Kelly
  (k ≤ 0.5). Makes the conservatism intentional + monitorable (guards against silent drift if the book
  concentrates or vol regime shifts).
- **RUN** the conviction tilt only as the already-planned **C3 arm** (mean-preserved m≈[Q1 0.8 … Q5 1.2]
  on risk_per_trade, edge map fit walk-forward on prior folds only, 1-day lagged, 15% cap binding,
  flag-gated + golden-byte-identical when off); hold to the 7-criterion bar; bump n_trials once before
  the cloud run; expect a clean null and treat it as a valid registry result, not a reason to retune.
- **DON'T** build a Kelly sizer; **DON'T** raise the 3%/15% knobs to "get closer to Kelly" (cash is
  ~fully deployed — it would only concentrate, a separate CONCENTRATE_8-type decision); **DON'T** route
  drawdown reduction through sizing (that is the deferred Stage-G tail hedge).
