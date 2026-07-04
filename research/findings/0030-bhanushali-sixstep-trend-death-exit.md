# 0030 — Trend-death exit (EMA44 stall / deep-6.5%) on all positions: worse on every axis, and it did NOT free capital — KILL

- **Status:** TRIAL (pre-reg [0087](../../diagnostics/research/preregistry/0087-bhanushali-sixstep-trend-death-exit.md),
  n_trials 104→105, params frozen before the run). **Verdict: KILL** (negative continuous slice per the
  pre-committed rule; also worse Sharpe, worse DD, and it failed its own design goal).
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_sixstep_stall.py`; ledger
  `research/exports/bhanushali_sixstep_stall_0087_trades.csv` (528 trades). Same cell as 0084/0085.

## What was tested
0084 entry/stop/targets byte-identical; the 3-close-below-SMA44 `ma_breach` rule replaced by two
daily-EMA44 trend-death rules applied to ALL open positions: **stall** (EMA44 rose <0.5% over the
trailing 10 sessions) OR **deep** (close >6.5% below the EMA44) → sell the whole position next open.
Owner motivation: free the capital locked in stalled positions (findings 0026/0029). Entry deliberately
left unchanged — the withdrawn recycle idea's T+1-only entry was the KILLed lever, not re-tested here.

## Result (corrected universe, real tiered costs)

| | trades | win | expR | CAGR | Sharpe | MaxDD | mult |
|---|---|---|---|---|---|---|---|
| **0087 trend-death exit** | 528 (56/yr) | 36.9% | +0.14 | **+3.5%** | **+0.268** | **−55.9%** | 1.39× |
| 0084 reference (same cell) | 476 | 38.7% | +0.18 | +8.6% | +0.477 | −37.2% | 2.19× |
| 0085 runner-trail | 432 | 39.6% | +0.23 | +11.5% | +0.587 | −37.5% | 2.80× |

Slices **−0.20** / +0.39 / +0.38 (2017-18 negative → gates FAIL). CI [−0.489, +0.956]; DSR@105 = 0.024.
**ΔSharpe vs 0084 = −0.209.** Exit mix: stall 162 + 32 half, deep 25 + 5 half, stop 192, target3 103.

## Root-cause readout (REQUIRED)
1. **It did not free capital — the whole premise fails.** Cash-skipped fills **78,922 vs 0084's 79,116**
   (essentially unchanged); median hold only 22d→18d. The book is **capacity-bound, not selection-bound**:
   it is fully invested because 2% risk × ~15 concurrent names exhausts the cash, and selling a dead name
   just lets the next equally-mediocre queued signal fill the freed slot. Faster exits cannot unlock
   capital when the replacement is drawn from the same signal pool — the lock is a *sizing* property, not
   an *exit* property.
2. **The stall rule clips winners mid-pause** (the exact skeptical-prior risk). It fired **194 times** —
   a 2-week-flat EMA is a normal consolidation inside a strong trend, so the rule sells the IRFC/SWANENERGY
   class of runner during its base-building, then the name breaks out without us. This is why expR fell
   0.18→0.14 and the +3R target hits dropped.
3. **Drawdown got WORSE (−37→−56%).** Selling on a flat MA doesn't cut tail risk — the candle-low stop and
   the deep-6.5% rule already handle downside; the stall rule mostly exits *sideways* names near breakeven
   while leaving the actual drawdown drivers (gap-downs through the stop) untouched. Net effect: churn out
   of winners, keep the losers' path — lower return, deeper DD.
4. **Costs compound it:** 56 trades/yr at shorter holds → more legs; gross +2.8% is already near zero, and
   the trend-death churn adds friction that the thin edge can't carry.

## Verdict & next setup
**KILL.** Worst arm of the six-step family (0022 −1.6 → atr4 +0.397 → 0084 +0.477 → 0085 +0.587 →
0086 +0.444 → **0087 +0.268 with a −56% DD and a negative slice**), and it disproves its own thesis: the
capital lock is not an exit problem. Per findings 0027/0029 and now 0087, the locked slots ARE the
eventual top-10 trades; cycling out of them faster cycles out of the profit. **The only registered lever
for the capital/lock and the CHOP-bleed is portfolio-level** — vol-target the sleeve's deployed equity
(O-009 mechanism, already shipped for the base) or size the sleeve smaller inside a multi-sleeve ERC book
(O-018). Do NOT re-propose exit-acceleration or hold-shortening on this funnel; it is now twice-killed
(withdrawn recycle idea + 0087). **0085 remains the family's best book** for the 2026-10-01 review.
