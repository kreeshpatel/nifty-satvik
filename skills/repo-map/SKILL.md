---
name: repo-map
description: >
  A living map of the LIVE system, the NSE weekly-swing book (44-week SMA pullback, CRS-ranked
  Grade-A fills, config-P scaled exit): which file owns each value and formula, what else reads it,
  where it is duplicated, which test or manifest enforces live-vs-research parity, and how the Saturday
  data flows from download to archive. Use this BEFORE changing any value, formula, or structural
  file so you know the blast radius. Trigger words: "weekly swing", "bhanushali", "Grade A", "CRS rank",
  "44-week SMA", "LIVE_DISCIPLINE", "LIVE_EXIT", "config P", "where is", "what depends on",
  "single source of truth", "which file owns", "is this duplicated", "live vs research parity",
  "mem=None", "PIT membership", "corporate action", "demerger", "holiday calendar", "archive",
  "drift", "manifest", "golden", "file inventory", "how does X flow".
---

# Repo Map: the live weekly-swing book

**Why this exists.** Values that live in more than one place drift, and the drift is almost never in the
signal maths; it is in the plumbing around it. The last stale version of this map described a retired
book, and the live engine was not in it. That is how research diagnostics came to pass `mem=None`
(no point-in-time membership gate) while the live cron gates every fill on `load_membership()`: the
research book read Sharpe 1.67 where the live book reads about 1.03. Every line below was read out of
the code, not out of a doc. Line numbers are as of 2026-10-20; if one has moved, the symbol name is the
reliable handle.

**The live system in one paragraph.** Every Saturday 6 PM IST a GitHub Actions job
(`.github/workflows/cron-bhanushali-scanner.yml`) runs `scripts/run_bhanushali_cron.py`. It tops up the
OHLCV cache, runs three guards on it, rebuilds the whole weekly history from inception through the engine
in `scripts/run_bhanushali_weekly_rank.py` (called `R94`), and publishes the current state as
`results/*_weekly.*`. Signal: weekly low within 7% of the 44-week SMA, SMA slope floor, quality-green week,
relative strength above its 40-week SMA against Nifty-50. Fill order: strongest CRS distance first, Grade A
= top 5 per setup week. Exit: config P, a three-tranche scaled exit with no time cap.

**Open this when you are about to:** change a cost, stop, sizing, exit, or universe value; touch
`config.py`, `nq/data/*`, or the cron; write a research script that calls `R94.backtest`; ask "does the
research book agree with the live one on this?"; or find where a number comes from.

Cross-reference: [`session-router`](../session-router/SKILL.md) (class the task first),
[`data-quality`](../data-quality/SKILL.md) before any OHLCV or corporate-action change,
[`backtest-rigor`](../backtest-rigor/SKILL.md) and [`leakage-audit`](../leakage-audit/SKILL.md) before
trusting a number, [`program-laws`](../program-laws/SKILL.md) before proposing a change of rule.

---

## Part 1. Shared kernels (single sources of truth)

If the same value appears elsewhere, that copy is a derivative and a drift hazard (Part 2 lists them).

### 1.1 What the live book is: the `LIVE_*` blocks in `scripts/run_bhanushali_cron.py`

The cron's constants are the definition of the live book. **The engine does not read
`models/bhanushali_weekly/config.json`**; that file is a dated decision log plus display data for the
dashboard backend, held by `scripts/guard_production_commit.py` and `tests/test_production_guard.py`
(an edit needs a dated, documented block). Change the code constant and add the dated block; changing
only the JSON changes nothing that trades.

