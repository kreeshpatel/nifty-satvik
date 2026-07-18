# ADR 0012 — Inner-circle-only distribution; SEBI question routed to a qualified professional

**Date:** 2026-07-18
**Status:** ACCEPTED (owner decision)
**Affects:** who the product is offered to, the SEBI compliance gate from the Stage-6 plan
(cross-cutting track), onboarding/access flows, and all public-facing copy.

## Decision

The model and the product built around it are distributed to **a qualified (compliance)
professional for review and a very limited inner circle only**. There is **no public offering, no
broadening of the user base, and no marketing** until the owner explicitly reverses this with a new
ADR.

The open SEBI questions (research-analyst classification, research-vs-advice boundary,
performance-claim rules — `QUESTIONING_THE_FOUNDATIONS.md` §B) are **routed to that qualified
professional**, not resolved in-house. Building continues; distribution does not widen.

## What this means operationally

- **Access stays invite-shaped.** There is no self-serve registration; accounts are created only via
  admin approval of an access request (the existing flow). The public access-request form stays up
  but is strictly rate-limited and alias-deduplicated (see the 2026-07-18 security hardening), and
  approval is a deliberate owner action.
- **The SEBI gate binds exactly as the plan wrote it**: it blocks *broadening the user base*, not
  building. All product stages (0–6) are built; nothing about this decision pauses engineering.
- **Compliance copy discipline continues** — research/decision-support framing, no performance
  promises, the paper book always labeled a reference — because inner-circle users are still real
  people acting on real capital, and because the qualified professional will review exactly this
  surface.
- **Solo-operator context** (memory: the owner is the only live-model user today) extends to: the
  inner circle are known individuals the owner personally admits, each self-reporting their own
  executions on their own broker (ADR 0011).

## Why

- The in-sample program is closed and the forward wall is the only certifier — the honest offer
  today is a *discipline harness around a paper-certified-pending model*, which is precisely what a
  compliance professional should see before anyone else does.
- Broadening before the SEBI classification is resolved risks the product being read as investment
  advice to clients. Keeping distribution to a reviewing professional + a hand-picked circle keeps
  the question academic while it is answered properly.

## Reversal condition

A new ADR, after (a) the qualified professional's review lands and (b) the owner decides the
forward-wall evidence justifies a wider offering.
