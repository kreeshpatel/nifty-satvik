# Pre-registration — entry-only diagnostic (P2b)

**Status:** PRE-REGISTERED (2026-06-28). **Type:** MEASUREMENT — **0 trials** (no PROMOTE/KILL of a
candidate; it characterises the EXISTING frozen strategy's entry vs exit attribution). n_trials
unchanged (73 arm-level).

**Anchor:** baseline_v0 = 26.1% gross / 23.1% after-tax CAGR (`research/baseline_v0.json`). Never 30.26 / 34.67.

## Question
Is the `sma200_slope_63` top-15 ENTRY rank a standalone, net-of-cost edge, or is the headline
(ENTRY_SIGNAL_ARC §2) dominated by the exit calendar (78% of net PnL batched to the day-10 min_hold
boundary; target+trailing ≈ −stop)?

## Mechanism (one sentence)
If durable-uptrend selection is real alpha, a book that ONLY acts on the entry rank — equal-weight,
fixed 63-day hold, no stop/target/trailing/min_hold — should still earn a positive net-of-cost
expectancy; if instead the edge is the exit machinery batching winners at day 10, the entry-only
book collapses toward zero.

## Design (the runner: `diagnostics/run_long_horizon_entry_only.py`)
- **ARM A — entry-only book:** top-15 by `trend_rank` as slots free, equal-weight, fill at next
  open, hold EXACTLY 63 trading bars, exit at close. No stop/target/trailing/min_hold. Costed
  (shared both-leg brokerage+STT+tiered slippage), swept 1×/2×/3×.
- **ARM B — min_hold sweep:** full FROZEN cfg, min_hold ∈ {5,7,10,12,15}.
- FROZEN cfg via `load_frozen_cfg` (baseline_v0 parity, NOT `derive_all`'s 34.67%).
- P4 demerger quarantine + P5 feature-parity assert wired into the universe build.
- Canonical 682-name cloud universe (local cache degenerate → inadmissible).

## Predicted direction (stated before the run)
Entry-only expectancy POSITIVE but materially below the full strategy's risk-adjusted return (the
exit machinery genuinely adds via trailing/target harvesting + stop loss-cutting). Plausible: a
modest positive avg-return/trade at 1× that thins at 2–3× cost. Two named failure modes:
1. Entry-only collapses to ~0/negative at 2× → edge is exit-timing, not entry (the STOP trigger).
2. Entry-only ≈ full strategy → the exit machinery adds little and the real lever is the entry
   (would re-frame the whole arc toward entry alternatives).

## Decision rules (pre-committed)
- **STOP for owner review** if ARM A avg-return/trade ≤ 0 OR CAGR ≤ 0 at 2× cost (predominantly
  exit-timing) — and thereafter judge every Phase-1 entry candidate on **pure-entry expectancy**,
  not the exit-amplified headline.
- If ARM A is solidly net-positive at 2× (≥2019 folds, paired): the entry rank is the reference the
  Phase-1 candidates must beat; proceed (after the owner reviews) to the candidate race.
- **Verdict policy (P3):** restrict to ≥2019 per-year folds, paired per-fold deltas, never absolute CAGR.

## Output
`diagnostics/cpcv_long_horizon_entry_only.json` (per-arm metrics + per-year + the
`entry_alone_clears_net_of_cost_zero_at_2x` flag) → the one-page "entry vs exit-timing" attribution
appended to `ENTRY_SIGNAL_PHASE0.md`.
