# 0141 — Are the targets too high? Excursions against the random-walk null and a matched control

**Type:** MEASUREMENT — no trial, no screen row, nothing adopted.
**Standing counts:** screens 19 · sealed opens **2** · n_trials 2. The study itself caused the second
open; see *Governance* below.
**Date:** 2026-09-16 · **Plan:** Satvik Brain, Phase 1, item 1.
**Spec:** [`diagnostics/research/excursions_null/SPEC.md`](../../diagnostics/research/excursions_null/SPEC.md),
committed before the code, with amendments A1 (sealed slice) and A2 (post-hoc matched control, the live
stop rule, three fixes), each committed before the run it describes.
**Record:** `diagnostics/research/excursions_null/2026-09-16/summary.json` (+ `rows.csv.gz`).
**Reproduce:** `python scripts/diag_excursions_null.py --live-end 2026-09-15 --run-date 2026-09-16`.

## The question

The owner observed that "our targets are too high somewhere and that price is never hit." A low hit rate
can come from three places:
- **geometry:** a 2:1 target is reached before its stop about a third of the time by chance, whatever
  is bought;
- **the market:** a rising market lifts every stock toward its target;
- **selection:** our entries themselves.

This measures all three for the live setup (`touch44`), in R multiples, against:
- a first-passage null for the same geometry (as specified);
- same-day stocks with similar volatility and the same stop distance (A2, post-hoc — the null that
  separates selection from the market).

## Result (touch44, k = 2 — the live first target)

| population | stop rule | trades hit 2R first | first-passage null | **matched control** | excess vs control [95% CI] |
|---|---|---|---|---|---|
| train 2019–22 (n 570) | continuous | 43.0% | 36.1% | **41.2%** | **+1.8 [−1.9, +5.7]** |
| train 2019–22 (n 568) | weekly close (live rule) | 51.6% | — | **52.8%** | **−1.2 [−4.7, +2.3]** |
| holdout ≤ 2024-06 (n 329) | continuous | 55.3% | 35.7% | **50.9%** | **+4.4 [−1.1, +9.6]** |
| holdout ≤ 2024-06 (n 329) | weekly close (live rule) | 70.2% | — | **65.4%** | **+4.8 [+0.0, +9.6]** |
| live book since 2026-07-04 (n 24–26) | weekly / continuous | 33% / 31% | 35.0% | — | uninformative (95% CI ≈ 14–55%) |

CIs are cluster-bootstrapped on ticker. The full grid (k = 0.5 to 3, three stop bands, all setups) is
in the summary.

## What it says

1. **The 2R target is not too high.**
   - Under the live weekly-close stop, touch44 entries reached +2R before the stop **52% of the time in
     2019–22 and 70% in 2023–H1 2024.**
   - Against the matched control, the picture is mixed and does not support moving the target:

     | touch44, excess vs matched control (continuous stop) | +0.5R | +1R | +2R | +3R |
     |---|---|---|---|---|
     | 2019–22 | **+4.7 [+1.0, +8.3]** | +3.7 [+0.3, +7.3] | +1.8 [−1.9, +5.7] | +1.0 [−2.6, +4.5] |
     | 2023–H1 2024 | +4.2 [−0.1, +8.3] | +3.2 [−1.8, +8.0] | +4.4 [−1.1, +9.6] | +3.0 [−2.3, +8.2] |

     In 2019–22 a small early advantage (about 4–5 points at +0.5R) fades to nothing by 2R. That is the
     SPEC's rule-2 shape, an edge that decays before the target. In 2023–24 it does not fade (about +4
     points throughout, none clearly non-zero), and under the weekly-close stop 2019–22 is +3.1 at
     +0.5R, falling to −1.2 at 2R.
   - A pattern in one population, against a post-hoc null, is not a finding (A2). At most it is a
     **candidate for a pre-registered trial** of a closer first tranche, tested on train windows only,
     and decided only at a quarterly review. Nothing here supports changing `tp1_r` now.
2. **How often 2R is hit is set mostly by the market, not by our picks.**
   - Randomly chosen same-day stocks with the same volatility and stop distance hit 2R about as often:
     53% and 65%.
   - The swing from 43% to 55% between periods is the market regime.
   - Against the matched control, the entries' excess is **indistinguishable from zero in 2019–22 and
     at most borderline in 2023–24**. A2 allows a selection claim only when it holds in both evidence
     populations, and none does.
   - The large "excess" against the first-passage null (+7 to +20 points) is drift the null leaves out:
     the universe drifted about 20% a year in both periods.
3. **The live book's low hit rate cannot be read yet.** 8 targets out of 24–26 resolved trades has a 95%
   CI of roughly 14–55%, which contains both substrate rates. It sits in a falling market (Nifty −3.6%
   since inception), which on (2) is where hit rates should be lowest. Nine to eleven trades are still
   unresolved, and a 2R target takes a median ~19–27 sessions.
4. **Stop width.** No band-level claim survives. The r ≥ 10% band looked weak in one population and
   strong in the other, and near zero against the control in both. That band is also not what the live
   book trades: `max_risk_pct` pulls the stop up to 10%.

**What this points to:** the lever behind "the target is never hit" is **selection or market exposure,
not target placement**. That is consistent with program-laws II (population information does not
survive the funding margin) and with the Phase 1 plan's next item, the portfolio risk decomposition
(beta, correlation, effective bets), which measures the market-exposure half directly.

## Limits

- The matched control is **post-hoc**: added after the red-team read of the first run, and labelled
  as such.
- Controls come from the corrected universe, not point-in-time index membership.
- The substrate is the research engine's uncapped trade population (stop = signal-week low, no 10%
  cap), not the capped live book.
- "Hit before the stop" ignores the book's other exits (pattern tranche, runner). It measures entry
  geometry, not realised R.
- About 160 cells were examined. Only the pre-stated primary row and the both-populations rule are read.

## Governance

**The first run read the substrate's `holdout` split, which contains the sealed validation slice
(2024-07-01..2026-06-30).** It became the unplanned **sealed open S2**, and the red-team review of that
run read the same rows. `/skills-first` found the breach afterwards. By owner decision:
- it is **counted** (ledger row S2; standing counts updated);
- it is **disclosed**: the sealed rows sit under `sealed_S2` in the summary, never as evidence;
- it is **guarded**: `nq.brain.io.assert_unsealed` now refuses any substrate read reaching into the
  slice without a ledger row written first.

**The sealed slice is no longer clean for validating any rule about target distance, R-multiple
targets, or stop-width bands.**

The red team also found three defects in the first run, all fixed in A2.3:
- adjusted prices against raw entry and stop on the live leg;
- float noise at the 10% band edge;
- a SPEC/source mismatch.
