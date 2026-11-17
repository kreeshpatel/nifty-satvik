# 2026-11-17 — IC decay and half-life of the two rankers

**Tier:** EXPLORE, descriptive. Weekly panel 2019-01-01..2024-06-30, prices cut at 2024-06-30 and the cut asserted. No trial, no screen row, **no sealed read**, nothing live changed, nothing adopted. Standing counts unchanged.

**What is measured.** For each Friday and each horizon *h*, the cross-sectional Spearman correlation between the ranker's value and the forward return from that Friday's weekly close to the close *h* weeks later, over the PIT Nifty-500 members. Mean IC per horizon, then an exponential fit `IC(h) = IC₀·e^(−λh)` whose half-life is `ln2/λ`.

**Why the bands are wide.** Overlapping forward windows make consecutive weekly ICs strongly dependent, so the intervals come from a **moving-block bootstrap over weeks** (block 13 weeks, 2,000 resamples). An iid interval here would be several times too narrow and would be wrong.

**One universe for both.** Both rankers are measured on the live swing universe so the two curves are comparable. The momentum book trades its own canonical universe, so its IC *level* below is not its IC on its own book — the **shape of the decay** is the comparable part.

## crs_dist (live swing ranker, 0094)

| horizon | mean IC | 95% band (block bootstrap) | weeks IC > 0 | weeks |
|---|---|---|---|---|
| 1w | +0.0222 | [+0.0028, +0.0440] | 58.0% | 286 |
| 2w | +0.0310 | [+0.0067, +0.0568] | 60.0% | 285 |
| 4w | +0.0424 | [+0.0103, +0.0765] | 62.9% | 283 |
| 8w | +0.0581 | [+0.0182, +0.1018] | 67.4% | 279 |
| 13w | +0.0786 | [+0.0314, +0.1241] | 73.4% | 274 |
| 26w | +0.1216 | [+0.0582, +0.1714] | 85.1% | 261 |
| 39w | +0.1254 | [+0.0531, +0.1746] | 85.9% | 248 |
| 52w | +0.1026 | [+0.0375, +0.1499] | 83.4% | 235 |

Half-life: no decay fitted. 0.5% of resamples produced a decaying fit. Median cross-section: 498 names.

## sma200_slope_63 (momentum ranker, 0001)

| horizon | mean IC | 95% band (block bootstrap) | weeks IC > 0 | weeks |
|---|---|---|---|---|
| 1w | +0.0412 | [+0.0200, +0.0645] | 61.2% | 286 |
| 2w | +0.0500 | [+0.0207, +0.0792] | 61.4% | 285 |
| 4w | +0.0614 | [+0.0213, +0.1018] | 66.4% | 283 |
| 8w | +0.0784 | [+0.0282, +0.1324] | 74.6% | 279 |
| 13w | +0.0980 | [+0.0354, +0.1579] | 76.6% | 274 |
| 26w | +0.1205 | [+0.0449, +0.1851] | 75.9% | 261 |
| 39w | +0.0959 | [+0.0143, +0.1615] | 72.6% | 248 |
| 52w | +0.0572 | [-0.0221, +0.1250] | 63.8% | 235 |

Half-life: no decay fitted. 32.3% of resamples produced a decaying fit. Median cross-section: 498 names.


## What this says

**Neither ranker has a half-life inside a year, because neither decays.** Both ICs *rise* with the horizon,
roughly five-fold from 1 week to 26, and only then turn:

| | 1w | 13w | 26w | 39w | 52w | peak |
|---|---|---|---|---|---|---|
| `crs_dist` (swing) | +0.022 | +0.079 | +0.122 | **+0.125** | +0.103 | ~39 weeks, still +0.10 at a year |
| `sma200_slope_63` (momentum) | +0.041 | +0.098 | **+0.121** | +0.096 | +0.057 | ~26 weeks, fading by a year |

The exponential decay model does not fit: 0.5% and 32.3% of bootstrap resamples produced a decaying curve, so the
half-life is **not estimable and is not reported**. That is the answer to the question, not a failure of the
measurement — these are slow trend signals, and the honest statement is a **peak horizon**, not a half-life.

Three things follow, none of which is a proposal:

1. **Weekly re-ranking is not too slow.** The information a fresh rank adds over one week is tiny (IC +0.022 for the
   swing ranker, 58% of weeks positive); nearly all of it is in where a name sits over months. A faster cadence
   would be buying noise, and the cost of a slower one is small. This is a direct negative for any "re-rank more
   often" idea.
2. **The swing book's rank is weakest exactly where the book acts.** The live horizon of record is 63 days (13
   weeks), where the swing ranker's IC is +0.079 — and the book's own trades are closed well before the 39-week peak
   by the scaled exit. What the rank knows and what the book holds for are not the same horizon. That is a statement
   about the exit, not an argument to hold longer, and nothing here measures what holding longer would have paid.
3. **The two rankers differ in shape, not just level.** Momentum peaks at 26 weeks and is near zero-crossing by 52
   (band includes zero); the swing CRS peaks later and is still positive at a year. They are not the same clock, so
   a shared re-ranking cadence across the two books would be a convenience, not a finding.

**Limitations.** Both are measured on the live swing universe (PIT Nifty-500, median 498 names), so the momentum
ranker's IC *level* is not its IC on its own canonical universe; only the shape is comparable. The bands come from a
moving-block bootstrap because overlapping windows make consecutive ICs strongly dependent — an iid interval would
be several times too narrow. One window, 2019 to mid-2024, which contains one crash and one long trend. Nothing is
adopted and nothing is proposed.
