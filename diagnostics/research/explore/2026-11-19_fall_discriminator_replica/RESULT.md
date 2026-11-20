# Feature (a) blind replica — result

Code: replica.py (reads inputs/ only). Per-trade output: per_trade.csv.

| cohort | n | mean a | median a |
|---|---|---|---|
| noise_stop | 367 | -0.128593 | -0.094846 |
| false_touch | 299 | -0.120588 | -0.091555 |

diff = mean(false) - mean(noise) = **+0.008005**
Cluster bootstrap (2000 draws, seed 20261119, 265 noise / 230 false unique tickers): 95% CI **[-0.008700, +0.025867]**
Pooled SD of a (all 666, ddof 1) = **0.116252** (within-group pooled alternative: 0.116272)

Edge-case counts: entry/stop not a ticker session 0; peak reset to window start 2; empty leg 0; beta n<126 0; index return missing in leg or beta window 0.

## Ambiguities and readings chosen
1. "Last 126 sessions" = 126 return observations dated on the 126 ticker sessions before entry (not 126 prices -> 125 returns). All trades got n=126.
2. Calendar mismatch: stock returns are on the ticker's own calendar (a return after a gap spans several days) but are paired with the single-day index return on the same date. 218/666 trades have at least one ticker gap in beta+window span. Followed spec literally; not compounding the index over gaps.
3. rm_leg compounds index returns only on ticker leg sessions (index days the ticker skipped are dropped), per spec literal wording.
4. Peak reset rule applied when argmax (first among ties) == stop_time; leg then = sessions after window start.
5. Percentiles: numpy default (linear interpolation).
6. "Pooled SD" read as SD of the concatenated a values (ddof 1); within-group pooled variant reported too.
7. Bootstrap: clusters are per cohort (a ticker present in both cohorts is a separate cluster in each); empty draws impossible.
