# 0129 — Event-proximity SIZING: the activation bound

**Status:** PRE-REGISTERED — committed, and the ledger row appended, **before the run**.
**Class:** **ACTIVATION BOUND** — ledger row **#15** (it touches outcomes, so it is priced).
**No trial. Sealed set untouched. Judge log unread. No engine change.**
**Standing counts at registration: screens 14 · sealed opens 1 · n_trials 138.**

**Date:** 2026-08-06. **Owner:** Kreesh Patel.
**Standing law it satisfies** (`label_screen_ledger.md`): *no usage trial may be pre-registered until
a zero-trial clairvoyant activation bound has been run.*

---

## §0 IMMUTABLE — the relitigation basis, stated verbatim per the collision rule

This proposal collides with **0121 (deferral)**, which killed a *different usage* of the *same*
measured effect. `program-laws`' collision rule requires naming which of {new data, new feature
source, new sub-period, new formulation} is brought. **It is NEW FORMULATION, and only that.**

| | 0121 — DEFERRAL (killed) | 0129 — SIZING (this bound) |
|---|---|---|
| the trade | is postponed, and 94% of the time never happens | **still happens**, at the same time, at the same price |
| the slot | vacates; must be refilled or idles | **stays occupied**; the book stays full |
| lapse exposure | 94% (`program-laws` §IV: deferral is a de-facto skip) | **zero by construction** — nothing is deferred |
| what changes | *whether* to take the trade | *how much* of it to take |

**Nothing measured in 0120 is re-measured.** The effect (−0.383R raw / −0.294 conditional, 5/6 years,
ADV-robust, ~10% activation) and the event definition (`known_event_within_14cd`, N=14cd) are
**FROZEN and imported verbatim from 0120/0121**. This bound prices a usage, not a hypothesis.

**Family placement, stated in advance so it is not claimed after the fact.**

- **The family is O-009 (vol-target, PROMOTED & shipped).** From the registry: *"scale deployable
  sizing equity by `vol_scalar` … de-gross only, never lever up"*, giving *"CAGR-neutral DD
  reduction"*. O-009 scales to **realized** book variance; this proposal scales to **known
  forthcoming, name-specific** variance. Same mechanism (de-gross into variance), different clock.
- **The family is NOT C3/0073 conviction sizing (KILLED).** From the registry: *"a mean-preserved
  tilt can't lift the mean"* — C3 sized by **predicted return** and was mean-preserved
  (renormalised to 1.0). This sizes by **known variance**, is **not** mean-preserved, and is a pure
  de-gross. That distinction is the whole claim, and §4.1 names the way it can still fail.

## §1 IMMUTABLE — frozen definitions (imported, not re-derived)

| name | definition (frozen) |
|---|---|
| `sig_fri` | `entry_date − (weekday + 3) days` — the signal-week Friday, the decision moment |
| `monday` | `sig_fri + 3 days` — the entry-week Monday |
| **`known_event_within_14cd`** | a results event with **`ann_ts ≤ sig_fri`** (announced by the decision moment) whose **`event_date ∈ [monday, monday + 14d]`**. **N = 14cd FROZEN from 0120.** |
| event source | `nq.data.earnings.build_event_table` on `data/_earnings_raw.parquet`, alias-mapped — the same two-layer PIT layer 0120 audited (coverage 97.7–99.5%/yr; lag median 8d) |
| **size grid** | **f ∈ {0.50, 0.75}** — the position multiplier on activated entries. **Both stated in advance and both reported.** This is a **bound, not a search**: neither value is selected on outcome, and no other value is evaluated. |
| window | `entry_date ∈ [2019-01-01, 2024-06-30]` — train only, 5.5 years. The 2024H2+ sealed set is not read. |
| disaster class | `R ≤ −1.5` (the 0109 disaster-floor convention) |

## §2 IMMUTABLE — populations, and why two

