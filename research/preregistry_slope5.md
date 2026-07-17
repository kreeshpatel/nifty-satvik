# PRE-REGISTRATION — `slope_min=0.05` (owner: "make the trend rising 5% instead of 3%")

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 122 -> 123.*

## The change

The live floor is `SLOPE_MIN = 0.03` — the 44w SMA must be up **≥3% over 13 weeks**. Owner raises it to
**5%**. One param, frozen: `slope_min=0.05`.

## Registry check — NOT a relitigation, but close to one

- **0092 (KILL)** bundled a slope floor with a **tight pullback band** (low ≤3%, close ≤6% of the MA) and
  quality-green: Sharpe 0.869→0.142, CAGR 18.2→0.5%, DD −41.5→−61.0%. **Finding 0035 established the
  TIGHT BAND was the killer, not the slope** — 0093 kept slope+qgreen, reverted the band, and became the
  live book.
- **`slope_min=0.06`** has been run only *inside* a 3-guard conjunction (with `prior_above_n=2` +
  `require_progress`) — 22-26 slice 0.75 / 0.11. **Confounded; not a verdict on slope alone.**
- **`slope_min` alone, on the live A-only + discipline book, has no record.** New formulation
  (R-registry rule 1).

## Frozen spec

`slope_min=0.05` on the LIVE config exactly: A-only (top-5 CRS/week, recomputed on the new signal set)
+ `LIVE_DISCIPLINE` (`ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20`) + P2 exit, Rs10L, 2% risk.

## Pre-declared measurements

Sharpe · CAGR · MaxDD · **2022-26 continuous slice** · trades · win% · meanR · median R% · median entry
extension · mean hold · pool size · exit mix.

## Skeptical prior — written before the run

1. **Entry-side changes are 0-for-12** on this book.
2. **0092's own readout warns the mechanism is backwards:** *"a 'visibly rising' 44-week SMA is a LATE
   signal (lagging MA → mature trend)"* — a 44-week average that has already risen 5% in 13 weeks is
   describing a trend that has largely happened. Raising the floor may select **later**, more extended
   entries, not better ones. **Mechanism check: if median entry extension RISES, that is this effect.**
3. `EXT_IS_THE_ENGINE` + `FINDING_open_progress` both found that anything raising entry extension costs
   money.
4. Fewer signals → the CRS queue reaches deeper per week; `FINDING_more_slots` showed dilution walks the
   book toward the null.

**KILL / UNDERPOWERED is a first-class outcome. Nothing ships in-sample (R11).**

## Gate

2022-26 continuous slice (R3) vs the LIVE book (A-only + discipline) **1.04** and the prior live A-only
**1.17**; random null **0.74** (sd 0.24). DSR bar acknowledged at trial 123.
