# Company engine, Phase 0: data panels, holdout guard and a calibrated gate harness

**Class:** engineering and measurement only. No candidate signal was computed or evaluated, and no screen or trial
was run. Standing counts are untouched: screens 24 · sealed opens 4 · n_trials 3, read from the ledgers. The task
brief quoted 25 screens; the ledger says 24, and the ledger is the authority.

**Goal link.** Phase 0 builds and calibrates the inputs the January company-engine study needs, so that study can run
as pre-registered screens plus one trial, judged against 60/40 after tax.

**Branch.** PR #217 was still open, so this branch (`eng/company-engine-phase0`) was cut from its head, `c884ec1`.

**Pre-registration.** `diagnostics/research/preregistry/0153-company-engine.md`, status DRAFT, for signature at the
January 2027 review. It was committed first, as `b0eb693`, before any Phase 0 code.

## Method

### Holdout guard

[`nq/research/holdout.py`](../../nq/research/holdout.py)

- `assert_pre_holdout` raises `HoldoutViolation` when a series' last date is after 2024-06-30, unless it is given an
  unseal token.
- A valid token has the form `AMD-YYYY-MM-…` and stands for a signed owner amendment.
- The layer-gate harness passes the **exit date** of every forward return through the guard. A signal is kept only if
  its exit date is on or before 2024-06-30.
- Tests: `tests/test_holdout_guard.py` (5) and `tests/test_layer_gate.py::test_gate_never_reads_past_train_end`.

### Pre-2019 XBRL extension

- The NSE legacy listing was probed month by month for 2013-01..2018-12, for Quarterly, Half-Yearly and Annual
  results.
- The integrated-filing listing was not probed before 2024-10. That regime did not exist earlier.
- A row counts as having an XBRL link only if the link ends in `.xml`. Earlier years carry a placeholder link
  (`…/corporate/xbrl/-`). Counting that placeholder first gave a false 100% availability; it was corrected before any
  fetch was planned.
- Files were fetched with the PR #217 pipeline: the same manifest, resumable, newest year first, at most 2 requests
  per second to the archive host.
- The dataset was then rebuilt, and the PR #217 quality report re-run with 2018 included.

### Quarterly fundamentals panel

[`nq/data/fundamentals_q.py`](../../nq/data/fundamentals_q.py); rules in the module docstring.

**Rows and keys**
- One row per (company, fiscal quarter, filing). Revisions are separate rows (`version` > 0).
- The company key is the ISIN, falling back to the symbol when the ISIN is missing.

**Basis**
- Consolidated if consolidated figures exist for at least 80% of the company's reported quarters; otherwise
  standalone.
- One basis for the whole history; it is never mixed within a company.

**Discrete quarters**
- Taken from the 3-month context where present.
- Otherwise derived: cumulative context minus the cumulative context one quarter shorter (e.g. Q4 = FY − 9M), using
  the version known at the later filing's broadcast. Derived rows are flagged `derived`, and their EPS is left NaN.

**Earnings and shares**
- Core PAT = PAT − exceptional items × (1 − 25.17%). The 25.17% rate is **[assumed, CONFIRM]**: the Section 115BAA
  rate with surcharge and cess.
- Shares = paid-up equity ÷ face value, else PAT ÷ basic EPS.

**Splits and bonuses**
- **Scope change:** the repo's corporate-action registers (`data/corporate_actions*.csv`) list demergers only, with no
  split or bonus. Detection therefore uses each company's own paid-up share count instead.
- A split or bonus is a quarter-on-quarter step within 3% of a standard ratio (1.5, 2, 2.5, 3, 4, 5, 6, 10, 20, or the
  inverse for a consolidation).
- `share_factor` is the cumulative product of those steps up to the row's quarter, so it only uses the past.
- adj_shares = shares ÷ share_factor; adj_core_eps = core PAT ÷ adj_shares.

**Financials**
- Flagged if the company uses the bank or insurer taxonomy (no RevenueFromOperations tag while total income is
  tagged, in at least 50% of its current rows), or if its name matches
  `BANK|FINANC|FINSERV|INSURANCE|ASSURANCE|CREDIT|LEASING|HOUSING FIN`.
- Financials are kept, flagged.

**Trailing twelve months**
- TTM sums this quarter and the latest-known versions of the previous three quarters at this row's broadcast.
- It is never forward-filled: a missing input gives NaN plus a reason code.

**Tests:** `tests/test_fundamentals_q.py` (7). They cover PIT truncation, basis never mixed, a synthetic 1:1 bonus
adjustment, a rights issue left unadjusted, NaN-not-zero, Q4 = FY − 9M, and the session rule.

