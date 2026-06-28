# ADR-0004 — Hold real capital until the conviction layer is validated

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Owner  
**Related:** ADR-0001 (frozen base), ADR-0002 (vol-target overlay)  
**Roadmap stages:** C (conviction model), D (hybrid layers), E (paper-revalidate)

---

## Context

The operational goal is not to ship the frozen base as quickly as possible. It is to deliver a
**conviction-layered model** to ~10 paying users — a model where per-trade conviction within the
top-15 drives sizing, exit, and risk, and where every layer has been independently validated by the
same statistical harness that validated the base. Quality at launch matters more than speed to
launch.

### What "conviction-within-top-15" means

The frozen base selects names purely by `sma200_slope_63` cross-sectional rank. All 15 held names
are treated identically: same sizing formula, same exit thresholds, same risk exposure. A
conviction layer does not change the selection (the top-15 stays the top-15); it operates on the
relative ordering and quality signal *within* those 15 names to modulate:

- **Sizing** — higher-conviction names receive larger allocations (quintile-scaled, mean-preserved,
  15% position cap unchanged);
- **Exit** — tighter stops and narrower trailing for lower-conviction names; wider for higher;
- **Risk** — soft sector/correlation caps triggered by conviction distribution, not hard screens.

This is the intended "conviction-within-top-15" scope. It is not a new signal, not a regime gate,
and not an ML model layered on top of a rules-based signal.

### The current state of the paper book

The paper book is live on the frozen base (ADR-0001) with the vol-target overlay (ADR-0002,
pre-reg 0068 V2: target 0.15 / vol-window 42 / vol-floor 0.40). The paper-gate pre-commitment
(≥ 30 trades / ~2 months reviewed before any real rupee) was set against the current base. If
the corrected universe triggers a cfg re-derivation (Stage B, §decision below), the paper-gate
clock resets against the new baseline.

### The path from here

Stages C–E of the destination-ordered roadmap must complete before real capital:

- **Stage A** — reproduce the headline on the corrected 682-name universe via the cloud
  `cpcv-research.yml` run; persist `equity_curve` to `baseline_v0.json`; confirm ≤1pp of the
  30.3% CAGR / 1.15 Sharpe frozen-cfg headline. Gate: harness reproduces the headline AND
  the §11 KILLs hold.
- **Stage B** — correct the universe (split-vs-demerger root-CA cleaner; widen to
  `current_members ∪ config.NIFTY_500`; PIT fundamentals for the 48 new entrants; financials
  capital-adequacy policy for banks/NBFCs); re-derive the frozen cfg on the widened universe;
  regenerate the golden master; persist `baseline_v1.json`; restart the paper book. Gate:
  corrected-universe walk-forward holds the edge; ADR-0003 issued for the universe change.
- **Stage C** — build `src/research/conviction.py` with PIT-safe features; validate via the
  harness (conviction-top-15 arm vs rank-only base on the corrected universe); output
  `conviction_score` / quintile appended to `signals_today.json`. Model form = z-score blend,
  logistic, or ranked composite — NO uninspectable ML.
- **Stage D** — conviction-driven hybrid layers: sizing, exit, risk, sell-replace (S-series /
  R-series). Each layer gated by the promotion bar independently.
- **Stage E** — paper-revalidate the full conviction-layered system: ≥ 30 trades / ~2 months;
  kill-criteria switched from observe to enforce. This is the pre-committed real-capital gate.

---

## Decision

**Hold real capital until Stage E is cleared.** The frozen base does NOT go live on its own.

The path to the first real rupee runs through Stages A → B → C → D → E in sequence, each ending
with an owner review before the next stage starts.

Additionally:

**Model evolution scope is conviction-within-top-15 only for the near term.** Two programmes are
explicitly deferred off the critical path:

1. **Tail hedge / options-carry second stream** — a defined-risk tail hedge (which §7.1 /
   pre-reg 0070 showed is the mechanism needed to bring max DD below ~−30%) is deferred.
   The vol-target overlay (ADR-0002) is the only DD-reduction tool active in the paper book. The
   tail-hedge programme restarts after the conviction layer is live and producing a paper track
   record.
2. **Vol-carry "second orthogonal stream"** — harvesting IV > realised volatility as a structurally
   independent return stream is deferred. It is a sound research direction but it is not on the
   critical path to serving paying users with the long-horizon strategy; it gets its own charter
   after Stage E.

---

## Consequences

### What this delivers

- **A better model at launch.** Every user-facing signal carries a conviction score that the
  sizing and exit logic can act on. The model is explainable at the per-trade level.
- **A longer path to the first real rupee.** Stages B (corrected universe), C (conviction), D
  (hybrid layers), and E (fresh paper-gate window) must all complete and gate before any real
  capital. That is materially longer than "go live on frozen base, layer later."
- **A stable foundation.** If Stage B moves the headline (corrected/widened universe may produce a
  different, possibly lower, CAGR than 30.3%), we anchor to the honest new number (baseline_v1),
  not the pre-correction result. We do not paper over a changed baseline.

