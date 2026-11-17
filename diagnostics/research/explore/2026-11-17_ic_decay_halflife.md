# 2026-11-17 — IC decay and half-life of the two rankers

> **WITHDRAWN as a decay measure, 2026-11-17 (owner).** Every table below uses **cumulative** forward returns, where
> a growing window mechanically inherits the trend the ranker is built from. The "IC rises with horizon, no decay, no
> half-life" conclusion, and the three reads that followed it, are **withdrawn**. The decay question is answered on
> the marginal measure in [`2026-11-17_ic_marginal_decay.md`](2026-11-17_ic_marginal_decay.md), which finds the
> per-week IC flat to about 13 weeks and dying between 26 and 52.
>
> The cumulative tables are kept because they are correctly computed and still describe something real — the
> correlation of the rank with the whole move out to h weeks. They are **not** a decay measure and no half-life may
> be fitted on them. The rest of the file is left unaltered as the record of what was reported.

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


## What this says — DELETED 2026-11-17 (owner)

The three reads that stood here ("weekly re-ranking is not too slow", "the swing book acts where its rank is
weakest", "the two rankers differ in shape") were drawn from cumulative returns and are **deleted, not softened**.
The conclusions that replace them are drawn only from marginal IC and live in
[`2026-11-17_ic_marginal_decay.md`](2026-11-17_ic_marginal_decay.md):

- each ranker's **per-week** information is flat, not decaying, out to about 13 weeks;
- both die between 26 and 52 weeks, where the bands include zero;
- the half-life is estimable but a weak summary of a plateau-then-fall curve, and this sample cannot say that one
  ranker decays faster than the other.

The limitations of the cumulative tables above are unchanged: one window, one universe, and 39 and 52 weeks added
after the first look.
