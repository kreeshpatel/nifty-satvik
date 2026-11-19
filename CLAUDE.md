# nifty-satvik

## Mission and verification

**Mission.** Build an investment system that, after costs and Indian capital-gains tax, beats the Nifty Midcap150
Momentum 50 TRI on risk-adjusted return over rolling 3-year windows, with a worst drawdown no deeper than −25%,
proven by a forward record rather than a backtest, and needing no more than about 1 hour a week of owner time. The
target system is the 70/30 momentum/swing blend at a 15% volatility target, with total system capital of
₹20,00,000: PILOT ₹2,00,000, SCALE ₹5,00,000, FULL ₹20,00,000. Promotion between stages needs 26 weeks on paper. If
no strategy meets this goal, core capital goes into the index fund.

**Every task must say in one line how it moves the system toward this goal. If it doesn't, say so and ask before
starting.**

**Verification rules — they bind every report.** Procedure and worked examples:
[`skills/verify-before-report`](skills/verify-before-report/SKILL.md).

1. **Method before result.** Every study states, before its results: the exact formula for each metric (with
   `file:line`), the data window, the universe, and how overlapping or dependent samples are handled.
2. **Artifact check.** Before any conclusion, list at least **3 ways the result could be an artifact of the method
   rather than a property of the market** (e.g. cumulative vs marginal returns, overlapping windows, survivorship,
   look-ahead, cap or sizing binding, single path, open trades counted at cutoff). For each one, say whether it was
   ruled out and how.
3. **Independent re-derivation.** Any number that drives a decision (a verdict, a pass mark, a change to live or to
   capital) is recomputed by a **fresh sub-agent that has only the spec, not the original code**. Report both numbers.
   If they differ by more than **5% relative**, stop and reconcile before reporting.
4. **Anchors.** Every study reproduces one known published number first (e.g. live A = **650.2R (filtered,
   marked-at-cut)**, 0001 = **21.73% / 1.130**). If it doesn't match, stop.
5. **No silent scope changes.** Horizons, settings or windows added after seeing results are listed as **"added after
   first look"**, with the reason, and they count toward multiplicity.
6. **Label every claim** in a final message as **[measured]** (with artifact path), **[inferred]** or **[assumed]**.
   No unlabelled facts.
7. **Corrections are loud.** When a later finding overturns an earlier claim, the final message opens with
   **"Correction:"**, naming the claim, the PR and what replaces it.
8. **Owner decisions are listed separately at the end**, each with the options and the evidence for each. Do not
   merge, sign or change capital without the owner's explicit word naming the item.

## Dependency map maintenance

After editing any `nq/**` module or root `config.py`, regenerate the import map and
commit the result:

```
python scripts/gen_depgraph.py
```

This rewrites [docs/DEPENDENCY_MAP.md](docs/DEPENDENCY_MAP.md) (a Mermaid graph of
first-party `nq/` ↔ `config` wiring). The regenerator is stdlib-only and deterministic,
so re-running produces byte-identical output. A committed pre-commit hook in `.githooks/`
does this automatically when `core.hooksPath` is set — enable once per clone with:

```
git config core.hooksPath .githooks
```

## Output style — ALWAYS use the `caveman` skill

**Always use the [`caveman`](.claude/skills/caveman/SKILL.md) skill: terse, token-efficient
responses** — minimal words, full technical accuracy ("why use many token when few do trick").
Applies to conversational / working output.

Keep FULL prose for artifacts that must stay readable, NOT caveman-terse: commit messages (the
git log is investor-facing), PR summaries, compliance-safe product copy, and committed docs.

## Route the task before doing it

Run [`/session-router`](skills/session-router/SKILL.md) first. It classifies the work as
**MEASUREMENT / RESEARCH / ENGINE / REFACTOR / PRODUCT** and names the gate that class must clear.
Almost every expensive mistake here has been a category error, not a reasoning error — a trial run
as a measurement, a re-anchor run as a config change — and the class is chosen in the first thirty
seconds, silently, by whoever starts typing.

A `SessionStart` hook (`scripts/session_brief.py`) puts the live standing state in front of every
session, generated from the ledgers rather than recited from prose.

## The rules that bind every task

**Reproduce-before-trust.** A number that informs a decision must be reproducible from the committed
pipeline, never from a chat transcript. Two hard-won corollaries:
- **Sub-period gates are a CONTINUOUS SLICE of one full run**, never a fresh-capital re-run from the
  window start — that resets the equity peak and manufactures a pass (phantom 2022-26 base 0.762 /
  −40% vs the correct slice **0.570 / −46.3%**, which produced false KILLs). Use
  `nq.runner.research.evaluate_overlay`, which slices.
- Trust ≥2019 folds and the 63d horizon only; old v1 7–14d kills do not transfer.

**Engine invariant.** Any overlay must be cfg-gated so the golden master
(`tests/test_stage2_golden.py`) stays byte-identical when off. After editing `nq/**` or `config.py`:
regenerate the depgraph (above) **and** run the full suite before pushing.

