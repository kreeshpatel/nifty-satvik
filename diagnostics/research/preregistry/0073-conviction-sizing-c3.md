# 0073 — Conviction-weighted sizing (C3): does a mean-preserved conviction tilt beat flat sizing?

- **ID:** 0073 (Stage C / C3 — ROADMAP Stage-D sizing layer). Owner-approved 2026-07-01.
- **Registered:** 2026-07-01, BEFORE the run. **TRIAL** (PROMOTE/KILL decision) →
  **cumulative_n_trials 79 → 80, incremented BEFORE the cloud run** per the discipline.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`, sha `f8625a8f…52142`), frozen cfg,
  corrected universe, 2017-01-01..2026-06-30. Byte-reproducible.

## Hypothesis
Redistributing per-trade risk toward higher-conviction names (within the existing caps), holding
aggregate deployed risk fixed, improves risk-adjusted return vs flat 3%-risk sizing. C2 found
conviction weakly ranks realised P&L (IC 0.056); this asks whether sizing on it clears the bar.

## Candidate (fixed, mean-preserved by construction)
`cfg["conviction_size"]=True`: scale `risk_per_trade_pct` by a quintile multiplier
(`DEFAULT_CONVICTION_MULT` = {Q1 0.6, Q2 0.8, Q3 1.0, Q4 1.2, Q5 1.4}), **renormalised across each
day's NEW entries to mean 1.0** so aggregate deployed risk is unchanged (redistribution, not size-up
— the Kelly/Stage-D charter). The 15% position cap + 5% ADV cap stay binding (they clip the Q5
overweight). Flag-gated in `portfolio.simulate`; golden byte-identical when off (verified).

## Method
Paired 63-day block bootstrap (n=5000) of ΔSharpe(candidate − base) + DSR(candidate) at n_trials=80,
via the same primitives as `evaluate_overlay`. `scripts/run_conviction_c3.py` on the pinned universe.
Report the **mean-preservation proof** (trade-set overlap ≈ 1.0, deployed-notional ratio ≈ 1.0 — same
selection, same capital, only the split differs) and the governance **Kelly multiple** k = realised-
ann-vol ÷ Sharpe (ceiling 0.5).

## Decision rule (pre-committed) — the 7-criterion promotion bar
PROMOTE-CANDIDATE only if ALL: ΔSharpe CI-low > 0 AND point > 0.30 (NOISE_FLOOR) AND DSR > 0.95
(then the full bar: ΔCalmar ≥ +0.05, 2022-26 positive ΔCAGR, fold-pass ≥ 60%, turnover ≤ +30%
[≈0 here — selection unchanged], mechanism one sentence). Positive point but CI-low ≤ 0 →
UNDERPOWERED. Else KILL. Record the verdict in `overlay_registry.md` + a finding.

## Skeptical prior (state it)
Kelly analysis (finding 0003) + 0020 (conviction-size multiplier = +0.000, CI [0,0] every fold)
both predict **UNDERPOWERED/KILL**: a mean-preserved tilt cannot lift the mean by construction, so any
ΔSharpe must come from variance reduction — which overlaps the already-promoted O-009 vol-target;
and IC 0.056 (sizing IR ≈ 0.20, overstated by trade correlation) is structurally too weak for a +0.30
ΔSharpe. The one genuinely new element vs 0020: a *dispersed* (not ~uniform) quintile tilt on the
pinned baseline_v1, which 0020 never actually applied. KILL/UNDERPOWERED is a first-class, expected,
registry-worthy outcome (ROADMAP tradeoff 4) — do NOT retune toward a pass.
