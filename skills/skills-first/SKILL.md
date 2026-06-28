---
name: skills-first
description: >
  The pre-flight habit: BEFORE running any command, writing any plan, or building anything,
  check what skills, agents, and ecosystem capabilities already exist — so we never reinvent
  or re-explain something the project (or the wider toolset) already encodes. A borrowed or
  existing capability always beats a fresh build. Run this first, every task, then open the
  matching skill. Trigger words: "before any task", "before planning", "before I build",
  "what skill applies", "which skill", "do we already have", "is there a skill for",
  "should I build", "where do I start", "how do I do X", "first step".
---

# Skills-First — the pre-flight check you run before doing anything

**Why this matters (plain language).** This project has spent months building up a library of
hard-won procedures (`skills/`), a roadmap (`docs/ROADMAP.md`), a KILL ledger of things already
tried and rejected, and a set of specialist agents. If you start a task by writing code or running
a command without checking those first, you will waste effort re-deriving a procedure that already
exists, or worse — re-run a "lever" the program already KILLed. CLAUDE.md says it directly:
**"Never duplicate logic — extend existing abstractions."** Skills are abstractions for *process*.
This is also a standing owner directive ("ALWAYS use `skills/` when working") and is enforced via a
CLAUDE.md pointer to the skills index.

**The principle.** A matching existing capability — a project skill, an available skill, an agent,
or a reputable ecosystem skill — **always beats a fresh build or a from-memory explanation.** Build
bespoke only when you have confirmed a real gap.

---

## The pre-flight checklist (run at the START of every non-trivial task)

Do this *before* the first `Bash` call, *before* writing a plan, *before* any `src/` edit.

- [ ] **1. PROJECT skills first.** Open [`skills/README.md`](../README.md) and scan the
      "Working procedures" table. If the task touches data, a backtest number, an overlay, a
      conviction feature, an exit/rotate rule, regime, or execution — there is almost certainly a
      skill for it. When unsure *which* applies, start at
      [`skills/methodology-synthesis`](../methodology-synthesis/SKILL.md) — that is the
      which-method-applies index AND the ledger of what we ADOPTED / made a CANDIDATE / REJECTED.
      **Check the REJECTED rows + the §11 KILLs before proposing any idea** — re-pitching a KILL
      (regime-as-entry-gate, sector-rotation alpha, RSI/MACD reversal) is the most expensive mistake.

- [ ] **2. AVAILABLE skills + agents (the harness toolbox).**
      - **Engineering skills** (`engineering:*`): `debug`, `code-review`, `architecture` (ADRs),
        `testing-strategy`, `deploy-checklist`, `system-design`, `tech-debt`.
      - **Just-installed ecosystem skills:** `prompt-engineer` (writing/refactoring LLM prompts —
        e.g. the news/AI-narrative or postmortem prompts), `creating-financial-models`
        (DCF / Monte-Carlo / scenario / sensitivity — for valuation or risk-of-ruin framing, NOT
        for replacing our walk-forward harness).
      - **Memory hygiene:** `consolidate-memory` (the MEMORY.md index is already over its size
        limit — use this rather than hand-editing).
      - **Specialist agents** (spawn instead of doing the work inline): **`flaw-hunter`**
        (lookahead / leakage / PIT-violation hunter — run on any data or feature change),
        **`backtest-validator`** (sanity-check a harness number against
        [`skills/backtest-rigor`](../backtest-rigor/SKILL.md)), **`overfit-skeptic`** (DSR /
        too-good-to-be-true / param-fragility), plus `engineering:debug` and `consolidate-memory`.

- [ ] **3. ECOSYSTEM (only for a genuinely new need).** If steps 1–2 turn up nothing, search the
      wider library before building: `npx skills find <query>`. Prefer **reputable, widely-installed
      (1K+) skills** over a hand-roll. The methodology-synthesis ledger shows the bar: a borrowed
      method is a **hypothesis**, attributed and adapted — never raw-copied, never auto-adopted.

- [ ] **4. REUSE > BUILD.** Use the matching capability. Build or install something new **only**
      when you have confirmed a real gap (no project skill, no available skill/agent, no decent
      ecosystem option). If you do build a project skill, follow the existing format
      (frontmatter `name` + `description`-with-triggers → tight operational body → checklist) and
      add it to [`skills/README.md`](../README.md).

---

## Decision tree

```
New task / new need
   │
   ▼
Have a PROJECT skill?  (skills/README.md → methodology-synthesis)
   │ yes → USE IT  (and check §11 KILLs / REJECTED rows before proposing anything)
   │ no
   ▼
Have an AVAILABLE skill or AGENT?  (engineering:*, prompt-engineer,
                                    creating-financial-models, consolidate-memory;
                                    flaw-hunter / backtest-validator / overfit-skeptic)
   │ yes → USE IT
   │ no
   ▼
ECOSYSTEM has one?  (npx skills find <query>; prefer reputable / 1K+ installs)
   │ yes → install + adapt + ATTRIBUTE  (it is a hypothesis, not an auto-adopt)
   │ no
   ▼
BUILD bespoke  (only now) — follow the SKILL.md format, register it in skills/README.md
```

---

## Quick examples (this repo)

- *"Let me write a backtest validator..."* → STOP. Use
  [`skills/backtest-rigor`](../backtest-rigor/SKILL.md) + the `backtest-validator` agent.
- *"I'll add a corporate-action cleaner..."* → STOP. Use
  [`skills/data-quality`](../data-quality/SKILL.md) (the split-vs-demerger / VEDL spec) and run
  `flaw-hunter` on the change.
- *"Let me test this regime entry gate..."* → STOP. `methodology-synthesis` §4 lists
  regime-as-entry-gate as a validated **KILL** — don't relitigate without extraordinary new evidence.
- *"I'll explain DCF / Monte-Carlo risk-of-ruin from scratch..."* → use the
  `creating-financial-models` skill instead of re-deriving it.
- *"I need a new conviction-model news prompt..."* → use the `prompt-engineer` skill.

---

## Cross-references

- [`skills/README.md`](../README.md) — the working-procedures index (start here)
- [`skills/methodology-synthesis`](../methodology-synthesis/SKILL.md) — which-method-applies index +
  ADOPT/CANDIDATE/REJECT ledger + §11 KILL pointers
- [`docs/ROADMAP.md`](../../docs/ROADMAP.md) — the destination-ordered stages (A→G); know which
  stage you're on before you plan
- [`docs/LIVE_OVERLAY_PROTOCOL.md`](../../docs/LIVE_OVERLAY_PROTOCOL.md) — the promotion bar every
  new idea must clear
- **CLAUDE.md** — "Never duplicate logic — extend existing abstractions" + the standing pointer to
  this skills library

**The one-line habit:** *check what already exists (project → available → ecosystem) before you
run, plan, or build — and reuse it.*
