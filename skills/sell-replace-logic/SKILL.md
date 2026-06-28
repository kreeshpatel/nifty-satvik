---
name: sell-replace-logic
description: Use when adding, modifying, or evaluating any rule that decides when to exit a held position beyond the four mechanical exits (stop/target/trail/time), or any rule that rotates capital from a held name to a fresh candidate. Trigger words include "sell rule", "exit rule", "replace", "rotate", "setup decay", "weak setup", "better opportunity", "conviction collapse".
---

# Sell and Replace Logic

## The honest starting point
We do NOT yet know which sell-beyond-mechanical and replace rules actually work post-cost post-tax on this universe. Section 11 of the strategy doc already shows that many candidate overlays were tested and rejected. The discipline here is:

1. Propose a rule with a written hypothesis (what should the data look like if this rule is real edge?)
2. Test it through the Phase 4 harness against the locked baseline
3. Test it post-tax and at 2x transaction cost
4. Walk-forward across folds; require ≥60% fold-pass rate
5. Test it in the 2022-2026 sub-period, not just the bull years
6. Log verdict in `research/overlay_registry.md`
7. Only PROMOTE to live if the post-tax post-cost Sharpe uplift is outside the bootstrap 95% CI of baseline

A rule that helps in 2017-2021 but hurts in 2022-2026 is REJECTED, not promoted.

## Candidate SELL rules (beyond the four mechanical exits)

Each is a hypothesis to test, not a confirmed edge.

### S1 — Setup decay (signal flip)
**Rule:** Exit if `sma200_slope_63` of the held name turns negative for ≥3 consecutive sessions.
**Hypothesis:** The thesis that got us in was a positive long-term trend slope. If the slope itself has flipped, the thesis is dead — riding it to a mechanical stop wastes drawdown.
**Risk:** May whipsaw in choppy regimes where slope oscillates around zero.

### S2 — Relative strength collapse
**Rule:** Exit if the name's cross-sectional rank by `sma200_slope_63` falls below the 50th percentile of the eligible universe.
**Hypothesis:** Trend strategies harvest *relative* strength. A name that is no longer in the top half of the universe has lost the cross-sectional edge that put it in the portfolio.
**Risk:** In strong bull markets the bar rises and we exit names that are still trending up absolutely.

### S3 — Conviction collapse (requires Phase 5 conviction model)
**Rule:** Exit if today's conviction quintile drops to Q1 (lowest) AND was Q4 or Q5 at entry.
**Hypothesis:** Conviction is a richer per-trade quality score than rank alone. A meaningful conviction collapse signals the multi-feature thesis has degraded, not just one signal.
**Risk:** Conviction model itself must be validated first.

### S4 — Sector regime reversal
**Rule:** Exit if the name's sector median `sma200_slope_63` flips negative.
**Hypothesis:** Individual momentum often rides sector momentum. When the sector rolls over, the individual name usually follows within weeks.
**Risk:** §11 of the doc notes sector overlays were tested and hurt the strategy's lean years. Sector-based exit is a different test from sector-based selection — re-test specifically as exit rule, do not assume the §11 verdict transfers.

### S5 — Earnings event de-risking
**Rule:** Exit if conviction quintile is Q1 or Q2 AND quarterly earnings announcement falls within next 5 trading days. Re-enter after the event if signal still qualifies.
**Hypothesis:** Earnings introduce idiosyncratic gap risk that the 63d ATR-based stop doesn't price correctly. Low-conviction names aren't worth the tail.
**Risk:** Re-entry friction may eat the saved gap risk; requires PIT earnings calendar data.

### S6 — Volume divergence
**Rule:** Exit if 20-day average volume drops >40% from entry-time 20-day average while price holds.
**Hypothesis:** Price holding on declining volume is classic distribution — institutional sellers leaving without forcing the price down yet.
**Risk:** Volume data quality varies; may be noisy on mid-caps.