**PRIMARY — the capped train book** (`research/exports/bhanushali_weekly_rank_0094_trades.csv`,
train slice). This is the owner's instruction and it is the honest population: sizing is a
**capital** decision and only the capped book has a capital constraint.

**CROSS-CHECK — the uncapped 0116/0117 substrate** (`context_windows.parquet`, train slice), the
*identical* population 0121 used. Reported so this bound's numbers are directly comparable to
0121's **−20.96 (pure skip) / −15.72 (deferral) / +36.9 (clairvoyant ceiling)** R/yr. It carries ~6×
the trades and therefore **inflates every magnitude** — a fail there is a fail on the friendliest
population available.

**Scale disclosure, pre-committed so it cannot be produced as an excuse afterwards.** The capped
train book earns **≈17.3 R/yr in total**. The ±10R/yr floor is therefore ~58% of the book's entire
annual output. This is not a defect of the gate — it is Law VI stated in the book's own units (a
4–5-name book's composition noise really is that large relative to its output) — but it does mean
**no per-trade-cohort tweak can clear this floor on the capped book**, and that fact is registered
*before* the run rather than discovered after it.

## §3 IMMUTABLE — the arms, and the arithmetic

For activated trades `i` with realized `R_i`, and multiplier `f`:

- **Arm (a) — freed capital LEFT IN CASH.** `Δ = (f − 1) · Σ R_i`.
  Mechanically negative whenever the cohort is positive-EV. This is the **Law III bookend in sizing
  form** and is priced first because it is the more common mistake.
- **Arm (b) — freed capital REDEPLOYED to the next ranked candidate.** The book stays full; this is
  the honest arm. `Δ = (1 − f) · Σ (R_repl,i − R_i)`. Two replacement models, both reported:
  - **(b-realistic)** — `R_repl` = the measured mean R of the **non-activated** trades of the same
    population and window. The typical replacement, not an assumed one.
  - **(b-clairvoyant)** — `R_repl` = the **best** same-week alternative in the uncapped queue, with
    perfect foresight. An upper bound no real rule can reach.

**Stated approximations (all inflate the bound; the conservative direction for a bound meant to
fail):** R is treated as additive across the book, so the second-order cash-path effect of freeing
capital (which slot gets funded three weeks later) is not modelled — that effect *is* the ±10R/yr
composition noise the gate tests against, and 0109 showed it can invert a strictly-positive
per-trade change. Arm (b) further assumes freed half-risk is always deployable in the same week.

**Linkage disclosure:** the capped 0094 book and the Stage-1 substrate are different pipelines —
only **55/156** train trades join on (ticker, entry_date). The clairvoyant replacement queue is
therefore the *substrate's*, not the capped book's own unfunded queue. This is reported as a
coverage caveat on (b-clairvoyant) only; (a) and (b-realistic) do not depend on it.

## §4 IMMUTABLE — named failure modes, quoted verbatim

1. **Law III, in sizing form — the mechanism most likely to kill this.** From `program-laws` §III:
   *"Identifying a below-average cohort does not license removing it."* And 0121: *"trades entered
   into a known imminent event are **worse than their peers by −0.38R and still make money (+0.51R
   mean)**. Removing them cost **−20.96 R/yr**."* Half-sizing is **half a removal**. If the cohort
   is positive-EV, arm (a) is negative by arithmetic, and arm (b) is positive only if the
   replacement out-earns the activated trade by more than the gap the effect promises.
2. **Law II — population effect ≠ decision-point value.** From `program-laws` §II: *"A real effect
   measured on a population does not survive to this book's decision points."* This gate is 3/3
   (0117 rotation, 0119 tiebreak, 0121 deferral) and 0119 is the specific mode to fear: a real
   population gradient that **inverted** at the funding margin.
3. **Law VI — the floor.** From `program-laws` §VI: *"On a 4–5-name cash-constrained book, any edge
   below roughly ±10R/yr is swamped by composition noise and cannot be certified in-sample."*
