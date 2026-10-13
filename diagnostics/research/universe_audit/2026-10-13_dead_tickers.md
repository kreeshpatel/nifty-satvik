# Universe audit, 2026-10-13: dead and truncated tickers

**Class:** MEASUREMENT (data audit). No screen, no trial, nothing changed. Prompted by HEG: the vendor
truncated its history and the weekly rebuild erased an open trade (2026-10-03).

## Sweep

All 500 names of `build_universe("current")` fetched from Yahoo (weekly bars, `period="max"`) on
2026-10-13:

| name | Yahoo today | pinned research cache | `corrected_universe()` (record path) | substrate trades |
|---|---|---|---|---|
| TATAMOTORS | nothing | absent | 2017-01-02..2025-09-30 via alias → TMPV (valid to the demerger) | 0 |
| LTIM | nothing | absent | 2022-12-05..2026-02-26 (backfill) | 0 |
| PEL | nothing | absent | 2017-01-02..2025-09-22 (backfill) | 0 |
| SWANENERGY | nothing | absent | 2017-01-02..2025-09-03 (backfill) | 0 |
| GSPL | 1 bar (2026-05-11) | absent | 2017-01-02..2026-03-30 (backfill) | 0 |
| GUJGASLTD | nothing | 2017-01-02..2026-06-29 | same | 10 |
| JBCHEPHARM | 1 bar (2026-07-16) | 2017-01-02..2026-06-29 | same | 14 |
| HEG | from 2026-07-13 only | 2017-01-02..2026-06-29 | same | 15 |

Five further names are genuinely young listings with 94–99 weeks of history (IGIL, IKS, VMM, SAILIFE,
NTPCGREEN): enough for the 44-week SMA, not a defect.

## Reading

- **The research record is sound for these names.** The record path reads the pinned cache plus the
  backfill and the alias map, and covers every name to its delisting, rename or demerger. No historical
  trade is missing or mispriced on their account.
- **The live scan path loses 8 of 500 names (1.6%) every week.** It downloads fresh from Yahoo for the
  carried `current` universe snapshot, so a renamed, merged or delisted symbol silently returns nothing,
  and a demerged one (HEG) returns a stub. Its successor tickers (e.g. TMPV and the CV entity for Tata
  Motors) are not in the live universe at all.
- **No open trade is exposed.** None of the eight is held or ACTIVE; if one were, the history guard
  (#132) now halts the scan instead of erasing it.

## The underlying issue, and the decision it needs

The live universe is a **carried snapshot**, not a point-in-time constituent list, so it drifts as the
index rebalances (March and September) and as symbols change. The dead tickers are the visible part;
missing new entrants are the invisible part. A refresh is a **data change to the live universe**: it
needs a PIT constituent source, the same coverage audit as any data layer, and an owner decision at a
review. Not done here.

Cheap interim option, also an owner decision: map the known successors (TATAMOTORS → TMPV, …) in the
live path, the way the record path's alias map already does.
