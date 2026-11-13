# ADR-0018 — Closed history is immutable: an append-only forward record (built, switched OFF)

**Date:** 2026-11-08 · **Status:** PROPOSED (code merged OFF; switching it on is an owner decision) · **Decider:** owner
**Class:** live record production (ops / governance-adjacent). Zero trials, zero screens. Standing counts unchanged.

## Context

The Saturday scan (`scripts/run_bhanushali_cron.py`) re-runs the engine from the 2026-07-04 inception and
publishes whatever that rebuild says. The past is therefore whatever this week's data and code make of it:

- re-adjusted or revised bars re-price closed trades (MRPL 2026-07-20 on the 2026-10-24 run; LINDEINDIA,
  GLENMARK, NATCOPHARM, CCL, NLCINDIA, OBEROIRLTY before and after it);
- a name joining the scan signals in weeks already published (ZYDUSWELL displaced the closed HINDZINC trade
  and ABDL the open BANDHANBNK, ADR-0017);
- an exit-rule change re-prices every trade unless it carries an effective-date gate
  (`SHADOW_EXIT_EFFECTIVE` is the current example).

`check_history_drift.py` and `results/history_restatements.json` detect these after the fact. Nothing
prevents them.

## Decision

Add an append-only forward record, `scripts/forward_record.py`. It is **OFF** in this change, and the
switch is which command the scanner workflow runs:

- **OFF:** `run_bhanushali_cron.py`, exactly as today. The production file is not edited at all.
- **ON:** `python scripts/forward_record.py cron -- <the same arguments>`.

The `cron` entrypoint runs the unmodified `main()` and observes two seams. It captures the kwargs of the
first uncapped grade-A `R94.backtest` call, the signal tracker. It passes the tracker's `build_envelopes`
outputs through the merge before `main()` writes them. Both patches are removed when the run ends.
Keeping the production file untouched means OFF is byte-identical by construction. It also means this
lands without a `prod-fix` / `prod-override` declaration, because it changes no live behaviour until the
owner switches the command.

When it is on, a committed ledger (`results/forward_record/ledger.json`) holds every closed trade and the
NAV curve through the last frozen scan. Each open trade records the exit rule it was opened under. Each
scan:

1. publishes every frozen closed trade exactly as frozen;
2. takes each frozen open trade from a rebuild under its own exit rule: new state if still held, a new
   close if it closed after the frozen week;
3. adds a trade the record has never seen only if it entered after the frozen week, and suppresses any
   earlier one (a universe entrant, a restated signal, a logic change);
4. freezes the NAV curve through the frozen week and chain-links the rebuild's later rows onto it;
5. lets the rebuild win for one trade (or for `"NAV"`) only through an explicit, dated amendment in
   `results/forward_record/amendments.json`, applied once and recorded in the ledger.

The from-inception rebuild still runs every week and becomes the audit. Every difference from the frozen
record is written to `results/forward_record/audit.json` and appended to `drift.jsonl`, classified:

- **red**: something new this week contradicts the frozen past. A closed trade restated beyond dividend
  re-basing, a closed or open trade vanished, an open trade closed in a frozen week, or a pinned rule's
  rebuild missing.
- **amber**: a new suppression of a retroactive trade, a NAV gap that moved by more than 0.5%, or a red
  finding still unresolved from an earlier week.
- **info**: dividend-scale re-basing (the `check_history_drift.is_rebase` test) and ambers already
  reported.

The audit never writes to the ledger. The health report can consume `audit.json["level"]`.

**Why a merge and not an engine resume.** `R94.backtest(return_state=True)` returns positions, orders
and cash, but it cannot be restarted from them. Pending orders hold positional indices into each
ticker's bar arrays, which a restated or extended series shifts. Demerger views and the event log are
keyed by `id()` of live objects. The prepared panel's indicators come from the full history. A resume
would mean new engine code under the golden masters. The merge leaves the engine untouched, and
`tests/test_stage2_golden.py` and `tests/test_r94_golden.py` stay byte-identical.

**Exit-rule changes need no effective date.** The ledger pins each trade's rule. A changed `LIVE_EXIT`
manages only trades opened after the change. Open trades keep their rule because the cron rebuilds the
tracker once per rule still referenced by a frozen trade. Closed trades are audited against their own
rule's rebuild, so a rule change does not read as a restatement.

## What is not pinned

- **The ₹10L capital book's holdings and cash** come from the current rebuild. Its NAV history is frozen
  and chain-linked; its positions are not. `paper_portfolio_weekly.json["record_nav_chain_link"]`
  appears whenever the chain-link scale is not 1.
