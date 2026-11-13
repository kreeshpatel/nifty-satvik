# Product wiring map — what the book publishes, and who reads it

**Generated — do not edit by hand.** `python scripts/gen_wiring_map.py`

This is the product-surface twin of [`skills/repo-map`](../skills/repo-map/SKILL.md),
which maps the engine's values. This one maps the path a value travels from the weekly
artifacts, through the API, to the page that prints it.

It proves REFERENCE, not correctness: a tick means the file mentions the field, not that
it uses the right one. Read the hazards section for the pairs where that distinction has
already cost us.

A field with no consumer is a decision the model made and the product withheld. That is
not automatically a bug — some fields are engine-internal — but each one should be a
choice somebody made, not an oversight nobody noticed.

## `results/signals_today_weekly.json`

Written by the weekly scanner (Saturday).

| field | on cards | api | api-exec | recon | cards lib | This week | Research | Dashboard | Portfolio | Paper book | Stock | History | read by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `actionability` | HIT_STOP,HIT_TARGET | ✓ | · | ✓ | · | ✓ | · | · | · | · | · | · | **3** |
| `band_is_wide` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `band_width_pct` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `body_ratio` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `bought_date` | ACTIVE,HIT_STOP,HIT_TARGET | ✓ | · | ✓ | ✓ | ✓ | · | · | · | · | · | · | **4** |
| `buy_window` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `buy_window_until` | FRESH | · | · | · | ✓ | · | · | ✓ | · | · | · | · | **2** |
| `buy_zone_high` | FRESH | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `buy_zone_low` | FRESH | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `close` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | **9** |
| `corporate_actions` | ACTIVE | · | ✓ | · | ✓ | · | · | · | · | ✓ | · | · | **3** |
| `crs_rank` | FRESH | · | · | · | · | · | · | ✓ | · | · | · | · | **1** |
| `current_price` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | · | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | **6** |
| `entry` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **10** |
| `entry_high` | FRESH | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `entry_low` | FRESH | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `entry_week_open` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `exit_plan` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `exit_stage` | ACTIVE,HIT_STOP,HIT_TARGET | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `ext_cap_pct` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `ext_pct_over_sma44` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `fill_price` | ACTIVE,HIT_STOP,HIT_TARGET | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `grade` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | · | · | · | · | · | · | ✓ | · | · | · | · | **1** |
| `hold_days` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | · | · | · | · | · | ✓ | · | · | ✓ | · | · | **2** |
| `no_chase_above` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `nq_position_id` | ACTIVE,HIT_STOP,HIT_TARGET | · | · | ✓ | · | · | · | · | · | · | · | · | **1** |
| `pattern` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | · | ✓ | · | · | · | · | · | · | · | · | · | **1** |
| `qty` | ACTIVE,HIT_STOP,HIT_TARGET | ✓ | ✓ | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **9** |
| `record_would_skip_as_extended` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `signal_conviction` | FRESH | · | · | · | · | · | · | ✓ | · | · | · | · | **1** |
| `signal_date` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | · | · | ✓ | ✓ | ✓ | ✓ | · | · | ✓ | ✓ | · | **6** |
| `status` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | · | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **9** |
| `stop` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **11** |
| `stop_week_low` | FRESH | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `target` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **11** |
| `ticker` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **10** |
| `tier` | ACTIVE,FRESH,HIT_STOP,HIT_TARGET | ✓ | · | · | · | ✓ | · | · | · | · | · | · | **2** |
| `why` | HIT_STOP,HIT_TARGET | ✓ | · | · | · | · | · | · | · | · | · | · | **1** |

**Unread and UNDECLARED (12):** `band_is_wide`, `band_width_pct`, `body_ratio`, `buy_window`, `entry_week_open`, `exit_stage`, `ext_cap_pct`, `ext_pct_over_sma44`, `fill_price`, `no_chase_above`, `record_would_skip_as_extended`, `stop_week_low`.

Each is a value the model computed and no surface shows, with no reason on
record. Wire it, or add it to `INTENTIONALLY_UNREAD` in the generator with the
reason. `tests/test_wiring_map.py` fails while this list is non-empty.

## `results/weekly_monitor.json`

Written by the daily monitor (weekdays 16:15 IST).

