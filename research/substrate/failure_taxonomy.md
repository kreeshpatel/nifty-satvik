# Weekly-swing entry failure taxonomy (blind vision forensic, n=299)

## 1. Headline — entry quality is barely visible at entry
Blind mean setup-grade: **winners 2.72 vs losers 2.75** — losers grade *marginally higher*.
Grade distributions are near-identical (A: 6.7% vs 6.7%; B: 62.2 vs 63.3). **A blind analyst
cannot separate survivor from stopout from the entry chart alone** — consistent with the
long-standing "survivor and stopout look the same at entry" wall.

Largest winner−loser tag deltas are all small and several point the "wrong" way:
- extension `moderately_extended` **+8.2** (W 52.1 / L 43.9)
- extension `at_or_near_sma` **−5.7** (W 38.7 / L 44.4) — losers were *more* at/near the SMA
- `mid_trend_continuation` −3.8; `extended_from_base` +3.2; `clear` overhead +3.6

The one directional signal: winners skew *moderately extended*, losers skew *right at the SMA* —
echoing the deep-near-touch trap band, **not** a clean near-SMA edge. Volume/base/overhead tags
are statistically flat. Net: entry-chart aesthetics carry weak, mostly non-monotone information.

## 2. Ranked loser failure taxonomy (40 graded C/D losers)
| Mode | Count | Share | Mechanically avoidable? |
|---|---|---|---|
| climax_reversal (falling knife off blow-off top) | 15 | 38% | Yes — trailing decline / DD-from-high |
| overhead_supply_rejection (buy under recent swing high) | 11 | 28% | Yes — trailing swing-high proximity |
| no_base_whipsaw (V-snap, no consolidation) | 10 | 25% | Yes — trailing-range / base-presence |
| bought_extended_near_top | 4 | 10% | Yes — extension cap |

**~90% of deep losers cluster in three mechanically-screenable structures.** But these are the
*graded-bad* tail; the median loser looks like the median winner.

## 3. PIT-safe candidate features for Stage 5
All three trim losers **and** winners (per the per-trade→portfolio wall) → route to the **forward
wall**, do not decide in-sample.

- **`overhead_supply_8pct`** — 1 if `min(trailing_12w_pivot_highs)/entry − 1 < 0.08`, else 0.
  Pivot = local max over ±3w. Evidence: 11/40 (28%) overhead-rejection losers. Trims valid
  breakouts-through-supply too.
- **`falling_knife_vel`** — 1 if `(entry − trailing_26w_high)/trailing_26w_high < −0.15` **and**
  no ≥6w sub-range inside a 10% band in trailing 10w. Evidence: climax(15)+no_base(10)=25/40
  (63%). Will also veto sharp-but-recoverable dips.
- **`dd_from_recent_high`** — continuous: `(trailing_26w_high − entry)/trailing_26w_high`, gate at
  0.20. Cleanest single scalar for the climax-reversal cluster.

**Cross-reference:** naive **extension-cap** and **near-SMA** filters were already found
**portfolio-negative in-sample** (O-019/0079 IC≠Sharpe; deep-near-SMA memo). These reuse the same
family, so they carry the same risk — forward wall is the only certifier.

## 4. Caveats
- Blind-grade noise is high (4-way ordinal, single pass); small deltas are within noise.
- Sample is **only** 44SMA-touch + trend-pullback setups — not the full book.
- Winner contrast has **no R-multiple detail beyond R≥2** — "winner" here is coarse.
- Failure-mode counts come from the **graded-C/D tail only** (40 of 180 losers); not representative
  of the median loser, which is visually indistinguishable from a winner.
