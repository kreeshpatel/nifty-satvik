# Signal-quality axis capture — the FRESH-only hole, and what can be done about it

**Status:** OPEN — owner decision. Written 2026-08-30 during the Oct-1 collector audit.
**Touches:** `forward/prereg_signal_quality.md` (4-axis family, owner-frozen 2026-08-17),
`scripts/run_bhanushali_cron.py` (PRODUCTION path), `scripts/collect_signal_quality_forward.py`,
`.github/workflows/cron-bhanushali-scanner.yml`.

Nothing in this document has been implemented beyond the two guards described in §2. The three
options in §4 all change either a production script or a pre-registered collection rule, which is
not a session's call to make.

---

## 1. The defect

The four quality axes are computed **only for cards in FRESH state**. Measured on the live envelope
(`results/signals_today_weekly.json`, generated 2026-08-28):

| status | n | body_ratio | signal_conviction | crs_rank | ext_pct_over_sma44 | band_width_pct |
|---|---|---|---|---|---|---|
| FRESH | 2 | 2 | 2 | 2 | 2 | 2 |
| ACTIVE | 24 | 0 | 0 | 0 | 0 | 0 |

`collect_signal_quality_forward.py` reads the axes from archived snapshots
(`results/archive/YYYY-MM-DD/signals_today_weekly.json`), and that archive is written **once a week,
on Saturday**.

Therefore: **a signal whose FRESH state falls between two Saturday archives is first observed as
ACTIVE, and its axes were never recorded by anything durable.** They cannot be recovered, because
the only source that ever held them was an envelope that has since been overwritten.

### The instance

`PHOENIXLTD`, `signal_date` 2026-08-24 (a Monday). Absent from the 2026-08-21 archive; present in
the 2026-08-28 archive already `ACTIVE`. Its row carries `touch_depth_min_ext` and `R_pct` — both
recomputed from OHLCV — and nulls for `body_ratio`, `signal_conviction`, `crs_rank`,
`ext_at_signal`, `band_width_pct`.

It sits between two complete weeks (2026-08-21 and 2026-08-28 are both full), which is what makes it
a hole rather than a start-up condition. The nulls before 2026-08-07 are different and benign: the
producer did not emit those fields at all yet.

### Why it went unnoticed

Coverage counts already existed and were already printed by the collector. They could not surface
this, because `body_ratio: 15/37` reads identically whether the nulls are the 22 documented
pre-schema rows or one hole that opened last week. A flat number nobody can interpret is not a
control.

---

## 2. What has been done (no decision required)

Two guards, both merged with this document. Neither changes what is captured — they only stop a
future loss being silent.

1. **`axis_holes()` + `KNOWN_INCOMPLETE`** — rows on or after `SCHEMA_COMPLETE_FROM` (2026-08-07)
   must carry every axis. Known losses are declared with a written reason; anything undeclared is
   new. `--validate` exits non-zero.
2. **`_coverage_drops()`** — the rebuild may add coverage or hold it level, never drop it. This
   caught a real regression during the audit: run against a two-month-old OHLCV cache, the rebuild
   produced **4 of 37** touch-depths against a committed 37, and would have overwritten the good
   table with the worse one while printing a success line.

The cron now runs `--validate` as its own step **after** the commit, so a research-collector defect
reports red without ever withholding the live book.

PHOENIXLTD is declared, not backfilled. `prereg_signal_quality.md` §1 freezes the axes **at signal**;
a `body_ratio` computed later from a different week's candle is a different measurement wearing the
same column name.

---

## 3. What it costs at the Oct-1 review

One row of 37, and 5 forward rows currently carry the axes. The review is a **first read** in any
case — `prereg_swing.md` §4 puts the primary decision at 2027-07-01 and needs ≥20 closed trades per
book, against 9 closed today — so the immediate cost is small.

The cost is not the one row. It is the **rate**: every mid-week signal from here loses its axes
until the capture changes, and the wall's power is exactly the count of rows with axes AND outcomes.

---

## 4. The options

### A. Do nothing beyond the guards
Accept the loss, declare each instance. Zero risk to production; the wall's power erodes at whatever
rate mid-week signals occur, and every erosion is at least visible and reasoned.

### B. Archive on the daily monitor as well as Saturday
`cron-bhanushali-monitor` already runs weekdays at 16:15 IST. If it snapshotted the envelope, a
mid-week FRESH card would be captured before it turned ACTIVE.

*Against:* the monitor reads the **frozen Saturday envelope** — it does not recompute signals — so it
would have to actually see a FRESH card that the Saturday envelope did not contain. Whether that is
even possible depends on where a Monday `signal_date` comes from, which §5 says is unresolved. This
option may not work at all, and that must be settled before it is built.

### C. Have the producer record the axes on ACTIVE cards too
Then any snapshot that sees the signal carries its axes.

*Against:* this is the option most likely to be quietly wrong. The axes describe the **signal week's**
candle. Computing them for a card that has been active for six weeks either re-derives them from the
original week (fine, but it is then a backfill and §1 must be amended to permit it) or reports the
current week (wrong, and silently so — the column would keep its name and change its meaning). It
also edits `run_bhanushali_cron.py`, a protected production path.

**Recommendation: settle §5 first, then A or B.** C is only safe with an explicit §1 amendment
saying which week the value describes, and that amendment should be written before any code.

---

## 5. The underlying cause: `signal_date` is two different fields

Resolved during the audit, and it changes §4. The two card states populate the same key from
different sources:

| card state | `run_bhanushali_cron.py` | value |
|---|---|---|
| FRESH | `:422` — `"signal_date": str(fri.date())` | the **setup Friday**, commented *"the just-closed setup week (stable)"* |
| ACTIVE | `:534` — `"signal_date": ed` | the **entry date** — the day the fill actually happened, any weekday in the buy window |

So a card does not merely lose its axes when it turns ACTIVE. **It changes identity.** The same
economic signal is `(PHOENIXLTD, <setup Friday>)` while FRESH and `(PHOENIXLTD, 2026-08-24)` once
filled, and the collector keys on `(ticker, signal_date)`.

That is what `_first_fresh_flags`'s `EPISODE_DAYS = 16` collapse exists to absorb, and it is why the
axes are null rather than merged: for PHOENIXLTD there was **no FRESH row in any archive to merge
with** — it is absent from the 2026-08-21 snapshot entirely, not merely present-without-axes.

### What this means for the options

- **Option B is weaker than it looked.** Archiving daily would capture a FRESH card, but under a
  *different key* from the ACTIVE row it later becomes. It only helps if the episode collapse
  reliably rejoins them, which makes this a collector-identity problem as much as a capture-cadence
  one.
- **The real fix may be neither B nor C but a stable identity** — carry the setup Friday on the
  ACTIVE card as its own field (rather than overloading `signal_date`), so a signal keeps one key
  for life. That is an additive producer change and does not require re-deciding what the axes
  measure, which is what makes C dangerous.

This is an **alias hazard** in the sense `scripts/gen_wiring_map.py` uses the term: two plausible
meanings for one name, where picking the wrong one is silent. It is not currently listed in
`ALIAS_HAZARDS`, and the map does not cover it because the map walks card records and this is a
cross-state comparison. Worth adding either way.

### Still open

Why PHOENIXLTD is absent from the 2026-08-21 archive at all, given it was entered on 2026-08-24 —
presumably off that week's setup. The envelope may publish a narrower FRESH set than the book
actually funds. Not required to choose between the options above, but it should be answered before
the wall's row count is treated as the population of signals issued.
