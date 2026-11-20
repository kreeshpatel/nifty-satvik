# Phase 0 close-out: merges, tax-fallback diagnosis, L5 risk panel, 60/40 forward record

Date: 2026-11-20 · Class: ENGINEERING + MEASUREMENT only.
No candidate signal, model, AUC, feature-label statistic, trial or screen was computed. Standing counts on `main` are
unchanged at **screens 24 · sealed opens 4 · n_trials 3**, read from `diagnostics/research/n_trials.json` and
`label_screen_ledger.md`; the reason is in section A.

**Mission link.** This close-out finishes the data layer that the company engine (pre-registration 0153) and its
crash-risk layer L5 will be judged on, and starts the forward after-tax record of the 60/40 benchmark that any
strategy must beat.

## A. Merges

| Step | Result | Merge commit |
|---|---|---|
| 1. PR #217 (XBRL results dataset) into main | merged after green CI | `d6624162404318b1bb587a7dfa6ea0e3e8111aec` |
| 2. PR #218 (Phase 0), rebased onto main | merged after green CI (Tests, Backend) | `a140e75a4ecefa65e60a12ff9e40795168db00fc` |
| 3. `claude/stoic-pascal-oys10b` into main | **held, not merged** | – |

Step 3 was held because the branch is not just the counts commit. It carries the full heads of #211, #214 and #215:
35 commits and 180 files. Merging it would merge PRs the owner excluded. That is why the counts on main still read
24 · 4 · 3, not 25 · 4 · 3. The owner decision is listed at the end.

## B. Effective-tax-rate fallback: causes (no re-fetch)

**Method** (`diagnostics/replica/phase0/tax_fallback_causes.py`, output `tax_fallback_causes.json`)
- Population: primary-basis, original-version quarters, fiscal year 2019 onward, from `data/fundamentals_q.parquet`.
- Fallback = `tax_rate_fallback` is true, meaning the 25.17% default was used because the trailing-4Q rate
  (TTM tax ÷ TTM PBT, clipped to [0, 0.40]) does not exist.
- Causes are assigned in a fixed order, and the first that applies wins:
  1. fewer than 4 same-basis quarters broadcast by the row's time;
  2. financial company with a tag missing;
  3. tag missing (which tag);
  4. TTM PBT ≤ 0;
  5. other.

**Result** [measured: `tax_fallback_causes.json`]
- 21,161 of 60,129 rows fall back.

  | Cause | Rows |
  |---|---|
  | Fewer than 4 quarters | 10,776 |
  | PBT ≤ 0 | 10,351 |
  | Both tags missing | 23 |
  | Financial tag set | 10 |
  | PBT tag missing | 1 |
  | Tax tag missing | 0 |
  | Other | 0 |

- **Parsing gap fixed.** Companies are now keyed by the modal 9-character ISIN prefix (`company_key`). An ISIN that
  is re-issued at a split, or mistyped in a filing, used to split one company into two short histories.
- **Fallback share by fiscal year** [measured: `2026-11-20_phase0_panels.json`]:

  | FY | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2027 |
  |---|---|---|---|---|---|---|---|---|---|
  | Share | 79.0% | 57.9% | 40.4% | 32.8% | 40.6% | 26.8% | 21.2% | 22.3% | 20.2% |

  Before the fix: FY2023 51.7%, FY2025 25.6%, FY2026 32.4%.
- **What is left is not a parsing gap.**
  - PBT ≤ 0 is economics: the rate is undefined, and the default is the honest choice.
  - Part of "fewer than 4 quarters" is NSE's own listings missing consolidated quarters (e.g. RELIANCE Mar-2022, HAL
    Dec-2021). That cannot be fixed without a re-fetch, which is out of scope.
- The 30-row adjusted-core-EPS replica was re-run after the change. It matches on 30 of 30 rows: max relative
  difference 1.3e-14; the one NaN row is NaN on both sides [measured: `diagnostics/replica/phase0/eps_replica_v3.csv`].

## C. L5 risk-feature and label panel (`data/risk_features.parquet`, gitignored)

### Method

**Rows and dates**
- One row per (PIT Nifty 500 member, Friday): 241,397 rows, 798 symbols, 495 Fridays, 2017-01-06 to 2026-06-25.
- The OHLCV cache ends on 2026-06-29, a Monday, so that partial week is dropped.
- "Friday" = the last session of each W-FRI week.
- Code: `nq/data/risk_features.py` (pure functions per family) and `pipelines/build/build_risk_features.py` (input
  loading and summary). Exact definitions: `diagnostics/replica/phase0/risk_features_spec.md`.