### EPS non-additivity diagnosis

PR #217 flagged pairs where the sum of the four original quarterly basic EPS differs from the full-year basic EPS by
more than 5%. Each flagged pair takes the first cause that fits, in a fixed order:

1. **Derived-quarter artefact.** A quarterly EPS equals a cumulative EPS in the same filing, or Q4 EPS equals FY EPS.
2. **Basis mix.** The opposite basis's FY EPS matches the quarterly sum.
3. **Restatement.** Latest versions close the gap, and a revision exists.
4. **Share-count change.** PAT adds up within 2% while the implied share count moves more than 2% inside the year.
5. **Unexplained.** None of the above.

The **after-fix** measure applies to every company-year on its single basis, using original quarters: the sum of
quarterly PAT against FY PAT, both over one adjusted-share denominator. That leaves PAT additivity as the only source
of gap.

### Event panel

`data/events_results.parquet` is the same rows as the fundamentals panel, plus the first tradable session.

- A broadcast on a session day before 15:30 counts that day, pre-open included.
- At or after 15:30, or on a non-session day, it counts the next session.
- Sessions are the cleaned OHLCV calendar (2016-01-01..2026-06-29), then config `NSE_HOLIDAYS` through 2026-12-31.
- The file holds no returns.

### Peer clusters

`data/peer_clusters.parquet` is rebuilt at every month end.

- **Universe:** PIT Nifty 500 members with at least 200 valid returns in the trailing 252 sessions, using prices up to
  that month end only.
- **Residuals:** each member's daily return minus beta × the members' equal-weight return.
- **Distance:** √(2(1 − ρ)) on pairwise residual correlations (minimum 150 overlapping days, otherwise ρ = 0).
- **Clustering:** average linkage, k = round(N/15).
- **Stability:** adjusted Rand index between consecutive months, on common members.
- **Range:** prices end 2026-06-29, so the clusters end there.

### Layer-gate harness

[`nq/research/layer_gate.py`](../../nq/research/layer_gate.py); every definition is in the module docstring.

- **Market:** the equal-weight return of the names the score covers. The first version used all members. That biased
  the null, because a seasoned-name subset was being compared with a market that includes fresh listings: the null t
  mean was +0.48 on 5 seeds. It was fixed before the reported calibration, which is **added after first look**.
- **Event-day cost:** 2 × (brokerage + STT + MID-cap slippage) per leg, from `config`.
- **Tax drag:** 20% × 1.04 on positive alpha.
- **Calibration:** `pipelines/diagnostics/phase0_calibrate.py`.

## Results

### Pre-2019 availability and fetch

[measured] `diagnostics/research/explore/2026-11-20_phase0_panels.json` (`pre2019_probe`) and
`.cache/data_audit_v2/pre2019_fetch.log`.

| year | quarterly rows | annual rows | half-year rows | rows with an XBRL file |
|---|---|---|---|---|
| 2013 | 7,886 | 2,499 | 64 | 0 |
| 2014 | 7,800 | 2,347 | 56 | 0 |
| 2015 | 7,637 | 2,309 | 0 | 0 |
| 2016 | 9,815 | 2,605 | 0 | 0 |
| 2017 | 11,717 | 2,908 | 0 | 0 |
| 2018 | 10,921 | 4,347 | 0 | 9,074 (5,955 quarterly + 3,119 annual) |

- **First month with XBRL links: 2018-05.** Before that, NSE lists results without a machine-readable file, so
  **2013–2017 cannot come from XBRL**. That is an availability fact, not a fetch failure.
- **2018 fetch:** 5,771 unique files attempted. 5,730 succeeded and 41 returned 404 (0.71%; 1.28% for members). It
  took 3,010 s at 0.52 s per file, with 0 persistent-403 stops.
- **Rebuilt dataset:** 199,612 rows from 111,677 filings.
  - 6 file failures:
    - 4 raw files were not found, because the broadcast year in the listing differs from the folder year.
    - 1 file has malformed XML.
    - 1 file has no reporting period.
  - 3,605 files had more than one candidate for the current context.
  - Rows published before their period end: 0.000%, so the stop did not trigger.
- **2018 quality** [measured] `diagnostics/research/explore/2026-11-20_results_xbrl_quality_with2018.json`:
  - PIT Nifty 500 coverage, ISIN-bridged: 96.9%.
  - Quarter completeness (either basis, 4 quarters): 83.3%; standalone 83.0%, consolidated 43.6%.
  - Parse failures: 0.00% for revenue, PAT and EPS.
  - FY2019 EPS check: 17.3% of pairs gap more than 5%, in line with the other years (15.4–17.5%).

