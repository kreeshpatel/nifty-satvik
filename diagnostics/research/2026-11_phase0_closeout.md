# Phase 0 close-out: merges, tax-fallback diagnosis, L5 risk panel, 60/40 forward record

Date: 2026-11-20 · Class: ENGINEERING + MEASUREMENT only.
No candidate signal, model, AUC, feature-label statistic, trial or screen was computed here. **Standing counts on
`main`: screens 25 · sealed opens 4 · n_trials 3**, read from `diagnostics/research/n_trials.json` and
`label_screen_ledger.md`. Screen #25 arrived with the research-record merge (#220, section A); this work added none.

**Mission link.** This close-out finishes the data layer that the company engine (pre-registration 0153) and its
crash-risk layer L5 will be judged on, and starts the forward after-tax record of the 60/40 benchmark that any
strategy must beat.

## A. Merges

| Step | Result | Merge commit |
|---|---|---|
| PR #217 (XBRL results dataset) | merged after green CI | `d6624162404318b1bb587a7dfa6ea0e3e8111aec` |
| PR #218 (Phase 0), rebased onto main | merged after green CI | `a140e75a4ecefa65e60a12ff9e40795168db00fc` |
| PR #211 (robust sizing), rebased onto main | merged after green CI | `530db98aaa8c6152210221666c3c8ebc5c1123dd` |
| PR #212 (India tax practices), rebased and retargeted to main | merged after green CI | `b3f9cc1a0308cc65834b1e0dc3648e19b56c922c` |
| PR #214 (tax Monte Carlo), rebased and retargeted | merged after green CI | `1191105da31c7e01682673a41de2a246096d69fc` |
| PR #215 (blend cost and tax), rebased and retargeted | merged after green CI | `6e4288227edc46ef56676e8191a6a75ae36cbe24` |
| PR #220 (`claude/stoic-pascal-oys10b`: research record and screen #25), rebased | merged after green CI; counts 25 · 4 · 3 | `c61095b6038b78fac021bca1e10bd7a52dc03aae` |
| PR #219 (this close-out), rebased onto `c61095b` | merges last, after green CI | see the PR |

**First pass: merge 3 held.** On the first pass the stoic-pascal merge was held, because the branch carried #211,
#214 and #215. The owner then authorised the stack on 2026-11-20: #211 → #212 → #214 → #215, then the branch.

**Rebase notes**
- #211 conflicted with main only in `.gitignore`; both blocks were kept.
- Each later PR was rebased onto main with only its own commits.
- On the stoic-pascal rebase, the 9 commits already merged dropped out, and the #211 spike-gate commit, already on
  main, was skipped.
- No ledger or count file conflicted. `tests/test_standing_counts.py` passed (61).
- Every file difference from the old branch tip is explained by main's own changes since it branched.
- When #219 was rebased, `pipelines/build/fetch_nse_price_bands.py` conflicted (add/add). This branch's version was
  kept: it is the #211 file now on main, extended to the present.
- #210 and #216 are not merged.

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
- **PIT Nifty 500 member-quarters still missing after the basis fallback** (no re-fetch, owner decision 2026-11-20)
  [measured: `diagnostics/replica/phase0/missing_member_quarters.py` → `missing_member_quarters.json`].
  - A member-quarter is a symbol that was a member on the quarter-end date, from 2018-03-31 to 2026-06-30.
  - "Missing" means no row for that company-quarter on either basis with PAT filed or derived.

  | Year | Member-quarters | Missing | of which: company files, quarter absent | of which: symbol never files | Missing % |
  |---|---|---|---|---|---|
  | 2018 | 1,964 | 328 | 324 | 4 | 16.70 |
  | 2019 | 1,993 | 275 | 268 | 7 | 13.80 |
  | 2020 | 2,004 | 76 | 60 | 16 | 3.79 |
  | 2021 | 1,992 | 146 | 130 | 16 | 7.33 |
  | 2022 | 1,990 | 173 | 159 | 14 | 8.69 |
  | 2023 | 1,998 | 73 | 59 | 14 | 3.65 |
  | 2024 | 2,000 | 49 | 37 | 12 | 2.45 |
  | 2025 | 2,000 | 15 | 3 | 12 | 0.75 |
  | 2026 H1 | 1,000 | 10 | 4 | 6 | 1.00 |

  - Five members never appear in the results XBRL at all: ABBOTINDIA, BAYERCROP, KENNAMET, MCX and SPICEJET.
  - The 2018–19 gap reflects the XBRL regime starting in May 2018 [inferred].
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
- A filing with no number whose promoter yes/no flags all say "no pledge" is **0**, an explicit declaration (owner
  decision 2026-11-20), and `pledge_declared_none` = 1 marks it.
- Any other missing number is NaN with a reason code, never 0.

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

