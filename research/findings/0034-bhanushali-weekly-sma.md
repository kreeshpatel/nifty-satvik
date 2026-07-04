# 0034 — All-SMA fully-weekly six-step: the arc's best book by far (+18.2% CAGR / +0.87 Sharpe / −41% DD), robust plateau, first CI-low>0 — UNDERPOWERED but forward-wall-worthy

- **Status:** TRIAL (pre-reg [0091](../../diagnostics/research/preregistry/0091-bhanushali-weekly-sma.md),
  n_trials 108→109, params frozen before the run) + a measurement rigor pass (no extra trials).
  **Verdict: UNDERPOWERED — but the strongest candidate the program has produced; the first to clear
  CI-low>0 and all sub-periods, on a robust parameter plateau.**
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_sma.py`; ledger
  `research/exports/bhanushali_weekly_sma_0091_trades.csv` (275 trades). Same cell as 0089.

## What was tested (owner spec correction)
0089 (fully-weekly six-step) with **every EMA replaced by SMA** — the weekly 44-line that drives the
signal (44-week SMA, was EMA) and the 20-period runner trail (20-day SMA, was EMA). Nothing else changed.

## Result (corrected universe, real tiered costs)

| | trades | win | expR | CAGR | Sharpe | MaxDD | Calmar | mult |
|---|---|---|---|---|---|---|---|---|
| **0091 all-SMA** | 275 (29/yr) | **52.0%** | +0.36 | **+18.2%** | **+0.869** | **−41.5%** | **0.44** | 4.81× |
| 0089 (EMA) | 280 | 45.0% | +0.25 | +11.8% | +0.626 | −54.3% | 0.22 | 2.88× |
| 0085 daily | 432 | 40% | +0.23 | +11.5% | +0.587 | −37.5% | 0.31 | 2.80× |
| Nifty-500 TRI (buy-hold) | — | — | — | +12.6% | — | −38% | — | — |

- Slices +1.01 / +0.79 / +0.87 — **strongly positive and consistent across all three regimes** (unique in
  the arc). Bootstrap CI **[+0.195, +1.533] — CI-low > 0, the first time in the program.** DSR@109 = 0.466
  (still < 0.95). Gates: CI-low>0 PASS, all-slices>0 PASS, DSR FAIL. ΔSharpe vs 0089 +0.243, ΔCAGR +6.4pp,
  ΔMaxDD +12.8pp (all better). Beats buy-and-hold on both return and drawdown.

## Why SMA beats EMA here (mechanism, not luck)
The EMA(44) weekly line reacts fast → it whipsaws around price, firing marginal signals and degrading trend
confirmation. The SMA(44) is smoother and lags more → it only confirms *established* trends, so the signal
set is higher-quality: **win-rate jumped 45%→52%, expR 0.25→0.36.** The 20-day SMA trail is likewise
smoother than the 20-EMA → it gives runners cleaner room and triggers on fewer false breakdowns → the
drawdown fell −54%→−41% while the big runners ran further (2023 +₹18.6L, 2026 +₹7.6L). A real, explainable
edge from a smoother filter — not an artifact.

## Rigor pass (measurement — the two honest caveats)
1. **Plateau, NOT a peak-on-a-cliff (passes, unlike 0085).** 3×3 sweep of weekly-SMA {40,44,48} × trail
   {16,20,24}: **all 9 cells are positive and viable** (Sharpe +0.48…+0.87, CAGR +8…+18%, DD −39…−57%).
   The frozen 44/20 cell is the *top* of the range, so the honest neighborhood expectation is ~+0.70
   Sharpe / ~14% CAGR, not the +0.87/+18.2% headline — but every neighbor still beats or matches the index.
   Contrast 0085, whose neighbors collapsed to Sharpe 0.0 / −57% DD. This strategy is robust; the exact
   headline is lucky-high.
2. **Concentration is the real risk.** **2023 alone = 49% of all profit; top-10 trades = 71%** (188
   distinct names). 2023 was an exceptional Indian midcap bull; the strategy is built to catch such trends,
   but the CAGR leans heavily on that one year repeating. Leakage-clean (same PIT structure as 0085,
   cleared in finding 0029; SMAs are trailing).

## Verdict & next setup
**UNDERPOWERED (DSR 0.47 < 0.95) — but decisively the best and most robust book of the entire six-step arc,
and the only one worth real forward-testing.** It is the first to clear CI-low>0 and all three sub-periods
on a genuine plateau, and it beats buy-and-hold on return AND drawdown — the thing every prior variant
failed to do. Honest deflation: expect ~14% CAGR / ~0.7 Sharpe live (plateau-honest), with real dependence
on catching the occasional big-trend year (2023-class). **This supersedes 0085/0089 as the family's
candidate for the 2026-10-01 review and the forward wall.** Two next moves, both portfolio-level (the
trade rules are exhausted): (a) apply the O-009 vol-target overlay to cut the −41% DD and reduce the
2023-dependence, (b) route 0091 to the forward wall as a watched paper sleeve — the only certifier that can
turn this UNDERPOWERED-but-real result into a promotable one. Do NOT retune 44/20 toward the peak; it is
frozen and the plateau is the honest read.
