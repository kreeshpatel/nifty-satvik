# 0004 — Chart-structure features (support/resistance & breakout-of-structure)

- **ID:** 0004
- **Registered:** 2026-06-02
- **Holdout:** unseen-universe (Holdout #2, immediate confirmation) → forward-wall
  (Holdout #1, decisive). Dev folds are used ONLY to generate the feature set and
  retrain the candidate — never to confirm the hypothesis (see `../HOLDOUT.md`).
- **n_trials (cumulative):** ~50 (conservative upper estimate of all model/strategy
  variants tried across the program — feature ablations, gate moves, regime/sweep
  gates, ensemble-weight schemes, Phase-A variants, v2-lean, etc.; must be tallied
  precisely from `diagnostics/` + `retrain_history.json` before the DSR read.
  Over-counting is the safe direction for Deflated-Sharpe deflation).
- **Status:** PENDING

## Motivation (the HFCL failure mode)

All 79 current features are trailing transforms of past price/volume. Measured on
HFCL (2026-06-02 audit): the model sat in watchlist purgatory for months
(46/80 days conf ≥0.75, predicting +9–13%), cleared the 0.92 BUY gate on only
2/80 days, and — critically — its confidence *fell* to 0.773 exactly as the stock
surged +30% (₹75→88). The confidence head down-rates extended names because the
trailing features (distance-from-52w-high, overbought RSI, EMA extension) all say
"too far, too fast." Adding a 90th trailing feature cannot fix this; the gap is a
*different kind* of signal: where price sits relative to **structure** (horizontal
support/resistance), and whether it is **breaking** that structure with conviction.
A chartist enters HFCL on the break of a multi-month ceiling; our model must wait
until the move is already in trailing momentum.

## Hypothesis

Augmenting `V1_FEATURES` with a small set of **chart-structure** features —
computed only from past OHLCV (no new data source) — produces a retrained ensemble
that has **higher after-cost per-trade expectancy on the unseen universe than the
current 79-feature ensemble**, by entering structural breakouts earlier rather than
chasing trailing momentum. Predicted direction: positive delta in per-trade
expectancy; predicted secondary: a higher share of large (+20% / 30d) moves entered
at/near the breakout rather than post-run.

Candidate feature set (all rolling, point-in-time, no lookahead — exact spec to be
frozen in the runner before training):
- `dist_to_resistance_pct` — distance to the nearest horizontal resistance (a
  swing-high cluster / local maxima band over a 60–120d lookback).
- `dist_from_support_pct` — distance above the nearest horizontal support.
- `breakout_of_structure` — signed: +1 when today closes above a resistance level
  that capped price for ≥N prior bars, with volume ≥ X× its 20d average; −1 on the
  symmetric breakdown; 0 otherwise.
- `resistance_tests_count` — how many times the level was tested before the break
  (more tests → stronger break).
- `consolidation_range_pct` — height of the pre-breakout base (tight base → cleaner
  signal), distinct from the existing `range_compression`.

These encode price *position relative to structure* and *the break event*, which
the current momentum/oscillator features do not.

## Holdout & procedure

1. **Dev (hypothesis generation only):** freeze the feature spec; retrain all three
   ensemble siblings on the rolling window via `runners.retrain_ensemble` with the
   augmented `V1_FEATURES`; run the walk-forward gate. A dev-fold pass is NECESSARY
   but NOT sufficient — it cannot confirm the hypothesis (multiple-comparisons trap).
2. **Confirmation (immediate):** run the unseen-universe OOS
   (`diagnostics/run_oos_unseen_universe.py --ensemble`) for BOTH the augmented model
   and the current 79f baseline on the SAME 145 unseen tickers, same period, same
   costs. This is the primary read.
3. **Decisive (slow):** the augmented model, if it confirms, is then a candidate for
   the forward wall (0003-style) — never promoted to live on dev/unseen alone.

## Primary metric

**Delta in mean after-cost per-trade return (%) on the unseen universe**
= `expectancy(augmented) − expectancy(79f baseline)`, both measured by
`bootstrap.bootstrap_metric(mean_return)` on the same unseen-universe trade set,
with a 95% bootstrap CI on the paired difference. Costs honest (brokerage + STT +
slippage + ADV floor) or the result is void.

## Secondary / diagnostic

WR delta + CI; per-year breakdown (must not be carried by one year); **early-entry
capture** — among realized +20%/30d moves, the share entered within the first 5
trading days of the breakout vs the baseline; feature importance of the new columns
in the confidence + return heads (a structure feature that earns 0 splits is dead,
as `sector_momentum_20d` was before 0002); trade-count (must stay within the gate's
50% floor — a "better" model that trades 3× less is overfitting the gate).

## Decision rule (fixed in advance)

- **SUPPORT (weak — one immediate holdout):** augmented per-trade expectancy CI
  lower bound > 79f baseline point estimate on the unseen universe, AND WR not down
  > 3pp, AND DSR > 0.95 at the current cumulative `n_trials`, AND ≥2 of the new
  features earn non-trivial importance. → escalate to the forward wall.
- **KILL:** augmented expectancy CI includes or sits below baseline, OR the new
  features are dead (near-zero importance), OR WR degrades > 3pp. → structure
  features don't add orthogonal signal; stop.
- **INCONCLUSIVE:** CIs overlap without a clear lower-bound separation → treat as no
  evidence; do not promote.

A SUPPORT result can only justify a forward-wall trial, never live promotion.

## Notes / risks pre-committed

- Survivorship: the unseen universe drops delisted tickers (same caveat as 0001) —
  read the immediate result as *suggestive*, the forward wall as decisive.
- Lookahead is the prime hazard for "resistance" features: a level must be built
  ONLY from bars strictly before the evaluation bar. The runner will be checked with
  the same truncation test used in the 2026-06-02 pipeline audit (feature[D]
  unchanged when future bars are appended) before any metric is trusted.
- Requires a retrain → ensemble parity invariant applies; all three siblings retrain
  together via the now-ensemble-aware orchestrator.

## Result

**Premise pre-check (2026-06-02, hypothesis-generation — NOT confirmation).**
Implemented the candidate features in `src/data/chart_structure.py` (standalone,
not yet wired into V1_FEATURES, so no retrain triggered). Two dev checks:
- **Lookahead:** truncation-invariance test passes (0/5 features change when future
  bars are appended) — `tests/test_chart_structure.py`. Point-in-time safe.
- **Does structure lead on HFCL?** `dist_to_resistance_pct` fell steadily
  37% (Dec) → 7.5% (Mar 12) — price pressing the ceiling for weeks — then to −9.1%
  on 2026-04-15 with `breakout_of_structure` firing +1 (Apr 10–15). Crucially the
  breakout fired *exactly* when the ML model's confidence FELL to 0.773 on the
  +30% surge: the structure feature is orthogonal to (and corrective of) the
  trailing-momentum blind spot. One stock is anecdote; this only clears the
  kill-early gate and authorizes the real test below.

Premise PASSES → proceed to the registered confirmation (wire into V1_FEATURES →
ensemble retrain → unseen-universe OOS vs the 79f baseline → forward wall). That
step is heavy (full training data + 3-sibling retrain) and is the actual evidence
under the decision rule above; the pre-check is not.

**Confirmation result (2026-06-02) — INCONCLUSIVE → do not promote (effectively KILL the as-features approach).**

*Importance screen* (84f retrain, 1.24M samples): ESCALATE — 4 of 5 features earn
non-trivial split importance: `resistance_tests_count` 2.88%/#12 ret, 2.23%/#11
conf; `dist_to_resistance_pct` 2.75%/#14, 1.53%/#15; `dist_from_support_pct`
2.35%/#17, 1.21%/#19; `consolidation_range_pct` 1.23%/#24, 0.75%/#33.
`breakout_of_structure` is DEAD (0.01%/0.07% — the sparse signed event flag earns
almost no splits). Caveat flagged at screen time: in-sample fit barely moved
(return_corr 0.538 vs 0.532; conf AUC 0.729 vs 0.725) — importance ≠ profit.

*Unseen-universe OOS* (Holdout #2; same 145 tickers, 2021-2025, honest costs;
single-model 84f candidate vs the 79f live model):

| | per-trade after-cost | WR | trades | Sharpe |
|---|---|---|---|---|
| 79f baseline | +4.093% [2.85, 5.31] | 68.9% | 357 | 2.76 |
| 84f augmented | +4.194% [2.90, 5.49] | 67.9% | 352 | 2.79 |

**Delta +0.10%/trade — deep within noise.** CIs overlap almost entirely; the
augmented CI lower bound (2.90) is NOT > the baseline point (4.09), so the
pre-registered SUPPORT rule is NOT met. WR ticked DOWN 1pp; per-year mixed and
WORSE in the most recent year (2025: +0.93% vs +1.07%... baseline +2.07%).

**Verdict: per the decision rule, INCONCLUSIVE (overlapping CIs, no lower-bound
separation) → no promotion, no escalation to the forward wall.** Chart-structure
information is *used* by the model but is **redundant with the existing momentum
features for per-trade expectancy** (likely correlated with `dist_from_20d_high`,
`breakout_20d`, etc.). The discipline did its job — caught this with a ~10-min
screen + ~5-min OOS, before any heavy ensemble retrain or deployment.

**What this implies:** the HFCL miss is fundamentally a GATING/TIMING problem
(confidence de-rated *on* the surge), not a missing-feature problem. Adding
features to the SAME 0.92-gated model does not change which names clear the gate.
This raises the priority of **0005 (latch/gating logic)** and of using structure
as a SEPARATE breakout-entry TRACK rather than as ML inputs to the existing model.
The 84f wiring lives on branch `feat/0004-chart-structure-screen` (NOT merged);
the standalone feature module + lookahead test remain on main as reusable parts.

_(pre-registration above this Result section is immutable)_
