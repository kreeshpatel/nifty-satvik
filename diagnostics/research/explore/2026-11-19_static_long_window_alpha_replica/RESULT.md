# Blind replica result (spec + inputs only; code: replica.py)

## Part 1 (2017-01-02..2026-06-30, 3466 calendar days, 10 tax days)
- After-tax CAGR: 15.640%  (final cash 79,41,232.71)
- p95 156-week drawdown: 23.988%  (T = 495 weekly returns)
- Total tax paid: 7,61,121.19
- Sensitivity (gain net of buy/sell costs instead of gross price): CAGR 15.640%, p95 23.988%, tax 7,61,082.86

## Part 2 (weekly returns 2019-03-15..2024-06-28)
- alpha annualised 2.710%; beta 0.5358; NW t 0.747; R^2 0.6545; n 277
- beta-matched mix CAGR 20.817%

## Ambiguities and readings chosen
1. Realised gain basis: gross (units x (sell px - lot px)); costs not in basis or proceeds. Alternative shown above; effect ~Rs 38 tax.
2. Buy cost: buy trade value = target - holding; cost 0.005% charged on top from cash (cash may dip slightly negative). Sell: proceeds x (1 - 0.001%). Targets not grossed up for costs.
3. Tax day per calendar year Y = last session <= Y-03-31 (2017..2026); paid before re-target, so cash may go negative briefly; re-target NAV includes negative cash.
4. Carried losses never expire (no 8-year limit stated). Ended at zero, so moot here.
5. Weekly series: resample W-FRI last, empty weeks dropped before pct change; partial first week (2019-03-08 / 2017-01-06) kept as a level.
6. Beta-matched years: "first week date" = date of first weekly *return* (2019-03-15), not first level week (2019-03-08).
7. R^2 = 1 - SSE/SST on excess blend returns (centred). Intercept/beta from OLS with constant.
8. NW lag term: sum_t x_t e_t e_{t-l} x_{t-l}' over t = l..n-1, plus transpose, no df correction.
9. Drawdown percentile: numpy default (linear) interpolation.
