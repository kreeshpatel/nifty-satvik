---
name: verdict-machine
description: >
  The cheap-roots/serialized-trunk research method — how to adjudicate a new data source, feature
  source, label idea, or usage proposal WITHOUT spending a trial. Use whenever a study is being
  designed or a candidate needs a verdict. Trigger phrases: "new data source", "external data",
  "does X predict Y", "screen it", "kill-shot", "label screen", "activation bound", "noise floor",
  "should this be a trial", "pre-register", "sealed set", "screen ledger", "how do we test this",
  "design a study", "banked labels", "coverage audit", "PIT audit", "instrument validation".
---

# Verdict Machine — the cheap-roots / serialized-trunk method

**What this encodes.** The programme learned, at the cost of an entire external-data campaign, that
the expensive thing is never the measurement — it is the *trial*. Trials deflate the Deflated-Sharpe
bar for every future test, permanently, and cannot be un-spent. So the method is: **push every
candidate through the cheapest instrument that can kill it, and let only survivors buy a trial.**
Four roots, one serialized trunk. Six candidates have gone through this machine
(0118, 0119, 0120, 0121, 0122, 0123) at a total cost of **zero trials**.

Use this skill whenever a session is handed a new data source, a new feature source, a new label
idea, or an "I wonder whether X predicts Y" question. Its sibling
[`skills/program-laws`](../program-laws/SKILL.md) tells you whether the idea is already answered;
read that FIRST. This skill tells you how to run what survives.

---

## The four gates, in order. Never skip. Never reorder.

```
  IDEA
   │
   ├─ GATE 0  REGISTRY CONFRONTATION ......... free ......... most ideas die here
   │             (program-laws + overlay_registry + findings + n_trials.json)
   ├─ GATE 1  COVERAGE / ACQUISITION AUDIT ... ~hours ....... 0122 died here
   │             (does the data even link to our universe, PIT-legally?)
   ├─ GATE 2  KILL-SHOT SCREEN ............... 1 ledger row .. 0116/0123 died here
   │             (against banked labels, train-only, matched cells)
   ├─ GATE 3  ACTIVATION BOUND ............... free .......... 0119/0121 died here
   │             (clairvoyant ceiling vs the ±10R/yr noise floor)
   │
   └─ TRIAL .................................. n_trials +1 ... nothing has reached here
                 (pre-reg → train design → sealed check → Stage-C capped endpoint)
```

**The asymmetry that justifies the order:** Gates 0–1 and 3 are free or nearly so. Gate 2 costs one
screen-ledger row (a multiplicity debt, not a trial). Only the trunk costs `n_trials`. A candidate
that dies at Gate 3 cost a measurement; a candidate that dies *after* a trial cost the whole
programme a permanently higher bar.

---

## GATE 0 — Registry confrontation (free; run before any design)

Produce a table mapping **every element** of the idea to its existing verdict:

| idea element | verdict | OPEN / CLOSED | citation |
|---|---|---|---|

Sources, all of them, every time:
- [`skills/program-laws`](../program-laws/SKILL.md) — the standing laws and their receipts
- `research/overlay_registry.md` — the append-only O-###/screen ledger
- `research/findings/NNNN-*.md` — the finding files
- `diagnostics/research/n_trials.json` — the cumulative trial count (the DSR denominator)
- `skills/methodology-synthesis` §11 KILL ledger

**Closed elements are excluded from the design.** If the idea *is* a closed element, you may not
relitigate it without naming which of {new data, new feature source, new sub-period, new
formulation} you bring — and that naming goes verbatim into the pre-registration. "A different
model / a bigger sample / a different rubric on the same question" is **not** new; it is refused
relitigation (see the 0123 re-open condition in `program-laws`).

If a prior thread already answers part of the question, **narrow the study to what it did not ask.**
That is how 0123 was legitimately run after 0004 had killed formula chart-structure features: the
feature *source* (model perception) was new, the formulas were not.

---

## GATE 1 — Coverage / acquisition audit (before any screen)

A screen run on data that does not link is not evidence — it is a void measurement, and saying so
is a first-class outcome (0122: the NSE ratings stream's symbol field was free-text junk, 0% of the
era universe linked, and the finding says **coverage-KILL, mechanism NOT adjudicated**).

