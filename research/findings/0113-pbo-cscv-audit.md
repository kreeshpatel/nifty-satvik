# Finding 0113 — PBO/CSCV audit: within-family config selection carries ZERO OOS skill (PBO 46%)

**Type:** MEASUREMENT (0 trials). `scripts/diag_pbo_cscv.py`; matrix `research/exports/pbo_monthly_matrix.csv`
(17 cfg-gated swing configs x 106 months); results `research/exports/pbo_cscv_results.json`.
Scope: the cfg-lever family on the frozen 0094 engine (cross-script family 0084-0099 not re-runnable).

## Result
**PBO = 46.2%** (P that the IS-best config underperforms the OOS median; <=20% healthy, >=50% overfit).
IS-best Sharpe **1.239 -> 0.843 OOS**, vs OOS median **0.835** — the in-sample winner lands exactly at the
median: **picking the IS-best confers no OOS selection skill within this family.** IS->OOS Sharpe
degradation factor ~0.68 (a ~32% haircut on any in-sample-selected number from this family).

## Read
1. **Validates the program's refusal to adopt in-sample winners** — every KILL/no-adopt this arc was the
   right call; a config chosen by IS Sharpe would have delivered median performance at best.
2. **Calibrates trust**: treat any in-sample Sharpe from this family as carrying a ~1/3 selection haircut;
   the family's honest OOS expectation is ~0.84, not the 1.13-1.24 in-sample prints.
3. Supports the barbell sizing logic: capital fraction should be set against the haircut number, not the
   headline. Consistent with DSR (0093 DSR 0.529) from an independent method.
