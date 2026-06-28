# 0025 — Meta-labeling: does a direction primary + cross-fitted meta head beat the fwd_max base?

- **ID:** 0025. Prompted by the owner ("plan a financial model fix to lift WR/IC/Sharpe/CAGR")
  + audit master finding AUD-025 + the 0024 direction-target lead.
- **Registered:** 2026-06-10, **BEFORE** any meta/direction arm is run on the corrected universe
  (question / method / gate fixed first — the discipline; the base arm A is the only thing measured
  at registration time, and it is the locked yardstick, not a candidate).
- **Type:** model experiment (per-fold retrain + walk-forward), **candidate-only** — never touches
  `models/v1`. Runs on the FIXED backtest engine (AUD-033/034/035/036) and the PINNED,
  survivorship-correct 744-ticker cache (Stage 0, content digest `64cda7c2…`, two-build deterministic).

## Question

The production return head trains on `fwd_max_14d` (max forward EXCURSION ≈ volatility) while the
gate/ranking/target treat its output as a directional return (AUD-025 → ranks vol not direction,
~49–54% WR). 0024 showed retraining on `fwd_return_14d` (direction) is directionally better but not
statistically robust on a survivor cache. **On the corrected 744 universe, does a proper meta-labeling
architecture — a DIRECTION primary + a SECONDARY (meta) classifier trained on the realized path-aware
win (`tb_hit_14d`) over only the primary's would-be bets — produce a model that is MORE useful
(risk-adjusted, consistent, IC-clean) than the fwd_max base, enough to clear a pre-committed
Sharpe-priority promotion gate?**

## Method

Walk-forward, expanding window, **embargo_days=45**, the FIXED engine, single-model (v1 14d), on the
pinned 744 cache (`diagnostics/run_walk_forward.py`). Honest window = **≥2019 folds** (the 69 unrecoverable
delisted names — pre-2020 PSU-bank mergers, DHFL — leave a small residual survivorship gap below 2019;
Stage 0 documents this). Arms:

- **A — base (fwd_max):** current design (`return_label=fwd_max_14d`, `confidence_label=hit_4pct_14d`).
  = the Stage-0 re-locked single-model base (`diagnostics/research/base_744_singlemodel.json`),
  `--apply-bear-block`, the live-parity gate. The frozen yardstick.
- **B — direction-only (AUD-025 fix):** `return_label=fwd_return_14d`, confidence head unchanged
  (`hit_4pct_14d`). Isolates the target fix.
- **C — meta-labeling:** `MetaLabeledPredictionModel` — direction primary (`fwd_return_14d`) + META head
  trained on `tb_hit_14d` over only primary-positive rows (bet mask from CROSS-FITTED OOF primary preds).
  `meta_labeling: true`.
- **D — meta + sample weighting + purge (Stage 1.3):** C plus label-uniqueness sample weights and an
  intra-set overlapping-label purge in the WF runner.

**Fairness control (the 0024 trap):** directional predictions are smaller-magnitude than excursions, so
the base's `min_predicted_return=8.0` (an 8% *excursion* floor) would starve B/C/D. Compare at **matched
selectivity** — set the directional gate (`min_predicted_return` = `primary_bet_threshold`) so B/C/D produce
a comparable trade count to A, then compare metrics at that matched count. Also compare **directional IC**
(primary pred vs `fwd_return_14d`) under 0023's matched-permutation + de-overlap null.

## Pre-registered promotion gate (Sharpe-priority — owner decision 2026-06-10)

A candidate (C or D) is a USEFUL improvement worth shipping iff, vs base A, on **≥2019 folds at matched
selectivity**, ALL of:

1. **Risk-adjusted (primary):** mean per-fold Sharpe improves by **≥ +0.15** (or median Sharpe ≥ +0.15).
2. **Consistency:** negative-fold count does **not increase**, AND mean WR ≥ base − 1.0pp.
3. **Robustness:** paired bootstrap 95% CI on per-fold (candidate − base) Sharpe has **lower bound > 0**,
   AND **DSR > 0.95** at the cumulative `n_trials` from `diagnostics/research/n_trials.json`.
4. **IC (mechanism):** the directional primary's IC clears 0023's matched-permutation null (real
   directional signal, not a vol artifact).

**Relaxed CAGR floor (the accepted trade-off):** mean ≥2019 CAGR may regress by up to **25% relative**
vs base (vs the status-quo 10% floor in `balanced_scorecard`) — PROVIDED 1+2+3 hold. A CAGR regression
**> 25% relative → KILL**, even if Sharpe improves (we will not give up the fat-tail upside beyond that).

