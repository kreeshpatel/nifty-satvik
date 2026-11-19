# NSE XBRL quarterly results: data quality (PARTIAL, broadcast years 2019–2020)

Class: DATA ENGINEERING. No signal, IC, return, backtest, trial or screen. Standing counts are not touched.
Goal link: this is the point-in-time quarterly EPS and line-item input for the January multi-signal model
(earnings surprise, quality), as named in the data-readiness audit (PR #213).

> **Correction:** the first push of PR #217 (commit a9565e9) chose the wrong current-quarter context in 29
> filings from 2019–2020. Those files carry two contexts of quarter length, and the parser broke the tie
> by context id. It took `FourD`, which in these files is the *prior* quarter (for example, Jan–Mar 2019
> inside a Jun-2019 filing). Rule (a) below now chooses the context whose end date equals the listing's
> period end, so 28 of the 29 now take `OneD` and all 29 have the correct quarter-end. In the old build,
> revenue, PAT and EPS for those 29 rows belonged to the previous quarter [measured, diff of the old and
> new builds].

Status: **partial**. These numbers cover filings broadcast 2019-01-01..2020-12-31 (19,939 filings). Each later
year is added on the same PR as its fetch completes.

## Method

**Source.** For each NSE financial-results filing, the XBRL instance it links to.

- Legacy listing: `api/corporates-financial-results`, period=Quarterly. Half-Yearly returned 0 rows. Annual
  rows mostly repeat XBRL URLs already in the quarterly listing.
- Integrated-filing listing: `api/integrated-filing-results`, type "Integrated Filing- Financials", from
  2025-04. **This listing was added after first look.** After 2025-03 the legacy endpoint returns only 0–31
  rows a month.
- The harvester is `pipelines/build/harvest_results_xbrl.py`. Raw files sit gzipped under `data/xbrl_raw/`,
  which is gitignored and never committed. The resumable manifest `data/xbrl_raw/manifest.csv` is committed.

**Parser.** `nq/data/results_xbrl.py:97` (`parse_xbrl`) produces one row per (filing, duration context).

- `context_role="current"`: the shortest context, i.e. the reported quarter (`results_xbrl.py:174`).
- `context_role="ytd"`: the year-to-date context.
- Values are taken as written:
  - unit INR is rupees; `decimals` is precision only.
  - Any other unit gives NaN with reason "unit".
  - An absent tag gives NaN with reason "absent". Never 0.
  - Aliases and their order are fixed at `results_xbrl.py:37`.

**Point-in-time rule.**

- Availability is the listing's `broadcast_ts`. Callers use `as_of` (`results_xbrl.py:228`).
- A revision is its own row with `filing_seq >= 1` (`results_xbrl.py:218`). The original is never overwritten.
- `latest_per_period` picks the newest filing known at the as-of date.
- Tests: `tests/test_results_xbrl_pit.py`. They check that an unbroadcast filing is invisible and that
  truncating the data at a date gives the same answer as filtering it.

**Metric definitions.** All are in `pipelines/diagnostics/results_xbrl_quality.py`.

- **Universe.** PIT Nifty 500 = members on 30 June of each year (`load_membership`, line 24).
  - Membership mixes filing-day and current tickers. A member matches a filing on either the filing's own
    symbol or the latest symbol its ISIN files under in the full 2019–2026 listing (`bridge_symbols`, line 150).
  - **The ISIN bridge was added after first look.** Without it, renamed names such as COFORGE/NIITTECH counted
    as uncovered.
  - Numbers are reported both with and without the bridge.
- **Coverage** (line 32): share of members with at least one parsed filing broadcast in that calendar year.
- **Completeness** (line 38): (member × quarter-end in year Y) pairs that have a current-quarter row, split
  into standalone, consolidated and either.
  - Only quarter-ends at least 60 days before the last broadcast in the data are counted. That leaves 3
    quarters for 2020 in this partial build.
- **Parse failures** (line 59): per field and broadcast year, over current rows.
  - `fail_pct`: reason is parse, unit or conflict.
  - `absent_pct`: the tag is missing.
- **EPS sanity** (line 71). For each (symbol, consolidated, fiscal year ending March), with original filings
  only (`filing_seq == 0`):
  - Four quarterly basic EPS are summed and compared with the FY basic EPS.
  - FY EPS comes from the FY year-to-date context inside the March-quarter filing.
  - `gap = |sum4 − fy| / max(|fy|, 0.01)`. A gap over 5% is flagged.
- **Cross-check** (line 95). Sample: 50 random FY contexts with a March period end, original filings only,
  seed 20261119.
  - Compared against `data/fundamentals_pit_depth.pkl` (Screener annual figures in ₹ crore). XBRL values are
    divided by 1e7.
  - The consolidated row is used if the filing set has one, else the standalone row. This rule was fixed
    before looking.
- **Revisions** (line 127): `filing_seq >= 1` on current rows. Time to revision = its broadcast minus the
  original's broadcast.
- **Timing** (line 141): broadcast time of day in IST, one per filing, bucketed <09:15, 09:15–15:30, >15:30.

**Dependence.** Each filing is one sample. Standalone and consolidated filings of the same company-quarter are
separate files, so they are both counted. No statistic here is used for inference.

**Anchor.**

- The rule-4 anchors (live A 650.2R, 0001 21.73% / 1.130) are strategy numbers and do not apply to a data
  build. **Not reproduced, by design** [inferred].
- The data-level anchor is the depth-pkl cross-check below. It is an independent source, matched before any
  other number was read.

## Results (2019–2020)

| item | value | label |
|---|---|---|
| files fetched OK / 404 (whole fetch so far) | 19,852 / 148 at 20,000 | [measured] `.cache/data_audit_v2/xbrl_fetch.log` |
| filings parsed / file-level failures | 19,939 / 0 (the 13 earlier label-only failures are recovered; see the edge-case fixes) | [measured] `.cache/data_audit_v2/results_xbrl_build_log.json` |
| rows (current + ytd) | 35,173 (current 19,939: 19,938 Q, 1 H) | [measured] `diagnostics/research/explore/2026-11-19_results_xbrl_quality.json` |
| PIT N500 coverage, raw symbol → ISIN-bridged | 2019 94.4 → 97.6% · 2020 94.4 → 97.4% | [measured] same json |
| quarter completeness, either / standalone / consolidated (bridged) | 2019 85.9 / 84.6 / 72.6% · 2020 96.5 / 95.7 / 84.7% (3 quarters) | [measured] same json |
| parse failures (parse/unit/conflict), every field | 0.00% | [measured] same json |
| absent rate, current rows | revenue_ops 1.9–2.1% · pat 0.1–0.7% · eps 0.0% · depreciation 2.4–3.4% (mostly banks, which have no such tag) | [measured] same json |
| balance-sheet fields | 100% absent | [measured] see artifact 4 |
| EPS sanity: pairs · median gap · share > 5% · share > 5% and > ₹0.5 | 1,783 · 0.04% · 15.9% · 10.3% | [measured] same json |
| cross-check vs depth pkl (n = 45 matched): revenue within 1% / PAT within 1% | 91.1% / 95.6% (one outlier, SHK FY19, −34% / −49%) | [measured] same json |
| revisions: share of current rows · median days · same-day | 0.60% · 1.38 d · 48.3% | [measured] same json |
| broadcast timing <09:15 / 09:15–15:30 / >15:30 | 2019: 0.4 / 41.2 / 58.3% · 2020: 2.0 / 40.8 / 57.2% | [measured] same json |

## Artifact check: could the method have made these numbers?

1. **Ticker renames make coverage look low.** Ruled out by the ISIN bridge, which raised coverage from 94.4% to
   about 97.5%.
   - The members still uncovered are insurers and a few other companies: HDFCLIFE, SBILIFE, ICICIGI,
     ICICIPRULI, GICRE, NIACL, BAYERCROP, NESTLEIND, MCX, ABBOTINDIA and others.
   - These have no row in the legacy Quarterly listing, or only rows whose XBRL link is "-".
   - This is a source gap, not a parser gap [measured, listing JSON].
2. **2019 completeness is low because of the pipeline.** Mostly ruled out. The per-quarter breakdown for 2019
   is Mar 83.5%, Jun 76.4%, Sep 87.7%, Dec 96.0%. For the misses that were traced:
   - RECLTD and AXISBANK Sep-2019: the listing row has XBRL link "-".
   - BANKBARODA Mar-2019: NSE returns 404, and the retry also returns 404.
   - The source is thinner in early 2019 [measured]. These names were spot-checked, not the full set
     [inferred for the rest].
3. **The EPS gap is a parser artifact.** Ruled out for most cases.
   - 10.8% of the pairs flagged on EPS agree within 1% on PAT.
   - Top cases have FY EPS filed as 0.00 (DTIL, IBREALEST, PRUDMOULI) or a single quarter's EPS mis-keyed
     (ANDHRACEMT).
   - These are filer-entered XBRL errors. EPS also does not sum exactly across quarters when share count
     changes.
   - **Users should not trust raw quarterly EPS without a PAT ÷ shares cross-check** [inferred].
4. **Balance sheet 100% absent is a parser bug.** Ruled out. NSE results XBRL instances carry only duration
   contexts (OneD/FourD plus the operating-expense sub-contexts) and no instant contexts or `Assets` facts
   [measured, 5 Sep-2019 instances inspected]. The balance-sheet columns stay NaN with reason "absent". A
   balance sheet needs a different source.
5. **`broadcast_ts` is late, not early, compared with the actual disclosure.** Measured on the timestamp
   embedded in each XBRL file name (DDMMYYYY):
   - Listing date minus file date ≥ 0 in 100% of filings, so there is no look-ahead.
   - 77.7% are on the same day, 13.1% are more than 7 days later and 4.3% more than 30 days later (max 550).
   - Example: AXISBANK Dec-2019 consolidated, file 23-Jan-2020, listing 09-Jul-2020.
   - The conservative listing date is kept as availability [measured; that file stamps are public dates is
     not assumed].
6. **Open or partial year counted as complete.** Ruled out. Completeness drops quarter-ends within 60 days of
   the last broadcast, so 2020 Q4 is excluded.

## Blind replica (step 6)

- A `blind-replica` sub-agent saw only the written spec, not this code. It wrote
  `diagnostics/replica/results_xbrl/replica_parse.py` and parsed 30 random files (seed 20261119), producing
  `replica.csv`.
- Compared afterwards against the engine's current rows:
  - 30/30 files matched.
  - **0 mismatches** in 270 value cells (9 fields × 30), and 0 in period dates, context id, consolidated flag
    and symbol. [measured] `diagnostics/replica/results_xbrl/replica.csv`
- The replica found no `ISIN` fact in any of the 30 files. The build fills `isin` from the listing row
  [measured].
- Spec ambiguities the replica raised that this sample did not exercise:
  - the meaning of the ReportingQuarter labels in files with no dates ("Half yearly" = Q2, "Yearly" = Q4);
  - tie-breaks among dimensional `One*` contexts.
- Both are now fixed; see the edge-case fixes below. After the fix the comparison was re-run: still 0 mismatches.

## Edge-case fixes (owner request, after the blind replica)

**1. Label-only periods.** These are files that carry a ReportingQuarter text ("Half yearly", "Yearly" …)
and no period dates. The period now comes from the listing row's `fromDate`/`toDate`
(`nq/data/results_xbrl.py`, label-only block in `parse_xbrl`).

- The current (`OneD`) row uses the listing start only when it spans one quarter. Otherwise it is the
  quarter ending at the listing end, because "Yearly" filings list the cumulative FY.
- The year-to-date row (`FourD`) runs from DateOfStartOfFinancialYear to the listing end.
- With no listing period, an unambiguous "<n> quarter" label plus the FY start is used.
- Failing both, the rows are kept with NaN dates and `period_reason = "period_label_only"`. They are never
  dropped.

Results:

- **All 13 of the 13 failed files are recovered** (all "Half yearly" NONINDAS, Jul–Sep quarters)
  [measured, build log].
- 173 files in total now take their period from the listing.
- 0 files are left label-only.
- The 160 files previously derived from the label keep their quarter-ends. Their current-row start dates
  are unchanged; the year-to-date rows now take their start from the FY start.

**2. Several current-period candidates in one file** (`_rank_current`).

- Candidates are the duration contexts in the same length class (Q/H/9M/FY) as the shortest one.
- They are ranked by: (a) end date equals the listing's period end; (b) consolidated flag equals the
  listing's flag; (c) most tagged values. After that, an id starting "One", then the id, as a pure
  tie-break.
- Each row records `context_id`, `n_current_candidates` and `current_rule`.

Results:

- **102 of 19,939 files had more than one candidate.** All 102 were settled by rule (a); none needed
  (b) or (c) [measured].
- Of the 102, 29 changed their pick (see the Correction above). The other 73 already picked the right
  context.
- Unit tests: one per rule (a, b, c), single-candidate, label-only from the listing, label-only kept with
  NaN dates, and the cumulative "Yearly" listing. All are in `tests/test_results_xbrl_pit.py`.

**Replica re-run on the same 30 files after the fix:** 0 mismatches across 270 values plus the period
dates, context id and consolidated flag. One of the 30 files had two candidates [measured].

## Period-sanity guard (owner request)

**Method.** `nq/data/results_xbrl.py`, `period_sanity`. It runs in the build and flags rows; it never
drops them.

- `lag_days` = broadcast calendar date (IST) − `period_end`.
- `period_flag` holds the reasons, `;`-joined:
  - `published_before_period_end`: `lag_days < 0`
  - `lag_over_120d`: `lag_days > 120`
  - `not_quarter_end`: `period_end` is not a Mar/Jun/Sep/Dec month-end
  - `no_period_end`
- The build exits with code 2 and a STOP line when more than 0.5% of rows have `lag_days < 0`
  (`pipelines/build/build_results_xbrl.py`).
- The counts, lag distribution and worst rows below come from `period_flags` in
  `pipelines/diagnostics/results_xbrl_quality.py`.

**Results (2019–2020)** [measured] `diagnostics/research/explore/2026-11-19_results_xbrl_quality.json`

- `lag_days < 0`: **0 rows (0.000%)**, so the stop did not trigger.
- `not_quarter_end`: 0 rows. `no_period_end`: 0 rows.
- `lag_over_120d`: 1802 of 35173 rows. By broadcast year: 2019: 618,
  2020: 1184. That is 912 current rows (4.57% of current rows)
  and 890 year-to-date rows. 31 of the flagged rows are revisions.
- lag_days, current Q rows (n=19938): median 44, p95 116,
  max 954, min 5.
- lag_days, FY rows (n=4866): median 81, p95 160, max 954,
  min 10.
- The flagged current rows cluster in the Mar-2020 quarter (458) and the Mar-2019 quarter (224).
- Reading of the flags [inferred]:
  - Mar-2020 fits SEBI's COVID-19 extension of results deadlines.
  - Mar-2019 fits the late XBRL broadcast dates in the legacy listing (artifact 5).
  - The extreme tail is companies catching up on filings years late. The worst 20 below are all of this
    kind: EASTSUGIND, UNITY, PRUDMOULI, JYOTISTRUC and JVLAGRO filing their 2018 quarters in late 2020.
  - None of the worst 20 looks like a wrong-period assignment: each period matches the company's own
    sequence of filings.
- Use: an earnings-surprise caller should treat `lag_over_120d` rows as stale news. They are kept because
  the dates are true.

Worst 20 flagged rows by |lag_days|:

| symbol | period | context | broadcast (IST) | lag_days | flag |
|---|---|---|---|---|---|
| EASTSUGIND | 2017-04-01..2018-03-31 (FY, ytd) | FourD | 2020-11-09 11:59 | 954 | lag_over_120d |
| EASTSUGIND | 2018-01-01..2018-03-31 (Q, current) | OneD | 2020-11-09 11:59 | 954 | lag_over_120d |
| UNITY | 2018-01-01..2018-03-31 (Q, current) | OneD | 2020-10-08 17:47 | 922 | lag_over_120d |
| UNITY | 2017-04-01..2018-03-31 (FY, ytd) | FourD | 2020-10-08 17:47 | 922 | lag_over_120d |
| PRUDMOULI | 2018-04-01..2018-06-30 (Q, current) | OneD | 2020-10-23 18:10 | 846 | lag_over_120d |
| PRUDMOULI | 2018-04-01..2018-06-30 (Q, current) | OneD | 2020-10-23 18:04 | 846 | lag_over_120d |
| JYOTISTRUC | 2018-04-01..2018-06-30 (Q, current) | OneD | 2020-10-15 12:02 | 838 | lag_over_120d |
| JVLAGRO | 2018-04-01..2018-06-30 (Q, current) | OneD | 2020-08-28 13:23 | 790 | lag_over_120d |
| EASTSUGIND | 2018-07-01..2018-09-30 (Q, current) | OneD | 2020-11-02 15:17 | 764 | lag_over_120d |
| EASTSUGIND | 2018-04-01..2018-09-30 (H, ytd) | FourD | 2020-11-02 15:17 | 764 | lag_over_120d |
| PRUDMOULI | 2018-07-01..2018-09-30 (Q, current) | OneD | 2020-10-23 18:28 | 754 | lag_over_120d |
| PRUDMOULI | 2018-04-01..2018-09-30 (H, ytd) | FourD | 2020-10-23 18:28 | 754 | lag_over_120d |
| PRUDMOULI | 2018-07-01..2018-09-30 (Q, current) | OneD | 2020-10-23 18:43 | 754 | lag_over_120d |
| PRUDMOULI | 2018-04-01..2018-09-30 (H, ytd) | FourD | 2020-10-23 18:43 | 754 | lag_over_120d |
| BILENERGY | 2016-10-01..2016-12-31 (Q, ytd) | FourD | 2019-01-18 11:12 | 748 | lag_over_120d |
| JYOTISTRUC | 2018-04-01..2018-09-30 (H, ytd) | FourD | 2020-10-15 12:06 | 746 | lag_over_120d |
| JYOTISTRUC | 2018-07-01..2018-09-30 (Q, current) | OneD | 2020-10-15 12:06 | 746 | lag_over_120d |
| JVLAGRO | 2018-07-01..2018-09-30 (Q, current) | OneD | 2020-08-28 13:29 | 698 | lag_over_120d |
| JVLAGRO | 2018-04-01..2018-09-30 (H, ytd) | FourD | 2020-08-28 13:29 | 698 | lag_over_120d |
| SUNILHITEC | 2017-01-01..2017-03-31 (Q, ytd) | FourD | 2019-02-07 17:43 | 678 | lag_over_120d |

## Late filers by universe membership, and not-found by year (owner request)

**Method.** Both are in `pipelines/diagnostics/results_xbrl_quality.py`.

- `late_by_membership`: `lag_over_120d` rows split by PIT Nifty 500 membership *on the broadcast date*.
  A row counts as a member when either its filing-day symbol or its ISIN's latest symbol is in the index
  that day.
- `not_found_by_year`: HTTP 404 ÷ attempted URLs, by listing broadcast year, taken from
  `data/xbrl_raw/manifest.csv`.
  - The quality script exits with code 2 and a STOP line if any *complete* year exceeds 2%.
  - **Restricting the stop to complete years was added after first look.** Run mid-fetch, the plain rule
    stopped on 2022, which so far holds 16 sample fetches with 2 not-found (12.5%).
  - Once the fetch ends every year is complete, so the final check is the owner's rule as written.

**Results (2019–2020)** [measured] `diagnostics/research/explore/2026-11-19_results_xbrl_quality.json`

| current-quarter rows, lag > 120 d | 2019 | 2020 | both |
|---|---|---|---|
| PIT N500 member at broadcast | 61 / 2,903 (2.10%) | 67 / 3,653 (1.83%) | 128 / 6,556 (**1.95%**) |
| not a member | 224 / 5,764 (3.89%) | 560 / 7,619 (7.35%) | 784 / 13,383 (5.86%) |

Across all rows (current and year-to-date), the late rate is 2.16% for members and 6.57% for non-members.
The rate that matters for the model is therefore about a third of the headline 4.57%.

| not-found (404) | 2019 | 2020 | 2021 (partial) |
|---|---|---|---|
| attempted / listed | 8,815 / 8,815 | 11,272 / 11,272 | 10,454 / 11,622 |
| 404 | 148 (**1.68%**) | 0 (0.00%) | 42 (0.40%) |

Every complete year is under 2%, so the stop did not trigger. 2019 is the closest to the line.

## Not yet done

- Years 2021–2026 (the fetch is running).
- Final numbers. Every figure above will be recomputed on the full build.
