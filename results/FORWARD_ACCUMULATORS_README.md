# Forward accumulators — coverage, gaps, and what they can never recover

`results/bulkblock_forward.csv` · `results/ratings_forward.csv` · `results/forward_accum_health.json`

These are **append-only, forward-only** stores for two datasets whose history cannot be bought back:
NSE bulk/block deals (the historical API is behind a bot-wall) and credit-rating filings (the
pre-2023 stream has junk equity linkage). Every row carries the timestamp of the fetch that first
saw it; the dedup key is content, so a re-run adds nothing and re-fetching is always safe.

Producer: `scripts/run_forward_accumulators.py`, wired as a step in the daily monitor workflow
(`.github/workflows/cron-bhanushali-monitor.yml`).

## The dormancy incident (2026-07-29 → 2026-07-30) — recovered, no permanent loss

The accumulators were wired on **2026-07-29**, but their wiring lived on an unmerged research
branch. **GitHub registers workflows only from the default branch**, so the step never ran on
schedule: what looked like a healthy feed was actually the output of manual local runs. The audit
row recording "fired 8/8 with the monitor" was inferred from a committed health file that a human
had produced by hand — see the constitution's Appendix S2 and flag S2-F3.

Merged 2026-07-30 (`a2befea`), then caught up through the front door with one
`workflow_dispatch` of the daily job so the rows arrived via the normal append path with real
timestamps:

| Store | Before | After | Recovered |
|---|---|---|---|
| `bulkblock_forward.csv` | 149 rows | 286 rows | **+137** (all 29-JUL-2026 deals) |
| `ratings_forward.csv` | 88 rows | 93 rows | **+5** |

**Permanent gap: none.** Coverage after catch-up is continuous — bulk/block holds both 28-JUL
(146 rows, from the pre-merge local run) and 29-JUL (138 rows, recovered), and the ratings window
spans 21-JUL → 30-JUL unbroken. The dormancy lasted about one day, which was shorter than both
sources' rolling windows, so the front-door catch-up reached everything.

**That outcome was luck of timing, and the near-miss is the point.** `bulk.csv` and `block.csv` are
rolling current-file endpoints: they serve recent deals only, and there is no working historical
API behind them — which is the entire reason a forward accumulator exists. Had the dormancy
outlasted that rolling window, those trading days would have been **unrecoverable by any means**.
A collector that is silently not running loses exactly the data it was built to preserve, and it
loses it permanently.

## What these stores can never recover

- **Anything before inception (2026-07-29).** Forward-only by construction. Bulk/block history is
  not purchasable through the blocked API; the ratings stream's pre-2023 history has no usable
  equity linkage (finding 0122, a coverage-kill).
- **Any trading day that falls outside the source's rolling window while the collector is down.**
  For bulk/block that window is short. Treat a missed run as urgent, not cosmetic.

## Operating rules

1. **Never point a probe or a test at the live files.** The health check
   (`scripts/diag_accumulator_health.py`) copies them to a scratch directory, probes the copies, and
   asserts the live bytes are unchanged. It once wrote a literal `PROBE` sentinel over real fetch
   timestamps; the append path now also refuses any `fetch_ts` that does not parse as a datetime
   (`_validate_fetch_ts`), so the record is unwritable with junk regardless of caller. Both layers
   are pinned by `tests/test_forward_accumulator_guard.py`.
2. **Firing evidence is the Actions run log, never a committed artifact.** A fresh-looking file
   proves nothing when a human can produce the same file by hand — that is precisely how the
   dormancy went unnoticed.
3. **Do not loosen the idempotency tolerance to silence a red health check.** A large re-fetch
   delta means the feed is behind; that is a signal to fix collection, not a threshold to relax.
4. **Catch up through the front door.** Dispatch the real workflow rather than running the collector
   by hand, so rows land with genuine timestamps through the same code path as every other row.