- **The base-swing and shadow-exit side records, the SMA panel and the brain logs** are still rebuilt
  from inception.
- **Discipline and staleness settings** are the current ones for every trade. Only the exit rule is
  pinned.
- **A suppressed trade's ticker** may lose a fresh buy card that week. The rebuild treated the name as
  held, so it never produced the card.

## Migration and dry runs

**Seeding.** The first run with the record on seeds the ledger from the committed `results/` files
verbatim, then merges that week's rebuild into it. Each committed closed trade's 3-dp R comes from the
same run's rebuild ledger wherever the rebuild agrees with the published 2-dp R.

**Byte-for-byte proof.** `python scripts/forward_record.py verify-seed` seeds from the committed
2026-11-08 record and republishes a same-data scan through the merge. Four of the five published files
are IDENTICAL. `signal_analytics_weekly.json` differs in one field, `avg_r` (−1.22 committed vs −1.23).
Offline, the 3-dp R is not committed and the seed can only average the 2-dp `r_multiple`. On the
hermetic engine fixture, where the same-run ledger supplies the 3-dp R as the live first run does, all
five files are byte-identical
(`tests/test_forward_record.py::test_first_run_on_unchanged_data_republishes_the_committed_record_byte_for_byte`).
The live OHLCV cache was not available locally (the local `data/ohlcv.pkl` ends 2026-06-29), so the full
engine path was exercised on the fixture, not on live data.

**Archive replay.** `python scripts/forward_record.py replay` seeds from the 2026-07-24 snapshot and
feeds each later weekly snapshot (what the rebuild published that week) through the merge. That covers
20 snapshots, re-runs included, through 2026-11-08. The forward record would have:

- kept HINDZINC 2026-08-31 as first published, through its 2026-09-18 restatement and its 2026-10-16
  displacement;
- suppressed ZYDUSWELL 2026-08-31, ABDL 2026-09-15 and GRAPHITE 2026-07-27;
- carried HEG 2026-07-27 and GRAPHITE 2026-08-10 as open (red) after the 2026-10-01 vendor truncation;
- frozen the 2026-09-15 Tuesday scan's entry keys (CHOLAFIN, ANGELONE, GESHIP, BANDHANBNK dated
  09-15) and suppressed the rebuild's 09-14 versions;
- held the 2026-09-11 NAV level, which the B′ demerger fix of 2026-09-15 later restated by about +13%,
  showing a −13% chain-link gap.

Six weeks would have read red, at 08-07, 09-18, 10-01, 10-16, 10-23 and 11-08. Clearing them needs roughly
four owner amendments: the 09-15 keys, HEG/GRAPHITE, HINDZINC, and `"NAV"` for B′. **This is the trade
the owner is choosing.** Every one of those rewrites happened silently before. Under this ADR each one
becomes a dated, explicit act.

## Switching it on (owner decision, follow-up)

1. Choose a Saturday on which `LIVE_EXIT` does not change. The seed pins every open trade to the rule
   in force.
2. In `.github/workflows/cron-bhanushali-scanner.yml`, replace
   `python scripts/run_bhanushali_cron.py --start ...` with
   `python scripts/forward_record.py cron -- --start ...`. Delete the guard in
   `tests/test_forward_record.py` that asserts the workflow does not do this yet. In the commit step, add `need results/forward_record/ledger.json` and
   `need results/forward_record/audit.json`, plus `opt results/forward_record/drift.jsonl` and
   `opt results/forward_record/amendments.json`. The paths are already whitelisted in `.gitignore`.
3. Decide whether to fold the existing `history_restatements.json` route into the amendments file.
   After switch-on, `check_history_drift.py` will see a stable published history, and the real drift
   signal moves to `audit.json`.
4. Once on, retire the effective-date constants for future exit changes. Do not retire the existing
   ones: they still govern the rebuild-from-inception side records.

## Consequences

- No backtest number, golden master or historical record moves. The record is off.
- With the record on, a past rewrite needs an amendment instead of happening silently.
- With the record on, the scan runs one extra uncapped backtest per retired exit rule still referenced by
  a frozen trade, which is usually none.
- The merge decides by dates alone: an entry after the frozen as-of date, a close on or before it. It
  never buckets by week, so it does not need the holiday-aware `week_key()` in
  `nq/data/trading_calendar.py`. Week semantics stay where they are, in the engine and the cron.
