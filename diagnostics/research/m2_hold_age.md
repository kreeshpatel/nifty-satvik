# M2 — hold-age distribution under the live no-cap exit

**Date:** 2026-07-29 · **Script:** [scripts/diag_m2_hold_age.py](../../scripts/diag_m2_hold_age.py)
· **Data:** [m2_hold_age.json](m2_hold_age.json) (survivor-only pin) ·
[m2_hold_age_corrected.json](m2_hold_age_corrected.json) (corrected universe)
· Descriptive only — no parameter searched, no arm compared, no gate evaluated.
**Counts unchanged: screens 11, sealed opens 1, n_trials 138.**

Answers the constitution G6 / B-2 question: under config P there is no time cap and no 52-week
backstop — *so how old do positions actually get, and does the tail earn its keep?*

Harness check: the frozen-defaults reference cell on the corrected universe returns **255 closed
trades**, matching the 0094 run of record exactly.

## Headline: the no-cap tail is where all the money is — and the survivorship correction makes it stronger, not weaker

Corrected universe (788 names), live config P, 130 closed trades:

| Hold bucket | n | mean R |
|---|---:|---:|
| 0–4w | 21 | **−1.72** |
| 5–13w | 30 | **−0.75** |
| 14–26w | 34 | +0.87 |
| 27–52w | 26 | +2.41 |
| 53–104w | 15 | **+9.08** |
| >104w | 3 | **+18.71** |

Mean R rises **monotonically** with holding period across all six buckets. Median hold 18w
(90d), mean 27w, max **201 weeks (~3.9 years)**; 60.0% of trades exceed 13 weeks, 33.8% exceed 26,
13.8% exceed 52. The longest decile (13 trades, ≥61w) earns **64.3% of the book's total R**.

Survivor-only pin, same config, for contrast: median 13w, max 201w, 10.6% over 52w, and the
longest decile earns **100%** of total R (53–104w mean +6.04R, >104w +6.75R). Correcting for
survivorship **raised** the long-hold cohort's mean R (6.04→9.08 and 6.75→18.71) while spreading
the R contribution more evenly — i.e. the tail is not a survivorship artifact.

The frozen 13-week cap, for reference, produces a hard wall: max 13.0w, **zero** trades past 13
weeks, and 164 of 255 exits are the time cap firing.

## Reading

1. **The cap question is now empirical, and it points the other way.** The binder's earlier
   provisional recommendation — reinstate the 52-week backstop that vanished with the P swap — is
   **withdrawn on this evidence**: a 52-week cap would truncate the 53–104w and >104w buckets, which
   together carry 18 trades at +9.08R and +18.71R. That is the book's entire positive expectancy.
2. **Short holds are the loss engine.** The first two buckets (51 of 130 trades, 39%) average
   −1.72R and −0.75R. The exit that matters is not a cap on winners but a faster cut of the
   early failures — which is precisely the pre-existing M5 question (post-tp1 giveback / the stop
   never moving) and the already-tested early-cut lever, not a new idea.
3. **Caveat that does not go away.** Long holds are the configuration where the stale-universe
   exposure (D1) bites hardest, because a name can leave the index mid-hold and keep trading in the
   book. The corrected-universe run addresses *survivorship*, not *membership staleness*; those are
   different defects. A 201-week hold spans four semi-annual rebalances.
4. Sample is small (130 closed trades, 18 past a year). This is a distribution readout, not a
   certification — it is exactly enough to stop a cap being reinstated on the assumption that the
   tail is noise.
