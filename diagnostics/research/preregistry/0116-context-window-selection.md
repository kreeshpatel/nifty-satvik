# Pre-registration 0116 — The ±1-month context-window study: path-shape selection on the uncapped substrate

**Status:** PRE-REGISTERED (written before any feature is computed). **Date:** 2026-07-27.
**Trial accounting:** Stages A/B are MEASUREMENTS (0 trials, like 0097/0098/STAGE1/STAGE2). **Stage C is
the trial** — `n_trials.json` increments 138→139 immediately before the Stage-C run, not before.

## Relitigation basis (registry-first; required citations)
The selection axis carries closed findings and this study may only reopen it with a NEW formulation:
- **0110** (CRS rank-floor KILL): absolute thresholds on the existing rank break on regime drift.
- **0111/0112** (trained selector): beat the CRS heuristic per-pool OOS (+0.215, 6/8y) but **KILLED at
  the cash gate** (expR fell under capital contention). Its features were bar-level entry-time statics
  (rank, wk_rel, ext, body, vol, stopw, mkt, OI z-scores, breadth, hi52, flood).
- **STAGE2_ml** (2026-07-16, measurement): LightGBM on this same substrate with entry-time statics —
  holdout AUC 0.536; discriminators 52wh-dist / vol-ratio / ATR; and the tri-confirmed wall: *"entry
  quality is NOT visible at entry (bar-level)."*
**What is NEW here (the reopening currency):** (a) the **pre-entry 21-trading-day PATH-SHAPE feature
family** — how price *approached* the signal (grind vs gap, efficiency, drawup/drawdown, compression,
acceleration, volume pattern) — absent from 0111/0112 and STAGE2_ml, both of which used point-in-time
*levels*, not paths; (b) the **post-exit 21-day LABEL family** — grading opportunity-quality separately
from exit-quality, a richer outcome variable than realized R alone. Known-closed ground NOT relitigated:
RSI-oversold, regime entry gate (O-001), the 63d zoo (0079), conviction sizing (C3/0020), Phase-1 entry
levers, daily-confirmation gate (O-022), body/ext/fundamental filters (0104/0108).

## Dataset
`research/substrate/trades.parquet` — the 4,391-trade uncapped substrate (Stage 0-1, live P2 exit,
origin-tagged), rebuilt from the committed `scripts/build_substrate.py` (determinism-guarded: capped
default must reproduce Sharpe 1.1319/255). One row per trade; context windows joined from the daily
OHLCV cache by `scripts/build_context_windows.py` (committed, deliverable 2).

## Window definitions (fixed)
- **PRE-ENTRY window (features):** the 21 trading days ending at the SIGNAL-week Friday close,
  inclusive — i.e. strictly ≤ the entry-decision time; the fill (next week) is outside it. PIT-legal
  by construction.
- **POST-EXIT window (labels only):** the 21 trading days after the exit date, exclusive of it.
- **Leakage firewall (HARD):** no quantity computed from any bar at/after the entry decision may enter
  a selection feature, directly or via an intermediate. Post-exit windows grade; pre-entry windows
  select. Any rule that looks too good is guilty until the leakage-audit clears it.

## Pre-entry feature family — FIXED (path-shape; computed once, no additions after unsealing)
| feature | definition (window = the 21d pre-entry closes/opens/volumes) |
|---|---|
| path_eff | \|total 21d return\| / Σ\|daily returns\| (grind→1, chop→0) |
| gap_share | Σ\|overnight gaps\| / (Σ\|overnight gaps\| + Σ\|intraday moves\|) |
| gap_max | max single-day \|return\| |
| runup21 | max cumulative return within the window (drawup into the signal) |
| dd_hi21 | last close / window high − 1 (how far below the approach high we signal) |
| updays | fraction of up days |
| accel | last-10d return − first-11d return (front- vs back-loaded approach) |
| range_comp | (21d high−low range) / (prior-21d range) — compression(<1)/expansion(>1) |
| vol_burst | mean(volume last 5d) / mean(volume 21d) |
| rs21 | cross-sectional percentile of the 21d return vs the full universe that day |
**Controls (previously tested — conditioning ONLY, never claimed as new):** ext_vs_sma, rank_crs,
atr_pct, dist_52wh, vol_ratio, risk_pct, origin.

