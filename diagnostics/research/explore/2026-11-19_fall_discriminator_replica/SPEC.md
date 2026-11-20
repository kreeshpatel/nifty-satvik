# Spec: feature (a), the market-adjusted drawdown-leg return, for two trade cohorts

Re-derive from this spec and `inputs/` only. Do NOT read anything under `/home/user/nifty-satvik/pipelines/`, `nq/`,
`diagnostics/`, `research/`, `scripts/` or any `.cache` folder. Write your own Python in this directory. Use
`source /home/user/nifty-satvik/.venv/bin/activate`.

## Inputs

- **`trades.csv`**: one row per trade. Columns:
  - `ticker`;
  - `cohort`: noise_stop or false_touch;
  - `entry_date`;
  - `stop_time`: the last session before the exit; the feature may use data up to and including this day only.
- **`closes.parquet`**: wide table of adjusted daily closes, one column per ticker, dates as the index. NaN where a
  ticker did not trade.
- **`m150_tri.csv`**: `date`, `tri`, the Nifty Midcap 150 total-return index.

## Per trade

1. **Prices.** Take the ticker's closes with NaN dropped: this is the ticker's own session calendar. Daily stock returns
   = pct change of that series. Daily index returns = pct change of the full TRI series by date.
2. **Beta.** Use the last 126 of the ticker's sessions strictly before `entry_date`. Align the stock returns with the
   index returns on those dates and drop any pair with a NaN. beta = cov(stock, index, ddof 1) / var(index, ddof 1).
3. **Window.** The ticker's sessions from `entry_date` to `stop_time`, inclusive.
   - peak = the session with the highest close in the window. Among equal maxima, take the first.
   - If peak == `stop_time`, set peak = the first session of the window.
4. **Leg.** The ticker's sessions strictly after peak, up to and including `stop_time`.
   - r_leg = close(stop_time) / close(peak) − 1.
   - rm_leg = product over the leg sessions of (1 + index daily return on that date) − 1. An index return missing on a
     date counts as 0.
5. **Feature.** a = r_leg − beta × rm_leg.

## Report, per cohort and for the difference

- n, mean of a, median of a.
- diff = mean(false_touch) − mean(noise_stop).
- **Two-sample cluster bootstrap on ticker**, 2,000 draws. For each draw, resample the noise_stop cohort's tickers with
  replacement, taking all of each drawn ticker's trades, and do the same independently for false_touch. Record
  mean(false) − mean(noise). Report the 2.5 and 97.5 percentiles.
  - Use `numpy.random.default_rng(20261119)`.
  - In each draw, draw noise_stop first and then false_touch, each as `rng.integers(0, n_unique_tickers, n_unique_tickers)`
    over that cohort's sorted unique tickers.
- The pooled SD of a over both cohorts (ddof 1).

Write `RESULT.md`, and list any ambiguity with the reading you chose.
