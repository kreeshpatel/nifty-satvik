# Label-Screen Ledger — every screen ever run against the banked 0116/0117 label dataset

**Standing rule (owner, 2026-07-27):** screens against the banked context/label dataset
(`research/substrate/context_windows.parquet`) are free of `n_trials` but NOT free of multiplicity.
One row per screen, appended BEFORE the screen runs. Every screen readout must state the running
count. The dataset's evidential value deflates with reuse — this ledger is how that reuse is priced.

| # | date | screen | features → target | slice | outcome |
|---|---|---|---|---|---|
| 1 | 2026-07-27 | 0116 Stage A (path-shape family) | 10 path features → per-trade R, conditional ext×CRS | train 2019-24H1 | 1 CI-clean candidate (path_eff) |
| 2 | 2026-07-27 | 0116 Stage B (frozen path_eff rule) | path_eff>q67 → kept-vs-skipped R | train + SEALED (opened once) | **sign flip on sealed → KILL** |
| 3 | 2026-07-27 | 0117 cohort 1 (whipsaw discriminability) | 5 in-flight stop-time features → noise_stop vs false_touch | train | all CIs straddle → hindsight-only |
| 4 | 2026-07-27 | 0117 cohort 2 (pyramid marks) | 5 day-10 features → exit_too_early / final R | train | unmarked; head-start confound exposed |
| 5 | 2026-07-27 | 0117 cohort 2b (forward-leg check) | ret10 → SUBSEQUENT-leg R | train | IC −0.029, 6/6 yrs ~0 → domain closed |
| 6 | 2026-07-27 | 0117 cohort 3 (rotation bound) | loser capital vs same-week queue | train (capped book) | bound ≈ 11R/yr with clairvoyance → closed |
| 7 | 2026-07-27 | **0118 delivery-quality screen** (pre-registered; appended BEFORE the run) | dlv_med21 / dlv_trend / dlv_dwn21 (+z forms) → R, false_touch vs noise_stop, exit_too_early | train only; sealed untouched | **PASS: dlv_med21 cond dR +0.363 [+0.13,+0.58], 5/6 yrs, ADV-robust** (Q1 weak/odd-sign; Q2 null) |

| 8 | 2026-07-27 | **0119 tiebreak activation bound** (appended BEFORE the run) | mechanical swap simulation: dlv_med21 tiebreak at the last funded slot → realized R delta | train capped book vs substrate | **GATE FAIL: 15 swaps/5.5y, clairvoyant bound −1.29 R/yr (wrong-signed, ≪ ±10R floor) → no trial** |
| 9 | 2026-07-27 | **0120 earnings-calendar screen** (pre-registered; appended BEFORE the run) | event exposure/proximity (two-layer PIT) → R, false_touch vs noise_stop, exit_too_early | train only; sealed untouched | **Q2 PASS: known-event-14cd dR −0.383 [−0.68,−0.12], 5/6 yrs, ADV-robust (10% activation). Q1 headline dismissed (duration confound); ft-vs-ns +9.8pp CI-clean; Q3 null** |
| 10 | 2026-07-28 | **0121 deferral activation bound** (appended BEFORE the run) | mechanical deferral simulation on the 0120-activated trades (engine-faithful re-signal within 28cd post-event, else lapse) → net annual R delta vs originals + cohort accounting | train only; sealed untouched | **GATE FAIL: 94% lapse (setup does not survive the event) → de-facto skip; net −15.72 R/yr (activated cohort is worse-than-peers but +0.51R positive-EV; pure-skip −21.0, ceiling +36.9) → no trial** |
| 11 | 2026-07-28 | **0122 ratings tail-screen** (pre-registered; appended BEFORE the run; the session's ONE screen) | PIT-knowable negative rating action in trailing 180cd → disaster (R≤−1.5) vs era-matched controls | covered era only (2023-02..2024-06 train); sealed untouched | **COVERAGE-KILL: the filing stream has no usable equity linkage (free-text symbol junk; 0% universe overlap) — mechanism never tested; census #4 closes** |

| 12 | 2026-07-30 | **0123 vision-graded chart structure** (pre-registered; appended retroactively 2026-07-31 — see note) | model-graded blind chart structure (681 entry-truncated charts, grader validated FIRST: test-retest kappa 0.867 + clean truncation probe) -> false_touch vs noise_stop vs strong-winner | train only, matched across all 9 ext x CRS cells; sealed untouched | **NULL: grades flat (winner 1.339 / noise-stop 1.313 / false-touch 1.383), per-year 2/6, all conditional CIs straddle zero; null in BOTH detector-agreement (+0.042 [-0.045,+0.130]) and disagreement (-0.032 [-0.166,+0.103]) cohorts -> fifth pre-entry wall** |
| 13 | 2026-07-31 | **0126 line-hugger screen** (pre-registered; appended BEFORE the run; the session's ONE screen) | name-level 52w signal base rate (`hug_index`, `median_abs_ext`, `touch_count`, PIT) -> Q1 false_touch vs noise_stop/winners; **Q2 split the <5% ext band's +0.717R core by hug**; Q3 re-touch within 8w of a stop-out vs cold touches | train only (split==train AND entry_date <= 2024-06-30 -> 2019-22, 1619 trades); sealed untouched | **KILL, all three legs.** Q1 conditional +0.022 [-0.192,+0.243], ADV-robust null; **Q2 rare +0.418 (N=62) vs chronic +0.954 (N=60), delta -0.536 [-1.493,+0.334] -- point estimate WRONG-SIGNED vs the hypothesis, UNDERPOWERED**; Q3 hot +0.446 (N=136) vs cold +0.459 (N=1483), delta -0.013 [-0.843,+0.617], 8.4% activation. Confounds did NOT fire (corr hug~CRS -0.181, hug~ATR -0.274) -- a genuine independent feature that separates nothing. Activation bound NOT run (pre-committed to a PASS only). |

**Running screen count: 13.** Multiplicity note: rows 1-6 spanned ~25 feature-target comparisons; any
future "significant at 95%" single comparison should be read against that denominator.

**Bookkeeping correction (2026-07-31).** Row 12 (finding 0123) was declared screen #12 in its own
finding and in the standing counts, but was never appended here; the ledger read 11 while the
programme read 12. Row 12 above reconciles the two. The standing count was always the correct one —
the omission was in this file, and no screen was ever run unpriced.


## STANDING LAW — the activation-bound gate (owner, 2026-07-27)

NO usage trial may be pre-registered until a zero-trial CLAIRVOYANT ACTIVATION BOUND has been run:
how often would the proposed rule actually fire on the train years, and what was perfect execution
worth historically, vs the ±10R/yr path-noise floor (0109). Below the floor (or wrong-signed) →
underpowered BY CONSTRUCTION, no trial, record the bound. Precedents: the rotation bound (0117,
~11R/yr clairvoyant → closed) and the tiebreak bound (0118 addendum, −1.29R/yr → no trial).
Population gradient ≠ decision-point value is an ENFORCED CHECK, not a remembered lesson.

## Sealed-set opens (2024H2+ validation slice — every open is priced like any other reuse)

| # | date | opened by | purpose | outcome |
|---|---|---|---|---|
| S1 | 2026-07-27 | 0116 Stage B (frozen path_eff rule) | sealed validation of the frozen rule | sign flip → KILL |
