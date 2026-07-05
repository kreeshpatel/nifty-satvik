# 0035 — Tightening 0091 to "clean" pullback charts DESTROYED it (+18.2%→+0.5%, win 52%→41%) — KILL, and the definitive "backtest > your eyes" lesson

- **Status:** TRIAL (pre-reg [0092](../../diagnostics/research/preregistry/0092-weekly-tightened-pullback.md),
  n_trials 109→110, params frozen before the run). **Verdict: KILL** (two negative slices; worse on every axis).
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_tight.py`; ledger
  `research/exports/bhanushali_weekly_tight_0092_trades.csv` (194 trades). Same cell as 0091.

## What was tested (owner chart-QA spec)
The owner reviewed 0091's live signals against real charts and drew the intended setup: price **dips to a
visibly-rising** 44-week SMA and bounces (good), reject when the **MA is flat/rolling** (bad). Encoded as
three tightenings vs 0091: (1) slope floor — 44w-SMA up ≥3%/13w; (2) tight pullback — low ≤3% and close
≤6% above the MA; (3) quality green (close in the upper half). Everything else = 0091.

## Result (corrected universe, real tiered costs)

| | trades | win | CAGR | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|---|
| 0091 (loose) | 275 | **52%** | **+18.2%** | **+0.869** | **−41.5%** | **0.44** |
| **0092 (tightened)** | 194 | 41% | +0.5% | +0.142 | −61.0% | 0.01 |

Slices −0.12 / +0.82 / −0.18 (two negative → gates FAIL). CI [−0.67, +0.98]; DSR@110 = 0.003.
Head-to-head: ΔSharpe **−0.727**, ΔCAGR **−17.7pp**, ΔMaxDD **−19.5pp worse**, ΔWin **−11pp**. Half the
years negative; the book is essentially break-even with one good year (2020) over many losing ones.

## Root-cause readout (REQUIRED) — the important part
1. **The "ugly" extended names are where the trend money is.** 0091's edge comes from names that had already
   run **6–18% above** the 44-week SMA — the strong, young trends. The tight band (low ≤3%, close ≤6%)
   **systematically excluded exactly those** and kept only the timid, hugging-the-line pullbacks. Those
   resolve WORSE: win-rate fell 52%→41%. The eye is drawn to "safe-looking" setups that have already given
   up their momentum; the market pays for buying strength, not comfort.
2. **A "visibly rising" 44-week SMA is a LATE signal.** The 44-week SMA is deeply lagging — by the time it's
   risen 3% over a quarter, the easy leg is often spent. The slope floor pushed entries later into more
   mature trends with worse forward risk/reward. "Looks like a clean uptrend" ≈ "the trend is old."
3. **Fewer trades → worse drawdown, not better.** 275→194 trades cut diversification; the DD DEEPENED
   −41.5%→−61.0%. Concentration got worse, not better — the opposite of the intent.
4. **Third entry-tightening failure on this family** (0086 RS gate, 0088 weekly-breakout, now 0092). The
   pattern is now overwhelming and mechanistic: **on this momentum-pullback book, making the entry stricter
   removes edge, not noise.** The loose net is loose *because* that's where the money is.

## Verdict & next setup
**KILL.** This is the single clearest demonstration in the program of why we backtest instead of hand-tuning
off charts: a coherent, textbook, obviously-better-looking setup (buy the pullback to a rising MA — a real
taught method) made the strategy **35× worse on Calmar** and half-losing. Had it been shipped off six
good-looking charts, it would have traded a +18% book down to break-even at a −61% drawdown. The owner's
eye was reasonable and the logic sound — the *data* says the opposite, decisively. **0091 (loose) remains
the live forward book; do not tighten its entry filter.** Entry-side tuning on this family is settled
(three kills). The only open levers remain portfolio-level (vol-target the sleeve, O-009) — not the trade
rules. No retuning; the 3%/3%/6% thresholds are frozen at their pre-registered values.
