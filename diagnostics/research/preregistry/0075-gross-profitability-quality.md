# 0075 — Gross-profitability quality overlay (Hanauer-Lauterbach / Novy-Marx): an orthogonal predictor at 63d?

- **ID:** 0075 (Stage-C orthogonal predictor / quality tilt). External candidate #2 from
  `research/external_edge_ideas.md`. Owner-pointed 2026-07-01.
- **Registered:** 2026-07-01, BEFORE the run. **TRIAL** → cumulative_n_trials 81 → 82 (bumped before
  run; conservative — kept even if the data build defers the run).
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg, corrected universe.

## ⚠️ DATA PRECONDITION (this trial is BLOCKED until step 0 completes)
The candidate needs **gross_profit** and **total_assets** (PIT) per name. The carried fundamentals
store (`data/fundamentals_pit_screener.pkl`, 654 names) has **only** `eps_ttm, book_value_ps, roe,
debt_equity` — **no gross profit, no total assets**. The external doc's claim that the data is "already
in the repo" is INCORRECT. **Step 0 = scrape PIT gross_profit + total_assets from Screener** into the
store (same pattern as the 2026-07-01 delisted-D/E scrape), then re-pin the dataset (the OHLCV pin is
unaffected, but the fundamentals store changes → note the new store hash). Until step 0 lands, 0075
cannot run.

## Hypothesis
**Gross profitability** = gross_profit / total_assets (Novy-Marx; pervasive EM predictor per
Hanauer-Lauterbach 2019, SSRN 3233614). A gross-profitability **tilt** on the cross-section improves
risk-adjusted return at the 63-day horizon, and is **orthogonal to the 200-day trend** (so it can add,
not dilute).

## Candidate (the distinct construction — the §11 reopen condition)
A **soft selection tilt** (NOT a hard screen): additive rank-norm tilt on the daily candidate sort by
the cross-sectional z of gross_profitability (λ blended with `trend_rank`), one pre-declared λ — the
0065 tilt pattern (re-orders slots, admits no name the gate wouldn't, flag-gated, golden byte-identical
off). PIT, 1-day lagged.

## Distinctness vs prior KILLs (cite the new-evidence condition)
- **≠ O-007** (heavier quality SCREEN: ROE/earnings hard filter → over-filtered, KILL): 0075 is a
  *continuous tilt*, not a screen, and uses **gross profitability** (GP/assets), not ROE.
- **≠ 0017/0018** (ep/bp VALUE legs: weak at 63d): gross profitability is Novy-Marx **quality**, a
  different, empirically-stronger-in-EM factor, not a value ratio.
- New factor + new construction + new (EM-specific) evidence → legitimate reopen, not relitigation.

## Method
Paired 63-day block bootstrap (n=5000) on the pinned panel (with the GP-augmented store): ΔSharpe +
CI, ΔCalmar, ΔCAGR; DSR(candidate) at n_trials=82; ≥2019 folds; 2017-21 / 2022-26 sub-periods.

## Decision rule (pre-committed) — the 7-criterion promotion bar
PROMOTE only if ALL: ΔSharpe CI-low > 0 AND point ≥ +0.10, ΔCalmar ≥ +0.05, 2022-26 positive ΔCAGR,
fold-pass ≥ 60%, turnover ≤ +30%, mechanism one sentence. UNDERPOWERED if positive but CI-low ≤ 0.
Else KILL. Record in `overlay_registry.md` + a finding.

## Skeptical prior (state it)
Quality is **slow** — the doc's own failure-mode note flags it as weak at a single quarter, and the
ep/bp value legs were already weak at 63d on this universe. The whole value/quality family has
underwhelmed here (0017/0018 KILL). The EM evidence is **not India-isolated** and was **not
adversarially verified** (deep-research verify pass incomplete). Honest expectation: a hard test;
quality may simply be too slow for the 63-day hold. KILL/UNDERPOWERED is a first-class outcome.
