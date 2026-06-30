# Near-Term Research & Testing Plan — "Find every component, then LOCK"

> 2026-07-01. The program has been mining alpha one candidate at a time with **no definition of
> done**. This plan inverts that: enumerate the complete-model component set, test the few remaining
> OPEN ones under the hardened rigor in **batched** pre-regs, and LOCK against an explicit checkable
> gate. **The default is now LOCK; re-opening a component requires owner sign-off, not stopping.**
> Authority for the destination stays `docs/ROADMAP.md`; this file is the near-term execution plan.

---

## 1. The flaws we're fixing (ranked)

1. **No definition-of-done / lock criterion** — the §11 graveyard can be researched forever; Stage C
   is exhausted (C2 INCONCLUSIVE, C3 KILL, Kelly says don't build a sizer) yet we keep opening
   candidates. **Fix:** §4 LOCK GATE + a hard STOP rule; default flips to LOCK.
2. **Over-investment in alpha when the binding constraint is the −46% drawdown** — effort flows to
   conviction (certified weak, IC 0.056) while the dimension that disqualifies the product for
   fee-paying clients is parked. **Fix:** §3 sequences DD/exit work first; LOCK is gated on a
   defensible **DD number**, not just a Sharpe.
3. **n_trials is a monotonic ratchet (82 and rising) with no offsetting policy** — every new
   one-at-a-time arm taxes the base and any future winner; correlated re-probes counted as
   independent. **Fix:** §5 trial budget — batch families, spend sunk trials first, measurements
   aren't trials, +6 hard cap to LOCK.
4. **The 7-gate bar is ~3 gates in code, 4 applied by hand** (`nq/runner/research.evaluate_overlay`)
   — verdicts are skippable/unauditable; after-tax & 2022-26 demonstrably deferred. **Fix:** §3 Step 1
   mechanizes the remaining 4 gates **before** any candidate runs.

(Also found, folded into the gate: component **interactions** untested — C3×O-009 de-gross collision
is live evidence overlays cannibalize; and near-total reliance on **in-sample** numbers — the forward
wall is barely populated, so every verdict is PROVISIONAL until the wall confirms it.)

---

## 2. The complete-model component map

**Binding constraint, bluntly: the product is disqualified by the −46% drawdown, NOT by alpha.** The
alpha is certified real-but-modest (PSR 0.974, Sharpe 0.667, MinTRL 6.2y < 9.5y). Every additional
alpha lever has low marginal value and high trial cost. The misallocation: over-testing alpha (where
it keeps KILLing as predicted) and under-investing in the DD foundation + the cost/tax + mechanization
plumbing a lockable client-facing model actually requires.

| Component | Status | What's left |
|---|---|---|
| Entry / selection (`sma200_slope_63`, top ~15) | **DONE — VALIDATED** | Nothing for in-sample lock (C4 horse-race confirmed). Only open axis = forward wall. |
| Position sizing | **DONE — VALIDATED (flat)** | Nothing. C3 conviction sizing KILL; Kelly (0003) pre-called it. Flat 3%-risk / 15%-cap is locked. |
| Regime gating | **DEAD — KILLED ×3** | Nothing. O-001 / §11 / A5 all KILL. Lock-ready as OFF. |
| Capacity / liquidity (5% ADV, 15% cap) | **DONE — VALIDATED** | Optional: confirm 5% ADV binds on illiquid mid-caps (non-blocking). |
| Execution / fill realism | **DONE — VALIDATED** | Full-engine golden master is hardening, not a blocker. |
| Conviction signal (4-factor) | **INCONCLUSIVE** | IC 0.056, p_block 0.058 — too weak to SIZE on. Only un-foreclosed use = exits (Step 2). |
| Exits + conviction-exit (**0071**) | **OPEN-LEAD** | Run 0071 (Step 2) — the last non-foreclosed alpha/expectancy lever. |
| **Risk / drawdown overlay** | **INCONCLUSIVE — the binding constraint** | Only O-009 vol-target promoted (paper-only, −45→−39, off-cfg). Dependable −30 needs Stage-G tail hedge (deferred, blocked on F&O data). **OWNER DECISION (§6-D1).** |
| Cost / tax model | **OPEN — must-fix before lock** | baseline_v1 is **gross-only**. Add ~3.5 bps micro-costs + after-tax STCG-20% on the cloud run. The bar is post-tax-post-cost, so every verdict to date is vs a gross base. Cheap, load-bearing. |
| Universe / financials (U-001/U-003) | **OPEN / INCONCLUSIVE** | **OWNER DECISION (§6-D2):** re-derive cfg on corrected+financials (heavy) or record "keep carried cfg". Excluding all banks/NBFCs is not complete for a large+mid mandate. |
| Promotion-bar mechanization | **OPEN — lock-critical (Step 1)** | Mechanize ΔCalmar / 2022-26 / fold-pass / turnover into `evaluate_overlay` (fail-closed). Re-anchor skills off stale baseline_v0. |
| Component interactions | **UNTESTED** | Any two survivors get a mandatory paired-composition run before lock (§4). |
| Monitoring / kill-switch / decay | **UNTESTED (observe mode)** | Flip observe→enforce at Stage E (behind the paper book). |
| Paper-gate (≥30 trades) | **MISSING** | The true gate to real capital. Restart fresh at LOCK. |

---

## 3. The near-term test sequence (ordered, BATCHED, by the binding constraint)

Spend the **sunk** trials first: 0071/0074/0075 are already in the 82 count but unrun — the trial cost
was paid without buying evidence, so running them is **FREE on the budget** and de-inflates the bar.

| # | What | Why now | Primary metric | Trial cost | Honest prior |
|---|---|---|---|---|---|
| **1** | **Mechanize the 4 missing gates** in `evaluate_overlay` (ΔCalmar, 2022-26 ΔCAGR, ≥2019 fold-pass, turnover-Δ) + emit after-tax STCG-20% & micro-costs by default; re-anchor pre-regs/skills onto baseline_v1. | Binding on everything downstream — every verdict below is non-reproducible until all gates are one code path. Cheapest, highest leverage. | 9-gate bar in code; re-grades A5/C3 KILLs identically (regression check). | **0 (measurement)** | — |
| **2** | **0071 conviction-EXIT** — 4 arms (A prod, **B stop_only PRIMARY**, C no-trailing, D no-target) through the Step-1 harness. | Highest-EV open lever, trial already paid; the only Stage-D axis with an in-sample signal; the correct 63d analogue of the v1 0022 KILL we're forbidden to transfer. | paired ΔSharpe vs prod, block-bootstrap CI-low > 0; secondary ΔCalmar. | **0 (sunk)** | Skeptical (0047 found trailing-off raised raw EV but lowered IR). Could PROMOTE; plausibly KILL. |
| **3** | **0074 vol-scaled momentum** (D-M crash-forecast scalar) on baseline_v1+O-009. | DD is the binding constraint. After 0071 (exit-widening changes the distribution it sizes). Bar = "adds ON TOP of O-009". | ΔMaxDD & ΔCalmar vs base+O-009; collapse-to-0070 correlation as a pre-gate. | **0 (sunk)** | Likely KILL (overlaps 0068/0070 plateau ~−38); auto-KILL if indistinguishable from 0070. |
| **4** | **Quality-predictor FAMILY** under ONE pre-reg: 0075 gross-profitability + Sloan accruals + net share issuance. Run the IC-measurement leg for all 3 FIRST (0 trials); spend ONE trial only on the single survivor as a soft tilt (0065 λ pattern). | n_trials discipline in action: 3 correlated quality tilts → 1 trial. Quality is the most orthogonal of the leads but slow-horizon — measure before spending. | Spearman IC(predictor, return_pct) vs the **block-permutation null**; only IC clearly above the null band proceeds. | **+1 max** (0 if 0075 wins) | Measurement filters most; survivor faces a skeptical 63d-quality prior. |
| **5** | **Conviction-EXIT decay rules S1/S2/S7** as ONE batched pre-reg + combination test — **ONLY IF Step 2 did NOT promote a structural exit.** | Contingent: if 0071 promotes stop_only, finer decay-exits are cannibalized → drop (saves 3 trials). | paired ΔCalmar + combination ΔSharpe if >1 clears. | **+3 max, contingent** | — |
| **6** | **PARK** residual-momentum + BAB low-beta; **DO NOT** open Stage-G options work (no PIT F&O backtester/data). Catalogue in `external_edge_ideas.md` + registry with each reopen condition. | Trial-budget discipline — opening these pushes toward 90 and raises the bar into un-promotability for the leads that matter. | none — catalogued OPEN/parked. | **0** | — |

---

## 4. The LOCK gate (Stage D → E)

**"Model complete → freeze cfg + regenerate golden + restart the ≥30-trade paper book"** requires ALL:

1. **High-EV leads RESOLVED** — 0071, 0074, and the Step-4 quality family each have a logged verdict
   (PROMOTE-heavy-path / SHADOW / KILL-with-root-cause). No OPEN row remains on the near-term critical
   path in `overlay_registry.md`.
2. **Every cfg-changing PROMOTE cleared the FULL mechanized 9-gate bar** (post-tax-post-cost ΔSharpe ≥
   +0.10, ΔCalmar ≥ +0.05, 2022-26 positive ΔCAGR, ≥2019 fold-pass ≥60%, block-bootstrap CI-low > 0,
   turnover ≤ +30%, one-sentence mechanism, n_eff ≥ 20, ΔSharpe > 0 in ≥2/3 regime buckets) — all
   emitted by `evaluate_overlay`, **fail-closed if uncomputed**.
3. **Base stays CERTIFIED**: PSR(>0) ≥ 0.95 AND MinTRL(95%) < track length (currently 0.974 / 6.2y <
   9.5y — re-confirm after any cfg change). *PSR certifies the base; DSR gates overlays — don't conflate.*
4. **DSR re-checked at final n_trials** for every promoted arm: DSR > 0.95, OR explicitly demoted to
   SHADOW as real-but-not-a-multiple-testing-standout.
5. **Cost/tax closed**: after-tax STCG-20% + ~3.5 bps micro-costs computed by the cloud run; the
   1279-vs-1445 trade-count gap explained.
6. **DD risk-profile DECIDED** (ADR): accept ~−39% (vol-target into cfg) as the locked risk profile,
   OR block lock on Stage-G. *(§6-D1.)*
7. **Universe DECIDED** (ADR): re-derive+re-freeze on corrected+financials, OR record "keep carried
   cfg"; U-003 financials policy resolved. *(§6-D2.)*
8. **Reproducibility frozen**: golden master regenerated GREEN in the SAME PR as any
   decide_exit/sizing/simulate change; dataset pinned (sha-verified).
9. **Owner sign-off as an ADR** on the final cfg + new baseline. THEN: regenerate golden, write
   **baseline_v2.json**, restart the paper book (Stage E clock → zero, kill-criteria observe→enforce).

> **STOP RULE (the definition of done).** When Steps 2-5 are run and **0071 + 0074 + the quality
> survivor all return KILL/INCONCLUSIVE/SHADOW**, declare **the base IS the model**. LOCK: ship the
> base + the one promoted overlay (O-009 vol-target) into the frozen cfg, regenerate golden, restart
> paper. Do not open the next candidate. The default is LOCK; re-opening needs owner sign-off.

---

## 5. The n_trials / multiple-testing budget

At **82 arm-level / 45 family-level** and rising. Discipline: **buy evidence per trial, don't spend
reactively.**

1. **SPEND THE SUNK TRIALS FIRST.** 0071/0074/0075 are already counted but unrun — running them is
   FREE on the budget and de-inflates the situation.
2. **MEASUREMENTS AREN'T TRIALS.** An IC/IR measurement vs the block-permutation null makes no
   PROMOTE/KILL decision (cf. 0021/0072). Use it as a FILTER: measure all 3 quality predictors at 0
   cost, spend ONE trial on the survivor. 3-trial spend → 1.
3. **BATCH CORRELATED ARMS UNDER ONE PRE-REG** with a shared null + combination test.
4. **HARD BUDGET: +6 arm-level trials MAX to LOCK (82 → ~88 ceiling).** 0 net for the 3 sunk; +1 for
   the quality survivor beyond 0075; +3 max for the S/R decay-exit family ONLY IF 0071 doesn't
   promote. Residual-mom + BAB PARKED.
5. **DSR vs PSR ROLE SEPARATION.** The rising DSR bar does NOT kill the BASE — the base ships on PSR
   (0.974) regardless of n_trials. DSR only gates whether an OVERLAY is a multiple-testing standout; a
   real-but-modest overlay that clears the 9-gate bar but not DSR > 0.95 is demoted to SHADOW.

---

## 6. Owner decisions this plan surfaces (the two non-implicit calls that gate LOCK)

- **D1 — DD risk profile.** Accept **~−39%** operational DD (promote O-009 vol-target into the frozen
  cfg) as the locked risk profile for the ~10 clients, **or block LOCK on Stage-G** (the tail hedge —
  the only known path to a dependable −30%, but heavy: needs an options/vol backtester + PIT F&O data).
- **D2 — Universe / cfg.** Re-derive + re-freeze the frozen cfg on the corrected + financials universe
  (heavy; golden regen), **or** record an explicit "keep the carried cfg" ADR (reproduction proved
  engine fidelity, not cfg-optimality on the corrected universe).

## Immediate next 3 actions
1. **Mechanize the 4 missing gates + after-tax/micro-costs** in `evaluate_overlay` (fail-closed) +
   re-anchor the 0071 pre-reg + skills onto baseline_v1 — **0 trials**, unblocks every downstream verdict.
2. **Run 0071 conviction-EXIT** (4 arms, stop_only PRIMARY) through the mechanized harness — **0 trials
   (sunk)**, highest-EV open lever, resolves the last non-foreclosed alpha axis.
3. **Get the owner ADRs on D1 (−39% DD acceptance) and D2 (carried-vs-re-derived cfg)** — the two calls
   that gate LOCK.