### Honest tradeoffs

1. **Longest path to first rupee.** Foundation re-derivation + conviction + hybrid + fresh ≥30-trade
   paper window all precede live. There is no shortcut through Stages A–E.

2. **The headline may move.** Re-deriving on the corrected/widened universe can give a different
   baseline than 30.3% CAGR / 1.15 Sharpe / −40.1% DD. We accept the honest new number.
   (The frozen-cfg values — stop 3.67× ATR, target 22.52%, trailing activate 4.0% / trail 4.27%,
   min-hold 10, max-hold 63, risk 3.0%, position cap 15%, ADV cap 5%, max 15 slots — are
   unchanged by this reframe; they are only changed by a formal re-derivation in Stage B.)

3. **Paper-gate clock resets at Stage B.** The current paper book runs on the pre-correction base.
   When Stage B produces a new corrected-universe cfg, the paper book restarts from that cfg and
   the ≥30-trade gate clock resets.

4. **Stages C/D may mostly KILL.** The §11 history is a precedent: every "obvious" within-universe
   improvement tested so far has been killed by the honest walk-forward gate. If the conviction
   model cannot clear the promotion bar (ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022–2026 positive,
   fold-pass ≥ 60%, bootstrap CI excludes 0, turnover ≤ +30%, mechanism explainable), then the
   corrected frozen base *is* the shippable product, and decision #1 (hold until conviction) gets
   revisited against the then-available paper track record.

### Promotion bar (applies to every Stage C/D layer)

All seven conditions must hold for PROMOTE-CANDIDATE (from the cross-cutting requirements in
`docs/ROADMAP.md`):

| Condition | Threshold |
|---|---|
| ΔSharpe (post-tax post-cost) | ≥ +0.10 vs. baseline |
| ΔCalmar (post-tax post-cost) | ≥ +0.05 vs. baseline |
| 2022–2026 sub-period ΔCAGR | Positive |
| Walk-forward fold-pass | ≥ 60% of folds |
| Bootstrap 95% CI on ΔSharpe | Excludes 0 |
| Turnover increase | ≤ 30% absolute |
| Mechanism | Explainable in one sentence |

SHADOW if 4–5 hold. KILL otherwise. All three verdicts are first-class outcomes.

---

## Alternatives considered

### A — Go live on the frozen base now; layer conviction later

**Considered; rejected.**

Faster path to first real rupee. But this means ~10 paying users are live on a base that is still
on the wrong universe (W-02: 48 invisible current members; W-04: 62+ financials dropped for a data
reason, not a leverage reason). The conviction layer that the service is being built around is absent.
Launching and then pulling signals for a major research change (Stage B re-derivation) would
undermine trust in a paid service. Quality before speed.

### B — Small real-capital position now, scale on results

**Considered; deferred, not permanently rejected.**

A small live allocation that grows only on demonstrated paper-track results would reduce the time
to first real rupee without betting the full user relationship on an unvalidated layer. The concern
is that paper and live can diverge in ways that aren't obvious until the live book is larger; and
the paper-gate requirement exists precisely to let divergences surface cheaply. If timeline
pressures become acute after Stage B (corrected base in paper), this alternative can be revisited
with a hard position-size cap (e.g. ≤ ₹1L own-capital only, no user exposure) and explicit owner
sign-off.

### C — Defer Stage B (universe correction); conviction-first on the current universe

**Considered; rejected.**

The 48 invisible current members and the financials policy gap are not edge cases — they are the
universe definition the model will trade on. Building a conviction layer on a universe that is
known to be wrong creates a compounding error: the conviction model may be selected for properties
that disappear on the corrected universe, and Stage B then forces re-training anyway. Fix the
foundation, then build on it.

---

## Operating rules derived from this decision

1. **No real capital before Stage E.** This holds even if the paper book looks exceptional. The
   pre-committed gate is ≥ 30 paper trades / ~2 months on the Stage B (corrected) base with
   kill-criteria in enforce mode.

2. **The frozen cfg block is unchanged by this reframe.** `models/long_horizon/config.json → cfg`
   remains the source of record (stop 3.67, target 22.52%, trailing 4.0/4.27, min-hold 10,
   max-hold 63, risk 3.0%, cap 15%, ADV 5%, max-positions 15). Stage B re-derivation may update
   it; no other path does.

3. **Conviction model form is restricted.** No uninspectable ML (LightGBM / neural net / random
   forest). Only z-score blends, logistic regression, or transparent ranked composites — forms
   where the conviction score can be audited at the trade level.

4. **Tail hedge and vol-carry are deferred.** No work begins on either until Stage E is cleared
   and a real-capital paper track record exists. The vol-target overlay (ADR-0002) already active
   in the paper book remains the only DD-reduction tool through Stage E.

5. **If the conviction layer fails to clear the bar after Stage D, revisit decision #1.** The
   corrected frozen base (Stage B result) may then be shippable on its own merits. That decision
   requires a fresh owner review, not automatic promotion.
