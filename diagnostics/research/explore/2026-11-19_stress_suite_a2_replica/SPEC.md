# Spec: harness-bias test (Amendment 2) for one placebo, from exported daily series only

Do NOT read anything under `/home/user/nifty-satvik/pipelines/`, `/home/user/nifty-satvik/nq/`,
`/home/user/nifty-satvik/diagnostics/` or any `.cache` folder. Write your own Python in this directory. Use
`source /home/user/nifty-satvik/.venv/bin/activate`.

## Inputs (`inputs/`)

- **`seed_000.csv` … `seed_099.csv`**: one file per placebo seed of a long-only random-entry stock book, with its
  trading costs switched off. The window is 2019-03-01..2024-06-28. Columns:
  - `date`;
  - `placebo_ret`: the book's daily return;
  - `expo_prior_close`: the share of the book invested at the previous close, between 0 and 1.
- **`ew_universe.csv`**: `date`, `ew_universe_ret`, the equal-weight daily close-to-close return of the book's eligible
  universe. It may cover more dates than the seeds; align on each seed's dates. Treat a missing date as 0.

## Per seed k

1. Baseline b_t = expo_prior_close_t × ew_universe_ret_t on the seed's dates.
2. Invested days: the days with expo_prior_close_t > 0.
3. Over the invested days only:
   - d_k = (mean(placebo_ret) − mean(b)) × 252;
   - vr_k = std(placebo_ret) / std(b), sample std (ddof 1);
   - Sharpe(x) = mean(x) / std(x, ddof 1) × √252;
   - observed gap g_k = Sharpe(placebo) − Sharpe(b);
   - predicted gap p_k = Sharpe(b) × (1/vr_k − 1).

## Across the 100 seeds

Report:
- mean(d) in % a year;
- SE = std(d, ddof 1)/√100;
- z = mean(d)/SE;
- pass if |z| < 3;
- mean vr, mean g, mean p;
- the mean placebo return and the mean baseline return, each annualised (×252);
- the number of invested days.

Write `RESULT.md`, and list any ambiguity in the spec and the reading you chose.
