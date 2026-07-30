# Pre-registration 0120 — Earnings-calendar label screen (census #2; the S5 territory)

**Status:** PRE-REGISTERED (before any feature-label join). **Date:** 2026-07-27. **Trial accounting:**
MEASUREMENT — 0 trials; n_trials stays 138. Screen-ledger row #9 (running count 9; sealed opens: 1).
Census basis: `data_census_20260727.md` candidate #2, owner-signed. Registry: **S5 is OPEN** ("earnings
event de-risking — requires a PIT earnings calendar we do not yet have") — this screen closes it either
way. The activation-bound LAW binds any downstream usage ask.

## Data & the two-layer PIT (encoded in nq/data/earnings.py; truncation-proven 4/4)
NSE board-meetings API, month-windowed 2019→present. Native fields carry both layers:
**ann_ts** (broadcast — when the meeting became public; the FEATURE layer: a decision at t may use only
events with ann_ts ≤ t) and **event_date** (the meeting itself; the LABEL layer: grading may use true
dates announcement-agnostic). Results-purpose filter; earliest announcement per (symbol, event) governs.

## Audit gate (STOP if it fails)
1. Per-year coverage: fraction of substrate trades whose symbol has ≥1 results event that year;
   delisted-name presence. 2. Announcement→event lag distribution: median must be positive-days; a mass
   at ≤0 means the PIT layer is broken, not that the market is fast. 3. Spot-checks of raw records.
4. Invalidation clause: coverage holes correlated with outcomes → screen invalid, report and stop.

## Frozen questions & features
- **Q1 (label-side exposure):** trades holding THROUGH ≥1 true results event vs event-free trades —
  ΔR conditional in ext×CRS cells; and false_touch vs noise_stop event-struck rates.
- **Q2 (feature-side proximity, PIT):** `known_event_within_14cd` — at the SIGNAL-week Friday (the
  decision time), is a results event KNOWN (announced ≤ that Friday) and dated within 14 calendar days
  after the entry-week Monday? (≈ the first 10 holding days; N=14cd FROZEN). Contrast R and cohort
  rates, conditional cells.
- **Q3 (label-side):** among winners, does a true event inside the 21d post-exit window associate with
  exit_too_early (sold before the favorable event)?

## The event-frequency trap (named per the sign-off)
Quarterly events × ~65-trading-day holds ⇒ most trades hold through ≥1 event. Base exposure rates are
reported FIRST; if exposure is near-universal (>90%), exposure cannot discriminate and the screen must
SAY SO for Q1 rather than manufacture a gradient from the residual tail — Q2's proximity contrast (a
minority condition) then carries the screen.

## Pre-committed pass/kill bar (0118 mold)
A contrast SURVIVES iff ≥0.15R-equivalent (or a cohort-rate difference) with a bootstrap 95% CI
excluding zero AND sign in ≥4/6 train years AND surviving ADV-tercile conditioning. Anything less →
**KILL: S5 closes resolved-negative**; census #3 (bulk/block deals) becomes the next owner decision.
On PASS: stop at the owner's door with the mechanism readout + one-paragraph usage sketch that must
state up front how it confronts the deferral-vs-skip territory (0104/0108) AND the activation-bound
law. Train-only; sealed never read; ONE run.

## Named failure modes
1. The 0116 flip precedent (train-clean can invert on any later sealed check).
2. The event-frequency trap (above). 3. Coverage bias: thin small-cap announcement coverage correlated
with outcomes — the audit gate's invalidation clause. 4. 0010-redux analogue: a pass authorizes
nothing beyond the recorded effect.
