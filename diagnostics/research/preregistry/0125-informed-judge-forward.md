# 0125 — The informed judge: a third watched stream in the habit ledger

**Status:** PRE-REGISTERED
**Class:** **FORWARD MEASUREMENT.** No trial, no label screen, no sealed-set contact.
**Standing counts at registration: screens 12 · sealed opens 1 · n_trials 138.** This study does not
move any of them, at registration or at read.

**Date registered:** 2026-07-31. **Owner:** Kreesh Patel.
**Companion:** the habit-ledger spec ([review_2026Q4/06](../review_2026Q4/06_habit_ledger_spec.md)) —
the judge is that spec's **third stream**: system / owner-override / judge.

---

## §1 IMMUTABLE — THE PROHIBITION

**There will be no historical variant of this experiment. Not now, not as a "cheap first look", not
as a "sanity check", not with a held-out slice, not ever.**

The rationale, stated in full so it cannot be softened later:

1. **The model's training data contains the outcomes.** The judge is asked to assess NSE equities on
   dated cards. Any card dated before the model's knowledge cutoff sits inside a corpus that already
   knows what the stock did next. A backtested verdict is therefore not a forecast; it is recall of
   varying reliability, and there is no instrument that can separate the two after the fact.
2. **Unblinding is inherent to the design, not incidental to it.** 0123 could blind its grader by
   truncating the chart at the entry bar. This design cannot: the judge is *given* live news and a
   PIT earnings-calendar status, and both identify the stock and the week directly. Removing them to
   restore blinding removes the only inputs that could carry new information (see §2's rationale).
   **The two properties are mutually exclusive — a blind judge has nothing new to say, and an
   informed judge cannot be blinded.**
3. **Chart-alone is already answered, at high reliability.** [0123](../../../research/findings/0123-vision-graded-chart-structure.md)
   graded 681 blind, entry-truncated charts with the instrument validated *first* (test-retest
   **κ = 0.867**, truncation-leakage probe clean) and found grades **flat** across cohorts — winner
   1.339 / noise-stop 1.313 / false-touch 1.383 — null in **both** the detector-agreement and
   detector-disagreement cohorts. So on this funnel, **any value here must come from the non-price
   context (news, event status) or from the fusion of that context with the chart — and only forward
   evidence can show it.**

**Enforcement.** The judge module must be structurally incapable of a historical run: it takes its
inputs from the live card envelope and a live news fetch at call time, and it has no
`--start` / `--as-of` / backfill path. A future session proposing to add one is proposing to void
this pre-registration.

## §2 IMMUTABLE — the 0123 collision, and the narrowing this brings

0123's re-open condition refuses *"model-graded charts on the same 44-SMA touch entries — with a
different rubric, a different vision model, more charts, or grade-ensembling."* **This study touches
that wall and must name what it brings.** Of the four admissible bases {new data, new feature source,
new sub-period, new formulation}, it brings **two**:

- **New feature source** — live news at call time and PIT event status. 0123's instrument saw a
  rendered chart and nothing else. This is not a different rubric on the same inputs; it is different
  inputs.
- **New sub-period** — forward only, from inception. No in-sample label is read, ever.

**What it does NOT bring, stated so it is not claimed later:** a different rubric, a different vision
model, more charts, or grade-ensembling would each be refused relitigation on their own. The chart is
present in the judge's inputs only as *context for the news*, and **a positive result may not be
reported as evidence that chart perception works on this funnel** — 0123 settled that.

**Attribution limitation (load-bearing, recorded before any verdict exists).** The judge sees chart +
arithmetic + event status + news in one call. If a spread appears, this design **cannot attribute it**
to any one component. A positive read is evidence for the **fused instrument only**. Component
attribution would require its own pre-registered forward arm (e.g. a second, news-withheld call per
card) — which doubles cost and entangles the streams, and is **not** part of this study.

**Law VI (±10R/yr noise floor).** The expected effect is far below the floor at this decision rate,
which is why this is designed as a **measurement**, not a trial. That is the correct application of
the law, not an evasion of it.

**Laws not engaged.** Law I is about predicting entry quality on *this funnel's chart at the decision
point*; the informed judge is a different instrument with different inputs, which is exactly the
narrowing above. Law II is engaged in the sense that any population effect must still survive to the
book's decision margins — but this study **does not propose a rule**, so no activation bound is due
here. **Any proposal to ACT on the judge's verdicts is a separate object** and must run
[verdict-machine](../../../skills/verdict-machine/SKILL.md) Gate 3 before it is even proposed.

## §3 IMMUTABLE — the judge call, frozen

| element | frozen value | note |
|---|---|---|
| **Model** | `claude-opus-5` | Pinned. 0123's grader — same model, so the instrument is continuous with the programme's one validated perception study. |
| **Determinism control** | `output_config.effort = "high"` — **frozen** | ⚠️ **AMENDMENT-BEFORE-RUN, recorded here because the brief specified otherwise.** The brief said "temperature fixed". **`temperature` is not a settable parameter on `claude-opus-5` — sending it returns HTTP 400.** It was removed on the Opus 4.7+ family. 0123 hit the same constraint and froze *effort* instead ("frozen prompt/effort/schema"); this study does the same. Recorded before any call is made, so it is an amendment and not a retune. |
| **Thinking** | default (adaptive; on by default on this model) | Not configured, so it cannot drift. |
| **Structured output** | `output_config.format` = `json_schema`, `additionalProperties: false`, all fields required | Schema frozen below. |
| **Verdict schema** | `verdict ∈ {take, skip, wait}` · `conviction ∈ 1..5` (integer) · `primary_reason` (one line, ≤ 200 chars) · `risk_flag` (string; `"none"` when absent) | Exactly the brief's four fields. Frozen. |
| **Calls per card** | **exactly one, independent** | 0123's protocol. No ensembling, no retry-for-a-better-answer (a *transport* retry that returns the same content is not a re-roll; a second scored call is). |
| **Prompt** | frozen verbatim in `nq/paper/judge.py::JUDGE_PROMPT`, hash logged per call | Any edit is an amendment with a dated entry here, and it **starts a new evaluation cohort**. |

### Inputs per card (frozen)

1. **Rendered chart** — full, unblinded. (Blinding is impossible here; see §1.2.)
2. **Ext band + SMA data** — `ext_vs_sma`, the signal-week 44w SMA, band label.
3. **CRS** — `crs_rank` as printed on the card.
4. **Printed zone / stop / target + the R:R arithmetic** — echoed from the card verbatim (D5 parity;
   never re-derived).
5. **PIT earnings-calendar status** — from `nq/data/earnings.py` (`known_events_features`, the 0120
   module, truncation-tested). Trailing-only by construction.
6. **Live news, fetched at call time** — via the model's server-side `web_search` tool. **The source
   and the fetch timestamp are logged per call.** No historical news backfill exists or may be added.
   *Interpretation recorded:* "live news" is implemented as the API's own web-search server tool
   rather than a new vendor, so no new credential, contract, or PIT-unaudited corpus enters the
   programme. The search queries and returned result metadata are logged verbatim.

## §4 IMMUTABLE — evaluation terms

- **Read only at quarterly reviews** (first trading day Jan/Apr/Jul/Oct). Between reviews: log and
  leave it alone.
- **Minimum two quarters AND ≥100 resolved verdicts** before the first read. Whichever binds later.
- **The question:** the spread in **realized R between judge-`take` and judge-`skip` cards**,
  conditional on **ext-band × CRS cells**, with **per-cohort counts reported** for every cell.
- **Outcome source:** realized R comes from the **uncapped signal tracker**
  (`results/signals_history_weekly.json`), not the capped book — a judge-`skip` card is frequently
  never funded, so the capped book has no outcome for it. Using the uncapped tracker is what makes
  `take` and `skip` comparable at all. `wait` verdicts are reported as their own cohort and are
  **not** merged into either arm.
- **UNDERPOWERED is a first-class outcome** and is the expected one at the first read.

### The power arithmetic, stated honestly at ~250 verdicts/yr

Two quarters ≈ **125 verdicts**, and only the resolved subset counts.

| effect to detect (ΔR between arms) | n per arm (σ_R ≈ 1.5) | total verdicts | time at 250/yr |
|---|---:|---:|---:|
| 0.5R | ~144 | ~288 | **~1.2 years** |
| 0.3R | ~400 | ~800 | **~3.2 years** |
| 0.2R | ~900 | ~1800 | **~7.2 years** |

**And that is the *marginal* comparison.** The pre-registered question is **conditional on 9
ext × CRS cells**: at 125 verdicts the median cell holds ~14 rows, ~7 per arm. **The conditional
analysis is uninterpretable at the first read and is expected to stay so for years.** The first read
is therefore a **cohort-count and instrument-health check**, not a verdict — and saying so now is
what stops a thin cell being read as a signal in April.

## §5 IMMUTABLE — sealing

**Default: SEALED.** Verdicts write to `results/judge_log.jsonl`, which **the owner does not read
until the first review read.** The purpose is specific: the habit ledger's *owner-override* stream is
the owner's own decisions, and a judge verdict read before acting would contaminate it — the two
streams would no longer be independent, and neither could be evaluated against the other.

- The seal is procedural, not cryptographic. It is a commitment, and the log records whether it held.
- **Unsealing after the first review read is a review decision**, recorded with its date.
- **If the owner instead chooses open-from-day-one:** that is a legitimate choice and is recorded
  here as a dated amendment. Its consequence must be stated in the same breath — **the owner and
  judge streams are entangled from inception**, the ledger marks every row written under the open
  regime with `judge_visible: true`, and no analysis may thereafter treat the owner-override stream
  as an independent comparator.

## §6 Operational commitments

- **Failure-tolerant.** A failed judge call logs the failure and **never blocks the scanner.** The
  Saturday cron's exit status must not depend on the judge.
- **Append-only + hash-chained**, the `nq/paper/forward_wall.py` §3 construction: each row binds its
  predecessor, so reordering, back-dating, or silent deletion is detectable.
- **Cost logged per run** — per-call token usage and a run total, from `response.usage`.
- **Model-version drift alarm.** If the pinned model id is unavailable, the run **logs and alerts and
  does not silently substitute another model.** A substituted model is a different instrument and
  would void the cohort.
- **Secrets.** `ANTHROPIC_API_KEY` via the existing `${{ secrets.* }}` → `env:` pattern. If the
  Actions runner lacks it, the job **reports that plainly and skips the judge** — nothing is invented
  and the scanner still succeeds.

## §7 What would end this study

- **Instrument failure** — sustained call failures, or drift that forces a model change.
- **Owner decision** at any quarterly review.
- **A read that resolves it** — a spread whose CI excludes zero in the marginal comparison, sustained
  across two consecutive reads, would make it a *candidate* worth proposing. It would then start at
  Gate 0 of the verdict machine like anything else. **Nothing here promotes itself.**

## §8 Reproduce

    python -m pytest tests/test_judge_log.py tests/test_judge.py
    python scripts/run_judge_cron.py --dry-run     # renders inputs, makes no API call

---

## AMENDMENTS

*(dated entries only; nothing above this line may be edited after registration)*

**2026-07-31 — registration-time, before any call:** `temperature` replaced by frozen
`effort="high"` as the determinism control, because `temperature` returns HTTP 400 on the pinned
model (removed on the Opus 4.7+ family). 0123's precedent is the same. No outcome data existed.

## OUTCOME

*(appended after the first review read — never above the immutable sections)*