**Price** (log returns `r`, simple returns `rs`; EW market `mk` = mean member `rs`)
- `rv63` and `rv126` = std(r) × √252.
- `dvol126` = sqrt(mean(min(r, 0)²)) × √252.
- `beta126` = cov(rs, mk) / var(mk).
- `dbeta126`: the same, on days with mk < 0.
- `mdd252`; `n_down5_252` = count of rs ≤ −5%.
- `adv20_cr` and `adv60_cr` = mean(close × volume) / 1e7.

**Bands**
- `lo/up_hits63/252` from NSE band-hitter files.
- `band_pct` and `gsm_stage` from the latest `sec_list` file on or before the Friday, starting 2019-12-30.
- GSM is keyed on the trading date the file applies to; no publication time exists.

**ASM**
- Each circular's consolidated sheet is a full snapshot of its framework (ST or LT; IBC and ICA excluded).
- Combined stage = 10+k for ST stage k, 20+k for LT stage k.
- Known at a Friday close only if the publication date is strictly before that Friday, because NSE gives a date and
  no time.
- `asm_days_in_stage` = Friday − effective date.

**Pledge**
- Promoter pledged-or-encumbered % of promoter holding, from shareholding XBRL. Both filing formats are parsed.
- Known time: submission date + 1 day for an unrevised filing; the revision broadcast for a revised one.
- A missing number is NaN with a reason code, never 0.
- `pledge_declared_none` = 1 when the filing has no number and its promoter yes/no flags all say false.

**Fundamentals**, from the Phase 0 feature view, as of Friday 15:30
- `de_ratio`: valid until the next scheduled balance-sheet filing + 60 days.
- `int_cover`.
- `ttm_core_pat_pos`, `ttm_core_pat_chg4`.
- `last_lag_days`, `late_filer` (lag > 120 days).

**Label**
- `label_crash` = 1 if the 63-session forward stock-specific path, cumprod(1 + rs − beta126 × mk) − 1, reaches
  −25%.
- It exists only where the 63rd session is on or before 2024-06-30, enforced by `assert_pre_holdout` on the exit
  dates.
- Dependent samples: weekly label dates overlap (63 sessions ≈ 13 weeks). The report gives the count of
  non-overlapping windows, and a design-effect n_eff from the within-date ICC of the label.

### Coverage: % of member rows non-NaN, by family and year

[measured: `diagnostics/research/explore/2026-11-21_risk_features.json`]

| Year | price | bands | band hits | GSM | ASM | pledge | pledge or declared none | D/E | int cover | TTM core PAT | lateness | ADV |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | 80.4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 95.5 |
| 2018 | 99.6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48.4 | 99.8 |
| 2019 | 99.4 | 0 | 0 | 0 | 100 | 0 | 0 | 0 | 52.9 | 54.2 | 97.6 | 99.4 |
| 2020 | 99.6 | 70.7 | 98.1 | 100 | 100 | 0 | 0 | 0 | 71.4 | 75.3 | 97.2 | 99.7 |
| 2021 | 97.7 | 62.9 | 100 | 100 | 100 | 17.4 | 17.5 | 0 | 84.7 | 90.5 | 95.6 | 98.2 |
| 2022 | 99.7 | 59.8 | 100 | 100 | 100 | 94.8 | 95.0 | 13.7 | 81.4 | 85.2 | 96.9 | 100 |
| 2023 | 99.8 | 61.7 | 100 | 100 | 100 | 96.2 | 96.4 | 81.4 | 77.7 | 80.7 | 97.1 | 100 |
| 2024 | 99.4 | 63.1 | 100 | 100 | 100 | 97.1 | 97.3 | 81.6 | 89.3 | 94.0 | 97.4 | 99.6 |
| 2025 | 99.8 | 56.3 | 100 | 100 | 100 | 63.9 | 96.1 | 80.6 | 89.0 | 94.8 | 98.6 | 99.9 |
| 2026 | 99.9 | 57.9 | 100 | 100 | 100 | 19.6 | 93.7 | 81.2 | 88.9 | 94.4 | 99.4 | 99.9 |

Why the gaps exist:
- **Bands: about 60%.** F&O stocks have no price band [assumed: NSE rule; consistent with about 40% of the Nifty 500
  being F&O names].
