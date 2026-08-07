---
name: seal
description: >
  Freeze a completed research folder or a blind evidence set so it can no longer be edited, and
  activate the guard that enforces it. Use after a study reports, or when standing up evidence that
  must stay unread until a pre-committed date.
argument-hint: "[path to the study folder or file]"
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep Bash
---

# /seal — make the record unable to change its mind

Sealing protects a record from the person most motivated to adjust it: the one who has since seen
how it turned out. Nobody edits a pre-registration dishonestly. They edit it because a parameter was
"obviously" mis-stated, or because the wording was ambiguous and the intent was clearly the other
thing. Every one of those edits is reasonable and every one of them destroys the evidence.

Two kinds of seal.

---

## A. Sealing a completed study

Once a run has reported, its pre-registration is closed. The
`scripts/guard_protected_paths.py` PreToolUse hook enforces this automatically: a `prereg.md` with a
`result.md` or `results.json` beside it, or a `preregistry/NNNN-*.md` with a matching
`research/findings/NNNN-*.md`, becomes unwritable.

**So sealing a study is mostly making the closing evidence exist:**

1. Confirm the finding is written (`/verdict` step 4) and the registry row is in.
2. Confirm the evidence file sits where the guard looks for it — same folder for `result.md`, same
   `NNNN` prefix for a finding. The guard keys off that adjacency; a finding filed under a different
   number leaves the pre-reg writable.
3. Commit both together.
4. Verify the seal actually bites, rather than assuming it: attempt an edit and confirm the guard
   denies it. An enforcement mechanism nobody has ever seen fire is a belief, not a control.

To amend a sealed pre-registration, add a **dated amendment file beside it** stating what changed
and why. Never edit in place. The override (`NQ_GOVERNANCE_OVERRIDE=1`) exists for genuine
emergencies and its use belongs in the commit message.

## B. Sealing blind evidence

Some evidence is worth something only while it is unread — the informed-judge log is the standing
example: `diagnostics/research/judge_log.jsonl` is sealed until the first review read (≥ 2 quarters
from 2026-08-01), and the guard denies both reads and writes.

To seal a new blind set:

1. **Write down what unseals it, before you start collecting.** A date, a trade count, a review —
   pre-committed and specific. "When we have enough" is not a condition; it is permission to look
   whenever looking would be convenient.
2. **Make it verifiable without being read.** Hash-chain the log and assert count and chain
   integrity in a test — `tests/test_judge_log.py` is the pattern. You get to confirm the evidence
   is accumulating and intact without learning what it says.
3. **Add the path to `FROZEN` or the read-deny rule in `scripts/guard_protected_paths.py`**, with
   the unseal condition written into the denial message. The person who hits that guard in eight
   months will be you, and you will not remember the reasoning.
4. **Add a test** asserting the guard denies that path, so removing the protection breaks the suite
   rather than passing quietly.

---

## What sealing is not

It is not a substitute for the pre-registration — a sealed record of an underspecified plan just
freezes the ambiguity. And it is not permanent: seals have unseal conditions, stated in advance. A
seal with no stated way out is not discipline, it is data you have thrown away.
