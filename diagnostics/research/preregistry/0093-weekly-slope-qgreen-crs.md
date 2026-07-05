# 0093 — Weekly six-step: slope floor + quality green + comparative-RS filter (loose band restored)

- **ID:** 0093. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 110 → 111.
- **Anchor / data:** identical cell to 0091 (corrected universe, PIT, tiered costs, 2017–2026, ₹10L) +
  pinned Nifty-500 TRI. Script `scripts/run_bhanushali_weekly_crs.py`.

## Why this trial exists
Owner spec after the 0092 KILL. 0035 showed the tight pullback band was the winner-killer, so this REVERTS
the band to 0091's loose 7% but KEEPS the slope floor + quality green, and ADDS a comparative-RS filter:
weekly RS = stock/index, buy only if RS is above its own 40-week SMA (the stock is outperforming the index
on a rising RS line). Owner asked for Nifty-50; not in the repo → uses the pinned **N500 TRI** (highly
correlated) — caveat recorded; a confirmatory Nifty-50 run only if this surprises positively.

## The FROZEN spec (deltas from 0091)

| Component | 0091 | **0093** |
|---|---|---|
| Trend | 44w-SMA up vs 4 weeks ago | `close > 44w-SMA` AND 44w-SMA up **≥ 3% over 13 weeks** (slope floor, kept from 0092) |
| Pullback band | low ≤ SMA × 1.07 | **unchanged — loose 7%** (the 0092 tight band is REMOVED per finding 0035) |
| Green | bare green | **quality green** (close > open AND close in the upper half of the range) |
| **CRS filter (new)** | — | weekly `RS = stock_close / TRI_close`; take the signal only if `RS > SMA40(RS)` |
| Entry / stop / exits / sizing / universe / costs | — | **exactly 0091** |

Thresholds frozen a priori: slope 3%/13w and CRS length 40 as owner-specified; loose band = 0091's.

## Primary metric + decision rule
Primary = corrected-universe NET Sharpe. Gates: DSR@111 > 0.95 AND CI-low > 0 AND all 3 slices > 0 →
PROMOTE; else Sharpe>0 → UNDERPOWERED; Sharpe≤0 or a negative slice → KILL. **Head-to-head vs 0091 decides
the live book**: beat-or-match on Sharpe/Calmar at cleaner trades → replace 0091; clearly worse → 0091 stays.
References: 0091 +0.869/+18.2%/−41.5%/win52; 0092 (tight) +0.142/+0.5% KILL; TRI +12.6%.

## Skeptical prior (honest)
CRS is the **0086 lever** (RS-vs-index-above-its-MA), which was a non-improvement (fixed 2025, hurt overall,
ΔSharpe −0.14), and entry-tightening on this family is **0-for-3** (0086, 0088, 0092). Removing the tight
band should recover most of 0091's return; the open question is whether slope-floor + CRS trim or help on
top of that. Most likely: no help or mild harm (RS filters lag and cut early-trend entries), verdict
UNDERPOWERED/KILL. A genuine beat of 0091 would be the first entry-side win of the arc — held to the bar.
