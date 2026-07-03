# 0027 — Runner trail (EMA20 −4%, 63d cap) on the six-step funnel: best exit geometry yet (+0.59 net), UNDERPOWERED

- **Status:** TRIAL (pre-reg [0085](../../diagnostics/research/preregistry/0085-bhanushali-sixstep-runner-trail.md),
  n_trials 102→103, params frozen before the run). **Verdict: UNDERPOWERED.**
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_sixstep_runner.py`; ledger
  `research/exports/bhanushali_sixstep_runner_0085_trades.csv` (432 trades). Same data/cost cell as 0084.

## What was tested
0084 unchanged except runner management: after the +2R half-book, the remainder drops the +3R target and
the 44-SMA-breach rule and rides `stop = max(prev, EMA20 × 0.96)` (ratchet-only), capped at 63 trading
days from original entry. Non-runners keep the exact 0084 exits.

## Result (corrected universe, real tiered costs)

| | trades | expR | CAGR | Sharpe | MaxDD | mult | 2022-26 slice |
|---|---|---|---|---|---|---|---|
| **0085 runner-trail NET** | 432 | **+0.23** | **+11.5%** | **+0.587** | −37.5% | **2.80×** | **+0.63** |
| 0084 target-capped NET (same run conditions) | 476 | +0.18 | +8.6% | +0.477 | −37.2% | 2.19× | +0.33 |

ΔSharpe +0.110 (informational). Slices +0.25 / +0.73 / +0.63 all positive. Bootstrap CI [−0.137, +1.188],
DSR@103 = 0.211 → gates FAIL → **UNDERPOWERED** per the pre-committed rule. Erratum sensitivity: identical
(no INDIAMART trade intersects the two pinned bad bars under these exits).

## Root-cause readout (REQUIRED)
1. **The tail pays for the trail.** Per-runner the trail is WORSE on average than the old cap (blended R
   mean +2.12 vs the guaranteed +2.5) — the tight EMA20−4% cuts many runners at their first normal
   pullback, as the skeptical prior expected. But 33 of 132 runners exceed +2.5R (max **+8.37R**;
   LAXMIMACH 2017 +6.5R time-capped), and that right tail lifts the book's expR +0.18→+0.23 and CAGR
   +8.6→+11.5. Same mechanism 0071/0076 found on the momentum book: expectancy lives in not truncating
   winners; the give-back is real but smaller.
2. **The 2022-26 slice is where it shows** (+0.33→+0.63): the choppy regime is exactly where a ratchet
   trail that banks trend legs beats a fixed +3R that either hits late or round-trips via MA-breach.
3. **Fewer trades (432 vs 476)** — runners occupy slots ~2× longer (med 42d), so the cash-constrained
   book recycles less; the per-trade quality gain outweighs the frequency loss.
4. **Still uncertifiable** — CI width ~1.3 at ~46 trades/yr; the DSR wall (0.211 at n=103) is unchanged.
   Tax note: max hold 97 trading days (<365 calendar) → all STCG; no tax-regime change vs 0084.

## Verdict & next setup
**UNDERPOWERED — recorded, not relitigated.** Fourth exit-geometry datapoint on the 44-SMA funnel
(taught KILL −1.6 → atr4 +0.397 → scaled+MA-breach +0.477 → **runner-trail +0.587**): a monotone story
that this funnel's small edge is exit-determined and improves as winners are truncated less. No cfg
change; 0085 joins 0084 + Path-B in the **2026-10-01 review packet** as the strongest variant of the
swing-sleeve family. Do NOT sweep trail widths/EMAs toward a pass — any new lever needs its own pre-reg.