| Year | price | bands | band hits | GSM | ASM | pledge | of which declared none | D/E | int cover | TTM core PAT | lateness | ADV |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | 80.4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 95.5 |
| 2018 | 99.6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48.4 | 99.8 |
| 2019 | 99.4 | 0 | 0 | 0 | 100 | 0 | 0 | 0 | 52.9 | 54.2 | 97.6 | 99.4 |
| 2020 | 99.6 | 70.7 | 98.1 | 100 | 100 | 0 | 0 | 0 | 71.4 | 75.3 | 97.2 | 99.7 |
| 2021 | 97.7 | 62.9 | 100 | 100 | 100 | 17.5 | 0.0 | 0 | 84.7 | 90.5 | 95.6 | 98.2 |
| 2022 | 99.7 | 59.8 | 100 | 100 | 100 | 95.0 | 0.2 | 13.7 | 81.4 | 85.2 | 96.9 | 100 |
| 2023 | 99.8 | 61.7 | 100 | 100 | 100 | 96.4 | 0.2 | 81.4 | 77.7 | 80.7 | 97.1 | 100 |
| 2024 | 99.4 | 63.1 | 100 | 100 | 100 | 97.3 | 0.2 | 81.6 | 89.3 | 94.0 | 97.4 | 99.6 |
| 2025 | 99.8 | 56.3 | 100 | 100 | 100 | 96.1 | 32.2 | 80.6 | 89.0 | 94.8 | 98.6 | 99.9 |
| 2026 | 99.9 | 57.9 | 100 | 100 | 100 | 93.7 | 74.1 | 81.2 | 88.9 | 94.4 | 99.4 | 99.9 |

Why the gaps exist:
- **Bands: about 60%.** F&O stocks have no price band [assumed: NSE rule; consistent with about 40% of the Nifty 500
  being F&O names].
- **D/E before late 2022.** Balance-sheet tags appear in the results XBRL only from the Sep-2022 half-year. Equity is
  present on 97% of half-year filings from 2022Q3, and about 0% before [measured].
- **Pledge in 2021.** NSE lists only 2,102 filings submitted in 2021, against 7,900–9,900 a year afterwards. Its
  listings re-broadcast most 2021 filings in 2022, and the rest are not listed [measured].
- **Pledge in 2025–26.** The new filing format leaves the number out when promoters declare no pledge. By owner
  decision (2026-11-20) those rows are 0, with `pledge_declared_none = 1`: 18,145 member-Fridays, almost all in
  2025–26.
- **GSM.** It is never above 0 for a member on a Friday: no member Friday matches a raw GSM remark [measured]. GSM
  covers small, illiquid names.
- **ASM.** Member-Fridays on ASM by year: 499, 1,277, 1,963, 596, 399, 1,053, 495, 151 for 2019–2026.

**Pledge sources** across 15,130 filings:

| Source | Filings |
|---|---|
| filed number | 11,079 |
| filed percentage | 406 |
| declared none (flags only, set to 0) | 3,442 |
| no promoter context | 203 |

8,415 filings carry a filed 0.

In the frozen 400-filing sample (`pledge_sample_400.txt`, seed 1), the current parser gives 304 zeros (291 filed
numbers, 13 filed percentages), 94 positives and 2 flag-only filings. Those 2 were NaN until the owner's decision of
2026-11-20, and are now 0 coded `declared_none`. The earlier figures (315, then 306, then 310 zeros) came from
different random draws while the fetch was still adding files.

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
- NAVs from api.mfapi.in, a mirror of AMFI's daily NAVs. The owner accepted 150738 (2026-11-20).

**Not the same series as the long-window 60/40 study.** That study (`pipelines/diagnostics/explore_after_tax_comparison.py`,
2019-03-01 to 2024-06-28) differs from this record in four ways [measured: its docstring]:
- **Index leg:** the Nifty Midcap150 Momentum 50 TRI less a 0.30%/yr expense ratio, not fund 150738's NAV. Fund
  150738's first NAV is 2022-10-31, after that window opens, so the study could not have used it.
- **Other leg:** a modelled liquid fund (6.5%/yr gross less 0.15%/yr, gains taxed at slab), not the Kotak Arbitrage
  Fund (real NAVs, equity-taxed).
- **Rebalancing:** yearly each March, not on 5pp drift.
- **What carries over:** the forward record uses real fund NAVs, which include the fund's actual tracking error. The
  study's return numbers do not transfer to this record one for one [inferred].

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
- **Re-run after the declared-none = 0 decision** (2026-11-20): the replica updated its pledge rule from the spec
  alone.
  - 10 newly affected rows (seed 11, `risk_sample_keys_declared_none.csv`): **30 of 30** pairs agree.
  - The 20 original rows: **540 of 540** still agree; BSE and JSWHL pledge moved from NaN to 0 on both sides.
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
- Declared-none pledge filings set to 0 (owner decision 2026-11-20); the saved panel's pledge columns were recomputed
  with the same build functions. 18,145 member-Fridays changed from NaN to 0, and no other value moved.
- Pre-registration 0153 gained a dated note: D/E exists only from Sep-2022, so it may be tested only as an add-on to
  L5, never as a core input.

None of these is a threshold or a model choice; no multiplicity is spent.
