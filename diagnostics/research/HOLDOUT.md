# Honest-Measurement Harness — Locked Holdout & Research Discipline

**Established:** 2026-05-30
**Owner:** quant research
**Status:** ACTIVE — binding on all model/strategy improvement work from this date forward.

---

## Why this exists

Every historical dataset NiftyQuant has, has **already been used in development**:

- The model trained on 2010-01-01 → 2024-12-31 (NIFTY_500, 2025-07-20 list).
- The walk-forward folds (2017–2025) drove model selection, the 0.88→0.92 gate
  move, the regime gates, the sweep override, the ensemble verdict, and every
  other shipped/rejected decision in `diagnostics/`.

So there is **no clean historical holdout left**. A "recent slice" (e.g. 2025) is
*weakly contaminated* — it was a walk-forward test fold and was inspected during
the audit. Claiming an improvement "works" by re-checking it on these folds is
the multiple-comparisons trap: with ~9 folds and dozens of ideas already tried,
something always looks good by chance.

This document defines the two holdouts that **are** honest, and the discipline
that makes any future improvement claim trustworthy.

---

## Holdout #1 — The forward wall (permanent, leak-proof)

**WALL_DATE = 2026-05-30.**

All market data dated **strictly after WALL_DATE** is permanent holdout. It may
**never** be used to train, tune, threshold, select, or in any way *fit* a model
parameter. It is used **only** to *test* a hypothesis that was pre-registered
**before** the data existed.

- The live/paper observe period accumulates here automatically.
- This is the only truly leak-proof OOS we will ever have. It is slow
  (~44 trades/yr) but unimpeachable.
- Moving WALL_DATE forward is allowed only to *start a new* leak-proof window;
  data between the old and new wall stays holdout for any hypothesis registered
  before it arrived.

## Holdout #2 — The unseen universe (immediate, caveated)

The model trained **only** on the 2025-07-20 NIFTY_500 list (~441 tradeable
tickers). Any NSE-listed ticker **not** in that list is a stock the model has
never seen.

**Unseen-universe holdout = constituents of a broader index (Nifty Smallcap 250
/ Nifty Microcap 250) that are NOT in NIFTY_500.** Running the current model on
these tickers tests whether the learned edge **generalizes to stocks it never
trained on**, or was memorization of the training universe.

**Caveats (state them in every result):**
- Macro features (VIX, USD/INR, etc.) for overlapping calendar dates *were* in
  training, so this isolates **per-stock + cross-sectional** generalization, not
  full OOS. For full OOS use Holdout #1.
- Liquidity skews smaller than the training universe. Since the edge already
  concentrates in small-caps, this is a **relevant stress test, not a softball** —
  but the ADV floor / liquidity-tier costing from the Path B audit MUST be applied
  so we don't credit untradeable fills.
- Survivorship: the unseen-universe ticker list is today's membership; same
  caveat as the main backtest. Relative comparisons stay valid.

---

## The discipline (binding)

1. **Pre-register every experiment before running it.** One file per experiment
   in `preregistry/`, written *before* the run: hypothesis, single **primary**
   metric, decision rule, which holdout, and the running `n_trials`. Hash/commit
   it first; results are appended separately and the pre-registration is never
   edited after the fact.

2. **The dev set is for GENERATION, not confirmation.** The 2010–2025 NIFTY_500
   walk-forward folds may be used to *form* a hypothesis. They may **not** be the
   evidence that it works. Confirmation happens only on a holdout.

3. **Multiple-comparison correction = Deflated Sharpe Ratio.** The correct
   adjustment for "we tried N strategies" is **not** naive Bonferroni on Sharpe —
   it is the **Deflated Sharpe Ratio** (`src/validation/overfitting.py::
   deflated_sharpe_ratio`), deflating by `n_trials` = the cumulative count of
   variants tried across this whole research program (tracked in the registry).
   Use **PBO** (`compute_pbo`) when selecting among several variants. A Sharpe
   only "counts" if **DSR > 0.95** at the current `n_trials`.

4. **Every metric reported with a confidence interval.** Trade-level metrics via
   `bootstrap.bootstrap_metric`; sequence-dependent metrics (Sharpe, CAGR, MaxDD)
   via `bootstrap.block_bootstrap_metric` over `risk_metrics` functions. A point
   estimate with no CI is not a result.

5. **A holdout result can only KILL or weakly SUPPORT — never bless.** Passing on
   a holdout is necessary, not sufficient (one holdout test ≠ proof). Failing is
   decisive. We are looking for reasons an idea is *wrong*, not confirmation it's
   right.

6. **Costs are honest or the result is void.** After-cost per-trade expectancy is
   the headline. Brokerage + STT + tiered slippage + ADV-floor / position-impact
   (Path B) must all be on. Pre-cost numbers are never reported as the result.

---

## What already exists (reuse, do not rebuild)

| Capability | Location |
|---|---|
| Trade-level bootstrap CIs | `src/validation/bootstrap.py::bootstrap_metric` |
| Block bootstrap CIs (Sharpe/CAGR/MaxDD) | `src/validation/bootstrap.py::block_bootstrap_metric` |
| Risk metric suite + `summary()` | `src/validation/risk_metrics.py` |
| Deflated Sharpe Ratio (MC-correction) | `src/validation/overfitting.py::deflated_sharpe_ratio` |
| Probability of Backtest Overfitting | `src/validation/overfitting.py::compute_pbo` |
| Walk-forward (generation only now) | `src/validation/walk_forward.py` |
| Deterministic seeds / provenance | `src/repro/` |

The harness was *mostly already built*. What was missing — and what this document
adds — is the **holdout** and the **pre-registration discipline** that make the
existing statistics mean something.