- **D/E before late 2022.** Balance-sheet tags appear in the results XBRL only from the Sep-2022 half-year. Equity is
  present on 97% of half-year filings from 2022Q3, and about 0% before [measured].
- **Pledge in 2021.** NSE lists only 2,102 filings submitted in 2021, against 7,900–9,900 a year afterwards. Its
  listings re-broadcast most 2021 filings in 2022, and the rest are not listed [measured].
- **Pledge in 2025–26.** The new filing format leaves the number out when promoters declare no pledge. Those rows are
  NaN with `pledge_declared_none = 1` (owner decision below).
- **GSM.** It is never above 0 for a member on a Friday: no member Friday matches a raw GSM remark [measured]. GSM
  covers small, illiquid names.
- **ASM.** Member-Fridays on ASM by year: 499, 1,277, 1,963, 596, 399, 1,053, 495, 151 for 2019–2026.

**Pledge sources** across 15,130 filings:

| Source | Filings |
|---|---|
| filed number | 11,079 |
| filed percentage | 406 |
| flag-only "no pledge" | 3,442 |
| no promoter context | 203 |

8,415 filings carry a filed 0.

In the frozen 400-filing sample (`pledge_sample_400.txt`, seed 1), the current parser gives 304 zeros (291 filed
numbers, 13 filed percentages), 94 positives and 2 NaN `flag_false_no_field`. The earlier figures (315, then 306,
then 310 zeros) came from different random draws while the fetch was still adding files. On a fixed sample, the
parser change moves only the flag-only filings from 0 to NaN.

**ASM timing** [measured]
- 3,723 circular attachments; 3,497 take effect at publication + 1 session.
- 222 do not: 204 take effect on the publication day, and 18 were published on a non-trading day and take effect 2
  sessions later.
- 4 state no effective date.
- 770 were published on a Friday. Under the strictly-before rule these count from the following week.

### Label: base rate and sample size (no feature-label statistic)

[measured: `2026-11-21_risk_features.json`]

**Totals**
- 170,976 labelled member-rows on 377 Fridays, 2017-01-06 to 2024-03-22.
- 13,829 positives; base rate **8.09%**.

**Base rate by year**

| 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 H1 |
|---|---|---|---|---|---|---|---|
| 5.99% | 7.63% | 10.97% | 12.94% | 8.11% | 5.54% | 5.15% | 5.70% |

**Concentration in bad markets**
- The 5 worst EW-market months inside the label window: 2020-03 (−28.9%), 2018-09 (−13.9%), 2019-07 (−10.4%),
  2020-02 (−7.8%), 2022-02 (−7.7%).
- 33.5% of positives have a forward window that overlaps one of them.

**Effective sample size**
- 29 non-overlapping 63-session windows (377 ÷ 13).
- Within-date ICC of the label 0.032 → design effect 15.6 → n_eff ≈ 10,900 rows.

### Tests (`tests/test_risk_features.py`, 7 passing)
- PIT truncation for each family: price, bands with GSM, ASM, pledge.
- Fundamentals validity window.
- Label never past 2024-06-30, and the guard raises on a bad token.
- NaN-not-zero: before each source starts, pledge missing-field reason codes, and ASM publication-versus-effective
  timing.

## D. 60/40 forward record (`forward/benchmark_60_40/`)

**Funds**
- 60%: Tata Nifty Midcap 150 Momentum 50 Index Fund, Direct Growth, AMFI **150738**.
- 40%: Kotak Arbitrage Fund, Direct Growth, AMFI **119771**.
- NAVs from api.mfapi.in, a mirror of AMFI's daily NAVs.

**Rules**
- Notional ₹20,00,000.
- Rebalance only when the index weight drifts more than 5pp.
- After-tax NAV from PR #212's lot engine (`taxlots.py`, vendored verbatim from commit 259546d, which includes the
  hash-seed fixes): 30% slab, no harvesting, financial-year settlement, full liquidation at this week's NAVs.

**Record**
- `ledger.jsonl` is append-only; each row stores its NAVs, its outputs, `recorded_at` and `prev_sha` (the SHA-256 of
  all prior bytes).
- `verify()` rejects an altered history. Tests: history never rewritten, tampering detected, deterministic replay
  (3 passing).
- The weekly health report gains one line: "60/40 forward record: week N, pre-tax NAV, after-tax NAV, status".
  Nothing else in the report changes.