Audit gate — all four legs, reported explicitly:
1. **Coverage by year** (%, and the count of delisted-in-window symbols present — survivorship).
2. **Linkage**: what fraction of the universe's symbols actually join?
3. **PIT legality**: the availability timestamp is the *publication* time, never the period end;
   truncation-proven (recompute on a series truncated at date *d*; the value at *d* must be
   byte-identical). Wire it as a tested layer (`nq/data/*.py` + `tests/test_*_pit.py`).
4. **Seam integrity**: where two vendor eras meet, verify byte-identity on overlap days.

Also record the **outcome-neutrality of the uncovered rows** — if the rows you cannot cover have a
different outcome distribution than those you can, coverage is itself a selection effect.

---

## GATE 2 — The kill-shot screen (costs one screen-ledger row)

### The verdict machine

The banked **0116/0117 per-trade label dataset** (`research/substrate/context_windows.parquet`) is
the standing instrument: `false_touch`, `noise_stop`, `exit_too_early`, `opp_quality_R`, plus `R`,
`ext_vs_sma`, `rank_crs` per trade. Build no new adjudicator when this one answers the question.

### Non-negotiable construction rules

- **Train years only.** `entry_date <= 2024-06-30`. The sealed set (2024H2+) is not subset, not
  rendered, not read. Opening it is an accounting event (see below).
- **Matched cells, never a one-sided list.** Condition every effect on **ext-band × CRS-tercile**
  cells; sample cohorts matched *within* cells so the joint distribution is identical by
  construction. A loser-only or winner-only list is not a screen (see `program-laws`:
  matched-controls law).
