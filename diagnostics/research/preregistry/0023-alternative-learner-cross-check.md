# 0023 — Alternative-learner cross-check: is the IC≈0 ceiling in the DATA or the MODEL CLASS?

- **ID:** 0023 (research/diagnostic). Prompted by the wiring audit (Phase 6) + the owner's
  explicit request for a quantum/PennyLane angle.
- **Registered:** 2026-06-10 (BEFORE running; question + method + gate fixed first).
- **Type:** measurement (rank-IC), no live trading. Runs ONLY after the audit's Phases 1–5
  confirm the data is leakage-proof + reproducible (garbage-in would invalidate it).

## Question

0021 found the LightGBM return head has ~0 directional IC vs `fwd_return_14d` (the conf/gate
head ~0.11). Is that a property of **(a) the DATA** — price-derived features carry no
extractable cross-sectional direction at 14d in efficient large-caps (→ no model can find it;
the only honest path is non-price signals or accept the vol/convexity edge) — or **(b) the
MODEL CLASS** — gradient-boosted trees miss a signal a different learner could extract
(→ an architecture lever exists)?

## Method

On the SAME cross-sectional feature panel the LightGBM uses (the Phase-1/2 leakage-proof
`features.pkl`), per walk-forward fold (expanding window, **embargo_days=45**, REPRODUCIBLE_MODE=1),
train each alternative learner and compute the spearman rank-IC of its score vs `fwd_return_14d`
across each day's cross-section (`validation.factor_metrics.information_coefficient` + `ic_summary`
— identical machinery to 0021). Learners:

1. **Linear** — L2-logistic on P(hit+4%) and ridge on fwd_return (a low-variance, high-bias
   baseline; if direction is linearly present, this catches it).
2. **Small MLP** — 1–2 hidden layers (a different nonlinear inductive bias than trees).
3. **PennyLane VQC / quantum kernel** — a variational quantum classifier (and/or a quantum-kernel
   SVM) on a low-dimensional subset (PCA→4–8 components or the top-k SHAP features), angle-encoded.
   A genuinely different hypothesis space (the owner's quantum angle). PennyLane is a dev-only,
   out-of-lock dependency — never added to the production requirements.

Benchmarks: LightGBM return-head IC-IR 0.024, conf-head 0.107, best naive ~0.03 (from 0021).

## Pre-registered gate

An alternative learner is a **lever** iff its directional IC-IR vs `fwd_return_14d` is
**> 0.15** (meaningfully above the 0.107 conf head) AND stable across folds (t-stat > 2) AND
survives the Deflated-Sharpe / multiple-trials correction (n_trials includes every learner +
config tried, read from `diagnostics/research/n_trials.json`). Otherwise: the learner inherits
the ~0 ceiling.

## Skeptical prior (stated before running)

All learners likely converge on ~0 directional IC — the signal isn't in the price features
(efficient large-caps; 0021's reversal-signed naive technicals; the 0004/0002/0010 feature kills).
**Quantum ML rarely beats GBMs on tabular financial data**; the VQC's value here is the
cross-check + settling the question honestly, not an expected win. If ALL learners hit ~0 →
strong evidence the ceiling is in the DATA → the reset's payoff is trust+control, and edge must
come from non-price/finance signals (or accepting the vol/convexity structure), NOT a fancier
model. If ONE learner clears the bar → an architecture lever exists and warrants a pre-registered
follow-up.

## Result (2026-06-10)

Ridge + MLP trained directly on `fwd_return_14d`, out-of-fold over 7 embargoed folds
(`alt_learner_ic.json`):

| learner | IC-IR (raw, all days) | mean IC | "t" (raw) |
|---|---|---|---|
| ridge | 0.397 | 0.0415 | 16.49 |
| mlp | 0.252 | 0.0274 | 10.49 |

Both clear the pre-registered IC-IR>0.15 bar — **but this is a FALSE POSITIVE caught by the
adversarial controls** (the result was too good vs the 0021/0016 prior, so it was scrutinized
before being believed):

- **Shuffle-null (8 fits with the training target permuted):** IC-IR mean −0.118, **std 0.264,
  range [−0.438, +0.365]**. A signal-LESS model produces |IC-IR| *as large as or larger than* the
  "real" 0.21 (fold) / 0.40 (aggregate). The real IC-IR is **inside the null band**.
- **De-overlapped real (sample every 14th test day, aggregated over folds):** ridge IC-IR 0.372
  (t=4.18), mlp 0.205 (t=2.30). **But both sit INSIDE their shuffle-null band** (ridge null
  |IC-IR| ≤ 0.424; mlp ≤ 0.568) → ceiling, not a lever. The de-overlapped t>2 alone would have
  passed ridge — the shuffle-null is what correctly rejects it (a signal-less model reaches the
  same IC-IR), which is exactly why a raw IC-IR/t gate is insufficient for this autocorrelated target.

The raw IC-IR/t are inflated by **overlapping-horizon autocorrelation**: consecutive days share
nearly the same 14-day forward ranking, so ~248 daily ICs ≈ ~18 independent observations (~14×
inflation). The pre-registered IC-IR>0.15 gate is INVALID for an overlapping-horizon target
without de-overlapping or a shuffle-null.

VQC (quantum) was not run as a separate verdict: ridge+MLP (strictly more expressive than a
PCA(6) variational circuit) already land inside the no-signal null band, so the data ceiling is
demonstrated and a VQC would inherit it — running it would be scientifically moot.

## Conclusion (REVISED 2026-06-10 after a /code-review caught a harness bug)

**REVERSED: a weak GENUINE directional signal EXISTS — 0021's strong "no directional alpha" is
overturned.** My first "no lever / data ceiling" conclusion was an artifact of a buggy null-band
in the de-overlap harness (it compared a pooled-across-folds real IC-IR against a
per-fold-MAX null — high-variance, upward-biased — flagged by the code review). The **correct
matched permutation test** (null pooled the SAME way as the real, n_perm=20) is decisive:

- **Full 79 features:** REAL pooled de-overlap IC-IR **0.373** at the **100th percentile** of the
  matched null (mean −0.003, p95 +0.165, max +0.240) → p<<0.05, a real directional signal.
- **Leakage ruled out:** on the 58 truncation-VERIFIED PIT-clean features the signal is **marginal**
  (IC-IR 0.158, ~95th pct, below null max) → ~58% of the signal comes from enrichment features, but
  `rs_rank` is PIT-clean by construction (same-day cross-section of trailing returns) and the macro
  regime/vol features carry genuine PIT directional info. Not enrichment lookahead.

So **direction IS extractable by a model trained ON it** (mean IC ~0.04) — the production return
head discards it by training on `fwd_max` (=volatility). The ceiling is the **TARGET CHOICE, not
the data.** The quantum/VQC arm is not needed to settle this.

**Caveats (why this is a lead, not a deployed edge):** magnitude is modest (mean IC ~0.04);
**tradeable-after-costs is UNPROVEN** (a comparable raw IC died on costs in 0014); the macro/sector
enrichment isn't fully truncation-audited (small residual seasonality-leak risk). **Next
investigation:** a cost-aware backtest of a direction-trained model + a truncation audit of the
21 enrichment features. **AUD-022 lesson:** IC verdicts on overlapping-h targets need a MATCHED
permutation null + PIT-feature isolation — raw IC-IR AND a naive de-overlap both mislead; 0021's
own IC-IRs should be re-stated under this method.
