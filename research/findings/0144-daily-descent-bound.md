# 0144 — "Extensively down on the daily chart": a null, and a lookahead found in 0127

**Status:** ACTIVATION BOUND — **no trial**. Screen ledger row **#20**.
**Standing counts:** screens **20** · sealed opens 2 · n_trials **2** (unchanged by this study).
**Date:** 2026-09-25 · **Plan:** Satvik Brain Phase 1, study B2.
**Pre-registration:** [`0144-daily-descent-bound.md`](../../diagnostics/research/preregistry/0144-daily-descent-bound.md),
committed with the ledger row in `4a72b41`, **before** the diagnostic existed.
**Record:** `diagnostics/research/daily_descent_bound_0144.json` (+ `.md`).
**Reproduce:** `python pipelines/diagnostics/diag_daily_descent_bound.py`.

## The question

The owner's observation: *"when the stock is extensively down on the daily charts, the trade goes to SL."*
0127 measured the weekly version and closed both responses. The one thing it could not answer is
whether a **daily** measure says something the weekly one does not.

## Population

Uncapped substrate, `setup == touch44`, `entry_date ∈ [2019-01-01, 2024-06-30]` — **train only**,
guarded by `nq.brain.io.assert_unsealed` (verified: 0 rows in the sealed slice). 918 trades, 5.44 years,
677.0R (124.4 R/yr). Frozen before the run: `dd63` = drawdown from the trailing 63-session high,
measured to the last close **before** the fill; primary cohort `dd63 ≥ 20%`.

## Result — the hypothesis is not confirmed, and not reversed either

| cohort | N | cohort meanR | rest meanR | win% | gap [95% CI] |
|---|---|---|---|---|---|
| **dd63 ≥ 20% (primary)** | 123 | +0.861 | +0.718 | 59.3 / 53.5 | **+0.14 [−0.25, +0.54]** |
| dd63 ≥ 15% | 251 | +0.972 | +0.649 | 59.4 / 52.3 | +0.32 [−0.02, +0.67] |
| dd63 ≥ 25% | 64 | +0.872 | +0.727 | 60.9 / 53.7 | +0.15 [−0.34, +0.67] |
| dd63 ≥ 20% and ≥32 days below the 50-DMA | 46 | +0.752 | +0.737 | 56.5 / 54.1 | +0.02 [−0.60, +0.62] |

Gaps are cluster-bootstrapped on ticker. **Every interval contains zero.** Deeply-down-on-the-daily is
not worse, and the apparent "better" is not established either:

- **52% of the cohort's R comes from 2020 alone.** Dropping that year flips the sign: +0.575 against
  +0.774, gap **−0.20 [−0.63, +0.21]**. A direction that flips on one removed year is not a direction.
  (Post-hoc sensitivity, labelled as such — the year is chosen as the cohort's largest contributor.)
- Effective sample: 123 trades across 31 distinct months, one of which supplies half the R.

**Bounds.** Refusing the cohort "costs" 19.46 R/yr, but that number is mostly arithmetic: a cohort with
*zero* edge holding 13.4% of a 124 R/yr book costs about 17 R/yr to refuse by construction. The
edge-attributable part is ~2.5 R/yr, far inside the **±10 R/yr floor**. Conditional management over the
frozen set {as-is, TP@2R, TP@3R, stop@−0.5R} gains **0.0 R/yr** — `TP@3R` is the argmax in every
subgroup, so the optimum does not move, exactly as in 0127. **No trial.**

**What `dd63` actually is:** corr(`dd63`, `dist_52wh_pct`) = **−0.851** — largely a re-measurement of a
column the substrate already carries, exactly as the pre-registration predicted before the run. It also
carries volatility: corr(`dd63`, `atr_pct`) = **+0.623**. It is *not* a proxy for extension
(corr = −0.213), and stratifying by ext band leaves a weighted gap of **+0.043** — so the extension laws
are not what closes this. The noise floor is.

## The thing this study actually found: a lookahead in 0127

`pipelines/diagnostics/diag_hegclass_bound_0127.py::descent_features` takes
`k = searchsorted(week_end, entry_date)` and measures the descent depth to `cl[k]` — the close of the
week **containing** the entry. The fill is that day's **open**, and `week_end[k] − entry_date` is a
median **+4 days** (100% ≥ 0). So the depth is measured up to a full week after the trade was already on.

**A trade that falls in its first week is therefore selected into the cohort by its own outcome.**
Measured in this diagnostic: `week_end − entry_date` is a median **+4 days**, never negative (100% ≥ 0),
and the shipped cohort's mean entry-week return is **−2.38%** against **+0.80%** for the rest.

Recomputing the identical definition with the depth taken to the last **completed** week before the fill:

| 0127's weekly cohort, on this train window | N | cohort meanR | rest meanR | gap [95% CI] |
|---|---|---|---|---|
| as shipped (depth to the entry's own week) | 142 | +0.521 | +0.777 | −0.26 [−0.62, +0.14] |
| **point-in-time (depth to the prior week)** | 118 | **+0.783** | +0.731 | **+0.05 [−0.34, +0.45]** |

And the 2×2 that was this study's one new leg **collapses**:

| cell | leaked | point-in-time |
|---|---|---|
| weekly-hot + daily-hot | 104 / +0.696 | 118 / +0.783 |
| **weekly-hot + daily-cold** | **38 / +0.044** | **0 / —** |
| weekly-cold + daily-hot | 19 / +1.769 | 5 / +2.702 |
| neither | 757 / +0.752 | 795 / +0.718 |

The "slow grind into the line" cohort I was about to report **does not exist**. All 38 of its members
qualified only because price fell after entry (mean entry-week return **−6.50%**, against +0.80% for the
rest of the book). Its 40% win rate was
guaranteed by selection on the outcome. **Withdrawn**, along with the bound built on it — which was also
post-hoc, being the minimum-mean cell of four.

## For the owner: 0127 needs a decision

Finding 0127 is closed and its cohort separation (+0.062 against +0.494) is cited across the programme.
Two problems, neither of which this study may resolve on its own:

1. **The lookahead above.** On the train window the separation does not survive a point-in-time depth.
2. **The population.** `diag_hegclass_bound_0127.py` filters only `entry_date >= 2019` with no upper
   bound. A census of **dates only** (no outcome column read) gives 1,415 touch44 rows under that
   filter, a maximum entry date of **2026-06-29**, and **495 rows — 35.0% — inside the sealed
   2024-07-01..2026-06-30 validation slice**, while the finding states the sealed slice was not read
   (it names `context_windows.parquet`, the 0116 feature set).

**What was done here:** a fail-loud DEFECT NOTICE at the top of the 0127 diagnostic, changing no logic
and no published number. **What was not done:** editing finding 0127, its pre-registration, or the
registry. Re-opening a closed verdict is an owner decision at a quarterly review.

**Note the direction of the correction.** 0127's conclusion was *"the cohort is a nothing engine —
excluding it costs 1.92 R/yr and managing it differently gains 0.0"*. Removing the leak makes the cohort
look **better**, not worse, so the verdict (no trial) is unaffected. What is affected is the widely-cited
*description* that beaten-down names underperform: on this window, point-in-time, they do not.

## What this means for the owner's hypothesis

Measured three ways — weekly (0127, with its instrument corrected), daily (here), and their
intersection — **there is no established difference in outcome between names that arrive at the
44-week line after a deep fall and names that do not.** The instinct is not confirmed. It is also not
refuted: every interval contains zero, on 918 train-year trades.

Nothing is adopted. No entry filter, no sizing rule, no stop change, no exit change.

## Do not re-test unless

Forward habit-ledger rows carrying the descent fields exist, **and** the question is neither exclusion
nor conditional management over the frozen set. A different daily window, a different depth threshold,
or velocity instead of depth is relitigation and is refused. The one genuinely open item is the owner's
decision on 0127.

## Defects fixed in this study before publication

- The weekly cohort, the 2×2 and the "worst cell" all inherited 0127's lookahead (found by the
  `red-team` read). Every conclusion now reads the point-in-time depth; the leaked version is kept
  only as the defect exhibit.
- The evidence for the lookahead was originally the reviewer's own scripts. It is now computed by the
  committed diagnostic (`lookahead_evidence`, `dd63_correlations`, `population_0127_date_census`),
  because a number that re-opens a published finding must be reproducible from the pipeline.
- No uncertainty was reported anywhere: every cohort gap now carries a cluster-bootstrap interval.
- Two cohort members (THYROCARE, 2019-11-18 and 2020-01-21) had a −67.5% single-session move inside
  their window — an unadjusted corporate action, not a drawdown. A split-size guard now drops them.
- `daily_features` bounds guard `k > len(idx)` corrected to `k >= len(idx)` (never triggered).
