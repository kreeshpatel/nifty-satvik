# Data-readiness audit v2 — multi-signal cross-sectional model (2019 to mid-2024)

**Class:** MEASUREMENT. Owner request of 2026-11-18. The owner approved an exception to the research freeze for this
audit only. It computes no signal, no IC and no return. It asks two questions: does the data exist, and when did each
item become public?

**Standing counts:** screens 24 · sealed opens 4 · n_trials 3 (unchanged). Branch `research/data-audit-v2`.

**Mission line:** this decides which candidate edges have point-in-time-safe data before any research effort is spent
on them.

## Method (stated before results)

- **PIT universe:** `nq.data.membership.load_membership()`. The universe for year y is every name whose membership
  interval contains 30 June of y. Sizes:

  | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|
  | 496 | 500 | 498 | 497 | 499 | 500 |

  694 names were members at some point from 2019 to mid-2024; 194 of them had left the index by mid-2024 ("leavers").
- **Coverage:** the share of the year-y universe that has at least one record dated in year y.
- **Public timestamp:** the date the information became public, not the period it describes. For NSE filings this is
  the exchange broadcast time.
- **Lag:** public timestamp minus the end of the period described, in calendar days, reported as median / p95.
- **Code:**
  - `pipelines/diagnostics/audit_data_readiness_v2.py` writes `explore/2026-11-18_data_readiness_v2.json`.
  - `pipelines/diagnostics/audit_index_press_releases.py` writes `explore/2026-11-18_index_press_releases.csv`.
  - NSE listings are pulled month by month (2019-01 to 2024-06) and cached in `.cache/data_audit_v2/`, which is
    gitignored.
- **Price match test:** 50 seeded random PIT members × 20 seeded random sessions.
  - Repo side: the close-to-close return from `corrected_universe()` (Yahoo, adjusted).
  - NSE side: `sec_bhavdata_full` CLOSE_PRICE / PREV_CLOSE − 1.
  - A pair matches if the two returns differ by 0.10pp or less.

## Summary

| # | data need | verdict | coverage of PIT N500 (2019 → 2024) | point-in-time lag (median / p95) |
|---|---|---|---|---|
| 1 | Sector / industry, PIT | **PARTIAL** | 72% → 90% (static labels) | none: today's label applied to every date |
| 2a | Quarterly results with true filing timestamp (NSE results API + XBRL) | **GO** (listing measured; XBRL line items sampled, not bulk-parsed) | 93% → 95% | 42 d / 92 d after quarter end, timestamp to the second |
| 2b | Annual fundamentals in the repo (`fundamentals_pit_*.pkl`) | **PARTIAL** | 76% → 88% | 90 d / 90 d, a **synthetic** period end + 90 days |
| 2c | Board-meeting calendar (`_earnings_raw.parquet`) | **GO** (dates only) | 94% → 97% | 41 d / 62 d after quarter end |
| 3 | Index rebalances: N500, Midcap 150, Midcap150 Momentum 50 | **PARTIAL** | announcements from 2017 (N500, Midcap 150) and from Dec 2022 (Momentum 50) | announced 17 / 42 d before effect (N500); 24 / 31 d (Momentum 50) |
| 4 | ASM / GSM surveillance, daily, with stage | **PARTIAL** | GSM touches 13 of 694 members | same day (circular or daily file) |
| 5a | Insider trades (SEBI PIT Reg 7) | **PARTIAL** | 68% → 34% (falling) | 3 d / 18 d after the trade |
| 5b | SAST Reg 29 | **GO** | 55% → 38% (event-driven) | 3 d / 28 d after the acquisition |
| 5c | Pledge creation / release | **PARTIAL** | inside the PIT stream (7,299 creations, 8,185 revocations) | as 5a |
| 6 | Price hygiene, 2019–24 | **GO** | 100% each year; all 194 leavers present | match 99.9% excluding 2024-01-23 (94.4% including it) |

All figures are [measured]; the artifact is the JSON unless a row says otherwise.

## 1. Sector and industry classification, point-in-time — PARTIAL