- The Saturday lifecycle workflow appends the week. A failure there is a warning, not a job failure.

**Start date**
- First record: Friday 2026-11-27, the first Friday after the merges.
- A dry run for 2026-11-20 (not appended) gave:
  - index NAV 18.4758 (dated 2026-11-20); arbitrage NAV 43.7481 (dated 2026-11-19);
  - pre-tax ₹19,99,900, after-tax ₹19,99,880, index weight 0.60003, status OK [measured:
    `diagnostics/replica/phase0/benchmark_week_original.json`].

## Verification

### Artifact check
1. **Look-ahead through re-broadcast dates (pledge).** NSE's `broadcastDate` is the latest re-broadcast, not first
   publication. Ruled out:
   - unrevised filings are keyed to submission date + 1 day;
   - revised filings are keyed to the revision broadcast, so a revised value is never known before it was published.
2. **Same-day circulars (ASM).** A date-only stamp could leak an after-close circular into that Friday. Ruled out by
   the strictly-before rule; the cost is at most a one-week delay.
3. **Label overlap inflating the sample size.** Weekly 63-session windows overlap. Not hidden: 29 independent windows
   and the ICC-based n_eff are reported.
4. **Survivorship.** Rows are PIT members only. Prices use the backfilled OHLCV that includes delisted names; this
   was the membership audit's finding, not re-checked here [inferred].
5. **Zero-filling.** Every family is NaN before its source begins, and tests pin this.
6. **The worst-month share counting months outside the label window.** Found and fixed (added after first look):
   the first summary drew the 5 worst months from 2016 onwards, which made it 28.6%; restricted to the label window it
   is 33.5%.

### Independent re-derivation
- A `blind-replica` sub-agent, given only `risk_features_spec.md` and no code, recomputed 20 seeded, stratified
  (symbol, Friday) rows (`risk_sample_keys.csv`, seed 7) across every family, plus the 2026-11-20 week of D.
- The comparison is in `risk_replica_compare.json` (flag: more than 5% relative difference, or a NaN on only one side;
  codes must match exactly).

**Result** [measured: `risk_replica_compare.json`]

- **C:** all **540 of 540** (row, column) pairs agree, across 20 rows × 27 columns. The largest relative difference
  is 6.0e-15 (rv63), and every code matches exactly. Non-NaN on both sides, by family:

  | Family | Pairs |
  |---|---|
  | price | 171 |
  | bands | 113 |
  | ASM | 24 |
  | pledge | 50 |
  | fundamentals | 108 |
  | label | 19 |

  - **First pass: 2 of 540 differed.** Both were `pledge_declared_none` on 2021 Fridays before any filing was known
    (TORNTPHARM 2021-01-29, M&MFIN 2021-06-04): the original gave 0 and the replica NaN. The replica's reading is the
    NaN-not-zero one. The original was fixed in code, spec and test, and the saved panel was corrected (24,924 rows
    set to NaN).
- **D:** every field agrees on the same NAV files: index 18.4758 and arbitrage 43.7929, both dated 2026-11-20;
  pre-tax ₹19,99,900; after-tax ₹19,99,880; weight 0.60003; status OK.
  - api.mfapi.in served two different versions of the data on the same evening, one ending 11-19 and one including
    11-20.
  - Both sides were therefore run on the replica's saved responses (`nav_20261120/`).
  - The live record should log the NAV dates it used. It already does: `nav_*_date`.
- **Limits of this check.** The replica listed 47 readings in `replica_notes.md`. Matching does not test readings
  that both sides made the same way, so these remain open:
  - The D/E validity month: both use the month of period_end + 6 month-ends, which matches the statutory 45-day
    half-year and 60-day annual deadlines.
  - A member trading in BE on the Friday gets a NaN band (EQ-series only).
  - A revised pledge filing replaces its original and is known only from the revision.

### Added after first look
- Worst months restricted to the label window, as above.
- The pledge known time switched from `broadcastDate` to submission date for unrevised filings, after finding the
  re-broadcast dates.
- New-format pledge tags, and the `pledge_declared_none` column.
- Panel restricted to member rows, and the partial last week dropped. The first build kept every symbol.
- `pledge_declared_none` set to NaN (not 0) while no filing is known, after the blind replica read the spec that way.

None of these is a threshold or a model choice; no multiplicity is spent.
