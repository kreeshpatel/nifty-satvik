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
| 3 | **Quality/value IC** (Step 4, 0-trial): ROE / earnings-yield / book-yield IC on per-trade P&L vs block null | local | ROE +0.078 (p.015) full-period; EY +0.046 (p.21), BY ~0. ROE looked significant. | dig → leak + regime checks |
| 3b | **ROE stress test**: 90d announcement-lag + regime split | local | **KILL** — 90d lag drops to p.053 (leakage); 2022-26 p.32 (bull artifact). Corrected ROE IC ≈ +0.037 (p.38) ≈ 0. Found a latent ~quarter fundamentals-lookahead in the store (immaterial to base). | finding 0007; orthogonal-predictor component CLOSED |
| 4 | **0074 vol-scaled DD overlay** | NOT RUN (judgment call) | DEFERRED — 4th swing at book-risk scaling; 0068 (PROMOTED) + 0070 (plateaued −38) already mapped this space; building a new engine overlay for a likely-KILL overnight is poor token value. DD is structural → Stage-G tail hedge or accept −39% (D1). | reopen only with the D-M forecast asymmetry as a distinct, owner-approved arm |
| 5 | **Randomized-entry null** (rigor P2, 0-trial): does slope beat random top-15 (same universe/exits/turnover)? 12 seeds | local | **Base VALIDATED but MODERATE:** slope CAGR 15.46 vs random mean 7.90 (DOUBLE; 92nd pct), Sharpe 0.667 vs 0.474 (+0.19, 83rd pct). ~half the return is structural (universe+exits). | finding 0008; explains why all overlays fail (no headroom) |

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

**What this means:** conviction (dead), sizing (dead), regime (dead), exit-target (regime-dependent),
quality/ROE (leak + regime KILL) — **every alpha/exit/predictor lever has failed the bar.** And the
randomized-entry null (finding 0008) explains WHY: the slope is a **real but MODERATE** edge (doubles
random's CAGR, +0.19 Sharpe) on top of a large **structural** return (universe quality + exit discipline
earn ~half the CAGR even with random selection). A moderate edge with the structural part already
captured leaves **almost no headroom** for marginal overlays — so they all KILL, exactly as observed.

**RESEARCH HAS CONVERGED. Recommendation: LOCK — the base IS the model.** It's a genuine, validated,
modest-edge strategy (PSR 0.974, certifiable; slope beats random) at its ceiling. Further alpha mining
is −EV (every lever dead + it inflates the DSR bar). The only open question is the binding constraint,
the **−46% drawdown**, which is STRUCTURAL (0070 proved sizing/exposure overlays plateau at −38%; the
COVID-2020 systematic floor). It is NOT an alpha problem.

**THE ONE DECISION FOR THE MORNING — LOCK_PLAN D1 (DD risk profile):**
- **(a) Accept ~−39% DD** → promote the O-009 vol-target into the frozen cfg, regenerate golden, write
  baseline_v2, restart the ≥30-trade paper book. LOCK in days. The base is real + certified; ship it.
- **(b) Block lock on Stage-G** (defined-risk tail hedge → dependable −30%) — the only lever that
  structurally fixes the DD, but heavy: needs an options/vol backtester + PIT F&O data (months).
My professional lean: **(a)** — the base is validated and the DD is operationally manageable with the
vol-target + kill-switch; ship to paper and build Stage-G in parallel as the scaling gate, not a launch
blocker. But it's your fiduciary call for the ~10 clients.

**Secondary (non-blocking) flags:** (1) fundamentals store has a latent ~quarter announcement-lag
lookahead — immaterial to the base (solvency screen only), fix before any fundamental-driven feature.
(2) target_pct may be *mildly* tight (25/28/35 marginally beat it in both halves) — a walk-forward cfg
re-derivation (D2) is optional polish, NOT a blocker (the base 22.52 holds up in 2022-26).
**Process lesson: regime-split + leak-test EVERY full-period "edge" before believing it — it killed
both the exit-target and the ROE leads tonight.**
