# 0010 — Delivery-percentage feature (orthogonal new data)

- **ID:** 0010
- **Registered:** 2026-06-03
- **Holdout:** unseen-universe → forward-wall. Retrain-gated.
- **n_trials (cumulative):** ~55.
- **Status:** PENDING (collector built; backfill + retrain + OOS owed)

## Motivation

Five experiments (0004/0005/0006/0007/0002) confirmed the per-stock model is at
its information ceiling on price/volume/sector data — every re-use of what it
already sees is redundant. Delivery% (deliverable qty ÷ traded qty) is the first
genuinely ORTHOGONAL signal: it measures ownership transfer (conviction) vs
intraday churn — information NOT in price/volume momentum. (HFCL during its surge:
delivery% only 22% — the move was churn, which the model couldn't see.)

## Data reality (from the 2026-06-03 feasibility probe)

NSE `sec_bhavdata_full` (one file/day, all symbols, DELIV_PER) is fetchable but
covers only **~2020-present** (pre-2020 = 404). So delivery% cannot train on
2010-2019. **Design: a 2020-2024-window retrain** — candidate (+delivery) vs a
same-window baseline (no delivery), so the comparison isolates delivery, not the
window. OOS (2021-2025) + forward-wall (2026+) are fully within coverage.

## Hypothesis

Adding delivery-derived features (delivery_pct, its 20-day average, and a
delivery-momentum/divergence term) to the model, retrained on 2020-2024, lifts
after-cost per-trade expectancy on the unseen universe vs a 2020-2024 baseline
trained without them — because conviction (high-delivery accumulation) is
orthogonal to the trailing price/volume signals the model already has.

## Primary metric

Delta in mean after-cost per-trade return (%) on the unseen universe, candidate
(2020-2024, +delivery) vs baseline (2020-2024, no delivery), 95% bootstrap CI on
the paired difference. Honest costs.

## Secondary / diagnostic

Importance of the delivery features in both heads (dead → KILL, like 0004's
breakout flag); WR + Sharpe delta; do high-delivery signals realize better than
low-delivery (the direct conviction test, à la 0008 buckets but on a mapped
universe); large-mover capture intact.

## Decision rule (fixed in advance)

- **SUPPORT:** candidate per-trade CI lower bound ≥ baseline point estimate AND
  ≥1 delivery feature earns non-trivial importance AND WR not down >3pp AND
  DSR>0.95 → escalate to the forward wall.
- **KILL:** no expectancy improvement OR delivery features dead → conviction adds
  nothing beyond what price/volume already encode (the 0004/0002 pattern).
- **INCONCLUSIVE:** overlapping CIs.

## Procedure

1. Backfill NSE delivery% 2020-2026 (`data/delivery_data.backfill`, resumable).
2. Build delivery features (lookahead-safe: each bar uses only that day's + prior
   delivery%); add to V1_FEATURES on a branch (retrain-gated, like 0004's 84f).
3. Rebuild features (2020-2024) → train candidate (+delivery) AND baseline
   (delivery cols zeroed), same window.
4. Unseen-universe OOS both → primary metric. DSR-correct. Forward-wall if SUPPORT.

## Priors

Cautious but the best remaining odds: it's the only un-tested *orthogonal* signal.
Unlike 0004/0002 (redundant re-uses of price/volume), delivery% is new
information. But the 5-KILL streak says the bar is high — expect it to need to
clear the same OOS gate honestly, with the partial-coverage / shorter-window
caveat noted.

## Result
_(appended when run)_

## Run note (2026-06-07, Phase 3 of the balanced program)

Executed under the program's REPRODUCIBLE-ONLY verdict rule (proven necessary by
the 0014 MR sleeve, which non-reproducible noise nearly promoted). Design:
- Delivery features wired into `data_store.enrich_with_layers` as AVAILABLE
  columns (NOT in `feature_columns()`/V1_FEATURES) — live 79f ensemble untouched;
  the `models/v1_delivery_candidate` config (82f) opts in. Lookahead-safety
  re-verified (truncating future leaves past `delivery_pct_20d_avg` unchanged).
- `diagnostics/run_delivery_experiment.py`: per fold trains BOTH the 79f baseline
  and 82f candidate on the identical 2020+ window (initial_train_years=2 → test
  folds 2022-2026), reproducible, then balanced-gates candidate vs baseline.
- Delivery cache (49MB) committed gzipped (16MB) + gunzipped on the runner.
- Workflow: `.github/workflows/delivery-experiment.yml`.

Primary verdict = balanced scorecard (candidate vs baseline) + delivery-feature
importance. SUPPORT only if composite > 0 with floors held AND ≥1 delivery
feature earns real importance AND DSR > 0.95. n_trials advances by 1.

## Result — KILL (2026-06-07, reproducible, post-fix)

First valid run (run 27091620903): the candidate GENUINELY differs from baseline
(after fixing the latent bug where PredictionModel.train ignored config
active_features — PR #66; the v1 run was a no-op). Reproducible same-window
(2020+, test folds 2022-2026), 82f candidate vs 79f baseline:

| metric | baseline 79f | candidate 82f (+delivery) | delta |
|--------|-------------|---------------------------|-------|
| mean Sharpe | 1.122 | 0.838 | **−0.284** |
| Sharpe wins | — | **2/5** | fail |
| WR | 53.2% | 47.6% | **−5.6pp** |
| trades | 305 | 319 | +14 |
| balanced composite | — | **−0.019** | NEGATIVE |
| DSR | — | 0.005 | ≪0.95 |

Delivery features made the model WORSE — fails sharpe_wins, mean_sharpe,
mean_cagr, AND win_rate floors. Per-fold: helps 2022/2023 (+0.08/+0.44) but
badly hurts 2025 (−0.63) and 2026 (−1.23). On the short 2020+ window the 3 extra
features let LightGBM overfit 2020-22 patterns that broke out-of-sample —
classic more-features/limited-data overfitting, caught by the reproducible
walk-forward. **KILL** (the 0004/0002/0008 orthogonal-feature pattern: the model
is at its information ceiling; new features add noise, not edge).