4. **C3's arithmetic.** From the registry: *"a mean-preserved tilt can't lift the mean."* This
   proposal escapes the *letter* of that (it is not mean-preserved) but inherits its spirit: a
   de-gross lowers the mean unless the freed capital earns more than what it left.

## §5 IMMUTABLE — the gate, pre-committed

**Primary gate (return):** net **≥ +10 R/yr** on arm (b) with **majority-year sign consistency**.
Wrong-signed at any magnitude is a FAIL (0119's mode). Arm (a) is reported but cannot pass alone —
it has no redeployment and therefore no route to a positive net.

**Secondary, NOT self-authorizing (owner condition):** a **material disaster-class tail reduction**
may be recorded even if the return gate fails. It is quantified **separately from the mean effect**:
cohort share of `R ≤ −1.5` events vs base rate, and the book-R contributed by that class before and
after scaling. **The session does not weigh this against the return loss and does not propose a
rule on it.** It is stated and routed to the owner's door.

**Branches:**
- **FAIL** → record, close, **no trial**. Finding + registry row + ledger row #15 closed.
- **CLEAR** → trial **#139** with the full gauntlet (pre-reg, sealed check, Stage-C capped
  continuous-slice endpoint, `n_trials` incremented **before** the run).

## §6 IMMUTABLE — what is reported

1. Activation counts (n, % of book, per-year), both populations.
2. Arms (a), (b-realistic), (b-clairvoyant) × f ∈ {0.50, 0.75}: annual R delta + per-year signs.
3. Disaster-class tail effect, quantified separately from the mean effect.
4. The 0121 comparison row on the identical population.
5. Standing counts.
6. A worked example on the owner's four named tickers — **illustration for the finding, explicitly
   not evidence**, and reported whatever it shows (including if all four are event-free).

## §7 Reproduce

    python scripts/diag_eventsize_bound_0129.py

---

## OUTCOME (appended 2026-08-06 after the run — nothing above this line was touched)

**VERDICT: GATE FAIL on every arm and every grid point → NO TRIAL.** Finding:
[`research/findings/0129-eventsize-activation-bound.md`](../../../research/findings/0129-eventsize-activation-bound.md).
**Standing counts: screens 15 · sealed opens 1 · n_trials 138.** Sealed slice never read.

The frozen rule **replicated 0120 exactly** on 0120's population (275 activations, gap −0.383),
which validates the import — and then failed at the funding margin, where it activates **12 times in
5.5 years (2.2/yr)** and the gap is **wrong-signed (+0.076)**.

| arm (capped, PRIMARY) | f=0.50 | f=0.75 | vs ±10 R/yr floor |
|---|---|---|---|
| (a) cash | −0.74 | −0.37 | FAIL |
| (b) redeploy, realistic | −0.08 | −0.04 | FAIL |
| (b) redeploy, **clairvoyant** | **+0.78** | +0.39 | **FAIL — 13× short with perfect foresight** |

**§5 secondary (tail), stated and NOT self-authorized:** the disaster class is **absent** from the
activated cohort — 0 of 12 (worst activated R −0.89); all 8 of the capped book's R ≤ −1.5 trades are
non-activated; enrichment **−5.6pp**; relief **0.00 R/yr**. On the uncapped population the tail
signal is real but mild (+2.4pp) and its relief (8.98 R/yr on a 367 R/yr book) is still sub-floor.
**Routed to the owner's door unweighed, per §5.**

**§4 failure modes:** #1 (Law III in sizing form) and #2 (Law II / 0119's inversion) both **fired** —
the cohort is positive-EV and the gradient inverted at the funding margin. #3 (Law VI) was
**decisive**: the pre-registered scale disclosure (floor ≈ 58% of the capped book's annual output)
predicted the outcome before the run. #4 (C3) was **not** engaged — the family placement held, this
is not a mean-preserving tilt, and sizing did legitimately dominate deferral on the population
(+9.57 vs −15.72 R/yr). The shape was right; the activation count was fatal.

**§5 branch taken: FAIL → no trial.** Event-window entries stay full-sized and identically managed.