**Pick the process tier before the method** ([`docs/PROCESS_TIERS.md`](docs/PROCESS_TIERS.md), owner
2026-10-19). Exploration in the Strategy Lab and re-runs/measurements need no pre-registration or screen
row; only a result that would change live money pays the full method below. Our own findings can be
wrong: never answer "no" flatly, offer the cheapest test that would change the answer.

**Ordering that cannot be recovered once broken.** Pre-registration written and committed → counter
incremented → *then* the run. Thresholds are fixed in the pre-reg and are not revisited afterwards.
**UNDERPOWERED and KILL are first-class outcomes; never retune toward a pass.** `/pre-register` and
`/verdict` carry the procedure.

**No path is killed without a run (owner amendment, 2026-08-08).** A negative verdict — KILL, or a
bound treated as one — may only come from a pre-registered run under the *current* harness. A prior
verdict is evidence about the regime that produced it, quoted as `KILL (epoch, book) — not re-tested
under the current harness`, and it sets priority, never closure. The apparatus has moved underneath
the ledger (continuous-slice fix, calendar annualisation, the v0→v1 re-anchor, the macro PIT gate,
the survivorship backfill), and only 7 of 108 closed verdicts were measured on the live book. Full
reasoning and its limits: the amendment at the top of [`skills/program-laws`](skills/program-laws/SKILL.md).

**Standing counts: screens 25 · sealed opens 4 · n_trials 3** — state them in every research
readout, and read them from `diagnostics/research/n_trials.json` and
`diagnostics/research/label_screen_ledger.md`, never from memory or from this line.
`tests/test_standing_counts.py` holds every copy of these numbers to those ledgers.

**Two things no session may do from memory:** state a count, and assert that a backtest number is
plausible. The anchors are reproducible (`/plausibility-check`); a recollection of them is not.

## Where everything else lives

| you are about to… | load |
|---|---|
| propose or judge any research idea | [`skills/program-laws`](skills/program-laws/SKILL.md) — standing verdicts with receipts; **cite and narrow, never relitigate** |
| design a study, or decide if it earns a trial | [`skills/verdict-machine`](skills/verdict-machine/SKILL.md) — registry confrontation → coverage/PIT audit → kill-shot screen → activation bound → *only then* a trial |
| report or believe a number | [`/plausibility-check`](skills/plausibility-check/SKILL.md) + [`docs/references/plausibility_anchors.md`](docs/references/plausibility_anchors.md) |
| trust a backtest at all | [`skills/leakage-audit`](skills/leakage-audit/SKILL.md), [`skills/backtest-rigor`](skills/backtest-rigor/SKILL.md) |
| change a value or a formula | [`skills/repo-map`](skills/repo-map/SKILL.md) — blast radius and single source of truth |
| judge a live or paper strategy, promote, fund, change or retire one | [`skills/strategy-lifecycle`](skills/strategy-lifecycle/SKILL.md) — stages, weekly status against frozen bands, **no forward verdict before 26 weeks**, changes only at quarterly reviews |
| record a result | [`skills/research-log`](skills/research-log/SKILL.md), then `/verdict` |
| move the pinned anchor | `/re-anchor` — governance class, owner decision |
| freeze a study or blind evidence | `/seal` |
| read the full research board as it stood | [`docs/PROGRAM_STATE.md`](docs/PROGRAM_STATE.md) (archive; `program-laws` is the maintained authority) |
| find any other procedure | [`skills/README.md`](skills/README.md), via [`skills/skills-first`](skills/skills-first/SKILL.md) |

## Adversarial reads — spend them, they are cheap

Fresh context is the point: a subagent reads the result without the session's accumulated reasons to
believe it. `red-team` (any finished result, especially a flattering one), `flaw-hunter` (leakage /
PIT / train-serve skew on any data or feature path), `backtest-validator` (any harness number),
`overfit-skeptic` (before promoting anything), `blind-replica` (a second implementation from the
spec alone, for differencing). Definitions in `.claude/agents/`.

**When handed an external research doc, be adversarial.** Cross-reference every recommendation
against the registry — an outside chat cannot see it, and most "new" ideas are already tested here.
Correct the doc's premises with our data. Credit only genuinely-new, non-relitigated ideas, and hold
them to the same bar.

## What the hooks enforce, so prose does not have to

`.claude/settings.json` wires two hooks. `scripts/guard_protected_paths.py` refuses the edits that
destroy evidence: the sealed judge log (no read, no write, until the first review read), a
pre-registration whose run has already reported, the frozen cfg, the pinned anchor, and
`forward/prereg.md`. Each denial states the law and the amendment route. It covers the **shell** as
well as the file tools — reads stay allowed, writes do not — because until 2026-09-25 it inspected only
Edit/Write, and a `python - <<EOF … write_text(…)` heredoc walked straight past it. Override with
`NQ_GOVERNANCE_OVERRIDE=1` — one variable, deliberately, and say so in the commit message.
