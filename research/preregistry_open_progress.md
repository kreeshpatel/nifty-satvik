# PRE-REGISTRATION — `open_progress` (the owner's "week must open above the previous week's open")

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 116 -> 118.*

## The rule

Signal week must satisfy `open[k] > open[k-1]` — the setup may not form inside a downswing.
From the owner's round-3 chart review: *"the open price of current week should be higher than the previous"*.

**Distinct from `require_progress`** (`close[k] > close[k-1]`), which **passes** on both owner cases:

| case | signal wk open | prior wk open | open test | close test |
|---|---|---|---|---|
| ASAHIINDIA 2024-07-22 | 610.67 | 651.40 | **BLOCK** | passes |
| COHANCE 2025-02-17 | 1090.00 | 1165.05 | **BLOCK** | passes |

New formulation (R-registry rule 1). Acceptance test verified: both cases blocked; guards byte-identical
(golden 1.1319/255 · live P2 1.0342/168). Pool **8,518 -> 3,436 windows (40%)**.

## Arms (K=2 new; the owner's standing rule is "test it combined")

1. **SPEC + open_progress** — the owner's discipline config (`ext_cap=0.20, max_risk_pct=0.10,
   max_notional_pct=0.20`) plus the new rule. **THE candidate.**
2. **BASE + open_progress** — isolates the lever from the caps.

Reported alongside BASE and SPEC (both already counted).

## Measurements

Sharpe · CAGR · MaxDD · **2022-26 continuous slice** · trades · win% · meanR · median R% ·
`meanR x R%` · notional/name · mean hold · **skipped_cash** · exit mix.

## Skeptical prior — written before the run

Entry-side filters are **0-for-9** on this book (0086/0088/0092 + the Phase-1 eight). The pool cut is
severe (60% of windows removed), and `FINDING_cash_starvation` showed the book already takes only ~2% of
signals — so removing 60% of the pool may not even bind on trade count, it just changes *which* names
reach the CRS queue. Expect UNDERPOWERED / no-help. **KILL is a first-class outcome.**

## Gate

2022-26 continuous slice (R3) vs BASE **1.29** / SPEC **1.21** / random null **0.74** (sd 0.24).
DSR bar acknowledged at trial 118. **Nothing ships in-sample (R11).**
