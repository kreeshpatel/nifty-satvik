# The real stop order — works exactly as specified, and is portfolio-NEGATIVE (2026-07-16)

Owner spec: the stop is a **real standing order** — live on every DAILY bar, filling **AT the stop price
(face value)** when the session trades through it, or **at the OPEN when the session gaps below it**. The
engine's default instead checks the stop only at the **weekly close** and fills the next Monday open.
Lever `hard_stop` (default off ⇒ byte-identical). R11: a FINDING, no retune.

## Result

| config | trades | Sharpe | CAGR | **MaxDD** | 22-26 | win | meanR | **worstR** | **R < −1** |
|---|---|---|---|---|---|---|---|---|---|
| BASE (weekly-close stop) | 168 | **1.03** | **21.2%** | **−34.8%** | **1.29** | **54%** | **+0.616** | −2.56 | **29.8%** |
| **BASE + HARD STOP** | 213 | 0.64 | 11.7% | **−55.4%** | 1.11 | 42% | +0.316 | **−1.35** | **2.3%** |
| OWNER SPEC (taught mechanics) | 172 | 0.86 | 15.0% | −34.1% | 0.79 | 44% | +0.517 | −1.61 | 12.2% |
| OWNER SPEC + HARD STOP | 200 | 0.55 | 8.8% | −43.7% | **0.41** | 38% | +0.318 | −1.09 | 2.0% |

## The mechanic is CORRECT — and that is what makes the result interesting

The hard stop does exactly what a real broker order does: trades losing more than 1R fall from **29.8% to
2.3%**, and the worst trade improves from **−2.56R to −1.35R** (the residue is honest gap-throughs). Risk
per trade is capped precisely as intended.

**And the portfolio drawdown gets WORSE: −34.8% → −55.4%.**

- trades **168 → 213** — the stop now fires on intra-week dips a Friday close never sees
- win rate **54% → 42%** — whipsawed out of trades that recover
- meanR **+0.616 → +0.316** (halved)

**You trade a few large losses for many small ones.** The equity curve then bleeds continuously instead of
taking occasional discrete hits, and continuous bleed compounds into a deeper drawdown than the gap
disasters it prevents. **Capping every individual loss made portfolio risk worse.**

This is exactly where the prior evidence pointed: **48% of stop-outs recover above the entry within 12
weeks** (`OWNER_CHART_REVIEW.md` / tv_review). A hard stop harvests more of those exits and forfeits the
recoveries. It also reproduces, on the weekly book, the repo's own appendix finding that the taught tight
candle-low stop "exits on 2-3% noise" and destroys the edge.

## The conclusion that matters

**The weekly-close stop is not a bug — it is load-bearing.** It behaves as a de-facto WIDE stop that
refuses to react to intra-week noise. The price is the occasional −2R gap disaster (KAYNES −2.03R); the
payoff is remaining in the 48% of stop-outs that come back. **Taking bigger individual losses yields a
smaller drawdown and a higher Sharpe on this book.**

Corollary: the "R" in 2R/3R is **not symmetric** — losses legitimately exceed 1R, and *making them
symmetric costs 0.62 Sharpe and 21pp of drawdown*. Any spec whose logic depends on a clean ±1R unit is
mis-specified for this book.

## 6th sighting of the standing law

Pool filter → broke CRS · 14-EMA gate → deleted the deep pullbacks · G1/G2 → chaotic cascade · ATR stop →
halved the width · taught 2R/3R → capped the tail · **hard stop → harvested the recoveries.** Every
mechanism that tightens, protects, or imposes structure removes the fat tail and regresses toward the null.
