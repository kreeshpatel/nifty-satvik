# 2026-11-17 — Artifact audit of the last two weeks' conclusions (rule 2)

Owner request 2026-11-17. **Facts only; nothing is fixed here and no conclusion is withdrawn by this file** (the one
withdrawal of the day, the cumulative-IC decay result, is handled in its own report). Each row names a merged PR, its
main conclusion as that PR stated it, the ways the conclusion could be an artifact of the method rather than a
property of the market, and whether each was ruled out — **ruled out**, **disclosed** (named in the PR but not
eliminated) or **not checked**.

"Not checked" is not an accusation of error. It is the honest state of the evidence.

| PR | main conclusion as stated | candidate artifact | state |
|---|---|---|---|
| **#191** stop floor and confirmation | Skipping tight stops is dead (total R 650 → 633–425); widening to 6–7% raises total R; the best single-path setting (2.0×ATR) is inside noise on 20 paths; confirmation entry is dead on A | single path for the 14-setting screen | **disclosed** — five settings were then re-run on 20 paired paths; nine have a single-path number only |
| | | selection: 8% was the best of 14 settings looked at | **disclosed** in the PR and again in pre-reg 0152 §3 |
| | | open trades counted at the cutoff (84 of 525 trades are `eos` at 2024-06-28, and total R sums include them) | **not checked** — every "total R" figure in that PR includes open positions marked at the cut |
| | | the best regime cell is one episode (90% of +136.8R is 2020) | **disclosed** in the PR |
| | | sizing: the position-shrinking channel assumed for widened stops | **not ruled out, and later shown false** (#204: the 20% notional cap binds on ~55% of positions) |
| **#192** system inventory and benchmarks | On a common 2019-03..2024-06 window: momentum 0001 43.1% CAGR / 1.85 Sharpe, live swing 20.6% / 1.03, Midcap150 Momentum 50 TRI 33.8% / 1.59 | survivorship in the momentum universe | **disclosed** — `docs/PLAN_2026Q3_STRATEGY.md` records the universe as survivor-biased; the inventory repeats it |
| | | anchor integrity | **ruled out** — the momentum run reproduces its published 21.73% / 1.130 / −37.17% exactly |
| | | single path for every row except the live swing (which also shows a 20-path median) | **disclosed** — the other rows are one start date and one cost assumption |
| | | strategy figures pre-tax, benchmark TRI net of a 0.4% fee assumption | **disclosed** in the PR |
| | | window alignment: a common window chosen after the series were in hand | **not checked** |
| **#194** frozen expectation bands | Forward bands for four strategies, keeping the wider of a 20-path ensemble and an 8-week stationary block bootstrap | the bands are built on the same train window the strategies were developed on | **not checked** — nothing in the band construction discounts for that |
| | | the 20 ensemble paths share one price history (dependence between paths) | **partly ruled out** — the block bootstrap is the second source and the wider percentile is kept |
| | | the live swing's band comes from a book whose sealed-slice median Sharpe was **−0.41** (finding 0151) | **not checked** — the band does not reflect that read |
| | | open trades at the cut inside the path statistics | **not checked** |
| **#202** 0152 withdrawn | The stop effect at fixed position sizes is inside path noise, so the rule is withdrawn unrun | the withdrawal rests on a noise reading, not on a sealed test | **disclosed** — the file says withdrawn **unrun**; no sealed read was spent and no KILL is claimed |
| | | the pre-registration's own funding-channel reasoning | **ruled out as false** and recorded in the file rather than edited away |
| | | multiplicity: 14 stop settings looked at before the pre-registration | **disclosed** in §3 |
| **#204** widen-to-8% decomposition | The stop level alone is inside noise (+0.20 [−0.20, +0.32], 15/20, drawdown 3.6pp deeper); the full rule's +0.37 is an interaction of two levers | cap/sizing binding | **ruled out by measurement** — median weight at entry 0.200, 55% exactly at the cap; this is the finding |
| | | single path | **ruled out** — 20 paired paths, paired by draw, read as p5 > 0 / p95 < 0 |
| | | fresh-capital sub-period slicing | **ruled out** — continuous slices of one run per path (`nq.lab.ensemble`) |
| | | open trades at the cut in the per-trade table | **not checked** — `total_R` and `big_winners` include `eos` rows |
| | | one window, 2019-03..2024-06, containing one crash and one long trend | **not checked** |
| **#205** FII/DII positioning | A descriptive null: no monotone relation in any of eight features; levels are largely the trend state already held; it does not separate the weak-but-calm state | instrument substitution — F&O **positioning** was measured, not the cash flows the spec asked for | **disclosed** prominently, with the reason the cash series is unobtainable |
| | | multiplicity: eight features × four buckets × three regime dimensions × six years | **disclosed**; no rule proposed, so nothing was selected on it |
| | | trade-level dependence — trades entered in the same week share one reading, and no clustered or block interval was computed | **not checked** — the bucket means carry no interval at all |
| | | power: a null on 467 trades in 24 cells | **disclosed** — stated as "not demonstrable on this sample", not "absent" |
| | | survivorship / PIT in the positioning series | **ruled out** — each day's file is read at its own publication date; nothing is backfilled |

## Pattern worth naming

Two artifacts recur and neither has ever been checked in this programme's swing work:

1. **Open trades counted at the cutoff.** Every `total_R` figure on dataset A includes the 84 positions still open at
   2024-06-28, marked at the cut. That inflates or deflates every total-R comparison by an unmeasured amount, and the
   650.2R anchor itself contains it.
2. **Trade-level dependence.** Trades entered in the same week share a market and, in the cross-tabs, share a single
   regime or flow reading. Per-bucket means are reported without any interval that accounts for it. The 20-path
   ensemble handles this for *account* statistics; nothing handles it for *per-trade* tables.

Both are flagged, not fixed, as instructed.
