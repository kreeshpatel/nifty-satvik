# 0033 — Market-regime entry filter on the weekly book: cut CAGR 4.8pp and did NOT fix the drawdown — KILL (and it reveals why)

- **Status:** TRIAL (pre-reg [0090](../../diagnostics/research/preregistry/0090-bhanushali-weekly-regime.md),
  n_trials 107→108, params frozen before the run). **Verdict: KILL** (negative slice; worse on every axis;
  failed its own stated goal).
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_regime.py`; ledger
  `research/exports/bhanushali_weekly_regime_0090_trades.csv` (225 trades). Same cell as 0089.

## What was tested
0089 (fully-weekly six-step) unchanged, plus one rule: take **no new entries** on any day the Nifty-500
TRI's latest completed weekly close is below its 44-week EMA. Open positions managed/exited normally.
Owner hypothesis: stop buying in market downtrends → avoid the losses → higher CAGR and lower drawdown.

## Result (corrected universe, real tiered costs)

| | trades | win | CAGR | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|---|
| **0090 regime-filtered** | 225 | 44.4% | **+7.0%** | **+0.447** | **−55.6%** | 0.13 |
| 0089 (unfiltered) | 280 | 45.0% | +11.8% | +0.626 | −54.3% | 0.22 |

Slices **−0.11** / +0.88 / +0.37 (2017-18 negative → gates FAIL). CI [−0.498, +1.203]; DSR@108 = 0.017.
ΔSharpe −0.179, ΔCAGR **−4.8pp**, ΔMaxDD **−1.3pp (worse)**. Filter was off ~30% of days.

## Root-cause readout (REQUIRED) — the important part
1. **It did not fix the drawdown, and that is the whole lesson.** MaxDD went −54.3% → **−55.6%** (slightly
   worse). Blocking NEW entries cannot rescue capital that is ALREADY invested. The −54% DD comes from
   positions **already open** when the market turns, riding down through the weekly-late exits (finding
   0032). The filter attacks the entry side; the drawdown is an **exit / already-deployed-exposure**
   problem. Wrong tool for the wound.
2. **It cut CAGR 4.8pp by blocking the recovery entries — A5's exact mechanism, fifth confirmation.** Look
   at the good years it shrank: 2020 +₹4.8L→+₹1.8L, 2021 +₹5.8L→+₹2.3L, 2019 +₹2.9L→+₹0.6L. The market is
   below its 44-week EMA precisely at the bottoms, which is exactly when the best pullback entries set up.
   Filtering them out removes the up-leg that follows the reversal — you keep the drawdown and lose the
   rebound.
3. **2024 improved a little** (−₹12L→−₹6.1L) but **2018 got worse** (−₹6.3L→−₹6.9L) — the filter's timing
   is a coin-flip: it helps when the downtrend persists, hurts when the market whipsaws around its 44-week
   line (chops you out of re-entries). Net across regimes: negative.
4. **Fifth straight market-regime / entry-gate failure** (O-001, A5, 0056, 0086, now 0090). The program's
   evidence is now overwhelming: on momentum/pullback books, vetoing entries by market or relative-strength
   regime removes more edge (the recovery trades) than risk. **This is settled — do not re-propose an entry
   regime gate on this family in any form.**

## Verdict & next setup
**KILL.** The honest CAGR truth stands: 0089's +11.8% already trails the TRI's +12.6% buy-and-hold, and
this filter widened the gap to +7.0%. But the trial earned its keep by isolating the mechanism: **the
drawdown is caused by already-open exposure bleeding through late exits, so the only lever that can fix it
is one that reduces DEPLOYED exposure during high-vol/drawdown periods — i.e. portfolio-level
vol-targeting (O-009), not any entry filter.** That is now the single well-motivated remaining test on this
whole arc, and it attacks the exact mechanism this trial exposed. Recommend the next (and likely final)
arm be: apply the shipped O-009 vol-target overlay to the 0089/0085 sleeve's deployed equity and measure
DD + Calmar. Everything at the trade-rule level is exhausted; 0085 (best DD-adjusted) and 0089 (best raw
Sharpe) remain the two candidates for the Oct-1 review.