| symbol | line | value | what it does |
|---|---|---|---|
| `LIVE_DISCIPLINE` | 86 | `ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20` | skip a fill priced >20% over the signal-week SMA; lift the stop to `entry*0.90` if the candle low is further; cap any name at 20% of sizing equity |
| `P_EXIT` / `LIVE_EXIT` | 178 / 187 | `scaled_exit`: 40% at +2R, 40% on the blow-off pattern (armed at 2.5R), 20% runner until a weekly close under the 44w SMA | the single swap point for the exit; no time cap exists under it |
| `LIVE_STALENESS` | 96 | `stale_absent_days=STALE_ABSENT_DAYS` (10) | force-close a held name that stopped printing bars (constitution B-1) |
| `LIVE_PREP` | 112 | `complete_weeks_only=True` | the last bar of a still-open week decides nothing |
| `LIVE_CA_HOLD` | 128 | `ca_hold_drop=R94.CA_HOLD_DROP` (0.15) | freeze a held name that gaps 15% down with no registered event |
| `LIVE_UNIVERSE_EFFECTIVE` | 120 | `2026-10-16` | no retroactive entrants (see `_mask_late_entrants`, 863) |
| `INCEPTION_DEFAULT` | 57 | `2026-07-04` | the book is rebuilt from here each run |
| `TARGET_R`, `HOLD_DAYS_DISPLAY` | 58, 59 | 2, 65 | card display only; `HOLD_DAYS_DISPLAY` bounds nothing |

Every engine default is OFF so the frozen 0094 research run stays byte-identical (`tests/test_r94_golden.py`
cell `frozen_defaults`). A new lever must be a `backtest()` kwarg defaulting OFF, switched on only by a
`LIVE_*` block.

### 1.2 The engine: `scripts/run_bhanushali_weekly_rank.py` (R94)

| symbol | line | role |
|---|---|---|
| `SLOPE_MIN, SLOPE_LOOKBACK, TOUCH_BAND, CRS_LEN` | 45 | the frozen pattern parameters (0.03, 13, 0.07, 40) |
| `week_closed_at` | 64 | the one test for "is this ISO week finished", holiday-aware, from `config.NSE_HOLIDAYS`; used by `prep_weekly_rank` and by the cron's `build_envelopes` |
| `CA_HOLD_DROP`, `_ca_hold_check` | 137, 140 | the corporate-action hold |
| `build_demerger_events`, `_apply_demerger` | 160, 187 | rule B-prime: realise the carved-out slice at the prior close, re-base the remainder |
| `prep_weekly_rank` | 224 | daily OHLCV to weekly bars, 44w SMA, slope, touch, quality-green, CRS rank, `entry_win`, `last_signal` |
| `grade_a_entries` | 552 | top-N CRS per ISO setup week; `filter_before_rank` (D6) default OFF |
| `backtest` | 595 | the engine: membership gate at fill (1119), vol scalar (1183), sizing at `RISK` (1202), stop lift (1224), notional cap (1237), ext cap (1155, 1168) |

It stands on older scripts that are imported, not copied: `prep` and `RISK=0.02` and `_cost_leg` from
`run_bhanushali_sixstep.py` (46, 52, 59); `EQ0` (1,000,000) and `START` (2017-01-01) from
`run_bhanushali_faithful.py` (27); `CAP_WEEKS` from `run_bhanushali_weekly_full.py` (46); the index path
`NIFTY50_CSV` from `run_bhanushali_weekly_crs.py` (42). Editing any of those moves the live book.

### 1.3 Costs and market constants: `config.py` and `nq/engine/portfolio.py`

- `BROKERAGE_PCT`, `STT_PCT` (`config.py` 47-48), `SLIPPAGE` tiers (60), `MAX_ADV_PARTICIPATION` (66).
- Per-leg cost in the swing engine is `_cost_leg` (sixstep 52) = brokerage + STT + `leg_slippage(adv, notional)`
  from `nq/engine/portfolio.py` (70). The slippage tier and the 0.5% ADV impact step live only there.
- Shared with the retired momentum book and therefore double-guarded: `STALE_ABSENT_DAYS` (portfolio 43)
  and `vol_target_scalar` (98). A change here moves both books; the momentum golden catches it.