**Sources checked.**
- `config.py::SECTOR_MAP`: 607 tickers, 18 labels, one label per ticker, no dates.
- `data/problem_sector_map.json`: a themes → sectors knowledge base with no ticker-level classification.
- `data/sector_intelligence.pkl`: sector-level return aggregates keyed by `SECTOR_MAP` labels, also with no
  ticker-level classification.
- The `industry` field on NSE results filings: present but `-` on all 65,133 rows.
- Wayback snapshots of `ind_nifty500list.csv`, which carries an Industry column: only 3 monthly-collapsed snapshots
  between 2018-10 and 2024-02.

**Coverage of the PIT N500 by `SECTOR_MAP`:**

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| 72.4% | 78.2% | 84.7% | 84.9% | 87.8% | 89.8% |

**Leavers:** 47 of 194 have a label.

**PIT:** no. The label is today's classification applied to every date. The gaps are the "Others" names and most
leavers.

**Verdict: PARTIAL.** Sector-neutral residual momentum would rest on current labels, which is a look-ahead even if a
small one.

Residual momentum against market and HML factors needs no sector label. `data/ff_india_factors.parquet` (mkt, hml)
runs from 2017-09-15 to 2026-06-29, and finding 0011 used it.

## 2. Quarterly results with announcement timestamps — GO for timing; line items need an XBRL pull

### a) NSE `corporates-financial-results` API — GO

**Coverage.**
- 65,133 filings, broadcast between 2019-01-11 and 2024-06-30.
- Every filing carries an XBRL link.
- 41% are consolidated.
- Coverage of the PIT N500:

  | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|
  | 92.9% | 92.6% | 92.8% | 94.2% | 94.8% | 95.4% |

- Leavers: 168 of 194 have at least one filing.

**Timestamp.** `broadCastDate` gives the exchange dissemination time to the second. It falls a median 42 days after the
period end, with a p95 of 92 days.

**Line items.** One 2019 XBRL file was fetched and contains `BasicEarningsLossPerShare`, `RevenueFromOperations` and
equity tags [measured]. The XBRL files were not bulk-parsed: each filing is one HTTP fetch, about 65,000 files.

- Debt and equity: Ind-AS quarterly results carry the balance sheet only at the half-year and the year end
  [inferred, not verified across files]. Quarterly debt and equity are therefore half-yearly at best.
- Standardised surprise against the same quarter last year needs only EPS, which is quarterly.