### Fundamentals panel

[measured] `…/2026-11-20_phase0_panels.json` (`fundamentals`).

- **Size:** 63,987 rows covering 3,298 companies and 61,809 original quarters, plus 2,178 revision rows. 450 rows are
  derived quarters.
- **Basis:** consolidated for 2,166 companies, standalone for 1,132.
- **Financials:** 142 companies flagged.
- **Splits and bonuses:** 1,011 detected. RELIANCE's 2024 1:1 bonus, for example, gives a factor of 2.
- **Coverage:** adjusted core EPS is present in 98.96% of original quarters; TTM PAT in 75.31%. TTM is NaN by rule
  where a prior quarter is missing, including each company's first three quarters.
- **Quarters lost to the single-basis rule** (share of company-quarters with a current filing but no panel row, by
  quarter-end year):
  - 2017: 16.7%; 2018: 27.7%; 2019: 4.5%; 2020 onward: ≤ 2.4%.
  - Cause [inferred]: before FY2019-20, quarterly consolidated results were optional. So a company that is "mostly
    consolidated" loses its standalone-only early quarters. See the owner decisions.

### EPS non-additivity

[measured] `…/2026-11-20_phase0_panels.json` (`fundamentals.eps_diagnosis`).

The anchor reproduces first: on the PR #217 dataset (2019+), the rule gives **19,243 pairs, 16.41% over 5%**,
matching PR #217's 16.4%. With 2018 added:

| cause (first match) | pairs | share of flagged |
|---|---|---|
| share-count change | 1,780 | 53.1% |
| unexplained | 1,130 | 33.7% |
| derived-quarter artefact | 217 | 6.5% |
| restatement | 117 | 3.5% |
| consolidated/standalone mix | 110 | 3.3% |
| **total flagged** | **3,354 of 20,380** | **16.46% of pairs** |

- **Unexplained** is 5.54% of all pairs. 52 of the 1,130 look like ×10ⁿ scale typos.
- **After the fix** (single basis, one adjusted-share denominator), 11,147 company-years remain. Of those, **4.99% gap
  more than 5%**, with a median of 0.000%.
- Each quarter on its own adjusted share count instead would leave 11.97%. That is genuine EPS non-additivity under
  QIPs and buybacks, which is why ranking should use PAT ÷ one denominator.

### Event panel

[measured] `…/2026-11-20_phase0_panels.json` (`events`).

- **Events:** 63,987, of which 61,809 are originals.

  | year | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|---|---|---|---|
  | events | 3,326 | 4,983 | 6,532 | 6,685 | 6,733 | 7,546 | 8,221 | 9,278 | 10,683 |

- **Timing:** 67.8% are broadcast after the close, and 25.9% are tradable the same day.
- **Sessions:** every event maps to a session (0 NaT), and 0 rows needed the weekday approximation.

### Peer clusters

[measured] `…/2026-11-20_phase0_panels.json` (`clusters`).

- **Coverage:** 105 month ends, 2017-10..2026-06, with a median of 481 members and median k = 32.
- **Month-to-month stability (median ARI by year):**

  | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|---|---|---|---|
  | 0.26 | 0.29 | 0.35 | 0.42 | 0.37 | 0.41 | 0.34 | 0.43 | 0.49 | 0.51 |

  Over all months the median is 0.386, with p10 0.294.
- **Cluster sizes:** median 11, p90 31, maximum 105, and no singletons. The largest cluster holds a median 13% of
  members.
- **Reading [inferred]:** the clusters are only moderately stable, with roughly 60% of pair assignments churning month
  to month. That matters for L4, which is gated on stable clusters (prereg 0153 a).

### Harness calibration

[measured] `diagnostics/research/explore/2026-11-20_phase0_calibration.json`.

- **Window:** weekly signal dates 2016-01..2024-06-21, with every exit on or before 2024-06-28. NMS coverage starts in
  2017-02 (it needs 252 sessions).

**Anchor: 0001's NMS ranker**

| statistic | value |
|---|---|
| correlation with itself | 1.000 |
| decile spread, 21 sessions | +3.14%, t 2.65 |
| decile spread, 63 sessions | +8.98%, t 3.06 |
| rank IC, 21 sessions | 0.068, t 4.52 |
| rank IC, 63 sessions | 0.110, t 4.71 |
| gross alpha (top decile, weekly) | +25.2%/yr, t 3.51, β 0.89 |
| gross alpha, tradable slice | +20.1%/yr, t 2.71 |
| delay sweep, 0–5 sessions | t 3.45–3.93 |
| decline-slope t | −1.98 |
| turnover | 8.5×/yr |
| friction | 17.2%/yr, below alpha |

