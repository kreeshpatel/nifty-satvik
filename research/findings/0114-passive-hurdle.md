# Finding 0114 — Passive-ETF hurdle: the book clears it in-sample, comfortably vs beta, THIN vs the best factor funds

**Type:** MEASUREMENT (0 trials). Investable-ETF NAVs (yfinance, auto-adjusted, net of expense) vs the swing
book's monthly NET returns (matrix base col). After-tax: book = yearly STCG 20.8% on positive years (no loss
offset, conservative); ETF = terminal LTCG 12.5%. Book haircut column = 10% execution-decay scenario.
(niftyindices TRI endpoint WAF-blocked 2026-07-27; ETF NAVs are the more honest investable benchmark anyway.)

## Result (common windows)
| vs | window | book AT | book AT-10% | ETF AT | margin (AT-10%) |
|---|---|---|---|---|---|
| **LowVol-30 ETF** | 8.1y | 16.4% | 14.8% | 11.3% | **+3.5pp** |
| **AlphaLowVol-30 ETF** | 5.8y | 17.0% | 15.3% | 14.2% | **+1.1pp (thin)** |
| **Nifty-50 ETF** | 9.5y | 18.3% | 16.5% | 12.2% | **+4.3pp** |

Book monthly-granularity DD −33% vs ETF −18/−24/−29. Reference: Momentum-30 funds ~15.2% (LTCG ~14% AT) —
too young to span; the book's AT-10% clears it thinly.

## Read (with 0113 applied)
The active book **clears the passive hurdle in-sample** — comfortably vs beta and plain low-vol, **thinly
vs the best factor alternatives** once the execution haircut is applied. Layer on the 0113 selection
haircut (~1/3) and the survivorship data-debt (headline inflated in a known direction) and the realized
margin vs a top factor fund is plausibly ~zero-to-small. **Conclusion: not either/or — the barbell**:
passive factor core (the hurdle asset itself) + the active book as a satellite sized by the risk-of-ruin
work, with the margin certified live on the forward wall. This is the empirical closure of action-plan
items #1-#2.
