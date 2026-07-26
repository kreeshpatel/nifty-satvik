# Selection-Model Study Spec v1.0 — can a trained multi-feature selector beat the CRS heuristic?

**2026-07-27. Status: Phase 0b PASSED (+0.215, 6/8 yrs — finding 0111); Phase 1 done (lift real, attribution diffuse); NEXT = Phase 2 (one pre-registered capped trial).**
Prompt-engineered per `prompt-engineer` (task/constraints/eval fixed BEFORE running; one change at a time;
versioned). Governing house skills: `conviction-features` (feature contract), `leakage-audit` (PIT/purge),
`xgboost-lightgbm` (model tier), `overlay-testing` (final gate), `research-log` (records).

## Task
Learn `score = f(features_at_signal_week)` on the UNCAPPED signal pool (3045 outcomes, 2017-2026) such that
top-K-per-week selection by `score` beats top-K-per-week by `crs_dist` (the live A-grade heuristic) on
WALK-FORWARD out-of-sample per-trade R. Selection layer only — no sizing (C3/0020 killed), no regime
switching (0103 killed), no config filters (0104/0108/0110 killed).

## Why this is fundable when regime-ML was not
3045 labeled trades across ~460 signal-weeks vs 37 independent windows. The selection layer is the one
place the program has both a PROVEN edge (funnel +0.16→+0.48) and a real training sample. Ceiling is
known: hindsight top-255 = +0.72 expR.

## Features (all PIT at the completed signal week; already validated computable this session)
crs_dist; ext_vs_44wSMA; realized vol63; candle body_frac; stop_width; rank-of-week (relative position
among that week's signals); market state (Nifty vs 50d SMA; breadth if cheap); origin (touch/box/SR).
NO fundamentals (0108: no per-trade signal), NO future data. ~8-10 features, that's all — small sample
discipline.

## Model tier (fixed)
Regularized logistic (target: R>0) AND a shallow GBM (depth<=3, target: R) — nothing deeper. If neither
beats the baseline, the answer is "the heuristic is enough" and the study CLOSES.

## Validation protocol (leakage-audit)
Expanding walk-forward BY YEAR: train on trades ENTERED < year Y with EXIT < Y-start (purge: no outcome
bleeding across the boundary; 65d holds ⇒ embargo the last ~3 months of the train window), predict all
year-Y signals, select top-5-per-week, score mean R of selections. First test year: 2019 (2 train years).

## Success criteria (fixed BEFORE Phase 0; the "80% checkpoint" analogue)
- **Phase 0 PASS** iff model-selected OOS mean R beats CRS-selected on the SAME weeks in ≥ 6/8 test years
  AND pooled OOS improvement ≥ +0.10 expR. Anything less = the heuristic stands; study closes, 0 trials.
- **Phase 1** (only on PASS): feature-importance audit (permutation) + stability check.
- **Phase 2** (only after Phase 1): ONE pre-registered capped-backtest trial swapping the selector
  (counted in n_trials; per-year judged; forward-wall certified only). Never adopted on Phase-0 numbers.

## Known traps (encoded up front)
Cross-sectional correlation within weeks (effective n ≈ 460, not 3045 — cluster by week when judging);
the +-10R portfolio noise floor applies at Phase 2 (the selector delta must be LARGE per-trade to survive);
class imbalance mild (46% win); regime drift in feature levels (use within-week relative forms where
possible — the 0110 lesson).
