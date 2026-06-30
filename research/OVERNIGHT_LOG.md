# Overnight Autonomous Research Log — started 2026-07-01

> Owner is away. This is the running journal of every test run + decision taken in their absence, per
> the autonomous mandate: advance `docs/LOCK_PLAN.md`, record + **question** every result and dig
> deeper, take professional decisions without waiting, keep multi-agent work on a hybrid
> haiku/sonnet/opus tier to save tokens. **Morning briefing is at the bottom — read that first.**
> All numbers are pinned (`dataset-pin-20260701`, byte-reproducible) unless noted; every verdict is
> through the mechanized 7-gate `evaluate_overlay`.

## Standing decision rules (how I'm judging things while you sleep)
- **PROMOTE** only if `gate_pass=True` (all 7 auto-gates) AND a clean mechanism. None expected.
- **SHADOW** = positive but UNDERPOWERED (ΔSharpe CI straddles 0 / DSR<0.95) → log, touch no trade,
  flag for the forward wall. The let-winners-run lead is the live SHADOW candidate.
- **KILL** = ΔSharpe≤0 or fails the bar with a clear root cause → record + do-not-retest.
- Respect the §11 graveyard + the v1-don't-transfer rule (memory). Stay within the +6 n_trials budget
  (82→88 cap); batch correlated arms; measurements aren't trials.

---

## Test ledger

| # | Test | Run | Verdict | Decision |
|---|---|---|---|---|
| 0 | LOCK Step 1 — mechanize 7-gate bar (regression: A5 re-grades KILL identically, after-tax base ~12.76%) | local + commit bdabe59 | DONE | gates fail-closed; A5 fails 5/7 |
| 1 | **0071 let-winners-run** (B stop_only / C no_trailing / D no_target) — local --quick preview | local | B UNDERPOWERED (ΔSh +0.114, dCalmar +0.05, 2022-26 +9.6%, fold 75%, DSR 0.36); D UNDERPOWERED (+0.138); C KILL | awaiting cloud canonical → likely SHADOW |
| 1c | **0071** — cloud canonical (full 5000 samples) | run 28481282947 | **B stop_only UNDERPOWERED** (ΔSh +0.114, Sharpe 0.667→0.781, after-tax 12.76→14.87%); **D no_target UNDERPOWERED** (ΔSh +0.138, Sharpe→0.805, after-tax 12.76→**16.76%**); C no_trailing KILL | **SHADOW** the let-winners-run family (removing the target). Mechanism: target clips momentum winners + forces taxable churn. DIG DEEPER → target sweep (#2). |
| 2 | **Target give-back sweep** {15,30,40,OFF} (mechanized bar) | run 28481542316 | 30 UNDERPOWERED (ΔSh +0.116, Calmar +0.14, fold 87.5%, maxDD −40.9, after-tax 16.1%); OFF UNDERPOWERED (+0.138, maxDD −51); 15 & 40 KILL | loosen target helps; 30 best DD/robustness |
| 2b | **Mechanism dig** (local): exit-mix + return dist + maxDD across targets | local | base clips 17.7% of trades at +22.5% (right tail truncated); target=30 → maxDD −46→**−41**, CAGR→19.1; OFF → maxDD −51 (over-rides, lumpy +125% tail) | mechanism = right-tail capture w/o over-give-back |
| 2c | **Finer plateau-vs-peak grid** {20,25,28,30,32,35,40,50} (local, no bootstrap) — QUESTIONING the optimum | local | **SPIKY surface** (Sharpe 0.66–0.88, no plateau; 32 & 40 are dips). **Base 22.52 is a local DIP (0.667)** — possibly vintage-overfit. | direction robust, value NOT — see conclusion |

| 2d | **Regime-robustness split** (local): Sharpe by target on 2017-21 vs 2022-26 independently — does the edge generalize? | local | **NO** — target=30/OFF strong in 2017-21 but WORSE than base in 2022-26 (0.58/0.64 vs 0.762); halves disagree on optimum (28 vs 25). Regime-selection bias (§C3). | **REVERSAL → downgrade 0071 to no-robust-edge** |

**Finding (rigorous): "loosen the target" is REAL + DIRECTIONAL but no in-sample optimum is trustworthy.** Almost every target in [20,50] beats the base 22.52; the effect is consistent across years (target=30 fold-pass 87.5%, so not pure noise) AND improves after-tax + DD. BUT the surface is spiky (overfitting; backtest-rigor C1b peak-not-plateau) so NO specific replacement value can be picked from this in-sample sweep. The base 22.52 sitting at a local dip suggests the frozen cfg may be mildly **vintage-overfit** (connects to LOCK_PLAN D2: walk-forward re-derive the cfg). **Disposition: SHADOW the directional finding; do NOT change target_pct off in-sample; the real fix is a walk-forward re-derivation of target_pct (+ the cfg) on the corrected vintage, confirmed on the forward wall.** This is the #1 morning-discussion item.

---

## MORNING BRIEFING (read first — filled as the night progresses)

**Headline (FINAL, after rigorous stress-testing):** I chased the one promising lead — "let winners
run" / loosen the +22.52% profit target — through 4 layers of digging, and **it did not survive.** The
honest arc:
1. Full-period sweep: loosening the target (→30/OFF) looked great (Sharpe 0.667→0.78–0.81, after-tax
   12.8→16.8%, target=30 maxDD −46→−41). The "first non-KILL lead."
2. Mechanism confirmed (base clips 17.7% of trades at +22.5%, truncating the momentum right tail).
3. Finer grid → SPIKY surface (no plateau; overfitting risk).
4. **Regime split (the killer): the edge is a 2017-21 BULL artifact.** In the live-relevant 2022-26
   regime, target=30 (0.58) and OFF (0.64) are WORSE than the base 22.52 (0.762). The halves disagree
   on the optimum (28 early, 25 late). Textbook regime-selection bias (backtest-rigor §C3).

**So: NO robust promotable edge in the exits either. Do NOT change target_pct.** A faint residual
(targets 25/28/35 marginally beat the base in BOTH halves) is a weak "the base target is *slightly*
tight" hint — forward-wall watch only, not actionable now.

**What this means:** conviction (dead), sizing (dead), regime (dead), and now the exit-target lead
(regime-dependent, not robust) — **every alpha/exit lever has failed the bar.** This is the §11
graveyard confirming the base is near its ceiling. Per the LOCK STOP rule, **the base IS the model.**
The binding constraint (−46% DD) remains unsolved by any tested lever — the only real options are the
deferred Stage-G tail hedge or accepting ~−39% via the vol-target (LOCK_PLAN D1). **#1 morning
decision: D1 (accept ~−39% DD → LOCK soon) vs Stage-G; the research has run its course on alpha.**
Process lesson logged: regime-split EVERY full-period "improvement" before believing it.
