# 0027 — volatility-contamination null: is the base's selection distinguishable from vol-loading?

- **ID:** 0027. Registered 2026-06-11, BEFORE any null arm runs.
- **Type:** measurement diagnostic with a matched null (like 0021/0023) — **NOT a trial**
  (no candidate strategy is promoted; the subject is the BASE's selection quality).
  n_trials unchanged.

## Question

The production model ranks excursion (≈ volatility) and harvests trend premium via
asymmetric exits. The worry: the recorded edge may be attributable to *vol-loading alone* —
"buy jumpy names, cut losers, let winners run" — with the model's specific SELECTION adding
nothing beyond picking from the high-vol pool. If true, (a) any vol-tilted data source can
fake a lift by re-sorting the same pool (re-prices the delivery-% near-miss), and (b) the
edge is replicable without a model (and more fragile to vol-regime shifts than believed.)

## Method (matched-null, same harness, same cache, same costs/exits)

Cloud, one shared corrected-universe cache, ≥2019 folds, embargo-45, bear-block:

- **Arm A — base:** the production recipe (the yardstick re-run on this cache vintage).
- **Arms N1..N20 — vol-matched random selection:** NO model. Each day, the candidate pool =
  names whose `atr_pct` falls in the SAME distribution band as the base's admitted trades
  (operationalized: top-K atr_pct decile band measured per fold from arm A's admitted-trade
  vol profile); pick `max_signals_per_day` names UNIFORMLY AT RANDOM (seeded per arm) and
  run the identical `_simulate` (same stops/targets/calibration/costs/caps). The null arms
  need no training → cheap; 20 seeds → a null DISTRIBUTION of fold-Sharpe means.

## Spec tightenings (pre-build, 2026-06-11 — external review)

1. **The claim is NAMED and NARROW: "beats vol-loading specifically."** The null matches the
   VOL marginal only (per-fold [p10, p90] band of arm A's admitted-trade `atr_pct`). A pass
   therefore does NOT license "beats dumb selection in its whole neighborhood" — the base may
   still be winning via sector/price/liquidity choices that correlate with vol. That broader
   claim would be a separate 0027b with full-profile matching; do not read it out of this run.
2. **Count-matched per day:** each null arm reproduces arm A's PER-DAY admitted count in that
   fold (not a flat 5/day) — breadth moves Sharpe independent of selection skill. Null draws
   come from names passing the same row filters (adx/rsi/uptrend per config) AND the vol band.
3. **(conf, ret) sampled from A's admitted joint distribution** (seeded, per fold) and
   assigned to the randomly chosen names — so calibration, targets, and sizing behave
   distribution-identically and ONLY the name assignment is random. This isolates selection.
4. **Seeds: 50 (1000–1049), fixed here.** With n=50 the tail is still an estimate: pre-commit
   an AMBIGUITY fork — base mean Sharpe between the null p90 and p99 → read as AMBIGUOUS
   (not a clean pass; the re-read consequences apply in soft form: vol-matched control on
   delivery-% before 0010b), only base > null p99 is a clean clear, base < p90 is inside.

Mechanics: arm A runs first with a per-fold trade export ({entry_date, atr_pct, confidence,
predicted_return}); the null job consumes it (same cache) and loops the 50 seeds through the
identical `_simulate` — no training, one job.

5. **Timing-invariance, named:** because the null inherits arm A's day structure (same signal
   days, same per-day counts) and A's realized (conf, ret) outcome pairs shuffled across
   names, BOTH arms hold timing skill constant — the test isolates NAME-LEVEL pairing only.
   A clean pass is read as "**name selection is real**," never as "all of A's skill is
   validated" (timing skill is invisible here, credited to neither side). Symmetrically, a
   null result says name selection adds nothing — it does NOT say A has no timing skill.
6. **Reporting (pre-committed):** the pooled placement (A's ≥2019 mean Sharpe vs the 50-seed
   null distribution, percentile + which side of the p90/p99 fork) decides the verdict; the
   PER-FOLD placement (A's fold Sharpe vs that fold's 50-seed null) is reported alongside —
   a base that clears in most folds but sits inside the null in some regimes shapes the
   delivery-% re-read scope either way.

## Pre-registered reading

- **Base mean ≥2019 Sharpe > the null distribution's 95th percentile** → the model's
  selection adds real information beyond vol-loading → selection-quality concern CLOSED;
  prior verdicts stand as read.
- **Base inside the null distribution** → the edge is vol-loading + exit asymmetry; the
  model's specific picks are not distinguishable from random picks in the same vol pool.
  Consequences (pre-committed): (a) re-read the delivery-% near-miss against a vol-matched
  control before 0010b; (b) the live model's value reduces to "a disciplined vol screen" —
  document honestly in CLAUDE.md; (c) data-acquisition priorities shift toward sources that
  could improve WITHIN-pool selection.
- No third option; no seed-hunting; the 20 seeds are fixed at registration (1000..1019).

## Results (2026-06-11 — cloud run 27326517647 arm A + local 50-seed sweep on the SAME cache)

(Implementation note: first cloud null-sweep produced an empty-green result — fold-grid
reconstruction mismatch, fixed by deriving the grid from arm A's JSON + fail-loud on zero
folds, commit 6f88479. The scored sweep ran locally on the downloaded cloud cache artifact —
same vintage, comparison valid.)

**POOLED ≥2019 (the fork-decider): A mean Sharpe +0.634 vs null seed-mean distribution
mean +0.115 / p90 +0.450 / p99 +0.619 / max +0.657 → A at the 98th percentile, ABOVE p99
by +0.015. Per the frozen rule ("only > p99 is a clean clear") → CLEAN PASS.**
Margin documented honestly: one of 50 seeds (+0.657) exceeded A; the pass is real but THIN —
recorded as such, and the rule is not re-interpreted in either direction post-hoc.

Per-fold placement (A's percentile within each fold's 50-seed null):
| fold | A | null mean | A pctile |
|---|---|---|---|
| 2017 | +1.89 | +1.61 | 68% |
| 2018 | +0.17 | **−2.00** | **100%** |
| 2019 | −0.15 | **−2.17** | **100%** |
| 2020 | +0.85 | +0.85 | 52% |
| 2021 | +3.27 | +1.22 | **100%** |
| 2022 | −1.02 | −1.05 | 58% |
| 2023 | +1.24 | +0.35 | 84% |
| 2024 | **−0.72** | +0.45 | **4%** |
| 2025 | −0.45 | +0.03 | 38% |
| 2026 | +2.04 | +1.24 | 94% |

## Verdict — SELECTION IS REAL (clean pass per the frozen fork), with a named caveat

1. **The selection-quality concern is CLOSED; prior verdicts stand as read** (incl. the
   delivery-% near-miss — no mandatory vol-matched re-read). The model's name-level
   discrimination beats vol/count/outcome-matched random selection at the 98th pctile pooled.
2. **WHERE the skill lives:** overwhelmingly in the toxic-pool years — 2018/2019 (null −2.0
   to −2.2, A ≈ flat → 100th pctile both) and 2021/2026. The picks avoid the poison in the
   vol pool more than they find extra winners in good years (2017/2020/2022 ≈ coin-flip vs null).
3. **Named caveat (forward-wall watch item, NOT a verdict change):** 2024 sits at the 4th
   percentile (A −0.72 vs null +0.45 — picks did WORSE than random) and 2025 at the 38th,
   on thin fold trade counts (40, 17). Either selection skill faded in the recent regime or
   small-n noise; 2026 at 94% argues noise. Pre-commit: revisit this per-fold placement when
   the forward wall has ≥6 more months — no other action now.
4. Timing-invariance reminder: this validates NAME selection only (timing held constant).
