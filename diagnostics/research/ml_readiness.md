# ML readiness — the path that makes "pursue ML, judge it forward" real

**Status:** memo, Oct-1 binder input. **No screen, no trial, no engine change.**
Standing counts: **screens 12 · sealed opens 1 · n_trials 138.**
Date: 2026-07-30.

**The owner's standing instruction** is that the learning-bot direction is pursued, not hard-killed,
but **judged on forward/OOS evidence only** — in-sample fit on this sample is meaningless. This memo
takes that instruction literally and writes down what would have to be true, and when, for a learner
to be trainable *and* certifiable. It is deliberately unflattering: the honest answer is that only
one lane is open today, one opens conditionally on 2026-10-01, and the lane everyone reaches for
first is arithmetically closed for years.

---

## 0. Why the obvious approach is not a lane

**NOT A LANE: any model trained on the current funnel's in-sample labels.**

This is not a preference; it is a measured verdict, five times over. The pre-entry wall
([`skills/program-laws`](../../skills/program-laws/SKILL.md) §I) has been tested with bar-level ML
(STAGE2_ml/0111/0112), loser forensics and eight hand-built entry levers, path shape (0116 —
train-clean, then **sign-flipped on the sealed set**), formula chart structure (prereg 0004), and
perception (0123 — a grader validated at test-retest κ=0.867 with leakage ruled out, returning
**flat** grades across winner / noise-stop / false-touch cohorts, and **null in both** the
detector-agreement and detector-disagreement cohorts).

