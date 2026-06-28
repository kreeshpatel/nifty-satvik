# 0024 — Direction-target test: does fixing AUD-025 (train on direction) make the model useful?

- **ID:** 0024. Prompted by the owner ("retrain — anything that tells us this model is useful or not")
  + the audit's master finding AUD-025.
- **Registered:** 2026-06-10 (BEFORE the direction retrain; question/method/gate fixed first).
- **Type:** model experiment (retrain + walk-forward backtest), candidate-only (never touches `models/v1`).
  Runs on the now-FIXED backtest engine (AUD-033/034/035/036) so the metrics are trustworthy.

## Question

The live return head trains on `fwd_max_14d` (the max forward EXCURSION ≈ volatility), but the
gate (`min_predicted_return=8.0`), ranking (`conf × predicted_return`), target, and RR all treat its
output as an expected DIRECTIONAL return (AUD-025). 0021 showed the model consequently ranks volatility,
not direction (≈49% WR). 0023's matched-permutation test showed direction IS weakly-but-genuinely
extractable when a model is trained ON it (pooled de-overlap IC-IR 0.37; marginal 0.16 on PIT-clean
features). **Does retraining the return head on `fwd_return_14d` (close-to-close direction) — the AUD-025
fix — produce a model that is MORE useful (better honest, cost-aware, walk-forward economics) than the
fwd_max baseline?**

## Method

Walk-forward (expanding window, **embargo_days=45**, the fixed engine), v1 single-model, 2 arms:
- **A — fwd_max (baseline):** the current design (`return_label=fwd_max_14d`). = the honest baseline run
  `usefulness_baseline.md`.
- **B — direction:** retrain a CANDIDATE with `return_label=fwd_return_14d` (config-swap in train.py →
  `models/v1_direction_candidate/`; `fwd_return_14d` exists in features.pkl). Walk-forward it.

**Fairness control (critical):** directional predictions are smaller-magnitude than excursions, so the
`min_predicted_return=8.0` gate (an 8% *excursion* floor) would starve arm B (≈0 trades). Compare at
**matched selectivity** — sweep/lower B's `min_predicted_return` so it produces a comparable trade count
to A, and compare Sharpe / CAGR / WR / **rupee** profit-factor / max-DD / DSR at that matched count.
Also compare **directional IC** (arm B's predicted_return vs fwd_return_14d) using 0023's matched-
permutation + de-overlap method (the leakage-clean significance test).

## Pre-registered gate

Direction is a USEFUL improvement iff, at matched selectivity: **(a)** B's median per-fold Sharpe ≥ A's
AND **(b)** DSR-robust (cumulative `n_trials` from the registry) AND **(c)** B's directional IC clears
0023's matched-permutation null. Otherwise the fwd_max design stands (the edge is the vol-selection +
asymmetric-payoff structure, not direction).

## Skeptical prior (stated before running)

Genuinely open. 0023 showed direction is real but WEAK (IC ~0.16 on PIT-clean) — and weak IC often dies
after costs/turnover (cf. 0014 reversal kill). The fwd_max model's edge is high-WR convexity (ride the
excursion, +4% target / ATR stop); a direction model will likely have LOWER WR and may not beat it after
costs even if its IC is "more honest." So the most probable outcome is **A ≈ B or A > B economically** —
which would mean the AUD-025 category error, while real, is not the source of recoverable edge, and the
honest verdict on the model's usefulness is the baseline number itself. A clear B > A would be a genuine,
surprising, actionable improvement (ship a direction model).

## Result (2026-06-10, local walk-forward, FIXED engine, embargo-45, survivor universe)

10 expanding-window folds (2017–2026), multi-threaded, matched selectivity (direction gate
`min_predicted_return=3.0` vs baseline 8.0 → comparable trade counts):

| arm | medSharpe | meanSharpe | trades | medWR | medCAGR | negative folds |
|---|---|---|---|---|---|---|
| A — fwd_max (baseline) | +0.48 | +0.54 | 511 | 53.6% | +5.0% | 4/10 |
| B — direction (fwd_return_14d) | **+0.95** | **+1.12** | 438 | **59.4%** | **+9.4%** | 1/10 (~flat) |

**Paired test (the gate):** per-fold Sharpe improvement (B−A) mean **+0.58**, **8/10 folds favor B**,
paired bootstrap **95% CI [+0.14, +1.04] — EXCLUDES 0**. Mechanistically sound: B selects
directionally-favorable names → higher WR (59% vs 54%) + far better consistency (1 vs 4 negative folds).

