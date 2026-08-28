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

| field | on cards | api | api-exec | recon | This week | Research | Dashboard | Portfolio | History | read by |
|---|---|---|---|---|---|---|---|---|---|---|
| `actionability` | HIT_STOP | ✓ | · | ✓ | ✓ | ✓ | · | · | · | **4** |
| `band_is_wide` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `band_width_pct` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `body_ratio` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `bought_date` | ACTIVE,HIT_STOP | ✓ | · | ✓ | ✓ | ✓ | · | · | · | **4** |
| `buy_window` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `buy_window_until` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `buy_zone_high` | FRESH | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `buy_zone_low` | FRESH | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `close` | ACTIVE,FRESH,HIT_STOP | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | · | **6** |
| `crs_rank` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `current_price` | ACTIVE,FRESH,HIT_STOP | ✓ | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | **6** |
| `entry` | ACTIVE,FRESH,HIT_STOP | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **7** |
| `entry_high` | FRESH | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `entry_low` | FRESH | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `entry_week_open` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `exit_plan` | ACTIVE,FRESH,HIT_STOP | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `exit_stage` | ACTIVE,HIT_STOP | · | · | · | · | ✓ | · | · | · | **1** |
| `ext_cap_pct` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `ext_pct_over_sma44` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `fill_price` | ACTIVE,HIT_STOP | · | · | · | · | ✓ | · | · | · | **1** |
| `grade` | ACTIVE,FRESH,HIT_STOP | · | · | · | · | ✓ | ✓ | · | ✓ | **3** |
| `hold_days` | ACTIVE,FRESH,HIT_STOP | · | · | · | · | ✓ | · | ✓ | ✓ | **3** |
| `no_chase_above` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `nq_position_id` | ACTIVE,HIT_STOP | · | · | ✓ | · | ✓ | · | · | · | **2** |
| `pattern` | ACTIVE,FRESH,HIT_STOP | · | ✓ | · | · | ✓ | · | · | · | **2** |
| `qty` | ACTIVE,HIT_STOP | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | · | **6** |
| `record_would_skip_as_extended` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `signal_conviction` | FRESH | · | · | · | · | ✓ | · | · | · | **1** |
| `signal_date` | ACTIVE,FRESH,HIT_STOP | · | · | ✓ | ✓ | ✓ | · | · | ✓ | **4** |
| `status` | ACTIVE,FRESH,HIT_STOP | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **7** |
| `stop` | ACTIVE,FRESH,HIT_STOP | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **8** |
| `stop_week_low` | FRESH | · | · | · | · | · | · | · | · | **0** |
| `target` | ACTIVE,FRESH,HIT_STOP | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **8** |
| `ticker` | ACTIVE,FRESH,HIT_STOP | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **8** |
| `tier` | ACTIVE,FRESH,HIT_STOP | ✓ | · | · | ✓ | ✓ | · | · | · | **3** |
| `why` | HIT_STOP | ✓ | · | · | · | ✓ | · | · | ✓ | **3** |

**Published and read by nothing (1):** `stop_week_low`.

Each is a value the model computed and no surface shows. Decide per field:
surface it, or record why it is engine-internal.

## `results/weekly_monitor.json`

Written by the daily monitor (weekdays 16:15 IST).

| field | on cards | api | api-exec | recon | This week | Research | Dashboard | Portfolio | History | read by |
|---|---|---|---|---|---|---|---|---|---|---|
| `as_of` | buy,hold | ✓ | · | ✓ | · | · | ✓ | · | · | **3** |
| `buy_window_open` | buy | · | · | · | · | ✓ | · | · | · | **1** |
| `buy_window_until` | buy | · | · | · | · | ✓ | · | · | · | **1** |
| `current_price` | buy,hold | ✓ | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | **6** |
| `dist_to_stop_pct` | hold | · | · | · | · | ✓ | · | · | · | **1** |
| `dist_to_target_pct` | hold | · | · | · | · | · | · | · | · | **0** |
| `entry` | hold | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **7** |
| `entry_high` | buy | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `entry_low` | buy | · | · | · | ✓ | ✓ | · | · | · | **2** |
| `expired` | buy | · | · | · | · | · | · | ✓ | ✓ | **2** |
| `filled_today` | buy | · | · | · | · | ✓ | · | · | · | **1** |
| `frozen_price` | buy,hold | · | · | · | · | · | · | · | · | **0** |
| `implied_trail_sma20` | hold | · | · | · | · | · | · | · | · | **0** |
| `kind` | buy,hold | · | · | · | · | ✓ | · | · | · | **1** |
| `plan_tags` | hold | · | · | · | · | · | · | · | · | **0** |
| `pnl_pct` | hold | · | · | · | · | · | · | · | · | **0** |
| `r_multiple` | hold | · | · | · | · | · | · | · | ✓ | **1** |
| `sma20` | buy,hold | · | · | · | · | · | · | · | · | **0** |
| `stop` | hold | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **8** |
| `stop_breached` | hold | · | · | · | · | ✓ | · | · | · | **1** |
| `target` | hold | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **8** |
| `target_reached` | hold | · | · | · | · | ✓ | · | · | · | **1** |
| `ticker` | buy,hold | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **8** |
| `today_open` | buy | · | · | · | · | · | · | · | · | **0** |
| `tranches` | hold | · | · | · | ✓ | ✓ | · | · | · | **2** |

**Published and read by nothing (7):** `dist_to_target_pct`, `frozen_price`, `implied_trail_sma20`, `plan_tags`, `pnl_pct`, `sma20`, `today_open`.

Each is a value the model computed and no surface shows. Decide per field:
surface it, or record why it is engine-internal.

## Alias hazards

Pairs where both fields exist, both are plausible, and picking the wrong one is
silent. Every one of these has been read wrongly at least once.

| prefer | easily confused with | why it matters | wrong one still referenced by |
|---|---|---|---|
| `buy_zone_low` | `entry_low` | entry_low is the signal WEEK's candle low, which IS the stop. The record buys inside buy_zone_*, never down to the stop. | This week, Research |
| `buy_zone_high` | `entry_high` | entry_high happens to equal buy_zone_high on most cards, which is exactly why reading the wrong one goes unnoticed until a card where it does not. | This week, Research |
| `window_filled` | `filled_today` | filled_today is recomputed against the LAST bar every run and means 'can I buy at today's open'. window_filled is whether the signal ever triggered. | Research |

## Calendar-date fields

These carry a day with no time and no zone. In JavaScript, `new Date('2026-08-28')`
is UTC midnight, so formatting it in a timezone behind UTC renders the previous day.
Parse them as LOCAL dates (`parseCalendarDate` in SignalsV3.jsx), never with a bare
`new Date(str)`.

| field | referenced by |
|---|---|
| `as_of` | api, recon, Dashboard |
| `bought_date` | api, recon, This week, Research |
| `buy_window_until` | Research |
| `signal_date` | recon, This week, Research, History |

## How to use this

1. Adding a field to the weekly envelope? Regenerate and check it has a consumer.
2. Reading a field on a page? Check the hazards table first — the plausible name
   is not always the right one.
3. Reviewing a surface that 'looks thin'? Scan the unread list. That is the model's
   own reasoning, already computed, sitting unused.
