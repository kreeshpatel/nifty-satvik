# Monte-Carlo random-selection NULL — the session's most informative test (measurement, no trial)

**Run 2026-07-16.** 100 sims. Reproduce: `python scripts/diag_random_selection.py 100`
(resumable; per-sim rows persist to `research/substrate/random_selection_sims.csv`).

## Why

The book activates 6,359 entry windows and funds **168 (2.6%)**, skipping 19,728 signal-days for cash
while ~100% invested in ~7 names. Every number we had (CRS-rank 1.29, conviction-rank 0.44) was only ever
compared to *another selector* — **never to chance**. This builds the null: identical setup, exits and
capital; only WHO gets the cash is randomised.

## The null distribution (n=100)

| metric | mean | median | std | p5 | p95 | min | max |
|---|---|---|---|---|---|---|---|
| Sharpe | **0.67** | 0.65 | 0.16 | 0.43 | 0.88 | 0.23 | 1.15 |
| CAGR | **12.5%** | 11.9% | 3.9 | 6.9% | 18.6% | 2.6% | 23.2% |
| MaxDD | **−45.9%** | −45.2% | 7.5 | −60.0% | −35.4% | −66.5% | −29.6% |
| 22-26 slice | **0.74** | 0.76 | 0.24 | 0.33 | 1.14 | 0.06 | 1.24 |
| trades | 167 | 167 | 7 | 157 | 179 | 147 | 186 |

## Where the real selectors sit

| selector | value | percentile |
|---|---|---|
| CRS-rank (live) Sharpe | 1.03 | **99th** |
| **CRS-rank (live) 22-26** | **1.29** | **100th — exceeds all 100 draws (max 1.24)** |
| CRS-rank (live) CAGR | 21.2% | **99th** |
| conviction-rank (L3) 22-26 | 0.44 | 10th — genuinely bad, not an unlucky draw |

## Findings

1. **Selection is the book's biggest lever — the owner's intuition was correct.** CRS-rank is worth
   **+0.36 Sharpe, +8.7pp CAGR, +11pp DD** over random funding of the same signals. No other lever tested
   this session approaches that magnitude.
2. **The edge splits cleanly:** ~**0.67 Sharpe is the SETUP** (touch + P2 exit + 2% sizing, funded at
   random); ~**+0.36 is CRS SELECTION SKILL** on top.
3. **This explains all five negatives with ONE mechanism.** The live book sits at the **100th percentile**
   of the selection distribution. Every change we tested perturbs *who gets the cash* — added setups,
   sleeves, routing, per-branch exits, conviction ranking — so each starts from an extreme and **regresses
   toward the random mean (0.74)**. Not five unrelated failures: one mechanism, five times.
4. **Conviction-rank (10th pct) was truly destructive**, consistent with its OOS AUC of 0.472.
5. **Calibration for every prior result:** the null's 22-26 std is **0.24** (range 0.06-1.24). Gaps
   smaller than ~0.2 in that slice are inside selection noise — e.g. sleeve D's 1.19 vs 1.29 is NOT a
   distinguishable difference, while the router's 0.71 (~2.4 std below) is genuinely bad.

## The honest caveat, and the forward expectation

CRS-rank was **not drawn at random** — it was *chosen* in-sample (findings 0037 / 0094). So part of its
99-100th-percentile standing may be selection bias rather than durable skill. Mitigating: CRS is relative
strength, an economically-motivated, well-established factor, not a fitted curiosity.

**Forward expectation (important):** if CRS's selection skill only partly persists out-of-sample, the live
book's forward Sharpe sits between **0.67 (setup only, no selection skill) and 1.03 (full skill persists)**
— it is *not* automatically 1.03. The null mean is the honest floor to plan against.

## Implication

Do not spend further in-sample effort trying to beat CRS-rank: it is already at the ceiling of what
selection achieves on this candidate pool, and any perturbation regresses toward 0.74. The live touch-only
book stands. Certification and the true forward Sharpe belong to the forward wall.
