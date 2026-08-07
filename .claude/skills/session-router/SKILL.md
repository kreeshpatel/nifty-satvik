---
name: session-router
description: >
  Route a task before doing it. Classifies the work as MEASUREMENT / RESEARCH / ENGINE / REFACTOR /
  PRODUCT and names the laws, skills, agents, and gates that class must clear — so a research
  question gets research discipline and a code change gets engine discipline, in the same session,
  without either borrowing the other's standards. Run at the start of any non-trivial task, and
  again when a task changes class mid-flight. Trigger phrases: "route this", "where do I start",
  "what applies here", "is this a trial", "what gate does this need", "can I just change".
---

# Session router — decide what kind of work this is, before doing it

Most expensive mistakes in this repo are **category errors**, not reasoning errors. A config change
treated as a refactor skips the changelog. A measurement treated as a trial burns multiplicity that
cannot be refunded. A trial treated as a measurement skips the pre-registration, and its result is
then worth nothing no matter how good it looks. The reasoning inside each class is usually fine; the
class was picked wrong at the start, silently, in the first thirty seconds.

So classify first. One task can contain several classes — a research question that needs an engine
change to answer is two pieces of work with two different gates, and running them as one is how the
engine change ends up uncertified.

---

## Step 0 — always

- **Standing counts** come from the SessionStart brief or, failing that, from
  `diagnostics/research/n_trials.json` and `diagnostics/research/label_screen_ledger.md`. Never from
  a document, never from memory. State them in any research readout.
- **`skills-first`**: check what already exists before building anything.
- If the task touches strategy, signal, entry, exit, sizing, universe, regime, or "a new idea" —
  load **`program-laws`** before forming an opinion. The collision rule is **cite and narrow, never
  relitigate**.

---

## The five classes

### MEASUREMENT — you are learning something, and adopting nothing
Coverage audits, PIT audits, distribution reads, correlation between two existing features,
"how often does X actually happen", forensics on trades already taken.

- **Spends no multiplicity.** Do not increment `n_trials`. `n_trials.json` is explicit: a trial is a
  strategy configuration evaluated for a PROMOTE/KILL decision; a pure measurement that makes no
  trade decision is not one.
- **The test that decides the class:** *if this comes back favourable, could it be adopted as-is?*
  If yes, it is a trial, whatever it is called. Multiplicity comes from the option to adopt, not
  from how many values were tried — this repo has already recorded one breach of exactly that kind
  (ENG-01, counted after the run, logged rather than hidden).
- Gate: reproducible from the committed pipeline. Skills: `verdict-machine`, `data-quality`.

### RESEARCH — a candidate could change what gets traded
Any overlay, signal, feature, exit, sizing rule, universe change, or sleeve.

- Run `verdict-machine` **in order**: registry confrontation → coverage and PIT audit → kill-shot
  screen (ledgered) → activation bound against the ±10R/yr floor → then a trial. Since the
  **2026-08-08 owner amendment**, none of those gates may close a path: they produce *bounds*, which
  rank what to test first. Only a pre-registered run under the current harness can issue a negative
  verdict.
- If it survives: `/pre-register` **before** running. Increment `n_trials` **before** the run.
  Thresholds are fixed in the pre-registration and are not revisited afterwards.
- Then `/verdict`, a `research/findings/NNNN-*.md`, and an `overlay_registry.md` row.
- **UNDERPOWERED and KILL are first-class outcomes.** Never retune toward a pass.
- Agents worth spending: `overfit-skeptic` before promoting, `red-team` on the finished result.
- Prior verdicts are **evidence about the regime that produced them**, not closures: the in-sample
  momentum programme, the cross-asset/macro branch, the technical-indicator zoo at 63 days, the
  Bhanushali external-strategy arc. Quote each as `KILL (epoch, book) — not re-tested under the
  current harness`, use it to set priority, and never to end a path. `program-laws` holds the
  receipts and the amendment.

### ENGINE — code that can change a number
Anything under `nq/**`, `config.py`, or a script that produces a result of record.

- **The invariant:** any overlay must be cfg-gated so `tests/test_stage2_golden.py` stays
  byte-identical with it off. If the golden master moves, you have changed history, and every
  finding measured against it is now measured against something else.
- After editing `nq/**` or `config.py`: regenerate the depgraph (`python scripts/gen_depgraph.py`)
  and run the full suite before pushing.
- A change that moves a number is not an engine change alone — it re-anchors. That is governance
  class: `/re-anchor`.
- Agents: `flaw-hunter` on any data or feature path, `backtest-validator` on any number it produces.
- Skills: `repo-map` first (blast radius, single source of truth, live-vs-backtest parity),
  `karpathy-guidelines` (surgical changes), `leakage-audit` before trusting the output.

### REFACTOR — behaviour must not change
Renames, extractions, typing, test structure, docs.

- Gate: golden masters and the full suite pass unchanged, and you can say *why* behaviour is
  preserved rather than only that the tests are green.
- If you find yourself arguing a test needs updating, it is not a refactor. Reclassify.

### PRODUCT — the dashboard, API, deploy, frontend
- Different discipline entirely: `repo-maintenance` for git and branch hygiene, the frontend
  design-system rules, deploy targets. Backend is Fly.io, not Render.
- Research laws do not bind here, and product urgency does not bind research. Keep them apart.

---

## Mixed tasks — the common case

"Make the engine do X so I can test whether X helps" is ENGINE **then** RESEARCH:

1. Build X cfg-gated, default off. Golden master byte-identical. Tests pass. This is done and
   committable on its own merit.
2. *Separately*, decide through `verdict-machine` whether X earns a trial. It may not — and the
   engine work is still correct and still worth keeping.

Keeping the order means the code is judged as code and the idea is judged as an idea. Collapsing
them is how an unjustified idea rides in on a well-written diff.

---

## Two things no session may do from memory

- **State a count.** Read the ledger.
- **Assert a number is plausible.** Run `/plausibility`. The anchors are reproducible; a model's
  recollection of them is not, and this programme has already been saved once by a drawdown that
  looked wrong against the literature.

## What a readout owes the reader

The class, the standing counts (screens · sealed opens · n_trials), the reproduction command for
every number that carries a decision, and — when the answer is negative — the negative answer
stated plainly. A finding that says "no effect, here is the bound" is worth more than one that says
"promising, worth further work", because only one of them can be acted on.
