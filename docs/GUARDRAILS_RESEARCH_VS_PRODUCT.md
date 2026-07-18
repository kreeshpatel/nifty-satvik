# Guardrails — the wall between the research discipline and the product build

*Written 2026-07-16 in direct response to "take care that we don't confuse ourselves and the rules."
The product build introduces new ways to fool ourselves that the research program's rules were never
designed to catch. This doc draws the wall and lists the specific confusions to guard against.*

---

## 0. Why this exists

The research program has a hard-won rulebook (registry-first, pre-registration, byte-identical golden,
reproduce-before-trust, DSR/multiple-testing, the forward wall). The product build is a DIFFERENT activity
with DIFFERENT rules (immutable snapshots, per-user state, no trials). The danger is **category confusion**:
applying a research rule where it doesn't belong, or — worse — *skipping* a research rule because "we're
just building the product now." Both corrupt the base.

The governing principle: **the research plane and the product plane are separate, and neither is allowed to
weaken the other.**

---

## 1. The two planes, and what "counts" in each

| | Research plane | Product plane |
|---|---|---|
| Unit of work | a **trial** (a config evaluated for PROMOTE/KILL) | a **build** (a feature that renders/serves existing model output) |
| Increments `n_trials.json`? | **YES** — before the run | **NO — never** |
| Needs a pre-registration? | YES (frozen params before the run) | NO |
| Judged by | DSR / the 2022-26 gate / the null | works / doesn't; correct / incorrect |
| Golden master | must stay byte-identical | must stay byte-identical (product must not perturb it) |
| Lives in | `research/`, `diagnostics/`, `models/` | `docs/` (design), `dashboard/`, `frontend/`, `scripts/*cron*` |
| Mutable? | idempotent/recomputable | immutable once published to a user |

**The bright line:** *changing the strategy or measuring an edge is research (trial, pre-reg, registry).
Rendering, serving, storing, or explaining the model's existing output is product (no trial).* Phase A
(shipping P + surfacing pattern/exit on cards) was **product** — it added no trial, changed no measurement,
and kept the golden byte-identical. That was correct. The moment a "product" task starts *tuning* the
exit/entry to look better, it has become a research trial and owes the full ritual.

---

## 2. The invariants that survive the product rush (non-negotiable)

No product deadline overrides these. If a product task would break one, the task is wrong, not the rule.

1. **The golden master stays byte-identical** (`test_stage2_golden` 1.1319/255). Every product commit
   verifies it. (Phase A did.)
2. **Reproduce-before-trust — now extended to the USER.** No user-facing number may be shown that can't be
   reproduced from committed data + the user's ledger. (This caught the MC config bug; it must catch a
   wrong P&L on a user's screen too.)
3. **Registry-first still applies to any strategy change.** If a "product" request is really "make the
   exit book more at 2R," grep the registry first — that is trial territory, not a card tweak.
4. **The config stays swappable.** The product is built against the exit-plan *interface*, never hard-coded
   to P (QUESTIONING_THE_FOUNDATIONS §31). When the forward wall speaks, P→LIVE is a config change.
5. **Honesty of the record.** Owner overrides (like shipping P) are documented AS overrides in the ADR +
   changelog, with the true gate status. The product shows forward numbers, never the backtest as forecast.
6. **The forward wall is untouched by the product.** Users trading P do not enter or contaminate the
   model's forward paper record. Decisions still happen only at quarterly reviews (plus the mechanical
   halt). The product must not create pressure to peek or relax thresholds.

---

## 3. The confusion register — the specific ways we could fool ourselves, and the guard for each

| # | The confusion | Why it's tempting | The guard |
|---|---|---|---|
| C1 | Treating a strategy tweak as a "product feature" (so skipping pre-reg/registry) | it's dressed as a card/exit change | If it changes what trades or what R is measured → it's a trial. Pre-reg + n_trials + registry. |
| C2 | Treating the paper NAV as the user's expected return | it's the nice number we have | Paper NAV is a CEILING (Part 3 §22). Show the user's own NAV; label the model curve "reference." |
| C3 | Letting the product's need for immutable history "fix" the research engine's idempotence | they feel contradictory | They are SEPARATE planes (§1). Research stays idempotent; the product snapshots at the boundary. Do not make the engine stateful. |
| C4 | Optimizing P's params because "users want better returns" | product pressure | That is retuning toward a pass — forbidden (R4). The config is frozen; improvement is a *new pre-registered trial*, not a product edit. |
| C5 | Believing the in-sample 27%/40R is what users will get | it's the headline | It's bull-regime, in-sample, trial-129 (FINDING_pattern_exit). The MC upside is optimistic. Forward-only in the product. |
| C6 | Confusing the model's state with the user's state | Phase A surfaces model exit_stage | The model recomputes its plan; the user's ledger is the truth (Part 1 §0). Never render model exit_stage as "you sold." |
| C7 | Adding a 5th/6th cron that re-scans the universe daily | "we need fresh exits" | Exit-mapping is position-scoped/observational (Part 1 §3). Universe scan stays weekly. Don't reintroduce the mutable-signal hazard. |
| C8 | Marketing away P's flaws to make the product sellable | commercial pull | The honesty rules (§2.5) are load-bearing for TRUST, which is the actual product. Forward numbers, true gate status, the tripwire (Part 3 §30). |
| C9 | Doc sprawl / contradiction across the brainstorm docs | many docs now | One synthesis doc per phase; cross-reference, don't duplicate; when two docs disagree, the newer + this guardrail doc win, and reconcile explicitly. |
| C10 | Subagent output taken as fact | agents feel authoritative | Agent output is DATA, not truth (the "agent-outputs-are-data" rule). Synthesize + verify claims against the repo before acting. |

---

## 4. Doc map — so we don't lose ourselves in our own notes

Product/design thinking (this build) lives in `docs/`, in a deliberate reading order:

1. `docs/PRODUCT_STATE_AND_DATA.md` — Part 1: two state machines, idempotent-vs-immutable, runner topology, storage plan.
2. `docs/PRODUCT_LAYERS_BRAINSTORM.md` — Part 2: journey, nudges, guidance, money, trust, cold-start, testing.
3. `docs/QUESTIONING_THE_FOUNDATIONS.md` — Part 3: the assumptions that could be wrong (cherry-picking=null, results-are-a-ceiling, P is execution-sensitive, capacity, calendar, config-agnostic hedge).
4. `docs/GUARDRAILS_RESEARCH_VS_PRODUCT.md` — this doc: the wall + confusion register.
5. *(next)* `docs/PRODUCT_SYNTHESIS.md` — Part 4: the combined behavioral/adversarial/positioning threads + the concrete build spec.

Research/strategy artifacts stay where they always were: `research/` (findings, pre-regs, registry),
`diagnostics/research/` (n_trials, pre-registry), `models/` (the frozen config + ADRs in `docs/decisions/`).
**ADRs (`docs/decisions/NNNN`) are decisions; the brainstorm docs are thinking.** Don't mix them.

---

## 5. The one-line test for any future task in this build

> *Does this task change what the strategy trades, or how an edge is measured?*
> **Yes** → it's a research trial: registry-first, pre-register, increment `n_trials`, keep the golden,
> reproduce before trusting.
> **No** → it's a product build: build against the exit-plan interface, snapshot-immutable, forward-honest,
> golden untouched, no trial.

Keep this test at the top of every session that touches this program. It is the whole of "don't confuse
ourselves and the rules."