- `NSE_HOLIDAYS` (181), `NSE_HOLIDAYS_COVERED_FROM/THROUGH` (207-208), `assert_calendar_covers` (215). The
  calendar is authoritative only inside its covered window. `week_closed_at` warns past it and
  `scripts/check_calendar_coverage.py` goes red 30 days before expiry. Regenerate with
  `scripts/build_nse_holidays.py --emit` when NSE publishes the next year (historically December).
- `NIFTY_500` (77) is the carried universe snapshot.

### 1.4 Data layer: `nq/data/`

| module | owns |
|---|---|
| `ohlcv.py` | `OHLCV_CACHE` = `data/ohlcv.pkl` (38), `download_ohlcv` (266, `min_bars` default 50 is wrong for a top-up), `merge_ohlcv` (359, new bar wins), `save/load_ohlcv_cache` |
| `membership.py` | `MEMBERSHIP_PATH` (37), `load_membership` (56; returns `None` if the file is missing), `ticker_in_index_on` (88), `current_members` (97) |
| `adjustment_guard.py` | `assert_no_new_seams` (296), `assert_no_live_escalation` (432), `load_book_positions` (459); `BENIGN_FACTOR_MAX` 66, `LIVE_WINDOW_WEEKS` 373 |
| `history_guard.py` | `assert_open_history_intact` (97), `MIN_WEEKS` 28; halts when a vendor series shrinks under an open trade |
| `weekly.py` | `build_weekly_panel`, the cached weekly panel for research (a re-derivation of the engine's grouping, see 2.2) |

Universe for the live download is `run_cpcv.build_universe("union")` (58): `NIFTY_500` snapshot union current
PIT members. Membership still gates eligibility, so an ex-member that is downloaded cannot signal.

### 1.5 Provenance: `nq/runner/manifest.py` and `nq/lab/runs.py`

- `manifest._live_blocks` (34) imports `LIVE_DISCIPLINE`, `LIVE_EXIT`, `LIVE_STALENESS`, `LIVE_PREP` from the
  cron. `build_manifest` (95) labels every run `LIVE BOOK` or `NOT LIVE BOOK: <first differing key>`, and
  `membership != "pit"` is always the first difference. Quote a number only with its label.
- `nq/lab/runs.py` `DEFAULT_CONFIG` (43) is the live book spelled as lab keys; `engine_kwargs` (185) builds
  the kwargs from the cron's blocks; `replay` (208) cuts at `CUT=2024-06-30` (the sealed slice never reaches
  it) and records each distinct config once in the multiplicity ledger.

### 1.6 Records and their archivers

`results/signals_today_weekly.json`, `signals_history_weekly.json`, `signal_analytics_weekly.json`,
`paper_portfolio_weekly.json`, `portfolio_history_weekly.csv` are the mutable working copy. The immutable
layer is `results/archive/<as_of>/` (`scripts/archive_weekly_snapshot.py`, `archive` 205, write-once), the
append-only `results/cards_archive.jsonl` (`archive_weekly_cards.py`), the dated `results/sma_panel/`,
and `results/brain/` (`position_log.csv.gz`, `management_events.jsonl`). `results/output_contracts.json`
says which of these each scheduled job must have committed. The 2026Q3 derived tables
(`results/attribution_ledger.csv`, `signal_quality_forward.csv`) are rebuilt deterministically from the
immutable layer and hold no state of their own.

---

## Part 2. Duplication hazards

Each row is a place where the same fact is written twice and nothing but care keeps the copies equal.
"Enforced" names what fails if they split; "NOT enforced" is a gap.

### 2.1 Pattern parameters in more than one place

`SLOPE_MIN, SLOPE_LOOKBACK, TOUCH_BAND, CRS_LEN` are defined in `run_bhanushali_weekly_rank.py:45` (live)
**and** `run_bhanushali_weekly_crs.py:38-40` (the 0092/0093 research script). `run_bhanushali_weekly_full.py:44`
holds a third `TOUCH_BAND` for the superseded EMA engine. `scripts/render_chart.py:15` imports from R94 (good).
Hardcoded copies:

