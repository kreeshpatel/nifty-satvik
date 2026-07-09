# Pre-registration 0096 — Sector-relative CRS denominator on the weekly-swing book

**Status:** PRE-REGISTERED (written before any run; construction + bar fixed here, not retunable).
**Date:** 2026-07-09. **Owner-selected lever** (L2 of `research/RESEARCH_PLAN_swing.md`).
**n_trials cost:** +1 (single arm) → cumulative 113 → 114, incremented before the run.

## Registry gate (done before writing this)
The obvious L2 — a **Nifty-500-TRI** denominator — is ALREADY TESTED and lost: 0093 (TRI) Sharpe
+0.677 vs 0093-N50 +0.900 (finding 0037: N50 admits the strong mid-cap trends the broad cap-weighted
TRI screens out). Relitigating that is forbidden. The genuinely-new denominator is **sector-relative
RS**: RS = stock ÷ its own sector index, instead of stock ÷ Nifty-50.

This is NOT O-004 (sector *selection*, killed, sector IC≈0) — it does the opposite, **neutralising**
sector beta to rank on intra-sector idiosyncratic strength. It is adjacent to O-002 (single-**market**-
beta residual momentum, killed "no improvement over raw trend; most residual benefit is market
residualisation") — the new formulation is **sector** residualisation, untested, with O-002's skeptical
prior carried forward.

## Overlay
Swap the CRS denominator from Nifty-50 to the stock's **own sector index**:
- Sector map = `config.SECTOR_MAP` / `config.get_sector(ticker)`.
- Sector index = **equal-weight daily-return index** of that sector's corrected-universe members
  (per-day cross-sectional mean of member daily returns, cumprod; PIT via skipna so new listings enter
  and delisted names drop out — built from the same corrected panel the book trades).
- `RS = stock_weekly_close / sector_index_weekly_close`; the gate `RS > SMA40(RS)` and the fill rank
  `RS/SMA40(RS) − 1` are otherwise UNCHANGED from 0094.
- **"Others" (unmapped, ≈249/814 names, 30%) fall back to the Nifty-50 denominator** — documented
  dilution of the treatment (failure mode #2).

## Params — FIXED
- Sector map: `config.SECTOR_MAP` (as committed). Sector index: equal-weight, per-day member-return mean.
- `CRS_LEN = 40` weeks (unchanged). Everything else = the frozen 0094 config.
- Fallback for "Others"/thin sectors: Nifty-50 (the current denominator).

## Hypothesis
If the swing book's edge is **stock-picking within sectors** rather than riding whole sectors, then
ranking/gating on sector-relative strength (idiosyncratic trend, sector beta removed) should surface
cleaner leaders → higher Sharpe / robustness than market-relative (N50) RS.

## Skeptical prior (adversarial — stated before running)
The book is a **trend-momentum** book that profits from **riding strong sectors**; sector-relative RS
**de-means exactly those sector tailwinds**. O-002 found residualisation gives "no improvement over raw
trend," and most residual benefit was market (not sector). Expect **NEUTRAL-to-WORSE**.

## Predicted direction
ΔSharpe ≤ 0 (likely); possible small robustness shift (composition change) but no clear gain.

## Failure modes (≥2)
1. **De-means the sector tailwind** → strips the book's best trend trades (the O-002 lesson).
2. **30% "Others" fallback** dilutes the treatment → a muddy / underpowered read.
3. **Reflexivity** — the EW sector index is built from the same universe the book trades (mild).

## Pre-committed verdict bar (signal/ranker change — fixed here)
This changes the entry GATE and the fill RANK, so it is judged on risk-adjusted return, not DD:
- **SHADOW (route to the forward wall as an alt-denominator candidate)** iff ALL hold on the corrected
  universe, continuous-slice: (1) **ΔSharpe ≥ +0.10**, (2) **2022-26 slice ΔCAGR ≥ 0**, (3) **MaxDD not
  worse by more than 2.0 pp**, (4) **ΔSharpe bootstrap CI-low > 0**.
- **PROMOTE to the live book:** forward-wall only (the book is already DSR 0.894 < 0.95).
- **KILL / UNDERPOWERED** otherwise. No retune, no re-run, no rounding a near-miss (the 0025 rule).

## Method
- cfg-gated: `prep_weekly_rank(..., index_provider=...)`; `index_provider=None` (default) → Nifty-50 for
  all → **byte-identical to the 0094 run of record** (engine invariant, verified inline + golden master).
- Universe: corrected (pinned + backfill + aliases), 2017–2026. Sub-periods via `_slices` (continuous).
- Report: full-sample + 3 slices, ΔSharpe/ΔCAGR/ΔMaxDD, block-bootstrap ΔSharpe CI, n_independent,
  trade-count / win-rate / concentration shift.
- vibe-trading not used (no PIT-NSE); our harness is canonical.
