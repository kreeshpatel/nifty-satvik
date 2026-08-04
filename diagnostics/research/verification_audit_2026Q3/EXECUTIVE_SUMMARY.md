# Verification audit 2026Q3 — executive summary for the Oct-1 binder

**One page. Verification class throughout: zero trials, zero new screens, no new hypotheses.**
**Counts identical at start and end: screens 14 · sealed opens 1 · n_trials 138.**
Sealed 2024H2+ never re-opened. No verdict was read from the judge log — chain and counts only.
The parking lot is empty: nothing in five sessions tripped the fishing guard.

## How much of the evidence base was re-verified

| tier | items | outcome |
|---|---|---|
| **Tier A** (live money / Oct-1 decisions) | NAV identity · D5 card arithmetic · band census · cost model · annualisation · alpha decomposition · anchor robustness · two-sleeve blend · swing record + goldens · corrected anchor · baseline_v1 | **9 PASS · 1 measured · 1 irreproducible** |
| **Independent re-derivation** (pass 2) | every Tier-A item above | done — **no audit script imports the engine, card builder or census code**, so a shared upstream bug could not survive |
| **Clean-clone drill** | full reconstruction from `git clone` + releases only | **4 min 37 s**; pin sha `f8625a8f…` verified; 22 goldens + 218 suite tests pass identically |
| **Blind adversarial replication** | separate context-free session | **filed as intake, not confirmed here** — its report is not in the repo |

**Numbers that reproduced exactly:** band census (+0.717 / +0.094 / +2.088, N exact), swing record
(Sharpe 1.132, MaxDD −42.4%), the golden masters, the full suite, and the dataset pin's sha256.

## Discrepancy ledger — final state

| # | item | status |
|---|---|---|
| **D1** | two-sleeve blend had no producer; ERC vol lookback unnamed | **REMEDIED** — producer committed, lookback recovered as 126d, reproducible figure **1.237 / −33.04% / +5.62%** (published 1.22 / −33% / +5.6% preserved as as-measured-then; residual +0.017 Sharpe unexplained, **not tuned away**) |
| **D2** | `baseline_v1` has no producer script | **OPEN** — corroborated by the blind session but still not reproducible from the repo alone. Blocked on that session's script path. |
| **D3** | clean clone won't `pip install` on Python 3.13 | **FIXED** — ceiling extended to `<3.14`; **CI stays pinned to 3.12** so the byte-compared goldens keep one interpreter |
| **D4** | `trades.parquet` and `fundamentals_pit_depth.pkl` in neither git nor any release | **HALF-CLOSED** — `trades.parquet` rebuild **exercised end-to-end: 100 s, reproduces all three band-census cells exactly**. `fundamentals_pit_depth.pkl` still has no rebuilder or release attachment. |
| **D5** | **judge log never persisted** | **FIXED** — `.gitignore`'s `results/*` whitelist omitted it, so the cron's `git add` was a silent no-op. The 2026-08-01 run judged 17 cards at a cost of $4.00 and **discarded every one**; the hash chain restarted from GENESIS weekly. Whitelisted, scanner re-dispatched. |
| — | corrected-anchor CAGR 25.21% vs published 24.7% (Sharpe and DD exact) | **recorded, not corrected** — window-end or compounding convention |

**Nothing in this ledger moved a standing research verdict.** Every entry is reproducibility,
recovery or persistence risk — the class of defect that is invisible until someone tries to rebuild.

## The audit's verdict on the evidence base

**The arithmetic is sound; the provenance was not.** Every number this audit could re-derive
independently came back right — often to the digit — and the programme survives total loss of its
working tree in under five minutes. What the audit found instead was a systematic gap between
*publishing a number* and *committing the thing that made it*: two of the most-cited figures in the
programme (the two-sleeve blend and `baseline_v1`) had no producer, and the forward record that the
pre-entry wall's only falsifier depends on was being silently deleted every Saturday. None of that
makes a past conclusion wrong. All of it means the evidence base was **less independently checkable
than it presented as** — and that is now measured, largely fixed, and governed by a written manifest
standard rather than by whoever happened to run the script.

## Falsification register — status

| law | falsifier | status |
|---|---|---|
| I pre-entry wall | judge take-vs-skip spread at first unsealing | **ARMED — clock from 2026-08-08** (was CONTINGENT: the key was set but the log was being discarded; fixed D5. The 17 recovered rows are a **late-called genesis cohort**, excluded from the primary test) |
| II population vs margins | breadth-50 EW/SW forward spread | **CONTINGENT** — Oct-1 amendment |
| III subtractive rules | habit-ledger owner-skip performance | **CONTINGENT** — ledger unbuilt |
| IV deferral = deletion | forward re-signal rate vs the 94% lapse | **ARMED** |
| V post-entry hindsight-only | forward day-10 IC vs −0.029 | **ARMED** |
| VI ±10R/yr floor | three-book forward separation | **ARMED** |
| VII robustness costs return | A-only DD **and** Calmar forward | **ARMED** |
| VIII method laws | — | ⚠ **demote to PROTOCOL** — procedural, not empirical |

**5 armed · 2 contingent · 1 to demote.** Law I moved from contingent to armed *because of this
audit*: its falsifier existed on paper but was being destroyed weekly in practice.

## What October must decide

1. **D2** — supply or commit `baseline_v1`'s producer, or accept the anchor as corroborated-but-not-
   self-reproducible.
2. **D4 remainder** — a rebuilder or release attachment for `fundamentals_pit_depth.pkl`.
3. **Three constitution rows** from the blind session (`gate_quantile` inert; `risk_per_trade`
   inert-then-chaotic via cash-scramble — a **fourth** sighting of composition noise; published
   precision exceeds what risk-sizing supports). **Records, not changes.**
4. **Binder corrections** — the true tradeable period is **2018-01-19 onward, 8.43 years**, not
   "2017–2026"; and the standalone-sleeve CIs must sit beside the pair-alpha sentence (**low-vol's
   [+0.06, +12.21] barely excludes zero**).
5. **Law VIII** — relabel PROTOCOL.
