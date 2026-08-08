# Definitions memo — the 8 open doors, reduced to 2 decisions

**Class: VERIFICATION / SEMANTIC. Zero trials, zero screens. Counts frozen: screens 16 · sealed
opens 1 · n_trials 138.** Nothing here re-runs a result, re-adjudicates a verdict, or generates a
hypothesis. Companion to [`DEFINITIONS_REGISTER.md`](DEFINITIONS_REGISTER.md), which established
*what the numbers mean*; this asks the only question left: **which of those ambiguities can still
change a decision, and which are already settled by rules you have already committed to.**

---

## The short version

The register left **8 rows tagged DOOR** (1, 5, 6, 7, 8, 11, 15, 18). They are not 8 decisions.

| | doors | why |
|---|---|---|
| **Already open elsewhere — no new ask** | 1, 11 | routed to binder §6–8 in a prior session; carried here only so the count reconciles |
| **Closed by a rule you already committed to** | 7, and the *promote* half of 5/15 | the reading that would help is a **retroactive relaxation**, which every pre-registration forbids |
| **A real choice** | 8 | one absolute gate in the whole programme reads `rf = 0` |
| **A real choice** | 5 + 15 together | the young-book bias runs *against* the book in both gates, and only one repair is legal |
| **Clarification amendments — recommend, not decide** | 6 + 18, 7 | pin a convention so it cannot be improvised at the review |

**The single most useful finding in this memo is the second row.** The "thresholds may be tightened
or clarified, never relaxed retroactively" rule in `forward/prereg.md` §10 and `prereg_swing.md`
§4 does more work than it looks like: it removes about half of the register's doors from the table
without anyone having to adjudicate them. A door is only open if *both* readings are still
available to you, and for several of these they are not.

---

## DECISION 1 — `KILL_SHARPE = 0.0` means "loses to cash at 0%", not "loses to the risk-free rate"

**Where it bites.** `scripts/bhanushali_review_scorecard.py:38`. This is the **only absolute Sharpe
gate in the programme**. Everywhere else Sharpe is used as a Δ between two books, where the
risk-free term cancels and nothing is affected.

**Both readings.**

| reading | the gate means | threshold |
|---|---|---|
| **as written** (`rf = 0`) | kill if the book underperforms **cash at 0%** | Sharpe < **0.00** |
| **excess-return** (Indian rf ≈ 6–7%) | kill if the book underperforms **the actual risk-free rate** | Sharpe < **≈0.25–0.30** |

**What is available to you.** Moving 0.00 → 0.25 makes the book **easier to kill**. That is a
tightening, and tightenings are always available. The reverse is not, so this is a one-way door.

**Why it is not academic.** The scorecard prints `[kill §10.2] TRIGGERED` right now — forward Sharpe
−0.74. It has no effect because readiness is not met (4/40 closed, 0/4 quarters), but the gate is
live and will be read the moment readiness fires.

**The ask.** Leave at 0.00 as an explicit choice, or tighten to an excess-return basis with a dated
amendment. **Either is defensible; what is not defensible is arriving at the review without having
chosen**, because at that point the choice is being made with the answer visible.

**No verdict on the record moves either way.** Every KILL in the corpus was decided on ΔSharpe, a
CI, or a slice test — none of which contain rf.

---

## DECISION 2 — win rate and expectancy are biased **against** the book, and only one repair is legal

**Where it bites.** `PROMOTE_EXPECTANCY_R = 0.10` (`scorecard.py:37`) reads `avg_r` = mean R over
**closed** trades (`run_bhanushali_cron.py:474`). Win rate has the same denominator.

**The bias, and its direction.** On a trend book losers stop out fast and winners stay open for
months. A closed-only denominator therefore **understates** both metrics on a young book, and the
understatement shrinks as winners mature. Right now the promote gate rests on **4 closed trades**
against a 40-trade readiness bar.

**Why the obvious fix is not available.** Including open positions at mark-to-market would raise
expectancy, which makes the promote gate **easier to clear**. That is a retroactive relaxation of a
pre-committed threshold and is forbidden. So the closed-only reading stands for the promote gate,
and this half of doors 5/15 is **closed, not open**.

**What remains genuinely open — and it is the more important half.** The same bias makes the book
look **worse** than it is, which means the **KILL** gate can fire on an artifact of youth rather
than on degradation. Killing early is conservative, so no rule forbids it; but it is still an error,
and it is the error most likely to actually occur here.

**The one legal repair is the readiness gate.** `READY_CLOSED = 40` **OR** `READY_QUARTERS = 4`,
whichever comes first. Raising either delays evaluation until the bias has washed out, and raising a
readiness bar is a **tightening** — available. Loosening the gates themselves is not.

**The ask.** One of:

- **(a) Accept the bias as stated.** Evaluate at 40 closed / 4 quarters knowing both gates read low
  on a young book, and record that you knew.
- **(b) Tighten readiness** — raise `READY_CLOSED`, or require *both* legs rather than either, so
  the first substantive read happens on a more mature book.

**Recommendation: (b), and specifically requiring both legs.** The `OR` means 4 quarters alone can
trigger evaluation at an arbitrarily small closed-trade count — which is exactly the configuration
where the bias is largest. Requiring both is a pure tightening, costs nothing but time, and removes
the failure mode. This is a recommendation, not a change: **nothing in the gates has been edited.**

---

