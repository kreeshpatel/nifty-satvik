# 0025b — meta-labeling retest with STATE inputs (reliability features, not alpha features)

- **ID:** 0025b. Prompted by the 0025 KILL post-mortem + external research review (2026-06-11):
  0025's meta head saw the SAME 79 features as the primary, so it had nothing orthogonal to
  learn from — the generic meta-labeling prescription silently assumes the secondary model
  gets *different* inputs. 0025b is the one pre-committed retest with the inputs the
  literature says a meta-model actually wants: state/context features that modulate
  RELIABILITY without generating direction.
- **Registered:** 2026-06-11, BEFORE any 0025b arm is run. The IC-decay diagnostic
  (`diagnostics/run_ic_decay.py`, NOT a trial) runs first and its collinearity reading is
  recorded below as a falsifiable prediction — then the spec freezes.
- **Type:** model experiment, candidate-only, one shot. If this fails, meta-labeling is dead
  on this system PERMANENTLY (no 0025c) unless a genuinely new DATA source ships first.

## Question

Does a meta head trained ONLY on state features — none of which are model-alpha inputs —
discriminate the primary's winners from losers where the 79-feature meta head (0025) could not?

## The three inputs (epistemic status pre-declared)

1. **Gate-distance** (well-grounded): `confidence − min_confidence` and the raw confidence
   percentile within the day's candidates. "Marginal calls are less reliable" is the
   textbook meta-labeling exploit and is orthogonal to alpha by construction.
2. **Cross-sectional dispersion** (well-grounded, REGIME-level): the day's cross-sectional
   spread of predicted returns / realized 20d return dispersion. Modulates the whole book's
   reliability ("is there spread worth capturing today"), not per-name direction.
3. **Horizon-agreement** (ON TRIAL): sign/rank agreement of the 7d/14d/30d ensemble scores
   for the name. RISK, pre-declared: agreement among models sharing 79 inputs may measure
   *correlated* confidence (loud features), i.e. signal persistence = alpha the primary
   already conditions on — the same orthogonality failure as 0025. The IC-decay
   collinearity check below is the advance reading on this.

## Falsifiable prediction from the IC-decay diagnostic (filled 2026-06-11, spec now FROZEN)

Measured (`diagnostics/research/ic_decay.json`, pinned 744 cache, embargo-60, 7 folds):
cross-horizon ridge-signal correlations — adjacent horizons are near-collinear (5d~10d **+0.95**,
10d~20d +0.85, 20d~30d **+0.95**, 30d~60d +0.90); only the extremes retain independence
(5d~60d +0.52). The ensemble's 7d/14d/30d span maps to proxy pairs in the **0.70–0.95** band
(10d~30d +0.70, 20d~30d +0.95).

