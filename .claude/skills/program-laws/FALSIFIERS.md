# Falsification register — one named, dated falsifier per standing law

**Committed 2026-07-31 by the 2026Q3 verification audit.** Sits beside
[`SKILL.md`](SKILL.md) and is read with it.

**The rule this file enforces: no falsifier, no law.** A claim that no scheduled future measurement
could overturn is not a law — it is an assumption, and it should be labelled one. Every entry below
names (a) what result would overturn the law, (b) the measurement that would produce that result,
and (c) when it is due.

**Status vocabulary**

| status | meaning |
|---|---|
| **ARMED** | the measurement is already running or computable from logs that already accrue. The falsifier fires on schedule with no further decision. |
| **CONTINGENT** | the falsifier exists but depends on an owner decision that has not been made. **Until that decision, the law is effectively unfalsifiable** — which is exactly the state this register exists to make visible. |
| **NOT FALSIFIABLE** | flagged for demotion (see Law VIII). |

**Standing counts at commit: screens 14 · sealed opens 1 · n_trials 138.** This register spends
nothing — it schedules.

---

## Law I — the pre-entry wall (entry quality is not visible before entry)

**Falsifier:** at the first unsealing of the judge log, **judge-`take` cards materially outperform
judge-`skip` cards in realized R, conditional on ext-band × CRS cells**, with a CI excluding zero.
The five walls tested price-derived and perception instruments; the judge adds **non-price context**
(live news, PIT event status). A clean take-vs-skip spread would mean entry quality *was* visible
before entry — to an instrument with different inputs.

**Measurement:** pre-reg [0125](../../diagnostics/research/preregistry/0125-informed-judge-forward.md) §4.
**Due:** first quarterly review after ≥2 quarters **and** ≥100 resolved verdicts.
**Status: ARMED — clock starts 2026-08-08.** (Armed 2026-08-05 by the 2026Q3 audit, session 5;
inception dated 2026-08-08 by the 0125 amendment of the same day.)

The first 17 persisted rows are the **genesis cohort** and do **not** start the clock. They judge
cards `as_of` 2026-07-31 but were called on 2026-08-04 — four days of news-context drift on an
instrument whose whole distinguishing input is news. They are classified **late-called**, excluded
from the primary take-vs-skip test, and reported separately at unsealing. The first clean cohort is
the scheduled run of **Saturday 2026-08-08**, and §7's two-quarter / 100-verdict thresholds count
from there.

