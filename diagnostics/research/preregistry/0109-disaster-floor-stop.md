# Pre-registration 0109 — Disaster-floor intraday stop (stop x 0.90) on the swing book

**Status:** PRE-REGISTERED (before the run; single arm, fixed). **Date:** 2026-07-27. **n_trials:** +1 -> 135->136.

## Overlay
A standing INTRADAY catastrophe stop at `floor = entry-time stop x (1 - 0.10)` — 10% below the candle-low
stop, FIXED at entry (models a real broker GTT disaster order). Daily: if the session's open < floor, exit
at the open (gap); else if the session's low <= floor, exit AT the floor. The weekly close-only stop and all
other exits are unchanged. cfg-gated `disaster_floor_pct` (default 0.0 = byte-identical 0094).

## Motivation (cohort forensic 2026-07-27)
The 0105 hard_stop KILL decomposed: its damage is whipsaw on shallow intra-week piercings (14 winners
pierced the stop and recovered, 34.6R), its benefit is catastrophe-capping. Sweeping the floor deeper:
at stop x 0.90, ZERO winners in 9 years pierced (0.0R whipsaw) while 21 losers did (+4.3R saved vs actual
exits). A pure-asymmetry small edge (~+3.5% of book R) — the first exit change with zero measured winner
damage.

## Params — FIXED: `disaster_floor_pct = 0.10`. Not retunable; no sweep.

## Predicted direction
Small: dSharpe >= 0, dMaxDD slightly better, dCAGR ~ +0-1pp. The catastrophe cohort (JSL-class -2..-5R
grinds) caps near -1.4R. NOT a transformation — a tail-insurance rung.

## Failure modes (>=2)
1. **Redeployment churn**: 21 earlier exits free cash -> book composition shifts (the 0095/0104/0105
   mechanism); even a per-trade +4.3R can net negative at portfolio level.
2. **Gap fills**: gapped opens fill below the floor -> part of the +4.3R is optimistic.
3. **OOS fragility**: 21 events in 9 years is a thin sample; the "0 winners at -10%" line may not hold
   forward (a future V-bottom winner could pierce it).

## Pre-committed bar (exit class; per-year judged)
- **SHADOW -> forward wall** iff continuous-slice: dSharpe >= 0 AND dMaxDD >= +1.0pp AND dCAGR >= -0.5pp
  AND no single year worse by > 2pp.
- **KILL/UNDERPOWERED** otherwise. No retune of the 0.10.

## Method
Frozen 0094 base (assert byte-identical) vs `disaster_floor_pct=0.10`; full capped book, per-year table,
bootstrap dSharpe CI, DSR@136, exit-mix shift.
