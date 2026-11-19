# Blind replica: Amendment-2 harness-bias test (from SPEC.md only)

Code: `replica.py`. Per-seed output: `per_seed.csv`, input diagnostics: `per_seed_diag.csv`.
Nothing under `pipelines/`, `nq/`, `diagnostics/` or `.cache` was read.

## Results (100 seeds)

| quantity | value |
|---|---|
| mean(d) | **+2.348 % / yr** |
| SE = std(d, ddof 1)/sqrt(100) | 0.610 % / yr |
| z | **3.85** |
| pass (abs(z) < 3) | **FAIL** |
| mean vr | 1.1803 |
| mean g (observed Sharpe gap) | -0.0843 |
| mean p (predicted Sharpe gap) | -0.1986 |
| mean placebo return, ann. (x252) | 24.817 % |
| mean baseline return, ann. (x252) | 22.469 % |
| invested days | 1313 per seed (all seeds; = every row) |

Per-seed spread: d in [-11.3, +17.1] %/yr (sd 6.10); vr in [0.998, 1.521]; g in [-0.73, +0.70]; p in [-0.44, +0.002].

## Input facts

- Every seed: 1313 rows, 2019-03-05..2024-06-28, no NaNs, expo in [0.137, 0.99999], never 0.
- ew_universe covers every seed date (0 missing; the "missing = 0" rule never fires). It has one in-window
  date the seeds lack: 2019-03-01 (the window's first day; seeds start 2019-03-05).

## Ambiguities and readings chosen

1. "Invested days: expo > 0" -- non-binding here (expo never 0), so the filter selects all 1313 rows. Outcome
   cannot depend on its exact reading (> 0 vs > epsilon) on this data.
2. "Treat a missing date as 0" -- read as filling ew_universe_ret with 0 on seed dates absent from ew. Never fires.
   Alternative reading (drop such dates) gives the same result.
3. Seed rows start 2019-03-05, not the stated window start 2019-03-01. Took the seed's own dates as given (spec says
   align on each seed's dates). 2019-03-01 is excluded; not re-added.
4. "mean vr / mean g / mean p" -- read as the arithmetic mean of the per-seed values (not vr of pooled series, nor
   p computed from mean Sharpe/mean vr). Note mean(p) != p(mean Sharpe(b), mean vr) in general.
5. "mean placebo/baseline return annualised" -- read as mean over seeds of (per-seed arithmetic daily mean over
   invested days x 252); not geometric/CAGR. Their difference equals mean(d) exactly (2.348 %), a consistency check.
6. "the number of invested days" -- reported per seed; identical across seeds (1313), so no aggregation choice.
7. Sharpe uses no risk-free rate (spec formula has none); sqrt(252) annualisation as written.
8. SE uses the 100 seeds as independent draws; the seeds share the same universe and dates, so they are not
   independent of the market path -- the SE measures seed-to-seed (selection) noise only, conditional on one
   market path. Taken as the spec states; flagged, not changed.