| field | on cards | api | api-exec | recon | cards lib | This week | Research | Dashboard | Portfolio | Paper book | Stock | History | read by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `as_of` | buy,hold,missed_exits | ✓ | · | ✓ | · | · | · | · | · | · | ✓ | · | **3** |
| `buy_window_open` | buy | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `buy_window_until` | buy | · | · | · | ✓ | · | · | ✓ | · | · | · | · | **2** |
| `cause` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | · | · | · | **2** |
| `current_price` | buy,hold | ✓ | · | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | **6** |
| `dist_to_stop_pct` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `dist_to_target_pct` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `do` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | ✓ | · | · | **3** |
| `drift_pct` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | · | · | · | **2** |
| `due_date` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | · | · | · | **2** |
| `due_price` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | · | · | · | **2** |
| `entry` | hold,missed_exits | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **10** |
| `entry_high` | buy | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `entry_low` | buy | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `expired` | buy | ✓ | · | · | ✓ | · | · | · | · | ✓ | · | · | **3** |
| `filled_on` | buy | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `filled_price` | buy | · | · | · | ✓ | · | · | · | · | · | · | · | **1** |
| `filled_today` | buy | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `frozen_price` | buy,hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `implied_trail_sma20` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `kind` | buy,hold | · | · | · | ✓ | · | · | ✓ | · | · | ✓ | · | **3** |
| `last_close` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | · | · | · | **2** |
| `plan_tags` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `pnl_pct` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `r_at_exit` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | · | · | · | **2** |
| `r_multiple` | hold | · | · | · | · | · | ✓ | · | · | · | · | ✓ | **2** |
| `reason` | missed_exits | ✓ | · | ✓ | · | · | · | ✓ | · | ✓ | · | ✓ | **5** |
| `severity` | missed_exits | · | · | ✓ | · | ✓ | · | · | · | ✓ | · | · | **3** |
| `signal_date` | missed_exits | · | · | ✓ | ✓ | ✓ | ✓ | · | · | ✓ | ✓ | · | **6** |
| `signal_id` | missed_exits | ✓ | ✓ | ✓ | · | ✓ | · | ✓ | ✓ | ✓ | · | · | **7** |
| `sma20` | buy,hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `source` | missed_exits | ✓ | ✓ | · | · | · | · | · | · | ✓ | · | · | **3** |
| `stop` | hold,missed_exits | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **11** |
| `stop_breached` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `target` | hold | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **11** |
| `target_reached` | hold | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `ticker` | buy,hold,missed_exits | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **10** |
| `today_open` | buy | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `tranches` | hold | · | · | · | · | ✓ | · | · | · | · | · | · | **1** |
| `window_basis` | buy | · | · | · | · | · | · | · | · | · | · | · | **0** |
| `window_filled` | buy | · | · | · | · | · | · | · | · | · | · | · | **0** |

**Unread by decision (5)**

- `implied_trail_sma20` — The producer marks it NOT an active level — the ratchet trail only moves at the weekly close. Showing a level the engine will not act on until Saturday invites acting on it.
- `plan_tags` — A second, LOSSIER phrasing of `exit_plan.tranches[].do`, which CasePanel already prints verbatim. The tag reads 'Hold 20% runner to the 44w-SMA 897.65'; the `do` reads 'Exit only on a weekly CLOSE below the 44-week SMA'. Dropping the weekly-close condition changes the rule from a close to a touch. Two phrasings of one instruction, and only one of them was backtested.
- `sma20` — Raw input to implied_trail_sma20 above; carries no instruction of its own.
- `today_open` — Engine input to window_filled. The reader-facing fact it supports — 'Filled Mon, 24 Aug at 1,298.00' — is already on the row, priced and dated.
- `window_basis` — Provenance for `buy_window_open`, added with B-4 (2026-09-28): the date the window was compared against, the feed's own as-of, and whether the feed is behind. Deliberately not a surface field — a reader does not act on it, and printing a second date beside the window invites reading the FEED's date as the window's. It exists so that a window reading 'open' against today while the data is days stale is diagnosable from the artifact rather than from the operator's memory, which is the failure B-4 fixed.

**Unread and UNDECLARED (10):** `buy_window_open`, `dist_to_stop_pct`, `dist_to_target_pct`, `filled_on`, `filled_today`, `frozen_price`, `pnl_pct`, `stop_breached`, `target_reached`, `window_filled`.

Each is a value the model computed and no surface shows, with no reason on
record. Wire it, or add it to `INTENTIONALLY_UNREAD` in the generator with the
reason. `tests/test_wiring_map.py` fails while this list is non-empty.

## Alias hazards

Pairs where both fields exist, both are plausible, and picking the wrong one is
silent. Every one of these has been read wrongly at least once.

| prefer | easily confused with | why it matters | wrong one still referenced by |
|---|---|---|---|
| `buy_zone_low` | `entry_low` | entry_low is the signal WEEK's candle low, which IS the stop. The record buys inside buy_zone_*, never down to the stop. | This week |
| `buy_zone_high` | `entry_high` | entry_high happens to equal buy_zone_high on most cards, which is exactly why reading the wrong one goes unnoticed until a card where it does not. | This week |
| `window_filled` | `filled_today` | filled_today is recomputed against the LAST bar every run and means 'can I buy at today's open'. window_filled is whether the signal ever triggered. | — none |

## Calendar-date fields

These carry a day with no time and no zone. In JavaScript, `new Date('2026-08-28')`
is UTC midnight, so formatting it in a timezone behind UTC renders the previous day.
Parse them as LOCAL dates (`parseCalendarDate` in SignalsV3.jsx), never with a bare
`new Date(str)`.

| field | referenced by |
|---|---|
| `as_of` | api, recon, Stock |
| `bought_date` | api, recon, cards lib, This week |
| `buy_window_until` | cards lib, Dashboard |
| `due_date` | recon, This week |
| `filled_on` | — none |
| `signal_date` | recon, cards lib, This week, Research, Paper book, Stock |

## How to use this

1. Adding a field to the weekly envelope? Regenerate and check it has a consumer.
2. Reading a field on a page? Check the hazards table first — the plausible name
   is not always the right one.
3. Reviewing a surface that 'looks thin'? Scan the unread lists. That is the
   model's own reasoning, already computed, sitting unused.
4. Publishing a NEW field? It lands in 'unread and undeclared' and fails the test
   until it is wired or declared. That is deliberate — the alternative is a list
   that grows quietly.