**PREDICTION (pre-committed, OPERATIONALIZED):** horizon-agreement is mostly correlated
confidence. Null band: estimate ablation noise σ by re-fitting the B meta head across the
per-fold resamples and measuring the spread of (B − B−agree) per-fold Sharpe deltas; the
agreement contribution counts as the predicted NULL iff its mean marginal Sharpe delta lies
within **±1σ of zero**. Above +1σ → the persistence-leak interpretation is FORCED (fold the
lead back to the primary's queue; meta stays killed) — never read as "meta works." The
experiment's live hypothesis rests on gate-distance + dispersion.

**Input asymmetry (pre-declared):** the three inputs do not compete for the same prize.
**Gate-distance is the ONLY input that can deliver the true meta prize** (per-name, within-day
trade/skip discrimination). **Dispersion is one number per day** — it cannot tell name A from
name B; any lift it carries is DAY-LEVEL TIMING (sit out low-dispersion days). Pre-registered
fork: if the attribution shows 0025b's lift lives in dispersion, the verdict is NOT "meta
works" — it is "a dispersion-timing overlay exists," to be re-implemented as a simple day-level
exposure rule and tested against the live bear-block for redundancy (the 0013 lesson: regime
overlays have already died once as redundant). A true "meta works" verdict requires the
gate-distance ablation to carry the lift. Horizon-agreement is predicted inert (above).

Decay-curve side-finding (recorded as a LEAD, not part of this experiment): mean directional
IC is flat ~0.04 at every horizon, but **IC-IR peaks at 5d (0.62 vs ~0.42 at 10–60d)** with
~5× more independent bets/year than 30d. Two pre-commitments for whenever this lead is
pursued: (a) the success criterion is **net IR at 5d ≥ net IR at 30d under the PRODUCTION
cost/impact model and ADV caps** — never the gross IC-IR ratio (mean IC 0.04 × ~5× turnover
is the classic short-horizon cost trap); (b) before trusting the 0.62, spot-check that the 5d
IC-series std isn't a de-overlap sampling artifact by re-measuring the 5d IC-IR on 30d-spaced
sampling — elevated IC-IR must survive the coarser grid.

## Method

Same harness as 0025 (walk-forward, expanding window, embargo-45, REPRODUCIBLE_MODE=1,
bear-block, corrected 744 cache, ≥2019 folds). Primary = the PRODUCTION recipe (fwd_max +
hit_4pct heads, frozen semantics — NOT the direction primary; 0024/0025 killed that).
Meta head = classifier on `tb_hit_14d` over cross-fitted primary-positive rows (the 0025
machinery, reused) with the feature matrix REPLACED by the 3 state inputs only.

**Arms:** A = base (0026_A vintage recipe, re-run on the same cache). B = base + state-meta
head as the confidence source. **Per-feature attribution (pre-committed):** B is additionally
re-scored with each input ablated (B−gate, B−disp, B−agree) — cheap, same trained models —
so a pass/flicker attributes to a named input.

## Pre-registered gate (same battery, no relaxations)

B clears iff vs A on ≥2019 folds at matched selectivity: mean per-fold Sharpe ≥ +0.15 (or
median ≥ +0.15); neg-folds not increased; WR ≥ base −1pp; paired bootstrap CI on per-fold
Sharpe delta > 0; DSR > 0.95 at the then-current cumulative n_trials; CAGR regression ≤ 25%
relative. **Attribution rule (three forks, pre-committed):**
- Lift lives in **horizon-agreement** → NOT "meta works"; persistence leak — fold the lead
  back to the primary's queue, record meta as KILLED.
- Lift lives in **dispersion** → NOT "meta works"; a day-level dispersion-timing overlay —
  re-implement as a simple exposure rule, test vs the live bear-block for redundancy
  (0013 lesson), record meta as KILLED.
- Lift lives in **gate-distance** → the only genuine "meta works" outcome → Stage 1.4/1.5
  path (refit thresholds, trio retrain, forward wall) as in 0025's GOOD branch.

## ADDENDUM (post-freeze, pre-data, 2026-06-11 — interpretation instrumentation only, gate unchanged)

The quantile map matches the MARGINAL trade fraction, not day-by-day counts — B can match
A's total while concentrating trades on different days (e.g. loading high-dispersion days).
That is the dispersion input working as designed, but it means a dispersion-attributed lift
needs its mechanism made visible, not inferred. Pre-commitment: **if the attribution lands on
the dispersion fork, a trade-date-exporting diagnostic must confirm the day-shift mechanism
(B's trades concentrating on high-dispersion days vs A) BEFORE any timing-overlay
implementation.** This run's artifacts carry fold aggregates only; the mechanism check is a
follow-up diagnostic, and a dispersion verdict is provisional until it passes. (A timing
overlay, if confirmed, is one number per day — implement as a scalar exposure rule, never a
16-fits-per-fold meta head.)

## Skeptical prior

0025 killed the 79-feature meta head decisively. Gate-distance is partially redundant with
the calibration the gate already applies; dispersion overlaps the (killed-as-redundant) 0013
regime overlay's information. Honest prior: ~70% clean KILL, ~20% flicker-attributed-to-
agreement (= KILL with a persistence lead), ~10% genuine pass. The value either way: this
closes the meta-labeling family with an airtight verdict instead of a confounded one.

## n_trials

+1 arm (B; the ablations are attributions of the same arm, not independent trials) →
register on run, not at prereg (the registry increments when the arm actually runs).

## Results (2026-06-10/11 — cloud run 27303663524, REPRODUCIBLE, embargo-45, bear-block, shared cache)

| arm | meanSh | medSh | neg | CAGR% | WR% | trades |
|---|---|---|---|---|---|---|
| A_base | +0.719 | +0.419 | 4 | +14.60 | 49.0 | 524 |
| B_full | +0.774 | +0.811 | 2 | +11.50 | 49.2 | 550 |
| C_no_gate | −0.318 | −0.195 | 4 | −5.07 | 28.4 | 203 |
| D_no_disp | +0.829 | +1.193 | 3 | +16.42 | 48.8 | 551 |
| E_no_agree | +0.549 | +0.457 | 3 | +8.49 | 46.4 | 613 |

- **B vs A: FAILS the gate.** Mean Δ +0.055 (< +0.15), median Δ −0.24; CI95 [−0.468, +0.618]
  straddles 0; DSR ≈ 0 @ n_trials=43. Consistency + CAGR floor pass. **Selectivity 1.05×** —
  the quantile map delivered matched trade count by construction (the 0025-C confound is gone).
- **Attribution:** gate_dist +1.09 ± 0.44 SE (POSITIVE — but see below); dispersion −0.05 ± 0.33
  (NULL); **agreement +0.23 ± 0.23 (NULL, within ±1σ) → the LOCKED PREDICTION IS CONFIRMED.**
- **The gate_dist attribution is structural, not alpha:** C_no_gate didn't underperform — it
  COLLAPSED (Sharpe −0.32, WR 28.4%, 203 trades): without the confidence inputs the referee is
  noise and the quantile map admits garbage. Gate-distance is load-bearing for the referee to
  FUNCTION — yet B (with it) still doesn't beat A. The referee's only working input is a
  re-coding of the production confidence the base already gates on directly. The meta head
  re-derives the existing gate; it adds nothing beyond it.

## Verdict — KILL, fork 4 (clean null; meta-labeling closed PERMANENTLY)

Per the frozen spec: B fails criteria 1+3; no input carries lift over BASE (gate-distance only
carries lift over a broken ablation); dispersion and agreement are inside the null band; the
pre-committed agreement-inert prediction validated against measurement. With 0025 (79-feature
referee) and 0025b (state-feature referee, matched selectivity, per-input attribution) both
null, the meta-labeling family is closed with an airtight, attributed verdict — no 0025c
unless a genuinely NEW data source ships first. The research budget moves to data acquisition:
delivery-% 0010b (collector accumulating), options-OI (UDiFF/PIT-membership landmines mapped),
fundamentals. (Cross-run note: A_base differs from 0026's arm A — separate cache vintages,
AUD-021; within-run comparisons only.)
