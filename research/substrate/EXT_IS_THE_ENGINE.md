# Entry extension on the TRADED book — the "we buy too high" objection, answered with the counterfactual

*Measurement only — no trial spent, live config untouched. 2026-07-16. Reproduces from the live book of
record (base 0094 + P2 exit, 168 trades, Sharpe 1.0342); 151 have a resolvable signal-week SMA.*

## The objection (owner, from charts)

Reviewing LTFOODS, KIRLOSBROS and KNRCON: *"why will we enter here… this big candle creates no upside
left"*, *"candle is very big"*, *"why will we enter at such high levels"* — **"I feel we are missing
something and that thing is selecting stocks like this."**

## The mechanism is REAL and exactly as described

| | signal range | body frac | entry ext vs SMA | risk% | R |
|---|---|---|---|---|---|
| LTFOODS 2025-06-30 | 28.1% | 0.58 | +23.1% | 19.5 | −1.08 |
| KIRLOSBROS 2024-11-04 | 24.8% | 0.93 | +29.5% | 19.9 | −1.04 |
| KNRCON 2024-06-10 | **43.8%** | 0.20 | **+40.1%** | 25.3 | −1.05 |

KNRCON is the clean illustration. SMA44 ≈ 269.7. The touch rule tests the **low**: 282.43 ≤ 269.7×1.07 =
288.6 ✓, so the signal fires legitimately. We then fill at the next open, **377.84 = +40.1% above the
SMA**, because the 0089 in-range fill may land anywhere inside a candle spanning 43.8%.

**The touch validates the LOW; the fill happens at the TOP.** The owner's structural read is correct.

## The conclusion, however, is backwards — extension is where the money is

Traded book, n=151, entry extension vs the signal-week 44w SMA:

| bucket | n | meanR | medianR | win% | **total R** |
|---|---|---|---|---|---|
| <0% | 1 | +1.47 | +1.47 | 100% | +1.5 |
| 0-5% | 3 | +0.05 | −0.07 | 33% | +0.2 |
| 5-10% | 15 | +1.71 | +2.14 | 80% | +25.6 |
| **10-15%** | 35 | **+0.14** | **−0.93** | **43%** | +4.8 |
| **15-25%** | **63** | **+0.89** | +1.50 | 59% | **+56.0** |
| **>25%** | **34** | **+0.44** | +0.08 | 53% | **+15.1** |

- `Spearman(ext, R) = −0.092` — **no meaningful relationship.**
- `corr(ext, signal candle range) = +0.481` — "we buy too high" and "the candle is too big" are **the
  same variable**, which is why the small-candle kill (`FINDING_small_candle.md`) already covers half of
  this objection.
- **The 15-25% and >25% buckets contribute +71.1R of the book's +103.1R — 69% of the entire return.**
  The three charts objected to sit in exactly those buckets.
- The **worst** traded bucket is **10-15%** (meanR +0.14, median −0.93, win 43%) — not the extended one.
- Only **4 of 151** trades entered below 5% extension. Not because the rule avoids them: because CRS
  never ranks them top. The near-SMA edge is real and **unreachable by selection** (this is the
  `POOL_vs_SELECTION.md` result, confirmed at trade level).

## Same setup, opposite outcome — the counterfactual the loser-list hid

Biggest winners bought at ≥20% extension:

| ticker | entry | ext | range | R | exit |
|---|---|---|---|---|---|
| MCX | 2023-09-04 | +20.3% | 16.8% | **+3.6** | trail |
| GUJGASLTD | 2019-08-05 | +20.5% | 18.4% | **+3.6** | blowoff_half |
| ESSELPACK | 2020-04-13 | +22.5% | 19.4% | **+3.2** | blowoff_half |
| INDIAMART | 2020-08-03 | +26.2% | 22.6% | **+3.1** | blowoff_half |
| GUJALKALI | 2021-04-12 | +24.0% | 22.8% | **+3.0** | trail |
| KALYANKJIL | 2023-06-19 | +25.6% | 23.8% | **+2.7** | trail |

## Root cause of the illusion — a methodology failure on OUR side

The review CSV handed the owner **30 randomly-sampled LOSERS** with no matched winner sample. Every
extended entry in that list lost, because **every trade in that list lost** — the bucket was defined by
outcome. Reading entry quality off it is selection-on-outcome, and the trap was built into the artifact
we produced, not into the owner's reasoning. **Any future chart-review export must ship a matched
winner sample for every loser bucket, or it manufactures exactly this false inference.**

## Why the fix cannot work (already established, not re-run)

`CRS_DISSECTED.md` §5: **relative strength and extension are the same phenomenon.** High-RS names *are*
extended — their extension is a *consequence* of the strength that makes them win. Every version has
been tested and lost: `near_sma`, `ext_cap`, pool-filter, stratified-CRS (H1), bucket-prior (H2).

The sharpest prior result (`POOL_vs_SELECTION.md`): dropping the worst pool band raises the **random**
floor 0.67 → 0.85, but **collapses CRS from 1.29 to 0.47** — *below that filtered pool's own random
mean* (~1.9σ). Filtering by extension pushes CRS out of its hunting ground and into the tail where it
has no skill.

## Verdict

**No trial spent. Nothing to test — the lever is already killed in five formulations.** Do not
re-propose extension caps, near-SMA fills, or candle-size filters without a genuinely new formulation
(R-registry rule 1). The live config stays FROZEN.

## Next setup

The standing law now has a corollary worth stating: **the properties that make these trades look wrong
on a chart are the properties that make them pay.** Big candle, high extension, wide stop, ugly entry —
all four are the same underlying variable (momentum), and all four are load-bearing. Chart intuition
reliably indicts the fat tail, because the fat tail is by construction the trade that already ran.