**DSR caveat:** the per-arm DSR (baseline 0.000, direction 0.007) was computed on n=10 **folds** (too
few obs for a meaningful DSR; it should use trade/day count) so it reflects the tiny sample + the
program's 38-trial penalty, NOT a clean absolute read. The **paired** comparison is the reliable one.

## Conclusion (PROMISING — confirmation pending)

**The AUD-025 fix works: training the return head on DIRECTION roughly DOUBLES risk-adjusted
performance (medSharpe 0.48 → 0.95) at matched selectivity, paired-CI-robust.** The current fwd_max
design's edge is marginal (0.48) and regime-fragile (4 negative folds); the category error
(select-on-volatility) was costing ~half the performance. This is the strongest POSITIVE lever found
in the engagement.

**Caveats before "ship a direction model" (the discipline — don't trust one run):**
1. Single MULTI-THREADED local run — needs a reproducible re-run to rule out threading luck (effect is
   large + paired, so low risk, but confirm).
2. **Survivor universe** — the COMPARISON is common-mode-robust (survivorship cancels), but the ABSOLUTE
   levels are optimistic; re-confirm on the corrected universe (membership_v2 + dropped-name OHLCV).
3. Reconcile with 0023 (ridge-on-direction IC was only marginal on PIT-clean features) — a LightGBM on
   the full 79f extracts more, but verify the IC under the matched-permutation null.
4. Cost/turnover at matched selectivity (trade counts ARE comparable, costs are in the fixed engine, so
   largely handled).
5. The live wiring change is non-trivial (retrain all 3 ensemble siblings on direction + re-fit the gate
   + re-fit calibration) — a real retrain + revalidation, owner-gated.

**Verdict: a genuine, validated improvement lead — not yet a shipped model.** Next: reproducible +
corrected-universe confirmation (cloud), then if it holds, a pre-registered retrain-on-direction promotion.

## Cloud confirmation (2026-06-10, GitHub Actions run 27260497761, fresh feature rebuild) — TEMPERS the local result

Independent clean-runner walk-forward (`usefulness-experiment.yml`, features rebuilt via download_all):

| arm | medSharpe | meanSharpe | trades | medWR | medCAGR |
|---|---|---|---|---|---|
| baseline fwd_max | **+0.058** | +0.329 | 579 | 48.3% | **−1.4%** |
| direction fwd_return | **+0.495** | +0.568 | 540 | 56.3% | +3.9% |

paired Sharpe gain mean **+0.239**, 6/10 folds favor direction, **95% CI [−0.186, +0.663] — INCLUDES 0.**

**The local "2× and significant" result did NOT replicate.** Two honest conclusions:
1. **Direction is still DIRECTIONALLY better in BOTH runs** (higher median Sharpe, WR, CAGR; 6–8/10
   folds) — a real, consistent qualitative signal that the AUD-025 fix helps.
2. **But the improvement is NOT statistically robust** (cloud paired CI includes 0), and the BASELINE
   swung **0.48 (local) → 0.06 (cloud rebuild)** — a stark manifestation of **AUD-021 (verdict
   instability across feature-cache rebuilds)**. On honest rebuilt data the current model is ~coin-flip
   (medSharpe 0.06, WR 48%, NEGATIVE median CAGR).

## CONCLUSION (final, honest)

**The model is NOT reliably useful as-is** — on independently-rebuilt data it is ~break-even/losing
(medSharpe 0.06, WR 48%, CAGR −1.4%). **Training on direction (AUD-025 fix) is a real but WEAK and
NON-ROBUST lever** — directionally better in both runs, but the gain is not statistically significant on
the clean-runner confirmation. **The single biggest obstacle to ANY trustworthy verdict is AUD-021**:
the baseline Sharpe is not reproducible across feature builds (0.06–0.95 depending on vintage/threading),
so no model claim can be trusted until the feature build is **pinned + reproducible**. → The prerequisite
is the reset's Stage 1 (a pinned, reproducible, survivorship-correct data foundation); only on that can
the direction lever (or any model) be honestly judged. **The cloud confirmation vindicates the distrust:
even the "promising 2× lever" was an over-optimistic single-run artifact.** Do NOT ship a
retrain-on-direction on this evidence.