*History, kept because it is the point:* when this register was written the status was CONTINGENT on
the API key. The key had in fact been set on 2026-07-31, and the 2026-08-01 run **did** judge 17
cards — but `.gitignore`'s `results/*` whitelist omitted `judge_log.jsonl`, so the cron's `git add`
was a silent no-op and every verdict was destroyed with the runner. **The falsifier looked armed and
was not.** Fixed 2026-08-05 (PR #64); scanner re-dispatched through the front door.

---

## Law II — population information is real; this book's margins cannot express it

**Falsifier:** the **breadth-50 SW book beats EW forward** on the pre-registered spread. SW tilts
weights by the banked delivery/earnings signals; EW is the no-information baseline. Law II says a
real population gradient dies at this book's decision margins. A 50-name weighted book has margins a
15-slot winner-take-all queue provably lacks (0119: 15 activations in 5.5y, bound −1.29 R/yr). If SW
wins, the gradient *can* be expressed — in a book shaped to express it.

**Measurement:** [`ml_readiness.md`](../../diagnostics/research/ml_readiness.md) Lane A.
**Due:** review following ≥2 quarters post-inception — **~2027-04-01** on an Oct-2026 inception.
**Status: CONTINGENT** — requires the **2026-10-01 amendment sign-off**. Machinery is built and
dry-run validated (`nq/research/breadth50.py`) but wired nowhere.

---

## Law III — worse-than-average is still positive-EV (subtractive rules pay for what they remove)

**Falsifier:** in the habit ledger, **owner-skipped cards underperform taken cards by more than the
redeployment value of the freed slot**, sustained across two quarterly reads. Law III says removing
a below-average cohort costs more than it saves because the slot is not free (0121: −20.96 R/yr;
0127: exclusion worth 1.92 R/yr against a 10 R/yr floor). A durable, redeployment-adjusted negative
on owner-skips would show subtractive selection *does* pay here.

**Measurement:** habit-ledger `owner_action` stream, joined to realized R
([binder §6](../../diagnostics/research/review_2026Q4/06_habit_ledger_spec.md) §1.2b).
**Due:** second quarterly review after ledger inception.
**Status: CONTINGENT** — the ledger is **spec-only**, awaiting the owner door at Oct-1.

---

## Law IV — setups do not survive events (deferral is a de-facto skip)

**Falsifier:** the **forward re-signal rate materially exceeds 94% lapse** — i.e. deferred/stopped
setups *do* come back. 0121 measured 16 re-signals in 275 cases within 28 calendar days in-sample.
If forward data shows the same names re-signalling at, say, >25%, deferral is a genuine delay rather
than a deletion, and the law's mechanism fails.

**Measurement:** directly computable from `results/signals_history_weekly.json` — count names that
stop out and re-signal within 28 calendar days, forward only.
**Due:** any quarterly review; first read **2026-10-01**.
**Status: ARMED** — the signal ledger already accrues this; no decision needed.

---

## Law V — post-entry is hindsight-only

**Falsifier:** recomputing 0117's day-10-strength IC against the *subsequent* leg **on forward-wall
closed trades** yields an IC materially above zero (0117 in-sample: **−0.029**), sustained across two
reads. Law V says the price path carries no exploitable conditional information beyond the original
signal. A positive forward IC on the same statistic falsifies it directly.

**Measurement:** forward-wall closed trades + the 0117 statistic, recomputed unchanged.
**Due:** the 12-month review, **2027-07-01** (needs enough closed trades to be readable).
**Status: ARMED** — the wall logs closed trades daily.

---

## Law VI — micro-edges are uncertifiable here (the ±10R/yr noise floor)

**Falsifier:** two of the wall's three books (`base`, `veto-0.1`, `drift-degross`) whose in-sample
difference sits **below** the ±10R/yr floor nonetheless **separate cleanly forward**, with
non-overlapping CIs, inside the wall's horizon. That would show the floor is an in-sample artifact of
composition noise rather than a real bound on certifiability.

**Measurement:** the §3 hash-chained three-book forward log
(`nq/paper/forward_wall.py`), read at review.
**Due:** the 12-month review, **2027-07-01**.
**Status: ARMED** — all three books log daily via `wall_cron.py`.

---

## Law VII — robustness is bought with return (nothing in-sample clears both)

**Falsifier:** forward **A-only delivers shallower MaxDD *and* Calmar ≥ base-swing**, per the
pre-committed rule. Law VII says every drawdown/consistency lever pays in CAGR. A-only's whole thesis
is "shallower DD at ~equal Calmar"; if it holds *both* halves forward, a lever cleared both axes.

**Measurement:** [`forward/prereg_swing.md`](../../forward/prereg_swing.md) §4 — rule already frozen,
thresholds tighten-only.
**Due:** primary decision at the **12-month review, 2027-07-01** (2026-10-01 is a first read only).
**Status: ARMED** — both books log from the same signal source.

---

## Law VIII — method laws ⚠ FLAGGED FOR DEMOTION

**No falsifier can be named, and that is not a defect — it is a category error in calling them
"laws."** Continuous-slice sub-periods, matched controls, reproduce-before-trust, instrument
validation, "leaks inflate", the SMA-not-EMA rule, and the engine invariant are **procedural
commitments about how a number must be produced**. They are not empirical claims about the market,
so no market measurement can overturn them.

**Flagged to the owner:** relabel Law VIII as **PROTOCOL** rather than LAW. It loses nothing — a
protocol is binding by decision, not by evidence — and it stops the register implying an empirical
backing that does not exist. Laws I–VII are empirical and falsifiable; VIII is not, and should say so.

*(Individual method rules can still be shown to have been mis-derived — the continuous-slice rule was
itself established by catching a phantom gate, and a future audit could find such a case. That is
error-correction of a protocol, not falsification of a hypothesis.)*

---

## Scorecard

| law | falsifier | status |
|---|---|---|
| I pre-entry wall | judge take-vs-skip spread | **ARMED — clock from 2026-08-08** (genesis cohort late-called, excluded; see Law I) |
| II population vs margins | breadth-50 EW/SW spread | **CONTINGENT** (Oct-1 sign-off) |
| III subtractive rules | ledger owner-skip performance | **CONTINGENT** (ledger unbuilt) |
| IV deferral = deletion | forward re-signal rate vs 94% lapse | **ARMED** |
| V post-entry hindsight-only | forward day-10 IC vs −0.029 | **ARMED** |
| VI ±10R/yr floor | three-book forward separation | **ARMED** |
| VII robustness costs return | A-only DD **and** Calmar forward | **ARMED** |
| VIII method laws | — | ⚠ **demote to PROTOCOL** |

**5 armed · 2 contingent · 1 to demote** (amended 2026-08-05: Law I armed once the judge log actually persisted).

**The finding this register produces (amended 2026-08-05):** **two** of the seven empirical laws —
population-vs-margins and subtractive-rules — have no live falsifier, each pending an owner decision
(the Oct-1 breadth-50 amendment, the habit-ledger build). Law I was in that set until the audit found
its falsifier was being **silently deleted every Saturday** despite appearing configured — the
sharpest illustration of why this register exists: *a scheduled falsifier is not an armed one until
someone checks that its data survives.* They are not unfalsifiable in principle; they are **unfalsified in practice
until those doors are opened**. That is a governance fact worth stating in the Oct-1 binder: the
programme's most-cited laws are, today, resting on in-sample evidence with their forward tests
unstarted.

## Maintenance

- A law whose falsifier fires **must** be re-adjudicated, not explained away.
- A law that acquires a new falsifier gains a row; one that loses its last scheduled falsifier
  **reverts to CONTINGENT** and is flagged.
- Status changes are dated. This file is append-and-amend, and every amendment carries its date.
