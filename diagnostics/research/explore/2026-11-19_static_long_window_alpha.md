# Static index/arbitrage mixes on 2017–2026, and gross alpha over beta for the blend, 0001 and swing — 2026-11-19

**Class: MEASUREMENT.** Owner request ("prompt 4"), on the #215 branch line. No rule, trial, sealed read, live change
or merge. **Standing counts: screens 24 · sealed opens 4 · n_trials 3** (unchanged).

**Goal link.** The mission's fallback is the index plus a cash leg at the exposure that meets −25%. This checks the
65/35 ranking outside 2019–24, and whether any book earns return beyond the beta a static mix would deliver.

## Step 0 — sealed check (answered before any run)

**Answer: index TRI and fund NAV data after 2024-06-30 are NOT a sealed slice.** [inferred, from these receipts]
- CLAUDE.md names a "sealed judge log" and a sealed-opens count. It defines no sealed price or benchmark data.
- `diagnostics/research/n_trials.json` contains no sealed-slice definition at all.
- The sealed set is defined in two places:
  - `skills/verdict-machine/SKILL.md:108`: the banked per-trade label set, rows with `entry_date` > 2024-06-30 ("not
    subset, not rendered, not read").
  - `nq/lab/runs.py:13-14`: the swing engine's own price series, cut and asserted at `CUT` = 2024-06-30.

  Both are **strategy** data. The judge log is a forward record.
- Precedent: the 0001 run of record and prompt 1's risk-matched benchmark (`explore_risk_matched_benchmark.py`,
  `FULL_WIN` 2017-01-01..2026-06-30) already read the TRI to 2026-06. Neither was counted as a sealed open.

**Hence Step 1 runs 2017-01..2026-06.** Strategy outputs stay cut at 2024-06-30 in every case: Step 2 uses 2019-03..2024-06
only, and the swing NAV never passes the cut.

## Method — fixed before any result

Script: `pipelines/diagnostics/explore_static_long_window_alpha.py`. It reuses
`explore_after_tax_frontier.run`/`FBook` and `explore_blend_cost_tax`, unchanged.

### Step 1 — static mixes

**Model.** The friction and tax model of #215: index fund = TRI less 0.30% TER, MF costs, STCG 20% / LTCG 12.5% above
₹1.25L, tax on 31 March, terminal liquidation, ₹20,00,000.

**Cash leg.** The real arbitrage-fund average: Kotak 119771 + ICICI 120364, Direct-Growth, via mfapi, AMFI-checked.
Both funds have NAVs from January 2013, so **the liquid proxy is not needed anywhere in 2017–2026**. The script asserts
this.

**Mixes.** Index/arbitrage 40/60 to 80/20 in 5pp steps. Bought at the first session, re-weighted at each 31-March close
after the tax payment.

**Windows.**
- Full window: 2017-01-02..2026-06-30, on the TRI's session calendar.
- Sub-periods 2017-01..2019-02 and 2024-07..2026-06, primary reading: **continuous slices of the full run** (CLAUDE.md).
  CAGR is from the slice's after-tax mark-to-market NAV (taxes paid to date, no liquidation), and p95 is from the
  slice's weekly returns.
- Secondary reading, labelled as such: a fresh-capital run on each sub-period, with liquidation.

**Metrics.**
- After-tax CAGR: the liquidation value (full window).
- p95 156-week drawdown: W-FRI returns of the after-tax mark-to-market NAV; stationary bootstrap, mean block 8, 10,000
  draws (`explore_blend_drawdown_sizing.boot_dd`).
- Highest passing mix: the largest index weight with p95 ≤ 25% on the full window.

**Anchor:** the owner fallback (prompt 1). On 2017-01..2026-06: exposure 0.60 to the TRI with cash at 6.5%, re-balanced
daily, pre-tax. Expected CAGR 16.34, p95 (block 8) 23.73, and 0.60 as the highest passing exposure at block 8
(`2026-11-18_risk_matched_benchmark.json`, `full_0001_window`). Reproduced with that script's own functions.

### Step 2 — alpha over beta, 2019-03-01..2024-06-28, weekly (W-FRI) returns

**Books.** The blend 70/30 at 11% (the #215 book), 0001 and swing.
- **Gross** (pre-cost): the engines re-run with their costs off (#215's `gross_books`). The blend is rebuilt from the gross legs with
  the net exposure series e_t, and cash at 6.5% less 0.15% (the #215 reconciliation series).
- **Net of cost**: 0001 and swing are their engines' net NAVs. The blend is #215's lot-simulator **pre-tax** run (engine,
  wrapper and TER costs all in).
- Pre-tax throughout.

**Regressors** (two separate regressions):
- (i) the static index return: the index fund, TRI less 0.30% TER;
- (ii) the raw Nifty Midcap150 Momentum 50 TRI.

**Regression.** Excess returns, with rf = 6.5% a year compounded weekly:
- r_book − rf = a + b (r_index − rf) + e
- alpha = 52·a; beta = b; R²;
- Newey-West HAC standard error of a: Bartlett kernel, lag 8. t = a / se.

**Beta-matched static mix.** b·index + (1 − b)·cash at rf, re-balanced weekly. Its CAGR is reported beside the book's.
The book's alpha against it is mean(book − mix) × 52, which equals the regression alpha by construction. Both are
reported, as a check.

**Significance.** |t| ≥ 2 is called significant. This is stated, not a gate. 278 weekly observations, one path.

### Step 3

A blind replica re-derives the full-window 60/40 point and the blend's net-of-cost alpha and t (regressor (i)) from a
written spec.

**Anchors and determinism.**
- The #215 anchors are read from the committed JSON: blend 11% after-tax 19.26 / p95 26.46; 65/35 23.02 / 24.81.
- 0001 21.73 / 1.130.
- The output must be byte-identical under PYTHONHASHSEED 0 and 7. Stop only on an unexplained miss or one over 5%
  relative.
