# 0011 — Multi-factor residual momentum as the sole ranker (0077): KILL, but the shape/DD mechanism is real

- **Status:** **KILL** as a sole ranker. The skew + drawdown benefit is real and large → reframes as a **blend / conviction / risk-overlay** candidate, not a ranker swap.
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0077-residual-momentum.md`](../../diagnostics/research/preregistry/0077-residual-momentum.md).
- **Type:** TRIAL (1 arm, sole-ranker swap; cumulative_n_trials 86 → 87).
- **Anchor:** pinned `baseline_v1` (`dataset-pin-20260701`); FF-India factors `data/ff_india_factors.parquet` (Market + HML, PIT-safe).

## Hypothesis
Ranking on multi-factor (Market + Value) residual momentum — momentum with common factor exposure
regressed out — improves the strategy's shape (skew / Sortino / Calmar / DD) vs total-return
`sma200_slope_63`, by shedding the factor bets that unwind in a rotation.

## Method
Per name, monthly: OLS of trailing 252d daily returns on `[mkt, hml]`; score = IR of residuals over
t−252…t−21; strict-before daily assignment; cross-sectional percentile rank injected as the rank
column (C4 sole-ranker-swap protocol). Paired 63d block bootstrap (n=5000) ΔSharpe/ΔSortino, DSR at
n_trials=87, continuous-slice 2022-26, ≥2019 fold-pass. `scripts/run_residual_momentum.py`; raw JSON
`research/exports/residmom_0077_results.json`. Leakage-clean (§1 trailing-only residual, score applied
strict-before; §2 HML `bp` via `value_quality_series` strict-before availability join).

## Result
| Metric | BASE (trend) | RESID-MOM | Δ |
|---|---|---|---|
| Sharpe | 0.667 | 0.503 | **−0.164** [−0.65, +0.32] |
| Sortino | 0.836 | 0.658 | −0.178 [−0.81, +0.48] |
| Calmar | 0.33 | 0.19 | − |
| MaxDD | −46.3 | −44.0 | +2.3 |
| **skew** | −0.639 | **−0.253** | **+0.385** |
| CAGR | 15.5% | 8.2% | −7.3pp |
| 2022-26 Sharpe | 0.570 | 0.309 | − |
| **2022-26 MaxDD** | −46.3 | **−24.9** | **+21.4** |
| fold-pass (≥2019) | — | 0.38 | fail |
| corr(resid_rank, trend_rank) | — | — | **0.11** (near-orthogonal) |

**SHAPE verdict → KILL:** the pre-committed bar required skew AND Sortino AND Calmar AND 2022-26
Sharpe to ALL improve; skew improves but Sortino / Calmar / 2022-26 Sharpe all worsen.

## Root-cause readout (REQUIRED)
Residual momentum is nearly orthogonal to the trend ranker (corr 0.11), so this is a real swap, not a
re-label. It **works exactly as BHM predicts on the RISK axis**: stripping Market+Value exposure
improves skew (−0.64 → −0.25) and structurally avoids the 2024-25 crowded-factor unwind, cutting the
live-window drawdown from −46.3% to **−24.9%** (a genuine mechanism effect — a lower-return book does
not automatically halve its DD; the residual names simply weren't in the factor bet that broke). **But
as a SOLE ranker it discards the trend signal's return edge** — CAGR 15.5→8.2%, 2022-26 Sharpe
0.57→0.31 — and the return loss dominates every risk-adjusted metric. This confirms O-002's spirit
(residual doesn't beat trend on return) while ADDING what O-002 missed: the *multi-factor* residual
delivers a large, real skew + drawdown improvement. Better-shaped, lower-returning.

## Next setup
The shape/DD win is precisely the disease (the −31.6pp residual-factor DD leg). The productive reframe
is NOT a ranker swap but a **complement that retains the trend return**: (a) a **blend** rank =
`trend_rank + λ·resid_rank` (small λ), or (b) a **within-top-15 conviction / risk tilt** on residual
momentum (down-weight names with weak residual momentum among the trend-selected), or (c) a
**residual-based DD/risk overlay** (the −46→−25 DD reduction alone is worth isolating). New pre-reg
(0078). Also: **SMB is deferred** — a Screener re-scrape of shares/net_worth would add the size factor
and sharpen the residual; worth it only if the blend/conviction reframe shows promise first.