- `nq/data/weekly.py:35-37`: `SMA_LEN=44`, `SLOPE_LOOKBACK=13`, with a comment "frozen to match". NOT enforced
  by a test that compares them to R94.
- `run_bhanushali_cron.py:1107`: `lo <= sma * 1.07` in `_write_sma_panel`. The audit panel's `touch_ok`
  would disagree with the engine the day `TOUCH_BAND` moves. NOT enforced.
- `models/bhanushali_weekly/config.json` `params`: documentation of the same values; not read by the engine.

Rule: import from R94, never retype. If you must change a pattern parameter, grep for `0.07`, `13`, `44`
and `40` in `scripts/` and `nq/`, and treat it as a re-anchor (`/re-anchor`), not an edit.

### 2.2 The 44-week SMA and weekly grouping are computed several times

`prep_weekly_rank` (the engine), `nq/data/weekly.py` (research panel; its docstring claims byte-identity
with the engine's grouping), `_sma44_now` in the cron (reads `wsma_at` from the engine, so it follows the
engine, and after a demerger reads the position's `ca_view`), `scripts/render_chart.py` (re-derives for
charts) and `run_bhanushali_sixstep.prep` (a daily 44-SMA, a different object). The line is a 44-week
**SMA**, never an EMA; `run_bhanushali_weekly_full.py` is the quarantined EMA path.

### 2.3 Research universe vs live cache

`corrected_universe()` (`run_bhanushali_path1.py:26`) = pinned cache + `data/ohlcv_backfill.pkl` + alias
materialisation from `data/delisted_alias_map.json`. The live cron does **not** use it: the backfill is not
committed to the cron's checkout and a forward book trades only listed names. Consequence: a research number
and a live number differ by universe even when every kwarg matches, and `nq/lab/runs.py` additionally cuts
at 2024-06-30. A research number is "the live engine on the research universe", never "the live book".
The live universe also depends on a mutable `data/ohlcv.pkl` that the workflow caches by month; the first
run of a month rebuilds it clean. The cache key prefix `ohlcv-live-<month>-` is shared with
`cron-forward-wall.yml`, so the two workflows restore one another's cache.

### 2.4 Card entry vs engine fill

The card is what the owner acts on; the record is what the engine books. They are computed separately.

- Entry: the card uses the current close if it is inside the signal band, else the band midpoint
  (`build_envelopes`, cron 506 onward); the engine fills at the in-range open. The stop is made equal through
  `_record_stop` (313), which reads `LIVE_DISCIPLINE["max_risk_pct"]`; `_ext_flags` (404) reads `ext_cap`;
  `_exit_plan` (251) derives tranches from `LIVE_EXIT`. Enforced by `tests/test_swing_card_record_parity.py`
  (constitution D5).
- NOT enforced: `TARGET_R = 2` (cron 58) vs `tp1_r=2.0` in `P_EXIT`, and the hardcoded `2.0` in the
  non-scaled branch of `_exit_plan`. They are equal today; change the exit and the card target can lag.
- NOT enforced: the card's size or share count; the card shows no sizing.

### 2.5 Membership gate at fill vs at ranking vs at the card

Three different dates and three different places:

1. **Fill.** `backtest` tests `ticker_in_index_on(t, dd, mem)` at the entry-window activation day (1119),
   after the `a_grade` test.
2. **Ranking.** `grade_a_entries` ranks all signals and, by default, does not look at membership at all. A
   non-member can occupy a top-5 slot, be refused at fill, and waste the slot (D6 / B-3). The fix is
   `filter_before_rank=True`, default OFF, because it changes which historical trades the book takes; it is an
   owner decision at a review and would need a re-anchor. Covered by `tests/test_low_rank_divergences.py`.
3. **Card.** `build_envelopes` tests membership on the **signal Friday** and then re-sorts and re-grades the
   survivors top-5. So the card's Grade A can differ from the engine's Grade A in a week where the A-set
   contains a non-member, and the membership date differs by up to a week from the fill date.

