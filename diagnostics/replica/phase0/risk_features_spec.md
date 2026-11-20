# Blind-replica specification: L5 risk features (C) and the 60/40 forward record (D)

This is the written specification for an independent re-derivation. The replica must **not** read
`nq/data/risk_features.py`, `pipelines/build/build_risk_features.py`, `forward/benchmark_60_40/record.py` or
`forward/benchmark_60_40/taxlots.py`. It may use the data loaders named below and read the raw inputs.

## C. Risk features: one row per (symbol, Friday)

### Calendar and universe

- **Sessions** are the dates of the close panel.
- **"Friday"** is the last session of each calendar week (weeks ending Friday, pandas `W-FRI`). If Friday is a
  holiday, it is that week's Thursday or earlier.
- **Membership:** `nq.data.membership.load_membership()` maps a symbol to a list of (start, end) intervals. A symbol
  is a member on a session if that session falls inside one of its intervals, ends included. A row exists only for
  members on its Friday.
- A final week whose last session is not a Friday (the data ends mid-week) is dropped. Price and label values are NaN for non-members.

**Prices**
- Load `data/ohlcv_backfill.pkl` (a dict of symbol to DataFrame) and update it with
  `nq.data.ohlcv.load_ohlcv_cache()`; the cache wins.
- Pass the result through `nq.data.ohlcv.clean_ohlcv_dict`. Use `Close` and `Volume` from 2016-01-01.

### Price family (inputs: close, volume, membership)

- **Returns and market:**
  - `r` = daily log return.
  - `rs` = simple return, with no forward-fill of missing prices.
  - `mk` = the equal-weight mean of `rs` across the symbols that are members that day.
- **Volatility:**
  - `rv63` and `rv126`: sample standard deviation (ddof = 1) of `r` over the last 63 or 126 sessions, × √252. At
    least 80% of the window must be non-missing (50 or 100 values), else NaN.
  - `dvol126`: sqrt(mean over 126 sessions of min(r, 0)²) × √252, with at least 100 values.
- **Betas:**
  - `beta126`: sample covariance of `rs` with `mk` over 126 sessions (at least 100 pairs), divided by the sample
    variance of `mk` over the same 126 sessions (at least 100 values).
  - `dbeta126`: the same, but using only days with `mk < 0` inside the 126-session window. At least 40 such pairs
    for the covariance and 40 for the variance.
- **Drawdown and down days:**
  - `mdd252`: let peak = the rolling 252-session max of close (at least 200 values) and dd = close / peak − 1;
    mdd252 = the rolling 252-session min of dd (at least 200 values).
  - `n_down5_252`: count of sessions with `rs <= −0.05` over 252 sessions. At least 200 non-missing `rs`.
- **Liquidity:**
  - `adv20_cr`: mean of close × volume over 20 sessions (at least 15), ÷ 1e7.
  - `adv60_cr`: the same over 60 sessions (at least 45), ÷ 1e7.
- All values are taken on the Friday.

### Band family

**Inputs**
- Hitters: `data/nse_bands/band_hitters.parquet`, with columns date, symbol, series, side (H/L).
- Band files: `.cache/nse_bands/raw/sec_list_YYYYMMDD.csv`, with columns Symbol, Series, Band, Remarks. Strip
  whitespace and use only series EQ.

**Hits**
- `lo_hits63`, `lo_hits252`, `up_hits63`, `up_hits252`: count of side-L or side-H EQ hits per symbol over the last
  63 or 252 sessions, ending on the Friday.
- A session with no hit counts 0.
- Sessions before the first hitter date (the earliest date in the hitters file) are unknown. Any window that touches
  them is NaN, and the full window is required.

**Band**
- `band_pct`: Band from the latest band file dated on or before the Friday. NaN if the symbol is not in that file,
  or if no file exists yet.

**GSM**
- Taken from the same file's Remarks:
  - not containing "GSM" → 0;
  - containing "GSM Stage - k", k in {0, I..VI} → k + 1;
  - containing "GSM" with no parseable stage → 1.
- NaN before the first file. A symbol absent from the as-of file → 0.

### ASM family

**Inputs**
- Raw circular attachments at `data/surv_raw/asm/<circNumber>/*.xlsx`, each with a `meta.json` holding `cirDate`
  (YYYYMMDD) and `sub` (the subject). Use only folders with `status == 200`.

**Which files count**
- Skip any file whose name contains IBC or ICA, or whose subject contains " IBC" or " ICA".
- Framework: ST if the file name contains `_ST`, or the subject contains "SHORT" or "ST-ASM" (spaces removed); LT
  otherwise.

**Snapshot**
- Use the sheet whose name contains "CONSOL" and not IBC/ICA.
- Its header row is the first row with a cell exactly "Symbol". The stage comes from the column whose header
  contains "Stage", as a Roman or Arabic numeral; if there is no such column, the stage is 1.
- That sheet is the complete list for its framework after the circular.

**Dates**
- `pub_date` = `cirDate`.
- `eff_date` = the first "w.e.f. <Month DD, YYYY>" date found in any sheet's cells (the comma and spaces are
  optional). If none is found, `eff_date` = `pub_date`.

**Combined stage**
- Apply snapshots in (pub_date, circular number) order; each replaces its framework's list.
- Combined stage = max(10 + k for ST stage k, 20 + k for LT stage k); 0 if the symbol is on neither list.
- A stage change is an event (symbol, pub_date, eff_date, new stage).

**Friday values**
- `asm_stage` = the stage from the last event with pub_date **strictly before** the Friday; 0 if there is none.
  NaN for Fridays on or before the first event's pub_date.
