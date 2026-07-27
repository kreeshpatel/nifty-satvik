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
| 9 | 2026-07-27 | **0120 earnings-calendar screen** (pre-registered; appended BEFORE the run) | event exposure/proximity (two-layer PIT) → R, false_touch vs noise_stop, exit_too_early | train only; sealed untouched | *pending* |

**Running screen count: 9.** Multiplicity note: rows 1-6 spanned ~25 feature-target comparisons; any
future "significant at 95%" single comparison should be read against that denominator.


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