Also `_mask_late_entrants` (cron 863) uses `mem` to floor a late entrant's signals.

### 2.6 Three books share a call pattern, not a function

The cron makes three `R94.backtest` calls with near-identical kwargs: `out_paper` (the capital book, A-only,
position and event logs), `out_all` (`uncapped=True`, A-only, the signal ledger and cards), `out_base` (no
`a_grade`, all grades, WATCHED only, never surfaced). Add a lever to one call and forget the others and the
books silently diverge. `ca_events` and `ca_hold` are built once and handed to all three on purpose
(`tests/test_cron_demerger_wiring.py`). `a_set` is built once from `P`.

### 2.7 Cost constants

`config.py` (47-60), `nq/engine/portfolio.py` (imports them), `run_bhanushali_faithful.py:26`
(`COST_LEG` rebuilt from config; an older engine) and `run_bhanushali_sixstep.py:42` (`STT_BROK`). All derive
from `config.py` today; a hardcoded literal elsewhere would be a new copy. Grep `0.0003`, `0.001`, `0.0022`
before concluding there is one.

### 2.8 The Nifty-50 CSV is a mutable runtime input

`research/exports/benchmark_nifty50.csv` is the CRS denominator and the cron overwrites it at runtime
(`_refresh_nifty50`, 908). The committed copy can lag the live book. It is fingerprinted by the archiver
(`nifty50_csv_sha256`) so a restatement caused by it is attributable.

---

## Part 3. Live-vs-research parity points and what enforces each

| point | live | research must match | enforced by |
|---|---|---|---|
| engine kwargs | cron's `LIVE_*` blocks | `nq/lab/runs.py::engine_kwargs`, any script that calls `R94.backtest` | `tests/test_replay_parity.py` (static key-by-key, plus dynamic ledger and NAV equality on the fixture) |
| which book a number belongs to | `LIVE BOOK` label | every run that wants to be quoted | `nq/runner/manifest.py` label; `diff_from_live` |
| PIT membership at fill | `load_membership()` passed as `mem` | pass it too | manifest (`membership` is always the first diff); NOT enforced for a script that never builds a manifest. Four diagnostics were corrected from `mem=None` on 2026-10-19; grep before trusting an old one |
| Grade-A set | `grade_a_entries(P)` with D6 OFF | same call | `tests/test_low_rank_divergences.py` pins both modes; parity test passes `a_grade` |
| completed-weeks-only prep | `LIVE_PREP` | pass `**LIVE_PREP` to `prep_weekly_rank` | manifest tolerates omitting it (it configures prep, not `backtest`) but flags a different value |
| frozen research run | every lever OFF | n/a | `tests/test_r94_golden.py` cell `frozen_defaults`; may never change |
| live config run | cron's exact call, capped and uncapped books, the envelope | n/a | `tests/test_r94_golden.py` cell `live_config`; changes only with a documented owner change, regenerate the fixture in the same commit (`scripts/build_r94_golden_fixture.py`) |
| card vs record | stop, target, tranches, ext flag | n/a | `tests/test_swing_card_record_parity.py` |
| stale panel | the panel must advance | n/a | `_assert_data_advanced` (cron 954); `tests/test_stale_panel_guard.py` |
| adjustment seams | guards in `_refresh_ohlcv` | n/a | `tests/test_adjustment_guard.py`, `tests/test_history_guard.py` |
| history rewrites | restated or vanished trades | n/a | `scripts/check_history_drift.py` against `results/history_restatements.json`; `tests/test_history_drift_tripwire.py` |
| holiday calendar | `config.NSE_HOLIDAYS` | n/a | `tests/test_calendar_coverage.py`, `tests/test_nse_calendar.py` |
| demerger on a held name | B-prime events to all three books | n/a | `tests/test_cron_demerger_wiring.py`, `tests/test_ca_hold_guard.py` |
| no retroactive entrants | `_mask_late_entrants` | n/a | `tests/test_no_retroactive_entrants.py` |
| shared kernels with the momentum book | `STALE_ABSENT_DAYS`, `vol_target_scalar`, `leg_slippage` | n/a | `tests/test_stage2_golden.py` guards `nq.engine.portfolio` byte-for-byte; it is not a swing test, it is the guard on the shared module |

