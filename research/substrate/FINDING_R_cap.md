# Capping R at 5% — the owner's diagnosis was right, the fix loses (2026-07-16)

Owner: "R of 15 percent is too much. we can max tackle R of 5 so 2r is 10 percent." Lever `max_risk_pct`
raises the stop to `entry*(1-max_risk_pct)` when the signal-week low is further away. Default None ⇒
byte-identical. R11: a FINDING, no retune.

## The diagnosis was CORRECT

The signal-week low sits a **median 14.2%** below entry, so **2R requires a ~28% gain** and the taught
2R/3R targets essentially never fire — the scaled exit's mix was **sma_break 72%**, i.e. the tranches never
ran and everything rode to the SMA. Capping R to 5% makes 2R a **10% move** and the tranches do book
(`stop_part` appears at 18%). The mechanism was diagnosed exactly right.

## The fix loses at every deployment level

| config | trades | Sharpe | CAGR | DD | **22-26** | meanR | R% | **meanR x R% = actual move** | avg pos |
|---|---|---|---|---|---|---|---|---|---|
| **BASE (2% risk, R~14%)** | 168 | **1.03** | 21.2% | **−34.8%** | **1.29** | +0.616 | 14.2 | **8.75%** | 6.9 |
| Rcap5% @2.0% risk | 122 | 0.67 | 12.6% | −47.5% | 0.55 | **+0.846** | 5.0 | 4.23% | 4.6 |
| Rcap5% @0.7% risk | 381 | 0.69 | 11.3% | −44.8% | 0.50 | +0.700 | 5.0 | 3.50% | 14.8 |
| Rcap8% @1.1% risk | 279 | 0.76 | 13.3% | −57.2% | 0.94 | +0.645 | 8.0 | 5.16% | 12.8 |
| Rcap5% + HARD stop | 217 | 0.18 | 1.5% | −54.7% | **−0.02** | +0.316 | 5.0 | 1.58% | — |

Deployment-matched controls (0.7% / 1.1% risk, to restore position count) **still lose**, so it is not a
concentration artifact. The idea itself does not pay.

## The metric trap — why "+0.846 meanR" was an illusion

R is a **ratio**. Capping R shrinks the denominator, so meanR rises *mechanically* while the money captured
falls. **meanR x risk% = the actual price move captured per trade:**

- BASE: 0.616 x 14.2% = **8.75%**
- Rcap5%: 0.846 x 5.0% = **4.23%** — **less than half**, while meanR looked **37% better**.

**R-multiples are not comparable across different stop geometries.** Any comparison that ranks configs by
meanR while the stop width changes is measuring the denominator, not the edge. This is precisely the class
of error that makes a backtest look good and a live account bleed.

## And the hard stop at R=5% is fatal

Median hold collapses to **10 days**, **80% of exits are the stop** (hardstop 71% + gap 9%), 22-26 **−0.02**.
A 5% stop sits **inside** the 7.83% median weekly ATR — it harvests noise, not information.

## 7th sighting of the standing law

Every mechanism that tightens, protects or imposes structure removes the fat tail and regresses toward the
null: pool filter · 14-EMA gate · G1/G2 · ATR stop · taught 2R/3R · hard stop · **R-cap**. The book pays
because its stops are wide enough and its exits loose enough to stay in a small number of trades that run
a long way.