**Verdict logic:** if D > C on the gate → ship D's recipe; if C passes but D doesn't add → ship C; if
neither C nor D clears (1)+(3) over base → **KILL** (meta-labeling does not rescue the signal, and the
base number IS the honest verdict on the model's usefulness). Promotion is then a separate, owner-gated
trio retrain (Stage 1.5) — this experiment never promotes.

## Skeptical prior (stated before running)

This engagement KILLed nearly every "obvious" fix (0011 triple-barrier label-swap, 0013 exposure, 0016
optimizer, 0018 value sleeve, 0020 sizing). 0011 specifically KILLed a `tb_hit` *confidence-label swap* —
but on a fwd_max primary, trained UNCONDITIONALLY on all rows; meta-labeling differs by (a) a direction
primary and (b) training the meta head only on cross-fitted primary-positive rows. 0021 shows the features
are directionally thin, so the meta head's discriminative ceiling is bounded by feature informativeness —
it may not separate winners from losers well. The most likely KILL path is the **WR/Sharpe-up vs CAGR-down
tension**: selectivity historically bleeds trend-year (2020/2021) CAGR; the relaxed floor is precisely the
pre-committed tolerance for that. **Genuinely open**, but the base prior is "C ≈ A or marginal," with a
clear C > A being a real, shippable improvement.

## Results (2026-06-10 — cloud run 27275347562, REPRODUCIBLE_MODE=1, embargo-45, bear-block)

All three arms ran on ONE shared expanded-universe cloud cache (vintage ≠ local pinned 64cda7c2;
relative deltas are the common-mode-robust comparison, as registered). ≥2019 folds, scored by
`diagnostics/score_0025_gate.py` → `diagnostics/research/0025_gate_score.json`.

| arm | meanSh | medSh | negFolds | meanCAGR% | meanWR% | trades | Δmean | Δmedian | paired CI95 | DSR@41 |
|---|---|---|---|---|---|---|---|---|---|---|
| A base | +0.543 | +0.857 | 3 | +12.56 | 48.7 | 520 | — | — | — | — |
| B direction | +0.559 | +0.584 | 4 | +5.52 | 53.5 | 431 (0.83×, matched) | +0.016 | +0.362 | [−0.589, +0.508] | ~0 |
| C meta | +0.705 | +0.366 | 2 | +18.82 | 50.1 | 1374 (2.64×, UNMATCHED) | +0.161 | +0.755 | [−0.885, +1.111] | ~0 |

Per-fold Sharpe deltas vs A:
- B−A: 2019 +0.74, 2020 −1.73, 2021 −0.68, 2022 +0.36, 2023 +0.48, 2024 +0.76, 2025 +0.37, 2026 −0.16
- C−A: 2019 −1.13, 2020 −1.15, 2021 +1.17, 2022 +0.97, 2023 +0.77, 2024 +0.74, 2025 +2.35, 2026 −2.42

**Gate score:**
- **B**: 1 PASS (median +0.36) · 2 FAIL (neg folds 4>3) · 3 FAIL (CI straddles 0; DSR≈0) ·
  CAGR floor FAIL (−56% relative, floor is −25%) → **FAILS**.
- **C**: 1 PASS (mean +0.161) · 2 PASS (neg 2≤3; WR +1.4pp) · 3 FAIL (CI [−0.885,+1.111]
  decisively straddles 0; DSR≈0) · CAGR floor PASS (+50%) → **FAILS**. Caveat: C ran at
  `min_confidence=0.5` → 2.64× base trade count, so the registered matched-selectivity control
  was NOT achieved — C's row is additionally confounded, not just statistically weak.
- **D**: NOT RUN — forward-registered to run only if C clears (n_trials.json note). C did not clear.
- **Criterion 4 (IC)**: moot under KILL.

## Verdict — KILL (2026-06-10)

Per the pre-registered logic ("if neither C nor D clears (1)+(3) over base → KILL"): **meta-labeling
does not rescue the signal.** Both candidates fail the robustness criterion decisively — the per-fold
delta dispersion is enormous (B: −1.7 to +0.8; C: −2.4 to +2.3), so any mean improvement is
indistinguishable from fold-level noise at this sample size (8 folds).

**What the experiment DID establish (the value of the run):**
1. **AUD-025's mechanism is real but unmonetizable**: B at matched selectivity lifted WR by
   +4.8pp (48.7→53.5) exactly as the direction-target hypothesis predicted — yet Sharpe was flat
   (+0.016) and CAGR halved (12.56→5.52, 2020 delta −1.73). The fwd_max "mis-target" is not a bug
   that costs performance; the excursion head is harvesting trend-year volatility premium that the
   honest direction target cannot capture. AUD-025 should be read as "objective mis-DESCRIBED"
   (gate/target semantics are wrong on paper) rather than "objective mis-CHOSEN" (the label that
   makes money). This closes the 0024 lead.
2. **The meta head adds trades, not discrimination**: C's meta probability at 0.5 threshold nearly
   tripled trade count with WR ~unchanged vs A (+1.4pp) — the tb_hit classifier cannot separate
   winners from losers on these features (consistent with 0021's directional-IC-≈0 finding and the
   skeptical prior: "the meta head's discriminative ceiling is bounded by feature informativeness").
3. **2026 fold (live regime): C−A = −2.42** — the candidate is at its WORST in the most recent
   regime. Promotion would have been live-harmful.

**Consequence (per the registered program):** the architecture family is now exhausted on this
data (labels 0011, exposure 0013, optimizer 0016, sleeve 0018, sizing 0020, direction 0024,
meta-labeling 0025 — all KILLed by the same honest battery). The base IS the honest verdict on the
model's usefulness. The levers that remain are (a) the forward wall (0003) and (b) orthogonal DATA
acquisition, plus the Stage-3 free-EV cleanups (sweep_override AUD-017) which run regardless of
this verdict.
