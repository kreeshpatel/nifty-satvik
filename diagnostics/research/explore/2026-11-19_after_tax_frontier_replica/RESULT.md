# Blind replica result (replica.py, numpy 2.5.0)

| | Point A (blend, 10% vol) | Point B (static 65/35) |
|---|---|---|
| After-tax CAGR | 18.3640% | 23.2523% |
| p95 156-wk drawdown | 24.2970% | 24.7330% |
| Excess Sharpe | 0.9717 | 1.3216 |
| Total tax | 664,494.57 | 527,112.57 |
| Final cash | 4,901,539.20 | 6,078,239.81 |

Calendar days 1942; weekly returns T = 277; tax days 2019-03-29, 2020-03-31, 2021-03-31, 2022-03-31,
2023-03-31, 2024-03-28; no book exits fell before the first or after the last session.

## Ambiguities and readings chosen
1. Realised gain on a sale = units x (price - basis). Sell cost NOT deducted, buy cost NOT in basis (spec: "cost per unit = price").
2. Trade sizing: units delta = (NAV x w)/price - units held, with NAV taken before costs. Costs come out of cash, so cash can end slightly negative. No scaling to fund the buys.
3. 2019-03-29 counts as a tax day (first FY, 3 weeks old). For Point B it also triggers a re-target.
4. "Pass-through" is read as applying only to MOM/SW. Point B holds no sleeves, so the pass-through is a no-op there.
5. Daily NAV for Sharpe/DD = the step-4 recorded NAV. The final session's value is pre-liquidation and pre-final-tax, so the final tax hits CAGR only, not Sharpe/DD.
6. Weekly series: resample('W-FRI').last(), with empty weeks dropped.
7. The vol window at t uses r[t-20..t-1], with r_0 = the first row's returns. e = 1 for t = 0..19.
8. A pass-through gain with u x pnl < 0 is booked as a loss in its class.
9. Point A tax-day settle precedes the re-target. Lot sales on that same session go to the next period.
