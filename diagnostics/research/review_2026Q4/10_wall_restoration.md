# §10 Forward-wall contract restoration — decision page (2026-10-13)

**Class:** governance, owner decision. Zero trials, zero screens. Standing counts: screens 22 · sealed
opens 3 · n_trials 2. **This page deliberately does not quote the three books' relative performance:**
the veto arm's fate is performance-based and belongs to a review, and this decision is only about
whether the wall's logging is enforced.

## The obligation

On 2026-08-08 three forward-wall artifacts were downgraded from `must_update` to
`must_update_if_produced` in `results/output_contracts.json` (job `forward-wall-log`):
`forward_wall.csv`, `forward_wall_start.json`, `paper_portfolio.json` (plus `signals_today.json` and
`scheduler_health.json`, which were conditional already). The note set a date to undo it:

> RESTORE these three to must_update at that review [2026-10-01], whichever way it goes — retire the arm
> and the wall logs two books, or extend the factors and it logs three.

The 2026-10-01 review passed without it. **It is overdue.**

## Why it was downgraded, and why that reason is gone

The veto arm needs the FF-India factor panel. In August the panel ended 2026-06-29 and no workflow built
it, so `_assert_veto_arm_live` correctly refused to log any row and a hard contract would have gone red
every weekday for doing the right thing.

**Since then the arm was funded, not retired.** `cron-forward-wall.yml` now refreshes the price cache,
deepens it, builds the factor panel (`pipelines/build/build_ff_india_factors.py`) and then appends the
row. The log shows it working:

- `results/forward_wall.csv`: **43 rows, 2026-08-12 → 2026-10-13**, all three books populated.
- **37 `ok` rows; on every one the veto arm differs from base**, so the arm is genuinely live, not a copy.
- **6 `gap` rows, 2026-08-24 → 2026-08-31**, written as gaps rather than skipped. Diagnosed 2026-10-13 (below).

## Why the restoration does not need to wait for the veto-arm decision

§7 of the wall pre-registration demotes a shadow only on **forward Sortino over a trailing ≥ 12-month
window**. The wall's first `ok` row is 2026-08-12, so **no demotion can be decided before roughly
2027-08-12**, i.e. the 2027-10-01 review at the earliest. Tying the contract to that decision would leave
the only certifier's log unenforced for another year. The August note anticipated this: restore
"whichever way it goes".

## The options

| | A. Restore now (recommended) | B. Restore at the 2027-01-01 review | C. Leave conditional until the arm is decided |
|---|---|---|---|
| what changes | the three files move back to `must_update` | same, later | nothing |
| a missed day | goes **red** the same day | goes red from January | stays a warning until ~2027-10 |
| risk | a factor-build failure now turns the wall job red (that is the point) | ~11 more weeks of a silent miss being possible | a year of the certifier's log unenforced |
| touches a pre-reg arm | no | no | no |

**Recommendation: A.** The reason for the downgrade no longer exists, the date set for undoing it has
passed, and nothing about the veto arm is decidable in the meantime. A contract change is a reliability
fix to the logger, not a change to any book, threshold or decision rule.

## Caveats the owner should carry, not resolve here

1. **The six gap sessions (2026-08-24 → 08-31) — diagnosed 2026-10-13, already fixed.** The runs on
   08-24..28 concluded green while the wall gained no row: a cache defect stalled it, and nothing checked
   that a row was actually written. Two controls landed on 2026-08-30 (`2fbf30b`, `2f7cbdc`):
   `scripts/assert_wall_advanced.py` turns a run red when the wall does not advance (it fired correctly on
   08-31), and a multi-session catch-up is written as hash-chained `gap` markers instead of reconstructed
   `ok` rows, per the wall pre-registration's section 3 rule 4. The 09-01 run did exactly that, which is
   where the six gaps come from. Every session since has logged `ok` (37 rows to 2026-10-13). With the
   contract restored, a recurrence now trips two independent reds.
2. **HML staleness.** The factor builder carries each name's last available book value forward against
   the live price, so the value factor, and therefore the veto arm's residual ranks, ages as the
   fundamentals scrape ages. The arm logs a real, different book, but its quality as a measurement
   decays until the fundamentals are refreshed. That is a question for the arm's review, not for logging.
3. Restoring the contract adds the wall job to what can go red. That is the intended effect: on
   2026-08-08 the wall's silence was correct; today it would be a defect.

## If A is chosen

One edit to `results/output_contracts.json` (move `forward_wall.csv`, `forward_wall_start.json` and
`paper_portfolio.json` to `must_update`, and date the note), the matching `need` lines in
`cron-forward-wall.yml`, and a test that the three are hard-contracted. No engine, book or rule change.
