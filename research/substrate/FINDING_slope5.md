# Finding — slope floor 3%→5% starves Grade A of competition; it dilutes selection, not selects trend

*Pre-registered `research/preregistry_slope5.md`, frozen before the run (R4). n_trials 122→123.
Guards: A-only baseline parity 1.004/171 PASS; frozen 0094 byte-identical 1.132/255.*

## The change (owner)

> *"make the trend rising to 5% instead of 3% and rerun"*

`slope_min` 0.03 → 0.05 — the 44w SMA must rise ≥5% (not 3%) over 13 weeks. On the LIVE config
(A-only + `LIVE_DISCIPLINE` + P2 exit). One param, frozen.

## Result — KILL, below the null

| metric | LIVE (slope 3%) | slope 5% | Δ |
|---|---|---|---|
| Sharpe | 1.055 | **0.651** | −0.40 |
| CAGR | 20.2% | **11.3%** | −8.95pp |
| MaxDD | −31.2% | **−43.0%** | −11.8pp |
| **2022-26 slice** | **1.04** | **0.51** | **−0.52** |
| trades | 184 | **196** | **+12** |
| win% | 50.5% | 48.0% | −2.6pp |
| median entry ext | +14.3% | +13.2% | −1.1pp |

0.51 is **−0.9σ below the random null (0.74)**. Signal pool 8,518 → 6,512 (76%).

## The mechanism is NOT what 0092 predicted — it is selection starvation

Pre-declared check: *if median entry extension RISES, that is 0092's late-signal effect.* **It FELL**
(+14.3% → +13.2%). So this is not "the visibly-rising MA is a late/extended signal." Different mechanism.

The tell: **trades ROSE (+12) while the pool SHRANK 24%.** Grade A is "top-5 CRS per setup week", so
thinning the weekly candidate pool does not make A better — it makes A *less selective*:

| | mean candidates/week | weeks with ≤5 candidates (all become A) | median CRS of the A-set |
|---|---|---|---|
| slope 3% (live) | 18.8 | **23.9%** | +0.0968 |
| slope 5% | 14.7 | **34.8%** | +0.0891 |

When ≤5 signals clear the filter in a week, **all of them become Grade A regardless of relative
strength** — the top-5 cut stops binding. Raising the slope floor pushed that from 24% to 35% of weeks,
so more slots fill with weaker names and the median CRS of the traded set falls. **The floor removed the
competition that makes CRS selective.** More trades, worse trades, deeper drawdown.

## Same law as `FINDING_more_slots`, from the entry side

`FINDING_more_slots` diluted A by adding cash slots (lowering risk). This dilutes A by thinning the pool
each slot draws from. Both walk the book toward the null, and for the same reason: **CRS's edge is
competition — a big field it ranks the top of. Anything that shrinks the field (fewer signals) or
enlarges the picks (more slots) degrades the ranking.** The selection is the edge; do not starve it.

## Registry note

NOT a relitigation of 0092 (KILL) — that bundled the slope floor with a tight pullback band, and finding
0035 established the **band** was the killer (0093 kept slope+qgreen and shipped). But the **direction**
is now settled the other way too: an *isolated* slope tightening also loses, via a different mechanism
(A-starvation, not the band). Entry-side changes now **0-for-13**.

## Verdict

**KILL.** R11 — nothing ships. Live config unchanged: `slope_min` stays at the 3% floor (`SLOPE_MIN=0.03`).
Frozen 0094 byte-identical.

## Next setup

The pattern is now overdetermined: entry filters (0-for-13), exit truncation (0-for-3), selection (both
directions), sizing (dilution). Every lever that touches *which* trades or *how many* loses, because CRS
selection on the full field is the edge and every change degrades the field. **The only survivor remains
the discipline config already shipped** (return-neutral, better drawdown), and the only genuinely-untested
idea is the faithful near-SMA-fire variant (`FINDING_decouple.md`) — the one lever that would *add* a
timing dimension rather than filter or resize the existing field.