**Known gaps in parity enforcement.**

1. `LIVE_CA_HOLD` and `LIVE_UNIVERSE_EFFECTIVE` are in neither the manifest's `_live_blocks` nor
   `test_replay_parity`'s key union. A replay with the hold or the late-entrant mask changed still labels
   `LIVE BOOK`. The lab leaves the hold off deliberately (a 5.5-year reconstruction has no owner to clear a
   freeze), so today the label overstates parity on that one axis.
2. `build_demerger_events` is called by the cron with `as_of` pinned to the panel's last session; the lab
   calls it without. Equal on a closed history, different in a live week.
3. The lab uses `corrected_universe` (2.3). The manifest does not record the universe.
4. Nothing ties the weekly research panel's constants (2.1) to R94.

---

## Part 4. The weekly data flow, end to end

All times are the Saturday run (12:30 UTC cron in `cron-bhanushali-scanner.yml`; `cancel-in-progress: false`).

1. **Download.** `_refresh_ohlcv` (cron 758). Cache loaded from `data/ohlcv.pkl`. Per ticker: a name with
   fewer than `MIN_CACHED_BARS` (300) bars is pulled for the full warm-up window; the rest get a 25-day top-up
   with `min_bars=1` (the default 50 once merged an empty dict and published week-old data). A shifted overlap
   close above `ADJ_JUMP` (0.5%) triggers a clean full re-fetch of that ticker. Saved to the cache. A download
   failure is caught and the cached bars are used.
2. **Guards, outside the `try` on purpose** so a poisoned cache halts instead of reading as "download failed":
   `assert_no_new_seams` (adjustment monotonicity, benign seams tolerated only if tiny, old and not held),
   `assert_no_live_escalation`, then `assert_open_history_intact` (a series that shrank under an open trade).
3. **Index and membership.** `_refresh_nifty50` (non-fatal), `load_membership()`.
4. **Panel.** `R94.prep_weekly_rank(ohlcv, **LIVE_PREP)`: weekly bars by ISO week, 44w SMA, slope, touch,
   quality-green, CRS distance, entry windows, `last_signal`. Then `_mask_late_entrants` drops pre-effective
   windows of names added to the universe.
5. **A-set.** `R94.grade_a_entries(P)`: top 5 by CRS per setup week.
6. **Corporate actions.** `build_demerger_events(ohlcv, load_demerger_rows(), **prep_kw)` from
   `data/corporate_actions_post_harvest.csv`; a registered ratio the prices contradict raises
   `DemergerCliffMismatch` and nothing publishes. Reviews in `data/corporate_action_reviews.csv`.
7. **Three books** (2.6): capital book `out_paper`, uncapped ledger `out_all`, all-grades watched `out_base`.
8. **Freshness check.** `_assert_data_advanced` raises `StaleDataError` if the panel did not advance although
   sessions have elapsed.
9. **Publish working copy.** `build_envelopes` then the `results/*_weekly.*` files, `base_swing_forward.json`,
   `weekly_sma_panel.csv` and `sma_panel/<as_of>.csv`, `results/brain/*`, decision memos.
10. **Same workflow, in order:** `bhanushali_review_scorecard.py` (Oct-1 gates) then
    `archive_weekly_snapshot.py` (write-once snapshot, input fingerprint, diff against the previous snapshot,
    one row in `drift_log.jsonl`) then `archive_weekly_cards.py` (non-fatal), the watched side books
    (`run_blend_paper.py`, `run_breadth50_paper.py`), `collect_attribution_ledger.py` (rebuilds
    `attribution_ledger.csv` from the archives), `collect_signal_quality_forward.py`,
    `render_weekly_postmortem.py` (reads, computes nothing), `run_prediction_producer.py`.
    **Order matters:** the snapshot must follow the scorecard; the ledger must follow the archivers.