- `asm_days_in_stage` = (Friday − that event's eff_date) in days, only where `asm_stage > 0`.

### Pledge family

**Inputs**
- Lists: `data/shp_raw/lists/*.json`, with records holding `recordId`, `symbol`, `submissionDate` (`%d-%b-%Y`),
  `broadcastDate` (`%d-%b-%Y %H:%M:%S`) and `revisedStatus`.
- XML: `data/shp_raw/xml/<recordId>.xml.gz`.

**Per-filing pledge %**
- Promoter contexts: the XBRL contexts whose only `explicitMember` local name starts with
  `ShareholdingOfPromoterAndPromoterGroup`.
- `held` = `NumberOfShares` in a promoter context.
- Try the old format first, then the new; take the first that yields a value.
  - **Old format:** 100 × `PledgedOrEncumberedNumberOfShares` ÷ held. If that is missing,
    `PledgedOrEncumberedSharesHeldAsPercentageOfTotalNumberOfShares`, already in percent.
  - **New format:** 100 × `NumberOfSharesEncumbered` ÷ held. If that is missing, 100 ×
    `EncumberedSharesHeldAsPercentageOfTotalNumberOfShares`, which is filed as a fraction.
- A missing or blank field is NaN, **never 0**.

**Known time**
- Unrevised filing (`revisedStatus` is not "Revised"): min(submissionDate + 1 day at 00:00, broadcastDate).
- Revised filing: broadcastDate.

**Friday values**
- `pledge_pct` = the value from the latest filing whose known time is at or before Friday 15:30.
- `pledge_chg_1q` = that value minus the previous filing's value.
- `pledge_declared_none` = 1 if that latest filing has no number and every promoter pledge or encumbrance yes/no flag
  (`WhetherAnySharesHeldByPromotersArePledgeOrOtherwiseEncumbered*` or
  `WhetherAnySharesHeldByPromotersAreEncumbered*`, the unsuffixed or `...ForPromoterAndPromoterGroup` variants) is
  false; otherwise 0. NaN before 2021, and NaN while no filing is known yet (resolved after the replica: the replica's
  reading, NaN-not-zero).

### Fundamentals family

**Inputs**
- `data/fundamentals_q_features.parquet` (the Phase 0 feature view; columns company, broadcast_ts, ttm_pbt,
  ttm_finance_costs, ttm_core_pat, ttm_core_pat_chg4, lag_days).
- `data/results_xbrl.parquet` for balance sheets.

**Company key**
- symbol → `nq.data.fundamentals_q.company_key` (the modal 9-character ISIN prefix).

**As-of rule**
- Use the latest view row with broadcast_ts at or before Friday 15:30.
- `int_cover` = (ttm_pbt + ttm_finance_costs) / ttm_finance_costs, only where ttm_finance_costs > 0.
- `ttm_core_pat_pos` = 1 if ttm_core_pat > 0, else 0 (NaN if NaN).
- `ttm_core_pat_chg4` is passed through.
- `last_lag_days` = lag_days.
- `late_filer` = 1 if lag_days > 120, else 0 (NaN if NaN).

**`de_ratio`**
- Balance sheets: rows of `results_xbrl` with context_role = "current" and bs_total_equity not missing, on the
  company's primary basis (the view's `primary_basis`).
- de = (bs_borrowings_current + bs_borrowings_noncurrent, a missing part counted as 0; NaN if both are missing) ÷
  bs_total_equity, only where equity > 0.
- Take the latest balance sheet broadcast at or before Friday 15:30.
- It is valid only while the Friday ≤ (period_end + 6 month-ends) + (60 days if that month is March, else 45 days)
  + 60 days. Otherwise it is NaN.

### Label

- For a Friday at session position p, the forward window is sessions p+1 … p+63.
- seg = rs − beta126(Friday) × mk, with missing `rs` treated as 0.
- path = cumprod(1 + seg) − 1.
- label = 1 if min(path) ≤ −0.25, else 0.
- The label is valid only if beta126 is finite and at least 80% of the 63 forward `rs` values (51) are non-missing.
- It is computed only when session p+63 is on or before **2024-06-30**, and only for members on the Friday.

## D. 60/40 forward record: one week

- **Funds:** index fund AMFI 150738; arbitrage fund AMFI 119771. NAVs from `https://api.mfapi.in/mf/<code>`.
  Each fund's NAV is its last NAV dated on or before the record Friday.
- **Opening book:** capital ₹20,00,000 in cash. In the first week, buy ₹12,00,000 of the index fund and ₹8,00,000
  of the arbitrage fund at that week's NAVs.
- **Costs:**
  - Buying value V adds V × 0.00005 (stamp duty) on top; units = V / NAV.
  - Selling value V receives V × (1 − 0.00001) (STT).
  - Cash may go slightly negative.
- **Pre-tax NAV** = cash + Σ units × NAV.
- **After-tax NAV:**
  - Sell every unit at this week's NAV, first-in first-out.
  - Gains held ≤ 365 days are STCG at 20%; longer holdings are LTCG at 12.5% above a ₹1,25,000 yearly exemption.
  - Cess is 4%; surcharge 0. Gains and losses are set off within the financial year.
  - Pay the tax from cash. The resulting cash is the after-tax NAV.
- **Rebalance:** in weeks after the first, rebalance to 60/40 only if |index weight − 0.60| > 0.05.
- **Status:** STALE if either NAV is more than 3 calendar days older than the Friday; otherwise OK.
- **Replica target:** the week with record Friday **2026-11-20**, as a first week. Report both NAVs and both NAV
  dates, the pre-tax NAV, the after-tax NAV, the index weight and the status.
