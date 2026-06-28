# 0062 — EXP-0 structure overlay, VALID-ONLY (degenerate-support exclusion)

**Status:** PRE-REGISTERED (pass/kill fixed before re-running). A NEW trial (DSR n_trials++).
**Date:** 2026-06-23
**Parent:** 0061 (the all-trades overlay) — **KILLed** on its pre-committed gate.

## Why a follow-up (and why this is NOT goalpost-moving)
0061's pre-committed selection gate FAILED and is **honored** (no re-spec of 0061): Spearman 0.052
(≥0.05 ✓), top-minus-bottom +3.79 (✓), but **clean-vs-poor CI-low = −0.191** (needed > 0 — a hair below).
The result was a *rich* KILL, not a flat null:

| R:R bucket | n | mean ret % |
|---|---|---|
| [0.01, 0.40] | 88 | 3.6 |
| [0.40, 0.76] | 88 | 7.2 |
| [0.76, 1.45] | 87 | 9.8 |
| [1.45, 5.70] | 88 | **17.1** |
| [5.70, **456.9**] | 88 | 7.4 |

A strong monotone signal (3.6→7.2→9.8→17.1%) that **REVERSES in the top bucket** — R:R up to **456**
means "support" sat ~0.2% below entry, which is **not a structural floor**. Independent confirmation:
the **worst-PnL trades had HIGHER mean R:R (9.8) than the rest (6.5)** — i.e. the degenerate
support-pathologically-close cases are genuinely *bad* setups, and they inflate the clean-group variance
into the hair-miss.

This is a **correlated cell** (the owner's own rule: a KILL kills one cell, not the hypothesis). 0061
tested *raw R:R over ALL trades*. 0062 tests the **a-priori-principled subset**: a setup is VALID only if
support is a real floor — **at least 1× ATR below entry** (`atr_est = (entry − stop_price)/stop_mult`).

**This is a specification fix, not a fitted exclusion:** the cut is on **support distance** (a structural
stop inside ~1 ATR of entry is daily noise, not a level), NOT on the R:R value or the returns; it ties to
the existing ATR/min-stop machinery; and it is **independently motivated** by the worst-trades-have-higher-R:R
finding. It is the spec I *should* have written for 0061. The threshold (1× ATR) is set a-priori, not tuned.

## PRE-COMMITTED pass/kill (identical gate, on the valid-only subset)
- **SELECTION signal — GATES:** PASS iff Spearman ≥ 0.05 AND top-minus-bottom > 0 AND clean-vs-poor
  mean-return-difference CI-low > 0, computed over **valid-only** trades (`structural_valid == True`).
- **STOP signal:** corroborating-only, recovery-conditioned (unchanged from 0061).

## On PASS / on KILL — and the discipline boundary
- **PASS (valid-only):** the structural-R:R signal survives a principled cleaning → the SELECTION thesis
  has real legs. **This remains an IN-SAMPLE precondition probe** — proceed to the DEFINITIVE test: build
  Track B (filter + rank), flag-gated, and run the OOS walk-forward (EXP-1/EXP-3). Do NOT treat 0062 PASS
  as "proven."
- **KILL (valid-only):** even clean of degenerate setups the signal doesn't clear the bar → the
  structural-selection thesis is genuinely dead → stop the arm.
- **Discipline boundary:** this is the ONE follow-up. No further metric re-specs without the owner's
  explicit judgment — the per-trade data is dumped to the output so any further cell is a LOCAL
  re-analysis the owner can audit, not a quiet re-run-until-pass.
