# Pre-registration 0112 — Phase 2: walk-forward model selector swap on the capped swing book

**Status:** PRE-REGISTERED (before the run; single arm, fixed). **Date:** 2026-07-27. **n_trials:** +1 -> 137->138.
Spec `research/SELECTION_MODEL_SPEC.md` (Phase 0b PASSED +0.215 6/8 yrs; Phase 1 diffuse-but-real; finding 0111).

## Overlay
Replace the fill-priority criterion of the frozen 0094 book: instead of ordering fillable candidates by
crs_dist (strongest-first), order by the **walk-forward GBM score** (HistGradientBoostingRegressor,
max_depth=3, max_iter=150, lr=0.05 — the exact Phase-0b model, no post-hoc feature trimming). Everything
else identical (cash gate, entry band, exits, sizing). Implementation: preprocessing overwrite of the
entry_win rank element — no engine edit; base byte-identical.

## Model protocol — FIXED (mirrors Phase 0b)
- Features (14, all PIT at the completed SIGNAL week, identical at train and serve — no skew):
  crs_dist, wk_rel, ext44, body_frac, vol63, stopw_sig=(sigClose/stop-1), mkt(spot vs 50d), ivz, skewz,
  term, pcrz, breadth(pct>200d), hi52, flood(signals that week).
- Refit yearly, expanding: train on pool signals whose uncapped-fill trade EXITED before Y-01-01 (purged);
  score all year-Y signals. Years with <200 train rows (2017-2018) keep the CRS ordering (fallback = base
  behavior; those years contribute ~zero delta by construction).
- Labels: uncapped-pool trade R (signal matched to its fill by ticker + entry within 7d of signal week).

## Pre-committed bar (selection class; per-year judged; same as 0110)
- **SHADOW -> forward wall** iff continuous-slice: dSharpe >= +0.05 AND dCAGR >= -1.0pp AND dMaxDD >= 0
  AND no year worse by > 3pp.
- **KILL/UNDERPOWERED** otherwise. No retune (features, depth, refit cadence all frozen above).

## Failure modes (>=2)
1. **Pool-to-book transfer failure**: the +0.215 was measured on top-5-per-EVERY-week; the cash-gated book
   funds differently — the lift may not survive contention/composition (the +-10R noise floor).
2. **Selection-of-best inflation**: 4 selector variants preceded this winner; OOS-book is the honest judge.
3. **Fold instability**: attribution was diffuse (no feature >5/8 folds); a regime where the interactions
   invert could produce a worse-than-base year.

## Method
Base (assert byte-identical 1.132/255) vs model-ordered book; full per-year table, bootstrap dSharpe CI,
DSR@138, trade count/turnover, exit mix. If SHADOW: route to the forward wall as a WATCHED selector
(live adoption also requires the weekly-refit + model-versioning infra decision — separate, owner-level).