11. **Commit.** `need` artifacts go red by name if absent; `opt` ones warn. Push retries three times.
    `results/output_contracts.json` is the dead-man list of what must be in the commit.
12. **After the commit (read-only, red if tripped):** `collect_signal_quality_forward.py --validate`,
    `check_weekly_loggers.py`, `check_history_drift.py`, `check_calendar_coverage.py`.
13. **Judge.** `cron-judge.yml` is a separate workflow triggered when the scanner completes; it checks out
    `main`, runs `scripts/run_judge_cron.py` on the freshly pushed cards and appends to a sealed,
    hash-chained log. That log is sealed until its first review read: verify it by count and chain only,
    never open or quote it. A missing API key reads as a warning, not a breach.

`cron-forward-wall.yml` is a different system: the daily momentum forward wall (`run_paper_cron.py`,
`assert_wall_advanced.py`). It shares the OHLCV cache key prefix with the swing scanner and nothing else.

---

## Part 5. Procedure before changing a value

1. **Route it.** Run [`session-router`](../session-router/SKILL.md). A value that would change live money is
   ENGINE or PRODUCT class and clears the engine gate; a research script is not allowed to edit a `LIVE_*`
   block "to test it".
2. **Find the owner.** Look the value up in Part 1. Then grep the whole tree for the literal and for the
   symbol (`scripts/`, `nq/`, `tests/`, `dashboard/`, `models/`), and walk the matching Part 2 row.
3. **Look up what enforces it** (Part 3). If nothing does, say so in the change and add the test, or record it
   as a known gap here.
4. **Make the change inside the kernel**, cfg-gated, default OFF, switched on only by a `LIVE_*` block. Never
   fix a duplicate by editing the copy.
5. **Run the gates:** `tests/test_r94_golden.py` (frozen cell must stay identical; the live cell changes only
   with a documented owner decision, fixture regenerated in the same commit),
   `tests/test_replay_parity.py`, `tests/test_swing_card_record_parity.py`, and, if you touched
   `nq/engine/portfolio.py` or `config.py`, `tests/test_stage2_golden.py`. Then the full suite.
6. **If the live book changes,** add the dated block to `models/bhanushali_weekly/config.json` (the production
   guard requires it), and re-anchor any recorded number measured on the old book via `/re-anchor`.
7. **Any number you quote** carries its manifest label and passes
   [`plausibility-check`](../plausibility-check/SKILL.md). A diagnostic that did not pass PIT membership is not
   the live book.
8. **After editing any `nq/**` module or `config.py`,** regenerate the dependency map
   (`python scripts/gen_depgraph.py`) and commit it with the change.
9. **Update this map** if you moved a kernel or added a duplicate. A stale map is how the last one failed.

---

## Retired: the long-horizon momentum book

The long-horizon momentum book (`sma200_slope_63`) is RETIRED and is not mapped here. Its material is in
`long_horizon/` (charter, strategy docs, research, results) and `models/long_horizon/`. Several paths the
previous version of this skill cited no longer exist. `nq/engine/portfolio.py` and `nq/data/*` survive and are
shared with the swing book, which is why `tests/test_stage2_golden.py` still guards the shared module.

---

## Cross-references

- [`data-quality`](../data-quality/SKILL.md): OHLCV cleaning, split versus demerger, corporate-action hygiene.
- [`backtest-rigor`](../backtest-rigor/SKILL.md) and [`leakage-audit`](../leakage-audit/SKILL.md): before a number is believed.
- [`plausibility-check`](../plausibility-check/SKILL.md): compare a result with the reproducible anchors.
- [`program-laws`](../program-laws/SKILL.md): standing verdicts; cite and narrow, never relitigate.
- [`research-log`](../research-log/SKILL.md): where a finding goes after a map-informed change.
