# ADR-0007 — Add after-tax Calmar to the promotion bar; adopt FY loss-carry-forward accounting; decline the ATR-trail cfg adoption

**Status:** Proposed (owner sign-off required — this changes the promotion bar, a governance artifact)
**Date:** 2026-07-02
**Deciders:** Owner (pending)
**Related:** `research/overlay_registry.md` (promotion bar), `skills/sell-replace-logic` / `skills/research-log` (bar text), `forward/prereg.md` §6 (forward promotion), finding 0010 (0076 ATR-trail, UNDERPOWERED), `nq/runner/research._after_tax_cagr`, `scripts/diag_tax_carryforward.py`.

---

## Context

The promotion bar certifies on **pre-tax ΔSharpe + DSR**. For a book whose every hold is < 12 months
(→ all gains taxed at 20% STCG), that is the wrong objective: an overlay that trades less (lower tax
drag) and improves the *after-tax* shape is undervalued, and the certified metric diverges from what a
fee-paying client actually keeps. The forward-wall promotion rule (`forward/prereg.md` §6) already
judges shadows on **after-tax Calmar AND Sortino** — so the in-sample bar and the forward bar currently
disagree on the objective.

A "Tier-1 mechanical wins" plan proposed three items: (1) restate the gate to after-tax Calmar, (2) wire
tax-loss harvesting, (3) adopt the 0076 walk-forward ATR-trail "for its deterministic turnover/tax
benefit." Applying the program's **reproduce-before-trust** discipline before adopting:

- **The deterministic tax win is small.** `scripts/diag_tax_carryforward.py` (on the pinned trade log)
  sizes proper **FY + STCL carry-forward** accounting against the current **per-calendar-year,
  no-carry-forward** approximation at **+0.35pp after-tax CAGR** (after-tax 13.35% → 13.70%; ₹0.8L of
  tax saved over 8.4y). It is small *because* a < 63-day-hold book rarely straddles FY boundaries — the
  losing FYs (2017/18/19/22/24) carried forward to offset the winners is the entire lever.
- **The ATR-trail's after-tax uplift is NOT deterministic.** 0076 showed the after-tax jump (→ ~16.3%)
  came *with* the return improvement whose ΔSharpe CI is `[−0.13, +0.40]` — **UNDERPOWERED**. The truly
  mechanical part (transaction-cost saving from −38% turnover) is a few bps/yr; the headline after-tax
  number is entangled with the uncertifiable return edge. "Adopt it for the tax win" is the return bet
  wearing a tax banner — the exact trap the program's discipline exists to prevent.

## Decision (proposed)

1. **Add after-tax Calmar as an explicit promotion-bar criterion** — computed on **FY-based STCG (20%)
   with STCL carry-forward** — alongside the existing gates (ΔSharpe CI, DSR, ΔCalmar, 2022-26 sub-period,
   fold-pass, turnover, mechanism). This is an **addition, not a relaxation**: it aligns the in-sample bar
   with the forward-wall §6 objective. No existing gate is loosened.

2. **Adopt the FY + STCL carry-forward tax model** as the standard after-tax accounting, replacing the
   per-calendar-year/no-carry-forward approximation in `_after_tax_cagr` (a measurement-correctness fix:
   +0.35pp, correct FY boundary + loss set-off; does not touch gross or the golden master).

3. **Decline** promoting the 0076 ATR-trail into the frozen cfg. Its after-tax uplift is the
   *uncertifiable* return edge, not a deterministic low-regret win. Its correct home is the **forward wall
   as a watched book** (like veto-0.1) — but the pre-reg's **two-shadow cap** (base / veto-0.1 /
   drift-degross) is full, so it either waits or displaces a shadow via a recorded §7 swap. It does **not**
   enter the cfg on an in-sample basis.

4. **Tax-loss harvesting** is adopted only as the correct accounting (item 2), not as active
   infrastructure: the deterministic benefit is ~+0.35pp for this hold-length, a rounding-level lever that
   does not justify a harvesting engine. (No wash-sale rule in India, so the accounting captures the
   available set-off already.)

## Consequences

- The certified objective matches the tax reality and the forward-wall §6 bar — future overlays (and the
  forward promotion of veto-0.1) are judged on the same after-tax Calmar. No prior verdict flips: the
  killed overlays fail the pre-tax gates too; adding a criterion cannot rescue them.
- **Honest sizing, client-facing:** the deterministic Tier-1 win is **~+0.35pp after-tax** (accounting
  correction) plus objective-correctness — **not** the ~15–16% the plan implied. That larger figure was
  the ATR-trail's uncertifiable return edge; the net client number stays **~12% net / lumpy / ~−39% DD**.
- Implementation is a measurement + governance change only: no strategy-engine behaviour change, golden
  master untouched. Item 2 edits `_after_tax_cagr` (recompute after-tax across the registry ~+0.35pp — a
  one-time restatement, flagged when it lands).

## Alternatives considered

- **Adopt the ATR-trail into the cfg for the "low-regret tax benefit."** Rejected: the tax part is +0.35pp
  and separable; the headline after-tax uplift is the uncertifiable return bet. Adopting the rule *is*
  taking that bet. The forward wall is its honest test.
- **After-tax *Sharpe* instead of Calmar.** Rejected: tax is a per-FY event, so a daily after-tax Sharpe
  is not cleanly defined; after-tax Calmar (CAGR/MaxDD) is path-level and clean.
- **Build active tax-loss-harvesting infrastructure.** Rejected for this book: +0.35pp does not justify it;
  the accounting correction captures the available set-off.

## Cross-references

| Reference | What it specifies |
|---|---|
| `scripts/diag_tax_carryforward.py` | Reproduces the +0.35pp FY-carry-forward win (the basis for this ADR) |
| `research/findings/0010-atr-scaled-trailing-exit.md` | 0076 ATR-trail = UNDERPOWERED; the return edge declined here |
| `forward/prereg.md` §6 | Forward promotion already on after-tax Calmar + Sortino — this aligns the in-sample bar |
| `nq/runner/research._after_tax_cagr` | The approximation this ADR proposes to correct (item 2) |
| `research/overlay_registry.md` | The promotion bar the after-tax-Calmar criterion is added to |
