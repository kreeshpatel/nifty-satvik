# NSE XBRL quarterly results: data quality (PARTIAL, broadcast years 2019–2020)

Class: DATA ENGINEERING. No signal, IC, return, backtest, trial or screen. Standing counts are not touched.
Goal link: this is the point-in-time quarterly EPS and line-item input for the January multi-signal model
(earnings surprise, quality), as named in the data-readiness audit (PR #213).

Status: **partial**. These numbers cover filings broadcast 2019-01-01..2020-12-31 (19,926 filings). Each later
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
| filings parsed / file-level failures | 19,926 / 13 (`no_reporting_period`, NONINDAS half-year) | [measured] `.cache/data_audit_v2/results_xbrl_build_log.json` |
| rows (current + ytd) | 35,147 (current 19,926: 19,925 Q, 1 H) | [measured] `diagnostics/research/explore/2026-11-19_results_xbrl_quality.json` |
| PIT N500 coverage, raw symbol → ISIN-bridged | 2019 94.4 → 97.6% · 2020 94.4 → 97.4% | [measured] same json |
| quarter completeness, either / standalone / consolidated (bridged) | 2019 85.9 / 84.5 / 72.6% · 2020 96.5 / 95.7 / 84.7% (3 quarters) | [measured] same json |
| parse failures (parse/unit/conflict), every field | 0.00% | [measured] same json |
| absent rate, current rows | revenue_ops 1.9–2.1% · pat 0.1–0.7% · eps 0.0% · depreciation 2.4–3.4% (mostly banks, which have no such tag) | [measured] same json |
| balance-sheet fields | 100% absent | [measured] see artifact 4 |
| EPS sanity: pairs · median gap · share > 5% · share > 5% and > ₹0.5 | 1,767 · 0.04% · 15.9% · 10.2% | [measured] same json |
| cross-check vs depth pkl (n = 45 matched): revenue within 1% / PAT within 1% | 91.1% / 95.6% (one outlier, SHK FY19, −34% / −49%) | [measured] same json |
| revisions: share of current rows · median days · same-day | 0.62% · 2.27 d · 47.2% | [measured] same json |
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
- The engine maps "Half yearly" to `no_reporting_period`; that is the 13 file failures above [inferred].

## Not yet done

- Years 2021–2026 (the fetch is running).
- Final numbers. Every figure above will be recomputed on the full build.
