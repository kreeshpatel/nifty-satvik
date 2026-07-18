# Finding — the candle's size IS the edge: you cannot buy a cheap stop without buying a small move

*Pre-registered in `research/preregistry_small_candle.md` (frozen before the run, R4). Run:
`scripts/run_small_candle.py` (2026-07-16). Guards verified byte-identical first (golden 1.1319/255 ·
live P2 1.0342/168). Judged on the 2022-26 continuous slice (R3). Baseline **1.29** · null **0.74**
(sd 0.24).*

## The spec

Signal week must have `(close − low)/close ≤ 5%` (**= R ≤ 5% by construction**) **AND** body ≥ 50% of
range ("solid green"). No position cap, no R cap. Exit 60%@2R / 30%@3R / residual 10% runs to the
weekly close below the 44w SMA.

Pool: **8,518 → 984 windows (11.6%)**.

## Result — every arm loses, and arm 2 is the decisive one

| arm | tr | Sharpe | CAGR | MaxDD | **22-26** | win | meanR | med R% | **move captured** | notional/name |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE (live P2) | 168 | 1.03 | 21.2% | −34.8% | **1.29** | 54% | +0.62 | 14.2 | **+8.7%** | 14% |
| SPEC candle + 60/30/10 | 103 | 0.39 | 4.4% | −33.2% | **0.50** | 49% | +0.42 | 4.6 | +2.0% | 43% |
| **candle + live P2 exit** | 101 | 0.52 | 7.0% | −24.5% | **0.37** | 47% | +0.36 | 4.6 | +1.6% | 43% |
| SPEC + 3 signal guards | 95 | 0.28 | 2.8% | −40.7% | **0.11** | 46% | +0.39 | 4.5 | +1.7% | 44% |

**Arm 2 is the clean experiment.** It holds the exit, the sizing rule, the ranker and the fill
identical to the base and changes **only which trades exist**. It scores **0.37 vs 1.29** — −1.5σ below
the random null. So this is not the exit, not the caps, not the 60/30/10. **The candle filter itself
destroys the book.**

## Root cause — R and reward are the same variable

Pool-level, 8,150 signal windows, forward 13-week move measured from the next week's open:

| signal candle (close-to-low = R) | n | mean fwd | median fwd | win% | **mean MFE** |
|---|---|---|---|---|---|
| <3% | 734 | +4.46% | +3.59% | 60.1% | **15.3%** |
| 3-5% | 1,888 | +4.08% | +3.15% | 56.7% | 17.1% |
| 5-7% | 1,845 | +4.33% | +1.48% | 53.3% | 18.7% |
| 7-10% | 1,749 | +4.03% | +1.16% | 53.0% | 19.9% |
| 10-15% | 1,327 | +6.85% | +1.52% | 52.5% | 24.5% |
| >15% | 607 | +6.69% | +0.32% | 50.3% | **26.9%** |

`Spearman(R, forward) = −0.023` (nothing) but **`Spearman(R, MFE) = +0.105`**.

Candle size barely predicts the *average* forward return — but it strongly predicts **MFE, the size of
the excursion**. And MFE is precisely what this strategy monetises: it is a trend book whose exit is
`blowoff_half + trail`, i.e. it gets paid by riding excursions. Small candles have small excursions.
**There is nothing for the trail to catch.**

The 14.2% median R is therefore **not a defect to be engineered away — it is the price of the edge.**
A wide signal candle is what momentum *looks like*. Filtering it out doesn't buy a cheaper stop; it
buys a smaller move. Move captured collapses **+8.7% → +1.6%** with the exit held constant.

Note the small-candle trades are *nicer* trades by the usual retail metrics — win rate 60% vs 50%,
median forward +3.6% vs +0.3%. They win more often and go nowhere. That is exactly the trade this
strategy is not trying to make.

## A real confound — this run does not cleanly isolate trade quality

Notional per name is `2% risk / R%`. At R% = 4.6 that is **43% of equity in one name**, so the book can
only hold **~2 positions at a time** (base: 14% → ~7). Arm 2's 0.37 therefore mixes two effects:

1. small-candle trades have small excursions (the mechanism above), **and**
2. the book is catastrophically under-diversified — ~2 names instead of ~7.

This was **pre-declared as risk #1** before the run, so it is a known limitation, not a post-hoc excuse.
The deconfounding arm is to scale risk so notional holds at ~14% (`risk ≈ 0.65%` at R% = 4.6). It is
**not run here** — R4 forbids adding arms to chase a pass, and it needs its own pre-registration.

Honest expectation if it *is* run: the mechanism table says it should still lose, because at *equal
notional* what pays is the **absolute** % move, and small candles have less of it (MFE 15.3% vs 26.9%).
The R-multiple looks flattering for small candles (15.3%/2% ≈ 7.7R MFE vs 26.9%/18% ≈ 1.5R) — but that
is **the denominator illusion for the third time**. R-multiples do not compound; rupees do.

## Verdict

**KILL — all three arms.** R11: nothing ships in-sample. Live config untouched and FROZEN.

## What this closes

- **Closed:** small-candle / tight-geometry **selection** as an R fix. This was the last distinct way to
  attack R — we have now tried moving the stop (`max_risk_pct`, killed), capping the notional
  (`max_notional_pct`, killed), and selecting the geometry (here, killed). All three fail, and this one
  explains the other two: **R cannot be reduced without reducing the edge, because they are one variable.**
- **Established (new, general):** for this book, `candle size ≈ excursion size`. Any future lever that
  narrows entry geometry is narrowing expected MFE. This should be checked *before* proposing, not after.

## Next setup

The R question is now closed in all three directions, which retires the whole line of enquiry the last
four findings have been circling. The −2R losses are not a fixable stop-geometry problem; they are the
left tail of the same distribution whose right tail is the entire return. The remaining honest levers
are unchanged and both near-exhausted: **selection** (CRS is already at the 99-100th percentile) and
**entry** (Phase-1 exhausted 8 levers). **Sighting #9** of the standing law.