## CLOSED BY THE RATCHET — door 7 (MaxDD grid). Recommend pinning it anyway.

**The fact.** The formula is uniform everywhere; **the grid is not.** The same book family publishes
**−42.4% on a daily grid and −33% at monthly granularity** (finding 0114). A coarser grid can only
ever *understate* a drawdown — it cannot see the troughs between samples.

**Why it is not a choice.** Four committed gates read MaxDD: `PROMOTE_MAXDD = −0.25`,
`HALT_MAXDD = −0.50`, `prereg_swing.md` §4 ("forward MaxDD shallower than base"), and the ext_cap
decision ("≥3pp shallower"). A monthly grid reads shallower on all four — easier to promote, later
to halt. **That is a relaxation on every one of them, so the monthly reading is unavailable.** The
daily grid stands by rule, not by preference.

**The residual risk is drift, not ambiguity.** Nothing in the pre-registration *states* that the
grid is load-bearing for a risk control. A future maintainer resampling the curve for a perfectly
good reason would silently relax the halt.

**The ask (clarification amendment, no threshold moves).** Add one line to `forward/prereg.md` §4
and `prereg_swing.md` §4: MaxDD is evaluated on the **daily** grid, and a coarser grid is a
relaxation. The code comment already says this
([`bhanushali_review_scorecard.py:91-96`](../../scripts/bhanushali_review_scorecard.py:91)); the
pre-registration does not.

---

## CLARIFICATION — doors 6 + 18, and an operational gap you should know about before Oct-1

**Door 6 (CAGR) does not reach any gate.** Two committed year-denominators — calendar years
(`run_bhanushali_sixstep.py:220`, prints 24.7%) and trading-bar years (`run_corrected_anchor.py:52`,
prints 25.21%) — on the same equity curve. No gate reads CAGR. The exposure is **cross-document
comparison only**: a book-vs-benchmark CAGR gap is valid only if both sides use one denominator.
(0114 is not an instance; it states its convention.)

**Door 18 (Calmar) does reach the gates — three times.** `prereg_swing.md` §4 keeps A-only only if
forward **Calmar ≥ base-swing − 0.05** and reverts if it falls **>0.10 below**; the ext_cap decision
requires forward **Calmar not worse**; `forward/prereg.md` §7 requires beating base on **after-tax
Calmar and Sortino**. Calmar is `CAGR ÷ |MaxDD|` — a ratio of two grid-dependent quantities, so it
compounds doors 6 and 7.

**Why that is nonetheless safe — conditionally.** Every one of those three uses is a **comparison
between two books**. If both sides are computed the same way, the grid and denominator conventions
cancel exactly, the same way `rf` cancels in ΔSharpe. The gates are sound *provided the comparison
is same-convention*.

**The operational gap.** No committed producer emits Calmar for either wall. `nq/validation/metrics.py:60`
defines the canonical one (bar-year CAGR ÷ daily-grid DD) and
`nq/engine/portfolio.py:375` defines another (percentage-scaled), but **nothing in `nq/paper/` or in
`bhanushali_review_scorecard.py` computes Calmar at all** — and the scorecard reads only one book,
not the A-only / base-swing pair §4 compares. So on the current code path, both the convention *and*
the pairing get chosen **at the review, with the data already visible.** That is precisely the
moment the tighten-only rule exists to protect.

**The ask (recommend, do not decide).** Two clarifications and one build, none of which move a
threshold:

1. Name `nq.validation.metrics.calmar` as the convention of record for every forward Calmar gate.
2. State in both pre-registrations that a Calmar comparison must be same-convention on both sides.
3. **Build the two-book forward producer before the review, not at it.** This is the only item in
   this memo that is work rather than a decision, and it is the one with a date attached.

---

## ALREADY OPEN — doors 1 and 11, no new ask

**Door 1 (R).** Routed to binder §6–8 in a prior session and fully worked in finding 0129. Carried
here only so the count reconciles. Its **standing caveat 1a** is in force and worth restating,
because it points the opposite way to the original worry: the engine credits the booked half at a
notional **2.0R** while it actually achieved a mean **3.04R**, on **34.3%** of the population — so
**published R is conservative, not inflated.** The consequence that binds: where two arms differ in
half-booking rate, **% of equity is the arbiter and R is reported beside it, never instead of it.**
In force for 0130's arms, 0131's shadow book, and `ZOO_TWO_LENS.md`.

**Door 11 (±10R/yr floor).** Internally consistent in its own units; fully treated in binder §8
including the invalid-comparison trap (deflating a bound while leaving the floor undeflated). Not
re-opened.

---

## What this memo does not do

It changes **no threshold, no gate, no config, and no verdict**. Two items are genuine owner choices
(Decision 1, Decision 2); three are clarification amendments recommended for a dated sign-off; one is
a build with an Oct-1 deadline. Nothing here is actionable by a session without your sign-off, and
nothing here re-adjudicates anything on the record.

## Root-cause readout

The register found 8 ambiguities. Only **2** survive contact with the rules already in force,
because a definitional door needs *both* readings to be available, and the tighten-only ratchet
removes one reading from most of them. The genuinely uncomfortable finding is not any single door —
it is that the metric with the most gate exposure in the whole forward programme (**Calmar**, named
in three pre-committed criteria) has **no producer**, so its convention would have been settled by
whoever wrote the review script, on the day, with the answer already on screen.

## Next setup

None proposed. The definitions work is terminal per the register's own scope rule.
