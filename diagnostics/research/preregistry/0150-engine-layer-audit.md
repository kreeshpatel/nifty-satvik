# 0150 — Engine layer audit: is the Grade-A rating on point, and what does each layer add?

**Class:** MEASUREMENT, one pre-registered family. **No trial.** Screen ledger row **#23**, appended
**before** this runs. Standing counts at registration: **screens 22 → 23 · sealed opens 3 · n_trials 2**.
**Registered:** 2026-10-13, owner request, before the diagnostic exists.

## Questions

1. **Is the Grade-A rating on point?** Grade A is the top 5 signals by CRS score in each setup week. Does
   the rank, read as a rating, order the outcomes of the trades it rates?
2. **What does each layer of the live engine add?** One layer switched off at a time against the live
   configuration.

## What is already answered, cited and not re-asked

- `research/substrate/CRS_DISSECTED.md`: the CRS-ranked **portfolio** beat random portfolios in 2022–26 and
  sat inside the noise in 2017–21; "relative strength is extension". That measured the book, not the
  rating, and its 2022–26 leg overlaps the sealed slice. This study measures the rating, trade by trade,
  on the train window only.
- 0104 (tightening `ext_cap` killed), 0099 (the scaled exit), 0148 (ratchet bound), Law II (seats are
  load-bearing), 0141 (2R hit rate ≈ random). Their numbers are not re-derived; the ablations below
  re-measure the same layers on the **current** live configuration so they can be read side by side.

## Population and window (both parts)

The live configuration (`LIVE_DISCIPLINE`, `LIVE_EXIT`, `LIVE_STALENESS`, demerger events, PIT
membership), `corrected_universe()`, **price data cut at 2024-06-30 before the engine sees it**, start
2019-01-01. The sealed slice is never loaded. Sub-periods 2019–21 and 2022–24H1.

## Part 1 — the rating (frozen)

**Data:** one uncapped, all-grades run (`uncapped=True`, `a_grade=None`), so every signal that fills is
tracked with its CRS score and its realised R under the live exit. Signals are grouped by the ISO week of
the fill (one setup Friday per week) and ranked by CRS score within the week. Trades still open at the cut
are marked at the cut. **Stated censoring:** a signal that never fills inside its band has no outcome and
is not in the pool.

**Statistics (all with a week-clustered bootstrap, 5,000 draws, resampling whole weeks):**

- **Rank IC:** the mean within-week Spearman correlation between CRS rank and R, with its 95% CI.
- **Monotonicity:** mean R of ranks 1–5 (Grade A), 6–10, and 11+.
- **The rating's edge:** mean R of Grade A minus mean R of the rest of the same weeks, with CI.
- **Hit rate:** share of Grade A and of the rest that ever reach +2R before the stop, against the
  driftless first-passage null b/(a+b) computed from each trade's own entry, stop and target.
- **Stability:** each statistic by year and by sub-period.

**Reading, pre-committed.** The rating is **"on point"** only if the Grade-A edge is positive with a CI
excluding zero **and** positive in both sub-periods. **"Regime-dependent"** if positive overall but not in
both. **"Not distinguishable from noise"** if the CI spans zero. All three are complete answers.

## Part 2 — layer attribution (frozen)

Capped ₹10L book. One run per arm:

| arm | what is switched off |
|---|---|
| **live** | nothing (control) |
| no_ext_cap | the 20% extension cap (`ext_cap=None`) |
| no_grade_gate | the Grade-A gate: all grades compete for seats (`a_grade=None`) |
| base_exit | the scaled exit P, replaced by the engine's default half-book exit |
| random_top5 × 20 | Grade A replaced by **5 random signals per setup week** (20 seeds) — the null for the CRS rank |

**Per arm:** Sharpe, CAGR, MaxDD (continuous slices of one run), and Σ R per year with open trades
marked. **A layer's value** = live − arm. The CRS layer is read as the live book's percentile within the
20 random-top-5 books.

**Reading, pre-committed.** A layer "carries its weight" if removing it costs **≥ 10 R/yr** (the 0109
floor) **or** ≥ 0.10 Sharpe, with the same sign in both sub-periods. Below that, the layer is
**not distinguishable from noise on this window**, which is a result and not a recommendation. With
n_eff ≈ 37 the ΔSharpe half-width is ≈ 0.59; every Δ here is read against that.

## What this study may never do

Change a layer. Any layer that reads wrong becomes a separate pre-registered trial at a quarterly review.
No threshold, grade, cap or exit changes on the strength of this page.

## Reproduce

`python pipelines/diagnostics/diag_engine_layer_audit_0150.py` → `diagnostics/research/engine_layer_audit/result.json`.
