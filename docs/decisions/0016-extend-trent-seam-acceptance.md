# ADR-0016 — Extend the TRENT seam acceptance until the seam leaves the window

**Date:** 2026-10-13 · **Status:** ACCEPTED · **Decider:** owner · **Extends:** ADR-0013
**Class:** governance. Zero trials, zero screens, no sealed open. No bar, threshold or config value changes.

## Context

ADR-0013 accepted one vendor-served adjustment seam (TRENT, 2026-01-01, bonus 1:2) as live-affecting
until the 2026-10-01 review. Its acceptance was dated so that it would expire on its own. It did: the
2026-10-03 scan (data as of 2026-10-01) passed, and the 2026-10-10 scan (as of 2026-10-09) halted in
`assert_no_live_escalation`. That was the design working.

The scope that justified ADR-0013 still holds. TRENT is the only seam inside the 44-week window, the
book does not hold it, and the defect suppresses a candidate rather than mispricing a position. The
seam leaves the window after as_of 2026-11-05. Leaving the scan halted until then would lose three more
Saturday weeks of forward record (2026-10-17, 10-24, 10-31) on top of the 2026-10-10 week already lost,
and a missed week of forward evidence cannot be backfilled.

## Decision

Re-accept the same seam, on the same scope, until **2026-11-05**, the last as_of on which it is
inside the window. `owner_status = "ACCEPTED_UNTIL_2026-11-05 (ADR-0016, extends ADR-0013)"`.

## What does not change

- Both pre-committed escalation triggers stay armed: any additional live-affecting seam, and any seam
  on a held name. If the book buys TRENT, the scan halts.
- No repair is applied. The seam repair, the demerger convention and the survivorship re-anchor are
  still decided together.
- The acceptance still expires by date. It is pinned to end exactly when the seam leaves the window,
  so it can neither halt the scan early nor outlive its reason
  (`tests/test_adjustment_guard.py::TestADR0013ExpiryGap`).

## Cost

One more month on a known-wrong input for one non-held name, the same cost ADR-0013 priced. The
2026-10-10 week is lost and is recorded as lost, not reconstructed.