- **Pre-commit the bar before running**, in the 0118/0120 mould — ALL legs required:
  - conditional separation with a **CI excluding zero**, beyond ext × CRS,
  - **per-year sign consistency ≥ 5/6** train years,
  - **ADV/liquidity-tercile sign-robustness**,
  - the **confound check** named in advance (e.g. "if this merely re-measures extension, that is a
    KILL, not a discovery").
- **Instrument validation precedes belief.** If the screen's measuring device is itself a model,
  a grader, or any stochastic annotator: validate it FIRST and gate on it — test-retest
  reliability, and a leakage probe that the device is reading signal rather than furniture. 0123
  passed κ=0.867 test-retest and a clean crop-length probe *before* the screen ran, which is the
  only reason its null is interpretable as "the world is flat" rather than "our ruler is bent".
- **Serialized, not parallel.** One screen at a time, each priced in the ledger. Fishing many
  features against many labels simultaneously and reporting the winner is exactly what the ledger
  exists to make expensive.

### Screen-ledger accounting

- Every screen — pass **or** fail — increments the running screen count and appends a row to
  `research/overlay_registry.md`. Current standing: **screens 19**.
- A screen does **not** touch `n_trials` — read the count from
  `diagnostics/research/n_trials.json`, which is the authority — because it makes no PROMOTE/KILL
  decision on the honest base. State both counts in every readout.
  *(This line read "currently 138" until 2026-08-08. The counter had been reset to 0 by owner
  decision on 2026-08-07 and stood at 2; the stale literal survived because it was punctuated in a
  way `tests/test_standing_counts.py` did not match. The fix is to state no literal here at all —
  a number that cannot drift is better than one a test happens to catch.)*
- **Sealed opens are priced like any reuse.** Current standing: **sealed opens 1**. Opening the
  sealed set is a governance-class event: it requires a frozen rule *amended into the pre-reg
  before* the open, it may happen once per study, and the count is stated in the readout forever
  after. Thresholds may be tightened, never retroactively relaxed.

---

## GATE 3 — The activation bound (free; mandatory before any trial ask)

> **AMENDED 2026-08-08 (owner decision).** This gate no longer kills anything. It measures a
> ceiling, and a ceiling below the ±10R/yr floor is a *bound*, not a verdict — it says the path is
> low-value, which is a reason to rank it last, not a reason to close it. **Only a pre-registered
> run under the current harness may issue a negative verdict.** See the amendment at the top of
> `program-laws`. Record what the bound says, then decide priority; do not record a KILL.

**This gate is 3/3 as a bound — it has capped every usage candidate that reached it, at zero trial
cost** (0117 rotation, 0119 tiebreak, 0121 deferral). Run it before proposing a trial, always: a
measured ceiling is how you choose what to test first now that nothing can be closed for free.

The question it asks: *even with perfect hindsight, how much could this rule have earned?*

1. **How often does the rule ACTIVATE?** Count the decision points where it would change anything.
   (0119: the delivery ordering disagreed with the incumbent pick in 15 weeks over 5.5 years.)
2. **What is the CLAIRVOYANT ceiling?** Give the rule perfect foresight at each activation and
   total the R. This is an upper bound no real rule can reach.
3. **Compare to the ±10R/yr path-noise floor** (0109/0117). A bound below the floor cannot be
   certified on this book *no matter how real the effect is* — composition noise swamps it.
4. **Check the sign.** A negative bound (0119: −1.29 R/yr) means the effect inverts at the decision
   margin and the population gradient is irrelevant there.
5. **Simulate the mechanics honestly.** A "deferral" must model lapses and worse re-entries — 0121
   found a 94% lapse rate, which turned deferral into a de-facto skip and cost −15.72 R/yr.

**Verdict rule:** bound below the floor, or wrong-signed → **NO TRIAL.** Record it, bank the asset,
stop. This is a success, not a failure: the territory closed for the price of a measurement.

---

## The trunk — a real trial (the only thing that spends `n_trials`)

Reached only by a candidate that cleared all four gates. In order, no shortcuts:

1. **Pre-registration committed first** — `diagnostics/research/preregistry/NNNN-*.md`, Status
   PRE-REGISTERED, parameters frozen, kill criteria explicit, the relitigation basis stated.
2. **`n_trials.json` incremented BEFORE the run** (the DSR deflates on the cumulative count;
   understating it makes the bar falsely easy).
3. **Train design → sealed check → Stage-C capped continuous-slice endpoint.**
4. **Continuous-slice sub-periods only** — never a fresh-capital re-run from the sub-window start
   (that reseasons the boundary and manufactures phantom gates; it produced false KILLs once
   already). Use `nq.runner.research.evaluate_overlay`, which slices.
5. **Report DSR at the cumulative count**, plus the CI, per-year folds, and turnover.

### Amendment-before-run, never-retune-after

- Any change to a frozen parameter, rule, or gate is an **amendment written into the pre-reg BEFORE
  the run it affects**, with its reason. An amendment after seeing results is not an amendment; it
  is a retune, and it voids the study.
- Symmetric changes made *before any outcome data exists* are legitimate and must be recorded as
  such (0123 raised n from ~450 to 681 on a pre-registered power-check contingency, before any
  chart was graded — no grade existed, so the change could not bias toward a pass).
- **UNDERPOWERED and KILL are first-class outcomes.** Never massage either into a pass. A KILL with
  a named mechanism is worth more than a PASS you cannot explain.

---

## Closing a study — what "complete" means

Whatever the verdict:
1. **Finding file** `research/findings/NNNN-*.md` with the mandatory **root-cause readout** (the
   mechanism, not the metric) and the **next setup**.
2. **Registry row** appended to `research/overlay_registry.md` (append-only; never edit prior rows).
3. **Pre-reg closed** with its outcome appended below the immutable section.
4. **A "do not re-test unless" clause** naming the specific falsification/re-open condition. If you
   cannot name one, the hypothesis was not scientifically framed.
5. **Standing counts stated**: screens / sealed opens / n_trials.
6. **Artifacts committed** — every number reproducible from a committed script, never from a chat
   transcript. Raw model responses, rendered inputs, and intermediate datasets are artifacts.

---

## Cross-references

- [`skills/program-laws`](../program-laws/SKILL.md) — read FIRST; the laws that pre-answer most ideas
- [`skills/research-log`](../research-log/SKILL.md) — exact file formats for findings/registry/ADRs
- [`skills/edge-research-pipeline`](../edge-research-pipeline/SKILL.md) — the overlay-specific
  ideate→design→test→review flow that sits *inside* the trunk
- [`skills/overlay-testing`](../overlay-testing/SKILL.md) — the harness protocol and promotion bar
- [`skills/leakage-audit`](../leakage-audit/SKILL.md) — the PIT/lookahead gate for Gate 1
- `diagnostics/research/external_data_campaign_capstone.md` — the campaign this method came from