### S7 — Trend break (raw, not slope)
**Rule:** Exit if close < SMA200 for ≥3 consecutive sessions.
**Hypothesis:** The slope can stay positive while the price has already broken the trend — slope is a lagging confirmation. Direct price-vs-SMA200 is faster.
**Risk:** Slower than the existing ATR stop in some regimes; may not add edge over what we have.

## Candidate REPLACE rules (rotation logic)

### R1 — Cross-sectional opportunity cost gap
**Rule:** Rotate if `(best_unheld_conviction - worst_held_conviction) > 0.3` AND worst held has been in portfolio >20 days.
**Hypothesis:** When the gap between the best available and the worst held is large, the opportunity cost of inertia exceeds the tax/cost of rotation.
**Risk:** Adds turnover; STCG drag is real; may underperform let-winners-run discipline.

### R2 — Decay-vs-fresh divergence
**Rule:** Rotate if held name's conviction has dropped ≥2 quintiles since entry AND a top-3 fresh candidate is in Q5.
**Hypothesis:** A real downgrade of held + real upgrade of available together justify the rotation cost. Either alone does not.
**Risk:** Requires the conviction model to be stable; two-condition trigger may be too rare to matter.

### R3 — Sector concentration relief
**Rule:** If portfolio has ≥5 names in one sector AND a top-5 fresh candidate is in a sector with <2 holdings, rotate the lowest-conviction held name in the over-concentrated sector.
**Hypothesis:** Sector concentration is a tail risk the existing rules don't address. Rotation that *also* reduces concentration is doubly justified.
**Risk:** §11 doc says sector overlays hurt — but this is concentration relief on entry margin, not a hard cap. Different test.

### R4 — Capacity recovery
**Rule:** Rotate from a held name where the position cap binds tightly (sized at <50% of risk-budget intent) into a fresh name where it doesn't, if both have similar conviction.
**Hypothesis:** Cap-bound positions are under-sized; the strategy's edge isn't being expressed. A similar-quality name that fits the risk budget delivers more edge per slot.
**Risk:** Constant slot-shuffling; turnover cost.

## Testing protocol (for any candidate rule)

1. Implement the rule as a function: `def candidate_sell_rule(state, market_data) -> Tuple[bool, str]` returning (exit_yes_no, reason).
2. Run through `src/research/harness.py` against baseline_v0.
3. Required output:
   - ΔCAGR, ΔSharpe, ΔSortino, ΔCalmar, ΔMaxDD — all post-tax post-cost
   - Verdict in 2017-2021 vs 2022-2026 sub-periods separately
   - Walk-forward fold-pass rate
   - Block bootstrap 95% CI on Sharpe uplift
   - Trade count change (does it materially raise turnover?)
4. Combination tests: rules don't compose linearly. If S1 and S3 both PROMOTE individually, also test S1+S3 together — sometimes one cannibalizes the other.
5. Verdict written to `research/overlay_registry.md` with full reasoning, including failure modes if REJECTED.

## Promotion bar (deliberately strict)

PROMOTE only if ALL of:
- Post-tax post-cost ΔSharpe ≥ +0.10
- Post-tax post-cost ΔCalmar ≥ +0.05
- 2022-2026 sub-period shows positive ΔCAGR
- Walk-forward fold-pass rate ≥ 60%
- Bootstrap 95% CI on ΔSharpe excludes zero
- Turnover increase ≤ 30%
- Mechanism is explainable in one sentence to the operator

SHADOW (log signal, don't act) if 4-5 of the above hold.
REJECT otherwise. Log reason in registry.

## What's been tested before (do not relitigate without new information)
See `research/overlay_registry.md`. Key rejections from §11 of the doc:
- Market-regime / dual-momentum gate (kills CAGR)
- Sector overlays for selection
- All RSI/MACD/ROC reversal signals
- Signal-level low-vol blending
- min_hold = 20

New evidence required = new data, new feature, new sub-period, or genuinely different formulation. Re-running an old test in the same way is not new evidence.