The momentum spread is positive, so the anchor reproduces.
- **Plausibility [inferred]:** the gross alpha is a weekly-rebalanced, cost-free decile number. It is not comparable
  to 0001's 21.73% / 1.130 book CAGR and is not quoted as performance.
- **The low-momentum-tercile statistic is degenerate for this anchor**, because the score is NMS itself.

**Null: 200 seeds of random scores with NMS coverage**

- False-pass rate at |t| ≥ 2.6: **0.0%**, two-sided and one-sided alike.
- t has mean −0.16 and sd 0.97; the p99 of |t| is 2.32.
- So the harness is unbiased and slightly conservative. The spec expected about 1%, and 0 of 200 is consistent with
  a 1% rate (P = 0.13).

**Placebo: NMS shuffled within each date, 100 seeds**

- Pass rate **0.0%**, mean t −0.05, max |t| 2.33. The placebo fails, as it must.

### Independent re-derivation (rule 3)

**Harness null and anchor.** A fresh `blind-replica` agent worked from the written spec only
([measured] `diagnostics/replica/phase0/null_replica.json`).

| | original | replica | difference |
|---|---|---|---|
| anchor alpha / t / β | 0.25212 / 3.513 / 0.894 | 0.2521 / 3.513 / 0.894 | 0.0% |
| null false-pass, 50 seeds (two-sided / one-sided) | 0% / 0% (seeds 0–49) | 0% / 0% | 0 |
| null t sd, 50 seeds | 0.894 (seeds 0–49), 0.931 (seeds 50–99) | 0.719 | −20% |

- **The t sd differs by more than 5%.** The seeds draw different random arrays (the draw shapes differ), so per-seed t
  values are not comparable. With 50 seeds the sd itself has a standard error of about 10%.
- The decision-driving numbers, the false-pass rate and the anchor, agree exactly.
- Both implementations put the null's t sd below 1, so the 2.6 bar is conservative, not loose.
- **Reconciliation:** not completed. Flagged as an open item.

**Adjusted core EPS (30 random company-quarters).** A fresh `blind-replica` agent rebuilt them from
`data/results_xbrl.parquet` and the written spec only ([measured] `diagnostics/replica/phase0/eps_replica.csv`;
keys drawn with seed 20261120 in `eps_sample_keys.csv`).

- **Rows:** 30 of 30 rebuilt. Every one is a direct 3-month quarter; none is derived.
- **Agreement:** the basis matches on all 30. The adjusted core EPS differs by **0.0%** at most (bit-identical), and
  0 rows differ by more than 5%.
- **Split/bonus factors:** 5 of the 30 keys carry a factor of about 2, and both implementations agree on all 5.
- **Choices the replica made itself that differ from the panel:** a null exceptional item is treated as 0, where the
  panel leaves core PAT NaN, and the derived-row path was not exercised. Neither affected the 30 keys.

## Artifact check

1. **"2013–2017 have XBRL"** was a placeholder-link artifact. It was caught by inspecting the link text and ruled out:
   the count is now on `.xml` links only.
2. **Null bias from the market definition.** Covered names against all members gave a t mean of +0.48. Fixed: the
   market is now the score-covered universe, and over 200 seeds the t mean is −0.16.
3. **Single path or overlap in the alpha t.** Returns are non-overlapping weekly, with Newey-West lag 8. Both the null
   (sd 0.97) and the placebo stay under the bar. Ruled out as a source of false passes.
4. **Look-ahead in the panel.**
   - Ruled out for values: the truncation test shows identical rows before the cut-off.
   - The **basis choice** reads the full filing history. That is a filing-format fact, not a value, and it is disclosed.
   - The split factor uses past quarters only.
5. **Corporate-action adjustment from filings, not a register.** Integer-ratio steps can misread a rights issue that
   happens to land on 1.5×. 1,011 events were detected and not individually audited; this is **not ruled out**.
6. **Holdout leakage.** Every harness return passes the guard on its exit date, and the tests enforce it. Ruled out.

## Owner decisions

1. **Basis rule for 2017–2018.** The single-basis rule drops 28% of 2018 company-quarters and 17% of 2017's.
   - Option A: keep the rule (no mixing; the January L1 window effectively starts FY2019-20).
   - Option B: allow a standalone fallback for quarters before FY2019-20, flagged. More history, but the bases are
     mixed.
   - Evidence: the "quarters lost" figures above.
2. **Core-PAT tax rate of 25.17%** is [assumed]. Confirm it, or supply a per-company effective rate.
3. **Pre-registration 0153** needs your signature at the January review. Nothing runs before then.