## Post-exit label family — FIXED
post_ret21; post_maxup21; post_maxdn21; **exit_too_early** (R>0 & post_maxup21>+10%); **exit_saved**
(post_ret21<−10%); **false_touch** (stop-out & post_maxup21<+5% — never recovered); **noise_stop**
(stop-out & post_ret21>+5% — the whipsaw class); **opp_quality_R** = (max close in [entry, exit+21d]
− entry)/risk — the signal's potential independent of our exit.

## Matched-control discipline (fixed)
Every effect is reported CONDITIONALLY: within ext-band (≤10 / 10-20 / >20%) × CRS-tercile cells,
winners vs losers and kept vs skipped. Ext is the engine (~69% of book R) and ext≈candle-size (r≈0.5);
a candidate must show marginal effect BEYOND those cells. Raw pooled effects are reported but carry no
verdict weight.

## Time split (fixed BEFORE any feature is computed)
- **Train / design years:** entries 2019-01-01 .. 2024-06-30 (pre-2019 excluded as untrusted, per the
  substrate's own split).
- **SEALED validation:** entries 2024-07-01 .. 2026-06-30 (~2y). Opened ONCE, after the feature set and
  the single rule are frozen by an amendment to this file. No second opening.

## Pipeline & pre-committed bars
- **Stage A (measurement):** per-feature marginal effects on train years only — per-trade R (mean AND
  median, with bootstrap 95% CIs), win rate, and label composition (false_touch vs noise_stop rates),
  conditional on the control cells; per-year sign tables. Candidate features must show: pooled
  conditional effect ≥ +0.15R (top-vs-bottom tercile) AND same sign in ≥4 of the 5.5 train years.
- **Rule freeze:** ONE selection rule (a single threshold on one feature, or a fixed unweighted
  combination of ≤2 surviving features), frozen by amendment BEFORE unsealing. No retuning after.
- **Stage B (measurement):** the frozen rule as a filter on the full substrate: kept-vs-skipped
  distributions, conditional on cells, train AND sealed. **Bar:** sealed-set kept-minus-skipped
  conditional ΔmeanR ≥ +0.10 with the train sign, and ≥50% of the train effect size.
- **Stage C (THE TRIAL — increments n_trials):** the rule as a cfg-gated activation filter in the
  capped harness (engine byte-identical when off), continuous-slice, full per-year table vs the
  unfiltered capped base. **Bar:** ΔSharpe ≥ +0.05 AND ΔCAGR ≥ −1.0pp AND ΔMaxDD ≥ 0 AND no year worse
  by >3pp AND 2022-26 slice not worse by >0.05. A rule that wins Stage B and dies at Stage C is
  recorded as a KILL with the 0112-style root-cause (which trades the cash rotated into).

## Named failure modes (before running)
1. **Path features proxy extension/candle-size** — the conditional cells expose this; a feature whose
   effect vanishes within ext-bands is a proxy, not a discovery.
2. **The tri-confirmed wall holds** — path-shape adds nothing beyond bar-level statics; Stage A comes
   back empty. (First-class outcome: closes the pre-entry axis at the path level too.)
3. **Cash-gate death (0112's mechanism)** — per-trade lift that reorders funding and dies at Stage C.
4. **Whipsaw-label leakage temptation** — noise_stop/false_touch are POST-EXIT labels; any attempt to
   "select against false touches" must use only pre-entry features that CORRELATE with the label, never
   the label itself.

## Standing constraints
44-period line is always SMA. Diagnostic-first (uncapped before recap). Continuous-slice sub-period
gates. Engine changes cfg-gated; depgraph regenerated; full suite green after any nq/** edit. Every
number from a committed script.
