# ADR-0015 — Build the intraday store without the delisted-name probe

**Date:** 2026-08-10 · **Status:** ACCEPTED · **Decider:** owner
**Class:** governance. Zero trials, zero screens. Counts unchanged: screens 19 · sealed opens 1 ·
n_trials 2.

## Context

The elected direction out of the resolution ceiling is an intraday bar store — the only route that
produces a genuinely new sample rather than re-spending the 2017-2026 daily panel, where n_eff = 37
independent 63-day windows caps the dSharpe half-width at ±0.59 permanently.

`diagnostics/research/intraday_feasibility.md` recommended a gate before building: probe five
known-delisted F&O names (DHFL, JETAIRWAYS, ALBK, LAKSHVILAS, INFRATEL) for intraday availability,
because Kite's instrument dump lists *currently tradable* instruments. If delisted names are absent,
a Kite-sourced store is survivor-only by construction. `pipelines/diagnostics/probe_kite_intraday_survivorship.py`
was written for this and needs owner credentials to run.

The concern was put with the strongest evidence available, and the owner has decided against it.

## Decision

**Build the store. Do not run the delisted-name probe first. Treat Kite's delisted coverage, whatever
it turns out to be, as immaterial for this project.**

## Reasoning

1. **The bias mechanism is holding-period-scaled, and this book is the short end.** Finding 0025
   measured that survivorship bias scales with holding period. That is precisely why the corrected
   universe cost the *swing* book so much — a book that holds a trend for months rides a delisting
   name all the way down — while the long-horizon book, measured on the same window, did not move at
   all. An intraday book holds for hours. The mechanism that produced the swing damage is
   structurally weaker at this horizon, and the programme's own finding is what says so.

2. **The absolute count is small.** ~15-20 names over the era, against a universe scoped to F&O
   membership. The owner's judgement is that the effort of gating the project on them is not
   proportionate to the expected distortion at this horizon.

3. **The gate was advisory, not a law.** No standing law requires a survivorship probe before
   building a data store. `skills/verdict-machine` Gate 1 requires a coverage/PIT audit before a
   *screen* is run on a stream — which is preserved below, and is a different requirement.

## What this decision does NOT waive

Recorded explicitly so the scope of the waiver cannot drift:

- **Gate 1 still applies before any screen or trial** on intraday data: coverage by year, symbol
  linkage to our universe, PIT legality (truncation-proven), and seam integrity at vendor-era joins.
  The waiver is of the *survivorship* leg only, and only as a build-gate.
- **The coverage audit remains the FIRST deliverable of the build, not the last.** Whatever the
  delisted coverage turns out to be, it gets *measured and published* as a property of the store —
  it simply no longer blocks starting.
- **Any result computed on this store must state its survivorship status** in the readout, the same
  way every number here states its trial count. A store known to be survivor-biased can still carry
  research; a store *silently* survivor-biased cannot.

## The falsifier

This decision is wrong if the measured coverage audit shows delisted-name absence is **not** a small,
short-horizon-immaterial effect — concretely, if the store's delisted tail is missing in a way that
correlates with outcome at intraday horizons. The audit above will produce that number without any
extra work. If it fires, this ADR is revisited; it is not a permanent finding that survivorship does
not matter, it is a decision that it does not gate the build.

## Consequences

- The store is built against Kite with whatever history it serves.
- `probe_kite_intraday_survivorship.py` is retained, unrun. It is superseded as a *gate* and becomes
  one input to the coverage audit, which the owner may run at any time.
- The evidence that motivated the concern stays on the record and is not deleted:
  `diagnostics/research/reanchor_smoke_2026-08-10.md` measured −0.225 Sharpe / −3.69pp CAGR /
  −6.0pp MaxDD on the swing book from +104 recovered names over 2019-21 (smoke window, not the
  record). That number is about a months-horizon book and is cited here as the reason the question
  was raised, not as a prediction for intraday.

## References

- `diagnostics/research/intraday_feasibility.md` — the feasibility work and the probe recommendation
- `pipelines/diagnostics/probe_kite_intraday_survivorship.py` — retained, unrun
- `diagnostics/research/reanchor_smoke_2026-08-10.md` — the swing-book measurement
- `research/findings/0025-*` — bias scales with holding period
- `skills/verdict-machine` Gate 1 — the audit that is preserved
