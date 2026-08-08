---
name: pre-register
description: >
  Scaffold a pre-registration and increment the trial counter BEFORE a run — the ordering that makes
  a result worth anything. Writes the outcome table with thresholds fixed in advance, so the verdict
  is already decided by the time the numbers land.
argument-hint: "[slug describing the candidate]"
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep Bash
---

# /pre-register — commit to the verdict before you can see it

A pre-registration is not paperwork. It is the only difference between a result and a story about a
result. Once the numbers are on the screen, every threshold becomes negotiable in a way that feels
like judgement rather than cheating — which is why the thresholds have to be written down while you
still genuinely do not know.

**Order matters and is not recoverable.** Pre-reg written, counter incremented, *then* the run. This
file's own increment log records one breach of that order (ENG-01, counted after the run because it
had been misclassified as an engineering change), kept visible rather than tidied away. Do not add
a second.

---

## Step 1 — is this a trial at all?

Run `verdict-machine` first if you have not. The question that decides it:

> **If this comes back favourable, could it be adopted as-is?**

If yes, it is a trial — however few parameters were swept. Multiplicity comes from the *option to
adopt*, not from how many values were tried. If no — you are measuring, adopting nothing — then
**stop: do not pre-register and do not increment.** A measurement wrongly counted as a trial raises
the bar for every future one.

Then confront the registry, and say so in writing:

- `research/overlay_registry.md` — the O-###/S#/R# ledger
- `research/findings/NNNN-*.md`
- `skills/program-laws` §KILL ledger and the five pre-entry walls

If the idea or a near-identical one is REJECT/KILL, you may not relitigate it without naming which
of {new data, new feature, new sub-period, new formulation} you bring. That sentence goes in the
pre-reg, not in the chat.

## Step 2 — pick the id and the location

Next free `NNNN`. Two layouts are in use; match the one the study belongs to:

- per-study folder: `research/NNNN-slug/prereg.md` (result lands beside it as `result.md`)
- flat registry: `diagnostics/research/preregistry/NNNN-slug.md` (finding lands in
  `research/findings/NNNN-*.md`)

Model it on `research/0001-xsec-momentum/prereg.md`.

## Step 3 — write it, with these sections

1. **Status: PRE-REGISTERED** — written and committed before the run. Date. The `n_trials` N → N+1
   transition, stated explicitly.
2. **Hypothesis** — one sentence, falsifiable, naming the comparator. Prefer a random or
   equal-weight control over zero: a long-only book in a rising market makes money by existing, so
   the only question is whether the *ranking* contributes.
3. **The book — every parameter fixed here.** Universe, screens, signal, selection, buffer, weights,
   costs, window. If a parameter is not written down now, it is a free variable later.
4. **Registry confrontation** — what was already tested, and what new thing you bring.
5. **Pre-committed outcome table.** The one that matters:

   | outcome | condition, fixed now | what happens |
   |---|---|---|
   | PROMOTE | *exact numeric bars, all of them* | route to the forward wall |
   | UNDERPOWERED | effect inside the resolution band | record, adopt nothing |
   | KILL | fails any bar | registry row, do not retune |

   Every bar numeric. Every gate on the **continuous slice** of one run, never a fresh-capital
   re-run. State the resolution floor you are working against (n_eff ≈ 37 windows ⇒ dSharpe
   half-width ~0.59) and say plainly whether the effect you are hoping for is above it.
6. **What would make this wrong** — the falsifier, and the leak that would most plausibly fake a
   pass.
7. **Reproduction command** — the exact script, config, data pin, and interpreter.

## Step 4 — increment the counter, before the run

Edit `diagnostics/research/n_trials.json`: bump `cumulative_n_trials` and `family_level_count`, and
append to `_increment_log` with the date, the pre-reg id, and the arm count. A multi-arm ablation
contributes its arm count, not one.

## Step 5 — commit, then run

Commit the pre-reg and the counter **before** executing anything. The git timestamp is the evidence
that the ordering held; a pre-reg committed alongside its result proves nothing.

Then run. Then `/verdict`.

---

**Standing rule, restated because this is where it gets broken:** the parameters are now fixed.
UNDERPOWERED and KILL are first-class outcomes. If the result misses, record the miss — 0025's swing
result sat 0.003 below its pre-committed bar and was recorded, not relitigated. That is the standard.