**Gap between NSE broadcast and board-meeting date** (added at the owner's request on 2026-11-18).

How it's measured:
- One broadcast per (symbol, period end), the earliest.
- Matched to the latest results meeting in `_earnings_raw.parquet` for the same symbol, on or before the broadcast
  date and at most 10 days before it.

Results:
- 38,663 broadcasts; 35,876 matched (92.8%).

| broadcast − meeting date | share of matched broadcasts |
|---|---|
| same day | 48.3% |
| next day | 43.8% |
| 2 days or more | 7.8% |

  The median gap is 1 day and the p95 is 3 days [measured].
- Time of day (IST), for broadcasts in 2019-01 to 2024-06:

  | before 09:15 | 09:15–15:30 | after 15:30 |
  |---|---|---|
  | 1.0% | 38.8% | 60.3% |

**Does this resolve 0128's blocker?** Finding 0128 recorded that `ann_ts` is the intimation timestamp, not the
results-release time. As a result, "announcement+1 if after-close" was not implementable on that data
(`research/findings/0128-pead-gate1.md:157-160`; pre-reg §1, lines 78-97).

`broadCastDate` is a per-filing dissemination timestamp to the second. For the 92.8% of broadcasts that match a
meeting, it places the release before the open, during the session, or after the close.

So: **yes for the filings the API returns.** The release time is now observable per event. It was not observable in
the calendar 0128 used.

Two qualifications:
- **It is the exchange broadcast time.** The company may have posted the results on its own site minutes earlier
  (`difference` field, typically under 3 minutes in the samples seen).
- **About half of results reach the exchange the day after the meeting.** That is 43.8% next-day plus 7.8% two days
  or more. The meeting date in the calendar is therefore not the release date for about half of events.

### b) Repo annual fundamentals — PARTIAL

**Files:** `fundamentals_pit_screener.pkl` (654 tickers), `fundamentals_pit_depth.pkl` (653) and
`fundamentals_pit_backfill_20260729.pkl` (57 leavers).

**Frequency:** annual, with a median 365 days between periods and data from 2002 to 2026.

**`available_date`:** always the period end + 90 days. This is a convention, not a filing timestamp.

**Coverage of the PIT N500 (depth file):**

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| 75.8% | 79.0% | 82.7% | 83.1% | 86.2% | 87.6% |

**Leavers:** 100 of 194.

**Verdict: PARTIAL.** These files can't support quarterly surprise or quarterly quality.

### c) Board-meeting calendar `_earnings_raw.parquet` — GO for dates only

**Contents.**
- 103,868 rows, of which 73,869 are results meetings, from 2019-01-01 to 2026-07-28.
- The meeting falls a median 41 days after quarter end (p95 62).
- The intimation precedes the meeting by a median 7 days (p95 23).

**Coverage.**

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| 94.4% | 94.0% | 94.2% | 95.8% | 96.6% | 97.4% |

- Leavers: 168 of 194.
- No line items.

**Can it be extended past 2026-07-24?** Yes. The same endpoint (`api/corporate-board-meetings`) returned 5,576 rows for
2026-10-01 to 2026-11-15 on 2026-11-18 [measured].

## 3. Index rebalance history — PARTIAL

**Repo.** `data/nse_circulars/transitions_wayback.csv` has 764 Nifty 500 add/remove rows effective from 2019-02-01 to
2026-05-02, with **effective dates only and no announcement date**. The repo holds no Midcap 150 or Momentum 50
membership history.

**niftyindices press releases.** There are 91 equity "Replacements in indices" releases from 2017 to 2024 (parsed
text; 2 are image-only). Each carries an announcement date and an effective date, and lists exclusions and
inclusions by index.

| index | releases | first – last | lead (announce → effective) median / p95 |
|---|---|---|---|
| Nifty 500 | 47 | 2017-03-06 – 2024-10-10 | 17 / 42 days |
| Nifty Midcap 150 | 20 | 2017-04-18 – 2024-09-25 | 29.5 / 44 days |
| Nifty Midcap150 Momentum 50 | 5 | 2022-12-01 – 2024-12-09 | 24 / 31 days |

**Momentum 50 history.** The index launched in August 2022. Its constituent changes before December 2022 are
back-calculated history and were never announced.

**Can the next Momentum 50 rebalance be reconstructed from prices alone?** The methodology (Nifty Equity Indices
Methodology, November 2026 edition, pp. 197-200) sets out:

- **Eligible universe:** Nifty Midcap 150 members at review.
- **Circuit-filter exclusion:** non-F&O stocks that hit the circuit filter on 20% or more of the last 6 months'
  sessions are excluded.
- **Score:** a Normalized Momentum Score. It is a z-score of MR12 and MR6, each being price return over σ, where σ is
  the annualised standard deviation of daily log returns over 1 year. Prices are taken on the last trading day of
  month M−1 and of month M−13 / M−7.
- **Selection:** top 50 by score, with a buffer:
  - members ranked within the top 75 stay;
  - non-members ranked in the top 25 are included compulsorily;
  - members ranked beyond 75 are excluded.
- **Weights:** score × free-float market cap, capped at the lower of 5% or 5× the stock's free-float weight.
- **Timing:** reviewed semi-annually, in June and December.

What follows:

- **Selection is reconstructable** from prices, the current Midcap 150 list (public) and circuit-hit history. The
  band-hitter files fetched on 2026-11-18 cover 2019-01 to 2024-06.
- **Weights are not.** They need free-float market cap, which the repo lacks (0001 pre-reg, line 74).
- **Midcap 150 membership itself is set by free-float market-cap ranking**, so its future changes are not reproducible
  from prices alone. Past changes are in the press releases above.

**Verdict: PARTIAL.** Announcement and effective dates and the lists exist from 2017 for N500 and Midcap 150. They exist
only from Dec 2022 for Momentum 50, and they are not yet parsed into a table.

## 4. ASM / GSM surveillance — PARTIAL

**Current lists.** `api/reportASM` and `api/reportGSM` return **today's lists only**. No date parameter was found.

**GSM history: daily, with stage.**
- Source: the Remarks column of `sec_list_DDMMYYYY.csv` (the band files fetched for the circuit study).
- Coverage: 2019-12-30 to 2024-06-28, 1,114 files, 59,557 GSM rows, giving stages 0 to IV.
- **Not archived for 2019.**
- Only **13 of the 694 PIT N500 members** were ever under GSM in that span.

**ASM history.**
- Source: NSE Surveillance circulars (`api/circulars?dept=SURV`), one per change, each with a ZIP or PDF list.
- Volume: 2,864 ASM circulars from 2019 to 2024-06 (437, 491, 482, 540, 607, 307 by year) and 1,049 GSM circulars.
- The **attachments were not parsed**, so entry and exit dates and stages are not yet tabulated.
- The circular date is the public timestamp.

**Verdict: PARTIAL.** Everything is retrievable, but ASM needs about 2,900 attachments parsed, and GSM barely touches
the N500.

## 5. Insider, SAST and pledge — PARTIAL

**PIT Reg 7 (`api/corporates-pit`).**
- 149,642 disclosures, 47,107 of them by promoters, broadcast from 2019-01-01 to 2024-06-30.
- The broadcast follows the trade by a median 3 days (p95 18).
- Coverage of the PIT N500:

  | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|
  | 67.5% | 67.0% | 65.5% | 51.5% | 42.5% | 34.0% |

  Disclosure counts fell over the same years:

  | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 (H1) |
  |---|---|---|---|---|---|
  | 38,371 | 30,667 | 34,325 | 19,280 | 18,817 | 8,182 |

  No per-call cap was found: the maximum month is 7,151 rows. The fall is a **known gap**. One possible cause is the
  move to depository system-driven disclosures [inferred, not verified].
- Leavers: 139 of 194.

**SAST Reg 29 (`api/corporate-sast-reg29`).**
- 25,590 rows, broadcast from 2019-01-01 to 2024-06-29.
- The broadcast follows the acquisition end by a median 3 days (p95 28).
- Coverage of the PIT N500 is 38–55% a year, because these filings only happen on threshold crossings.
- Leavers: 153 of 194.

**Pledge.**
- `api/corporate-pledgedata` returns **today's snapshot only**. All 1,558 rows were broadcast on 2026-11-18, and
  date-ranged queries return 0 rows.
- No SAST Reg 31 endpoint was found (404).
- Pledge *events* are inside the PIT stream: "Pledge Creation" 7,299 rows and "Revokation of Pledge" 8,185 rows, with
  the same timestamps as other PIT disclosures.
- Quarterly promoter pledge % is in shareholding-pattern filings (`api/corporate-share-holdings-master`). That endpoint
  returned 24 quarters for one symbol, back to 2021-09 only.

**Verdict: PARTIAL.**

## 6. Price-data hygiene, 2019–24 — GO

**Survivorship.** All 694 names that were PIT members from 2019 to 2024-06 have prices, including all 194 leavers.
Each year's universe is covered 100% (496/496 … 500/500).

**Corporate actions.** Prices are yfinance with `auto_adjust=True`, so splits, bonuses and dividends are back-adjusted.
On top of that sit the carried corrections: `corporate_actions_*.csv` and `delisted_alias_map.json`.

**Yahoo vs NSE bhavcopy.**
- 1,000 pairs drawn; 816 had both sides. 98 were missing on the Yahoo side because the name wasn't listed on that date.
  142 were missing on the bhavcopy side: 1 of 20 days failed to download, plus names not trading.
- Match rate at 0.10pp or better: **94.4%**.
- All 46 mismatches over 0.5pp fall on **2024-01-23**.
  - NSE held a special full session on Saturday 2024-01-20, and the repo's series has no bar for it: CEATLTD goes from
    01-19 to 01-23.
  - So the repo's 01-23 return spans two sessions, while NSE's PREV_CLOSE is the 01-20 close.
- **Excluding that date: 99.9%** (768 of 769). The one miss is LODHA on 2023-09-08, at 0.14pp.

**Known gap:** Yahoo omits special weekend sessions. The same five weekend dates turned up in the TRI calendar in the
2026-11-18 risk-matched study.

## Prior use of each source

**Sources and the studies that used them.**

| source | used by |
|---|---|
| `config.SECTOR_MAP` | 0096 sector-relative CRS (`pipelines/research/run_0096_sectorrel_swing.py`, `research/findings/0096-sectorrel-crs-swing.md`); pre-reg 0008 sector rotation overlay |
| `sector_intelligence.pkl` | pre-reg 0002 sector rotation activation; `diagnostics/research/portfolio_risk/SPEC.md` |
| `problem_sector_map.json` | no research study (the AI sector-regime analyst only) |
| `fundamentals_pit_depth.pkl` | 0019 depth IC (`pipelines/research/screen_depth_ic.py`); 0108 growth filter |
| `fundamentals_pit_screener.pkl` | 0007 quality IC; pre-reg 0075 gross profitability (blocked on data); 2026Q4 re-anchor review |
| `_earnings_raw.parquet` | 0128 PEAD gate-1 (`pipelines/diagnostics/diag_pead_gate1_0128.py`); 0129 event-proximity sizing bound; 2026Q4 breadth-50 proposal |
| `ff_india_factors.parquet` | 0011 residual momentum; 0012 residual blend / veto |
| NSE results API, niftyindices press releases, ASM/GSM, PIT, SAST, pledge | no study (first used here). Insider, SAST and pledge were catalogued as candidates only, in `diagnostics/research/data_census_20260727.md` §5–6 |
| N500 PIT membership | every book and replay (`load_membership`) |
| Bhavcopy (`sec_bhavdata_full`) | delivery % (pre-reg 0010, `scripts/harvest_delivery.py`); data census 2026-07-27 |

**Killed or closed studies on these sources.** The book each was tested in comes from
`diagnostics/research/TRANSFERABILITY_REGISTER.md`. The kill reason is quoted from each finding's own status line.

| study | data | book it was tested in | verdict | stated reason: signal or construction |
|---|---|---|---|---|
| 0007 quality IC (ROE, E/P, B/P) | screener fundamentals | standalone IC on the LH panel (baseline_v1) | KILL | **signal**: "leak + regime". With a 90-day lag p = 0.053; it splits 2017–21 vs 2022–26 |
| 0011 residual momentum, sole ranker (0077) | FF factors | LH long-horizon book (baseline_v1), not the swing book or 0001 | KILL | **construction**: killed "as a sole ranker". The finding states the "shape/DD mechanism is real" |
| 0012 residual blend / veto (0078) | FF factors | LH book (baseline_v1) | KILL (4 arms) | **construction**: arms failed the pre-committed bar; "veto construction is validated", veto-0.1 a near miss |
| 0019 fundamentals-depth IC | depth pkl | standalone IC on the LH panel | MEASUREMENT (not a kill) | rev_yoy real; six other features noise |
| 0096 sector-relative CRS | SECTOR_MAP | 5-seat swing (ladder-0094) | KILL, ΔSharpe −0.672 | **construction**: "residualising the sector strips the trend edge" of the swing book's ranking |
| 0108 profit + sales growth filter | depth pkl | 5-seat swing (frozen 0094) | KILL, ΔSharpe −0.537 | **construction**: as a universe filter "it removes momentum winners" |
| 0122 ratings tail screen | ratings filings | substrate (disaster census), no book | KILL | **neither**: coverage; "the mechanism was never tested and is NOT adjudicated" |
| 0128 PEAD gate-1 | board-meeting calendar | standalone universe event study, no book | closed (owner, 2026-07-31) | **signal** (differentiation): drift real but momentum-concentrated, insignificant in the tradable-ADV slice, decaying |
| 0129 event-proximity sizing bound | board-meeting calendar | substrate plus the capped train book (primary) | bound | n/a: an activation bound, not a kill |

**Untested.** The 0001 momentum book has had none of these sources tested in it [measured, register rows above].

## Edges this makes testable

| edge | verdict | why |
|---|---|---|
| Residual / smooth momentum | **GO** for factor-residual (mkt + HML, PIT, 2017–2026) and for smoothness (prices only); **PARTIAL** for sector-residual | sector labels are not PIT (§1) |
| Earnings-surprise drift (SUE against the same quarter last year) | **GO for timing** (broadcast to the second, release time now observable); **PARTIAL for values** | EPS needs about 65k XBRL fetches to be parsed (§2a) |
| Quality | **PARTIAL** | annual repo data on a synthetic +90-day lag; quarterly P&L via XBRL; debt and equity half-yearly at best (§2) |
| Forced flows (index inclusion / exclusion) | **PARTIAL** | N500 and Midcap 150 announcements from 2017 and Momentum 50 from Dec 2022, unparsed; selection reproducible, weights need free-float market cap (§3) |
| Insider actions | **PARTIAL** | PIT Reg 7 with broadcast timestamps from 2019, but coverage falls from 68% to 34%; pledge events inside PIT; no historical pledge snapshot (§5) |

## Artifact check (rule 2)

1. **Coverage counts records, not completeness.**
   - "At least 1 record in the year" overstates usable coverage for quarterly needs. A name with one filing out of
     four counts as covered.
   - Not ruled out. Quarter-level completeness is for the next step.
2. **Board-meeting matching window.**
   - The ±10-day match could pair a broadcast with the wrong meeting when a company holds two in 10 days.
   - Partly ruled out. 92.8% matched, and the gap distribution is tight (p95 3 days).
3. **API completeness.**
   - Month-by-month pulls showed no fixed cap, but NSE could silently drop rows.
   - Not ruled out. The PIT decline from 2022 is flagged rather than explained.
4. **Price match on returns.**
   - Dividends could create false mismatches, because the Yahoo series is dividend-adjusted and NSE's PREV_CLOSE is
     adjusted only for corporate actions.
   - Bounded: 99.9% matched outside the special-session date.
5. **PIT universe.** The membership file is itself a reconstruction (Wayback + circulars). It was used as given.

**Re-derivation (rule 3):** see the end of this file.

## Hand downloads needed

**None for this audit.** Every source above came from public endpoints, fetched programmatically.

Two sources are not available programmatically:
- **Historical pledge snapshots before 2021-09** (SAST Reg 31): no endpoint found.
- **Historical per-stock free-float market cap**, needed for Momentum 50 weights: not located.

No exact file URL is known for either, so none is listed.

## Re-derivation (rule 3)

A fresh `blind-replica` worked from the spec only, using the cached listings. Its results:

| quantity | replica | this study |
|---|---|---|
| broadcasts matched to a meeting | 92.79% | 92.8% |
| gap to meeting: same day / next day / 2+ days | 48.34% / 43.83% / 7.83% | 48.3% / 43.8% / 7.8% |
| median / p95 gap | 1 / 3 days | 1 / 3 days |
| broadcast time: before 09:15 / 09:15–15:30 / after 15:30 | 0.98% / 38.62% / 60.41% | 1.0% / 38.8% / 60.3% |
| results lag after quarter end, median / p95 | 42 / 92 days | 42 / 92 days |
| PIT Reg 7 lag after trade, median / p95 | 3 / 18 days | 3 / 18 days |

- The time-of-day gap is the 15:30 boundary: the replica compared to the second, this study to the minute.
- Results coverage by year (92.9 → 95.4%) and PIT Reg 7 coverage by year (67.5 → 34.0%) are identical.
- The replica also flagged that the PIT decline is not explained by pagination. That is consistent with §5.
