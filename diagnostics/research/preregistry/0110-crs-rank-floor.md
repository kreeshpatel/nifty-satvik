# Pre-registration 0110 — Absolute CRS rank floor (cash waits for quality) on the swing book

**Status:** PRE-REGISTERED (before the run; single arm, fixed). **Date:** 2026-07-27. **n_trials:** +1 -> 136->137.

## Overlay
An ABSOLUTE quality floor on signal activation: a signal may open an entry window only if its CRS strength
(crs_dist, the 0094 rank) >= the **expanding 75th percentile of all PRIOR signals' ranks** (PIT: strictly
earlier dates only; no floor until >=100 prior signals). Effect: in weak weeks the book does NOT fund the
best-of-a-bad-week — cash waits for signals that clear the absolute bar. Distinct from A-grade (relative
top-5 PER WEEK); this is absolute ACROSS time. Motivated by the funding-queue measurement: pool expR +0.16,
funded book +0.48, idealized top-255-by-CRS +0.72 — cash-timing costs ~1/3 of the achievable per-trade
edge, and CRS is the only limiter that ranks the pool (Q5 +0.48; every alternative queue loses).

## Params — FIXED
- Floor = expanding trailing 75th percentile of prior signal crs_dist; min_prior = 100 signals (no floor
  before). Single arm; the 75th is not retunable (no sweep).

## Predicted direction
Fewer, better trades; higher expR; Sharpe up if the idle-cash drag < the selection gain. Effect size
potentially large (the funding gap is worth tens of R — above the ~+-10R noise floor that killed the
exit micro-edges).

## Failure modes (>=2)
1. **Idle-cash drag**: sitting out weak weeks costs compounding; if strong signals cluster when the book
   is already full, the floor removes trades without improving what funds.
2. **Distribution drift**: crs_dist levels drift with market regime; an expanding percentile adapts slowly
   and may over-block entire regimes (e.g. post-2024 chop).
3. **Composition noise**: any activation change reshuffles the cash path (0109's lesson) — though the
   expected effect size here is larger than the noise floor.

## Pre-committed bar (selection class; per-year judged)
- **SHADOW -> forward wall** iff continuous-slice: dSharpe >= +0.05 AND dCAGR >= -1.0pp AND dMaxDD >= 0
  AND no year worse by > 3pp.
- **KILL/UNDERPOWERED** otherwise. No retune of the percentile.

## Method
Frozen 0094 base (byte-identical assert) vs rank-floored activation (preprocessing filter on entry_win —
no engine edit). Full capped book, per-year table, bootstrap dSharpe CI, DSR@137, trade count + floor
time-series summary.
