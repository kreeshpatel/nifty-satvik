# ADR-0017 — The live scan downloads current index members, not a stale snapshot

**Date:** 2026-10-13 · **Status:** ACCEPTED · **Decider:** owner
**Class:** live configuration (universe). Zero trials, zero screens. Standing counts unchanged.

## Context

The live weekly scan downloaded `build_universe("current")`: the carried `NIFTY_500` snapshot. A sweep
on 2026-10-13 (`diagnostics/research/universe_audit/2026-10-13_dead_tickers.md`) found 7 symbols the
vendor no longer serves and HEG truncated. Following up, the PIT membership file
(`data/nifty500_membership.csv`) already records the index changes the snapshot missed:

- **48 current members were never scanned**, including every successor of a dead symbol: TMPV and TMCV
  (Tata Motors demerger), LTM (LTIMindtree rename), PIRAMALFIN (Piramal merger), SWANCORP (Swan rename),
  plus 43 later entrants.
- **48 ex-members were still downloaded.** Membership already gated Grade-A eligibility on the live
  path, so these never signalled. They only cost download time.

The record path (`corrected_universe()` plus PIT membership) was never affected.

## Decision

The live scan downloads `build_universe("union")`: the snapshot union current PIT members. This mode
already existed (the AUD-007 fix) and is not new code. Membership continues to decide eligibility.

## Mid-quarter

The forward-wall pre-registration's §9 says the period between review dates is for monitoring and
logging only, with no config changes. This is a config change made between dates, by explicit owner
decision on 2026-10-13, after the alternative (wait for the 2027-01-01 review) was put to the owner.
It is recorded here and in `research/config_CHANGELOG.md` rather than as an edit to the pre-registration
itself, which is amended only at a review.

What it does to the forward record, stated now: from the 2026-10-17 scan, cards can include names that
were previously invisible. Any comparison of forward results across this date must note it. Thresholds
and rules are unchanged.

## Consequences

- No backtest number, golden master or historical record moves.
- New entrants become eligible only once they have enough history for the 44-week SMA. Several are
  recent listings and will be ineligible for months.
- The history-truncation guard (#132) covers any new name the moment it becomes an open trade.
- Dead symbols with no successor in the membership file (GUJGASLTD, GSPL, JBCHEPHARM) remain a known
  gap; GSPL and JBCHEPHARM are still listed as members while the vendor serves one bar.
