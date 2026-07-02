# 0077 — Multi-factor residual momentum as the sole ranker: does stripping factor exposure improve the shape?

- **ID:** 0077 (Entry-Signal Arc; external_edge_ideas candidate #3, Blitz-Huij-Martens 2011). Owner-approved 2026-07-02.
- **Registered:** 2026-07-02, BEFORE the run. **TRIAL** (sole-ranker swap, 1 arm) →
  **cumulative_n_trials 86 → 87, incremented BEFORE the run**.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg, corrected universe,
  2017-01-01..2026-06-30; FF-India factors `data/ff_india_factors.parquet` (Market + HML, PIT-safe).
- **Non-relitigation (required):** O-002 KILLed *single-beta* residual momentum ("no improvement over
  raw slope"). This is the **multi-factor (Market + Value/HML) residual** — the L5 genuinely-new
  variant flagged by `methodology-synthesis` + external_edge_ideas #3. New formulation; not a re-run.

## Hypothesis
Ranking on residual momentum — momentum computed on returns with common Market + Value exposure
regressed out — improves the strategy's **shape** (less-negative skew, higher Sortino, better Calmar,
shallower DD) vs the total-return `sma200_slope_63` trend signal, by reducing the time-varying factor
bets that unwind in a value/growth rotation (the −31.6pp residual-factor leg of the 2024-25 DD).
Falsifier: the residual-mom sole-ranker does NOT beat `sma200_slope_63` on skew/Sortino/Calmar AND
does not survive the continuous-slice 2022-26 window → KILL. DSR-certification is expected to fail at
~34 windows and is NOT the verdict (per the shape/forward-wall grading decision).

## Candidate (sole-ranker swap; C4 protocol)
Residual-momentum score, per ticker, monthly: regress the trailing **252** daily returns on
`[const, mkt, hml]` (OLS), take residuals, score = **IR of residuals over t−252…t−21** (skip the
recent 21d, per BHM). Computed at each month-end, applied to the NEXT month (strict-before), cross-
sectionally percentile-ranked to [0,1] per day, and **injected as the rank column** — the full frozen
strategy + the entry-only book, paired same-cache vs the `sma200_slope_63` base (exactly the C4 swap).
Effective active window ≈ 2019-2026 (residual mom needs 252d of factor history from the 2017-09 factor
start). SMB deferred (data-gated) → Market+Value 2-factor residual.

## Method
`scripts/run_residual_momentum.py`: base_panel (trend_rank) vs cand_panel (residual-mom rank), each
through `simulate` on the pinned universe; paired 63-day block bootstrap (n=5000) of ΔSharpe **and
ΔSortino**, Δskew, DSR at n_trials=87, continuous-slice 2022-26, ≥2019 fold-pass, turnover, after-tax.
Report skew / Sortino / Calmar / MaxDD for BOTH arms as the PRIMARY axes.

## Decision rule (pre-committed) — SHAPE-first, not DSR-certification
This is graded on **shape + forward wall**, because ~34 windows cannot certify a moderate edge (the
0076/0071 lesson). PRIMARY: does the residual-mom arm improve **skew AND Sortino AND Calmar** vs base,
AND hold the continuous-slice 2022-26 window? If yes on shape but ΔSharpe CI straddles 0 / DSR < 0.95 →
**SHADOW / forward-wall watch** (the honest status for a shape-positive, sample-uncertifiable signal),
NOT KILL. If it fails the shape axes or the 2022-26 slice → **KILL**. A PROMOTE would still need the
full bar + forward wall + owner sign-off; this run is EVIDENCE only.

## Leakage contract (skills/leakage-audit)
Factor series PIT-safe (HML `bp` via `value_quality_series` merge_asof backward/strict on availability
= period_end+90d). Residual regression is trailing-only (returns ≤ t). Score computed at month-end t,
applied to dates > t (strict-before, merge_asof(backward, allow_exact_matches=False)). No `fwd_*` in
the rank. Same PIT-masked universe as base (survivorship-consistent). SMB deferred.

## Skeptical prior (state it)
O-002 (single-beta residual) found no improvement; C4 confirmed `sma200_slope_63` beats mom_252_21 /
mom_126 / donchian as a sole ranker. Those were single-beta / total-return; multi-factor residual is
untested and BHM report ~2× Sharpe. But the strategy's edge is moderate (0008: 2× random) and residual
construction adds estimation noise thin net of Indian costs. Most likely outcome: at best a **shape**
improvement (skew/Sortino) with flat/UNDERPOWERED return — a forward-wall watch, not a promotion.
KILL/SHADOW is a first-class, expected outcome; do NOT retune the window toward a pass.