The mechanism is structural, not a modelling failure: **this funnel enters names that have already
trended** (0123's grader called 72% "extended", 98% "wait"), so the eventual winner, the recoverable
whipsaw and the unrecoverable false touch are *visually and numerically identical at the decision
point*. There is no label signal for a learner to fit. A model trained here will fit noise, and
0116 is the receipt for what happens next: a CI-clean, 5/6-year-consistent in-sample effect that
**inverted** out-of-sample.

Also not lanes, for the same reasons: regime switching (0103 — no regime feature has forward IC for
the sleeve winner; every walk-forward switch loses to the static blend), and in-flight/post-entry
learners (0117 — post-entry strength has IC −0.029 against the subsequent leg).

---

## 1. Lane A — weight learning on the breadth-50 SW book *(open, pending the Oct-1 amendment)*

**What it is.** The breadth-50 watched pair is, by construction, a learning experiment with no
in-sample fitting: **(a) EW** = equal-weight 2%/name, the no-information baseline; **(b) SW** = the
same names, weights tilted by the banked signals (`dlv_med21` percentile up-weight,
`known_event_within_14cd` down-weight), tilt bounded 0.5×–2× of equal weight, definitions **frozen
verbatim from 0118/0120**. The EW-vs-SW forward spread isolates the signals' portfolio-expressed
value.

**Why this lane is legitimate when the others are not.** It is a *portfolio-weight* question, not an
entry-quality question. It therefore does not collide with the pre-entry wall, and it sidesteps
Law II (population information cannot be expressed at *this book's* decision margins) by changing
the book shape — a 50-name weighted book has margins that can express a gradient, where a 15-slot
winner-take-all queue provably cannot (0119: 15 activations in 5.5 years, bound −1.29 R/yr).

**Gates and dates.**
- **Gate:** owner sign-off at the **2026-10-01 amendment slot**. Machinery is built cold and wired
  nowhere (`nq/research/breadth50.py`, `scripts/dry_run_breadth50.py`; dry-run validated 2026-07-29,
  weights sum to 1.000000, tilt bounds asserted, PIT joins lagged ≥ 0 with a 10d staleness cap).
- **If signed:** logging wiring + a dated inception. Evidence accrues forward-only from that date.
- **Certification:** the forward EW/SW spread, read at quarterly reviews. Not before.
- **What "learned" means here:** the *tilt* is frozen, not fitted. Only after the spread certifies
  that tilting-by-banked-signals pays would a *learned* weight function become a proposal — and it
  would then face the full verdict-machine sequence like any other idea.

**Honest data volume.** The spread is a portfolio-level comparison, so its unit is *time*, not
trades: it needs quarters of joint logging, and a first read is admissible at the review following
≥2 quarters post-inception. Earliest meaningful read: **2027-04-01** on an Oct-2026 inception.

---

## 2. Lane B — the pre-extension funnel as the perception/ML re-entry *(conditional on Oct-1)*

**What it is.** The **Path-B swing sleeve** (registered proposal for the 2026-10-01 review; spec
freeze gated on the delisted backfill) enters on box / S-R breakout structure that fires
**before** extension — not on a 44-SMA touch of an already-run name.

**Why it is the only perception lane.** The 0123 re-open condition, verbatim, permits chart-structure
work on exactly one class of subject: *"a materially different funnel … one whose entries are not
already-extended (e.g. the box/S-R breakout entries that fire pre-extension, or a
slack-capital/longer-horizon book)."* It explicitly refuses a different rubric, a different vision
model, more charts, or grade-ensembling on the same touch entries. Path-B and the breadth-50 book
are the only two territories that satisfy it, and both are already on the Oct-1 agenda.

**Why the prior is genuinely different here, with a receipt.** 0123's Phase-1.5 measured the visual
substrate of the touch funnel directly: on 681 touch charts the committed zoo detectors
(cup/double-bottom/ascending/VCP/flag) fired **0.0%** of the time, and the model's dominant read was
`sr_breakout` — i.e. the perceptible structure the funnel *lacks* is exactly the structure Path-B
selects for. That is a mechanism-level reason to expect non-zero visual variance across outcomes
there, which is the one thing the touch funnel did not have.

**Gates and dates.**
- **Gate 1:** Path-B promoted (or declined) at the **2026-10-01 review**; promote/kill pre-committed.
- **Gate 2:** if promoted, it accrues *forward* trades. No perception/ML study on it may use
  in-sample labels — that would re-import the 0116 failure into a new funnel.
- **Gate 3:** any study still runs the full verdict-machine sequence — including
  **instrument validation first** (test-retest + leakage probe, the 0123 protocol, which is the
  reason 0123's null is interpretable at all).

---

## 3. Lane C — the forward wall as the only admissible training set (and the honest arithmetic)

**The rule.** For any *entry-quality* learner, the forward wall's accrued closed trades are the only
admissible training data. In-sample labels from the current funnel are excluded by §0.

**The arithmetic, stated plainly.** The frozen 0094 capped book closes **255 trades over ~9.5 years
≈ 27 closed trades per year.**

| Training observations | Years of forward accrual at 27/yr |
|---|---|
| 200 (a bare minimum for a low-dimension learner) | **7.5 years** |
| 300 | **11.2 years** |
| 500 (defensible for a 10-feature model + held-out test) | **18.6 years** |

**Conclusion, unflattering and load-bearing: an entry-quality learner trained on forward-wall data
from the 15-slot book is not reachable on any decision-relevant horizon.** This is not pessimism
about ML; it is the same cash-constrained concentration that makes the book's edge hard to certify
at all (the ±10R/yr noise floor, Law VI). Any plan that quietly assumes "we'll collect forward data
and train on it" must state this table, or it is not an honest plan.

**What this implies.** Learners on this programme become reachable only via **book shapes with more
decisions per unit time** — the breadth-50 book (50 names), the uncapped/pre-extension sleeve, or a
longer-horizon/slack-capital variant. That is the same structural conclusion the external-data
campaign reached from the opposite direction (the banked delivery/earnings assets need "a
structurally different book shape — one whose decision points CAN express population-level quality
gradients"). **Two independent programmes now point at the same door.**

**The paper-gate analogue, for calibration.** The `portfolio-simulation` paper gate for real capital
is ≥30 closed trades / ~2 months. That is a *go-live* bar for an already-specified strategy. A
*learner* needs an order of magnitude more, because it must estimate parameters rather than confirm
a frozen one — which is precisely why the gate above is measured in years, not months.

---

## 4. Summary table (the memo in one screen)

| Lane | Status | Gate | Earliest evidence | Collides with a law? |
|---|---|---|---|---|
| **A — breadth-50 EW/SW weight learning** | OPEN, awaiting amendment | Owner sign-off 2026-10-01 + logging inception | ~2027-04-01 (≥2 quarters forward) | No — portfolio weights, not entry quality; changes book shape |
| **B — Path-B pre-extension perception/ML** | CONDITIONAL | Path-B promoted 2026-10-01; then forward accrual; then full verdict-machine incl. instrument validation | After Path-B accrues forward trades | No — satisfies the 0123 re-open condition verbatim |
| **C — entry-quality learner on forward-wall data** | ARITHMETICALLY BLOCKED on the 15-slot book | 200/300/500 obs = 7.5/11.2/18.6 years at 27 trades/yr | Not on a decision-relevant horizon | No, but it is not *reachable*; needs a higher-decision-rate book |
| **✗ — any learner on the current funnel's in-sample labels** | **NOT A LANE** | — | — | **Yes** — the five-wall pre-entry law; 0116 is the receipt for what in-sample fit does here |

---

## 5. What this memo asks of the Oct-1 review

Nothing new — it re-frames two decisions already on the agenda in terms of what they unlock:

1. **The breadth-50 amendment (§4 of the review binder)** is not only the named consumer-shape
   answer for the banked delivery/earnings assets; it is **the only ML lane that can start in 2026**.
2. **The Path-B promote/kill decision** is not only a sleeve decision; it is **the only door through
   which chart-structure and perception work can legitimately re-enter the programme**, per the
   0123 re-open condition.

Declining both is a coherent choice. It should just be made knowing that it also closes the ML
direction for the foreseeable horizon, per §3's arithmetic.

---

## Cross-references

- [`skills/program-laws`](../../skills/program-laws/SKILL.md) — the five walls, the closed axes
- [`skills/verdict-machine`](../../skills/verdict-machine/SKILL.md) — the gate sequence any study runs
- [finding 0123](../../research/findings/0123-vision-graded-chart-structure.md) — perception wall + the re-open condition
- [finding 0116](../../research/findings/0116-context-window-selection.md) — the sealed-set sign flip
- [finding 0117](../../research/findings/0117-postentry-stage1.md) — post-entry hindsight-only
- [finding 0103](../../research/findings/0103-regime-sleeve-switch-learnability.md) — regime switching not learnable OOS
- `diagnostics/research/review_2026Q4/04_breadth50_proposal.md` · `05_capstone_carryforward.md`
- `diagnostics/research/oct1_binder_decisions.md` — the owner-door list this memo feeds
