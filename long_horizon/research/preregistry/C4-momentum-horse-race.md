# Pre-registration — C4 momentum horse-race (Phase 1, Tier 1)

**Status:** PRE-REGISTERED 2026-06-28. **Type:** TRIAL (3 candidate arms). n_trials 73 → **76** (arm-level;
incremented BEFORE the run per the edge-research-pipeline). Anchor = baseline_v0 (26.1% gross / 23.1%
after-tax; `research/baseline_v0.json`). **Overlay type:** selection-re-rank (sole-signal SWAP).

## Question (answers G2)
`sma200_slope_63` was chosen as the max of a ~16-factor screen with **zero multiple-testing
correction** — it was never deflation-tested **as a trading strategy** against its co-equal momentum
factors. Is it genuinely the best **sole entry ranker**, or a selection artifact?

## Mechanism (one sentence)
If `sma200_slope_63`'s win was a multiple-testing artifact, a co-equal raw-momentum factor
(`mom_252_21` 12-1, `mom_126` 6-month, `donchian_pos_126` 126-day channel position) should **match or
beat** it as the sole cross-sectional ranker out-of-sample after the DSR penalty; if it is genuinely
the best trend-quality signal, the alternatives **tie-or-lose** and the entry pick is deflation-confirmed.

## Design
For each signal S ∈ {`sma200_slope_63` (base), `mom_252_21`, `mom_126`, `donchian_pos_126`}: rank the
SAME canonical universe by S → `trend_rank`, then run BOTH (a) the FROZEN full strategy
(`portfolio.simulate`, exit machinery identical) and (b) the **entry-only** book (equal-weight, fixed
63d hold, no exits — the validated Phase-0 pure-rank bar). All arms in ONE run on ONE cache → **paired**
deltas (the cache-vintage ±4pp lesson). FITTED? **No** — these are fixed factors, no learned weights,
so this is rule-only and does NOT need the CPCV embargo (P6); the standard paired walk-forward applies.

## Predicted direction (stated before the run)
`sma200_slope_63` remains the best sole ranker; the 3 alternatives **tie-or-lose** (ΔSharpe ≤ 0 or
within noise) and **none clears the promotion bar** → all KILL as replacements → **entry pick
CONFIRMED** (a SUCCESS that retires G2). Prior evidence (DOSSIER F2 mean IC: slope 0.092 > 12-1 0.086 >
6m 0.063 > donchian 0.054; F4 single-trend beats composites OOS; F5 generalises to unseen) supports
this — C4 is the strategy-level + DSR confirmation the factor-IC work did not provide.

## Failure modes (≥2)
1. **In-sample tie flips OOS.** `mom_252_21` (IC 0.086 ≈ slope 0.092) could match in-sample but fail on
   ≥2019 folds / under DSR — judge on paired ≥2019 fold-pass + DSR, never the pooled in-sample number.
2. **Cache-vintage noise (±4pp).** Absolute CAGR is unstable run-to-run; only the PAIRED same-run
   ΔSharpe + its block-bootstrap CI are signal. A candidate "winning" on absolute CAGR is meaningless.

## kill_criteria (a candidate REPLACES sma200_slope_63 only if it clears the FULL 7-gate bar; default = KILL)
- metric: paired ΔSharpe (full strategy, vs base)        threshold: < +0.10     verdict: KILL-as-replacement
- metric: block-bootstrap CI-low(ΔSharpe), block=63       threshold: ≤ 0          verdict: KILL-as-replacement
- metric: 2022–2026 sub-period ΔCAGR                       threshold: ≤ 0          verdict: KILL-as-replacement
- metric: ≥2019 walk-forward fold-pass                     threshold: < 60%        verdict: KILL-as-replacement
- metric: DSR at cumulative n_trials=76                    threshold: < 0.95       verdict: KILL-as-replacement

## Pre-screen
- [x] Mechanism explainable in one sentence
- [x] Not a decimal-tuned threshold (it's a signal swap, no new param)
- [x] Param count 0 (sole-ranker swap)
- [x] Not a §11 KILL — these are RAW momentum core factors (F2 contract), NOT the killed
      residual/beta-stripped or frog-in-the-pan variants; testing them as the sole ranker is legitimate
- [x] No lookahead — all signals are backward-only (data_store rolling windows); ranked PIT
- [x] >30 signals/yr (the whole top-15 book)

## Output
`diagnostics/cpcv_long_horizon_signal_race.json` — per-signal full-strategy + entry-only metrics,
paired Δ vs base, ≥2019 fold table, sub-period split, block-bootstrap ΔSharpe CI, DSR — and the
verdict per candidate. → finding file `long_horizon/research/findings/` + `overlay_registry.md` row.
