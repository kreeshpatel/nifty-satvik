# Finding 0111 — Selection-model study Phases 0-1: a trained selector BEATS the CRS heuristic OOS (first positive since 0107)

**Type:** MEASUREMENT (0 trials; spec `research/SELECTION_MODEL_SPEC.md`; a trial is spent only at Phase 2).
Feature matrix cached `research/exports/pool_features_0111.parquet` (3045 uncapped-pool signals, PIT).

## Question (owner-directed)
The A-grade selector is an untrained one-feature heuristic (top-5/week by crs_dist, pool IC +0.079). Can a
walk-forward-trained multi-feature model select better on the 3045-outcome pool — with lever-combinations
living as FEATURES inside one model instead of the (all-killed) stacked config filters?

## Protocol
Expanding walk-forward by year (2019-2026), purged (train trades must EXIT before the test year), top-5-per-
week selection, metric = OOS mean R of selections vs CRS top-5 on the same weeks. Bar fixed before running:
beats CRS >= 6/8 years AND pooled delta >= +0.10.

## Results
- **Phase 0 (7 generic features): near-miss.** GBM 6/8 years, delta +0.086 (< +0.10). Logit 5/8, +0.036.
- **Phase 0b (+ problem-aimed context: OI ivz/skew/term/pcr, market breadth, 52w-high dist, signal-flood):
  PASS.** GBM-ext **6/8 years, pooled delta +0.215** (CRS -0.106 -> +0.109). The fade years flip: **2025
  CRS -0.36 -> +0.22**, 2026 +0.21 -> +0.72, 2023 1.24 -> 1.83. New formulation (new features), not a retune.
- **Disaster-veto swap variant: KILL** (2/8, delta -0.02, disaster-rate 36.5% -> 36.3%): disasters remain
  unpredictable at entry even for a model; the lift is ranking QUALITY, not dodging losers.
- **Phase 1 (permutation on the real metric): lift is real but diffuse.** stopw +0.12, breadth +0.08,
  ivz +0.05 lead; no feature positive >5/8 folds; `rank` itself ~0 — the model's edge is INTERACTIONS
  (stop-geometry x breadth x IV-stress), not the CRS feature. skewz and hi52 hurt (would drop in v2 — but
  Phase 2 tests the exact 14-feature spec that passed; trimming after seeing importance is a fitted choice).

## Read
First selection-layer result above the noise floor since 0107, and the first evidence the funnel itself is
improvable: the heuristic leaves OOS-recoverable quality on the table, and the recoverable part concentrates
in the chop/fade years the book bleeds in. Consistent with the program's laws: the selection layer is where
the sample (3045 / ~460 weeks) and the edge both live.

## Caveats (why this is NOT yet an adoption)
4 selector variants were tried (logit/gbm/gbm-ext/veto) — the winner is a selection-of-best; attribution is
fold-unstable; the top-5-per-EVERY-week metric differs from the cash-gated funded book. All three route to
**Phase 2: ONE pre-registered capped-backtest trial** swapping the weekly selector (top-5-CRS -> top-5-GBM,
walk-forward refit, exact 14-feature spec), per-year judged, forward-wall certified — plus the live-infra
question (weekly refit + model versioning) priced in before any adoption.
