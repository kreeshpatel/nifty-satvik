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

---

## Results

**Reproduce:** `python pipelines/diagnostics/explore_static_long_window_alpha.py` →
`2026-11-19_static_long_window_alpha.json`. It is byte-identical under PYTHONHASHSEED 0 and 7 (sha256 `d9fc3efc…`)
[measured].

### Anchors — all exact [measured]

| anchor | committed JSON | reproduced |
|---|---|---|
| blend at 11%, after-tax / p95 | 19.26 / 26.46 | 19.26 / 26.46 |
| static 65/35 (2019–24, proxy liquid) | 23.02 / 24.81 | 23.02 / 24.81 |
| owner fallback, 2017–26, block 8: exposure / CAGR / p95 | 0.60 / 16.34 / 23.73 | 0.60 / 16.34 / 23.73 |
| 0001 full run | 21.73 / 1.130 | 21.73 / 1.130 |

### Step 1 — static index/arbitrage mixes [measured, `step1_static_mixes`]

**Data.**
- 2,351 sessions, 2017-01-02..2026-06-30.
- The arbitrage NAVs start in January 2013, so **the liquid proxy was not used anywhere**.
- The arbitrage leg earned 6.38%/yr; the index fund 22.10%/yr.

Full window 2017–2026:

| mix | after-tax CAGR | p95 156w DD | passes −25% | worst daily DD | excess Sharpe |
|---|---|---|---|---|---|
| 40/60 | 12.71 | 15.35 | yes | −14.76 | 0.877 |
| 50/50 | 14.21 | 19.69 | yes | −18.44 | 0.867 |
| 55/45 | 14.93 | 21.84 | yes | −20.25 | 0.864 |
| **60/40** | **15.64** | **23.99** | **yes, the highest passing** | −22.06 | 0.860 |
| 65/35 | 16.33 | 26.04 | **no** | −23.85 | 0.857 |
| 70/30 | 17.01 | 28.10 | no | −25.62 | 0.853 |
| 80/20 | 18.32 | 32.04 | no | −30.28 | 0.847 |

Sub-periods. The primary reading is a continuous slice of the full run (after-tax mark-to-market, taxes paid to date).
The fresh-capital run with liquidation is shown in brackets.

| mix | 2017-01..2019-02 CAGR / p95 | 2024-07..2026-06 CAGR / p95 |
|---|---|---|
| 40/60 | 10.74 / 13.8 (9.82 / 13.8) | 3.89 / 19.5 (4.44 / 17.2) |
| 50/50 | 11.71 / 18.2 (10.68 / 18.2) | 3.19 / 25.6 (3.85 / 23.4) |
| 60/40 | 12.65 / 22.5 (11.50 / 22.5) | 2.54 / **31.3** (3.24 / 29.2) |
| 65/35 | 13.10 / 24.6 (11.91 / 24.6) | 2.23 / **34.0** (2.88 / 32.1) |
| 80/20 | 14.42 / 30.5 (13.06 / 30.5) | 1.36 / 41.4 (1.78 / 40.2) |

The 2024-07..2026-06 sub-period is the stress case. Only 40/60 and 45/55 pass on the slice, and up to 50/50 on fresh
capital. A 2-year sub-period resampled to 156 weeks is a short history [inferred], so it is reported, not used to rank.

### Step 2 — alpha over beta, 2019-03..2024-06, weekly, pre-tax [measured, `step2_alpha_over_beta`]

Regressor: the index fund (TRI less TER). Excess returns, rf 6.5%; Newey-West lag 8; n = 277 weeks.

| book | costs | alpha / yr | beta | NW t | R² | book CAGR | beta-matched mix CAGR |
|---|---|---|---|---|---|---|---|
| blend at 11% | gross | +4.56% | 0.546 | 1.26 | 0.657 | 26.38 | 21.10 |
| blend at 11% | **net** | **+2.71%** | 0.536 | **0.75** | 0.654 | 23.78 | 20.82 |
| 0001 | gross | +9.94% | 0.957 | **2.29** | 0.783 | 45.45 | 32.37 |
| 0001 | **net** | **+8.04%** | 0.953 | **1.86** | 0.783 | 42.62 | 32.26 |
| swing | gross | −3.18% | 0.767 | −0.47 | 0.506 | 21.86 | 27.14 |
| swing | **net** | **−3.08%** | 0.729 | **−0.45** | 0.445 | 20.79 | 26.10 |

Against the raw TRI (n = 278), the readings are nearly the same:
- blend net: +2.48%, t 0.68;
- 0001 net: +7.73%, t 1.80 (gross +9.62%, t 2.24);
- swing net: −3.67%, t −0.54.

The alpha against the beta-matched static mix equals the regression alpha to the basis point in every row (the
identity check).

**Sign and significance, plainly:**
- **Blend:** positive alpha, not significant either way: gross t 1.26, net t 0.75.
- **0001:** positive alpha, significant **gross only**: t 2.29 against the index fund and 2.24 against the TRI. Net of
  costs it is not significant: t 1.86 and 1.80.
- **Swing:** negative alpha, not significant: t about −0.5.
- **No book has a significant net-of-cost alpha** at |t| ≥ 2, before tax.

### Step 3 — independent re-derivation [measured]

A fresh `blind-replica` worked from the written spec and two exported price files only, with no code. Spec, code and
result are in `2026-11-19_static_long_window_alpha_replica/`.

| quantity | replica | pipeline | gap |
|---|---|---|---|
| 60/40, 2017–26: after-tax CAGR | 15.640 | 15.64 | 0 |
| 60/40: p95 156w DD | 23.988 | 23.99 | 0 |
| 60/40: total tax | ₹7,61,121 | ₹7,61,121 | 0 |
| blend net, alpha / yr | 2.710% | 2.71% | 0 |
| blend net, beta | 0.5358 | 0.536 | 0 |
| blend net, NW t (lag 8) | 0.747 | 0.75 | 0 |
| blend net, R² | 0.6545 | 0.654 | 0 |
| beta-matched mix CAGR | 20.817 | 20.82 | 0 |

The replica flagged its own readings of the spec: buy cost charged on top of the trade, a partial first week kept,
and the first return week used for the years count. The pipeline makes the same choices, so the match confirms the
arithmetic under those readings. Its alternative gain basis (costs counted in the basis) moves tax by about ₹38.

## Artifact check

1. **The cap is one bootstrap of one 9.5-year history.** 60/40 passes at 23.99 and 65/35 fails at 26.04. The cut sits
   between two adjacent 5pp cells. **Disclosed;** the 0.05 grid is the stated resolution.
2. **The sub-periods are short.** 2 years (about 100 weekly returns) resampled to 156-week paths. **Reported, not used
   to rank.** Both readings, slice and fresh capital, are shown.
3. **Alpha is pre-tax.** After tax, the blend's 2.7% net alpha does not survive: in #215 the blend loses 4.89pp to
   65/35 after tax [measured there]. **Disclosed;** the request specified pre-tax.
4. **Single path and window for Step 2.** 2019-03..2024-06 is a strong momentum window: 0001 makes 43% a year in it,
   against 21.7% over its full run. 0001's gross t of 2.29 is one window's statistic. **Not ruled out.**
5. **Alpha is measured against the investable benchmark.** The index fund carries its 0.30% TER. Against the raw TRI
   every alpha is 0.2–0.3pp lower, and no sign or significance call changes.
6. **The blend's beta-matched mix uses a 6.5% cash rate.** The real arbitrage leg earned 6.38%, which would shift the
   mix CAGR by about −0.06pp at beta 0.54 [inferred]. Immaterial.

**Added after first look:** none.

## Owner decisions

1. **The fallback mix.**
   - Options: (a) 60/40 index/arbitrage, the highest mix that passes on 2017–26, which matches the 60% fallback draft;
     (b) 65/35, the best at the cap on 2019–24 only; (c) a lower mix, which the 2024–26 sub-period would favour (only
     ≤ 45/55 passes on its slice).
   - Evidence: 60/40 gives 15.64% after tax at p95 23.99 on the long window.
2. **0001's standing.** Its gross alpha is significant on this window (t 2.29) but does not survive costs (t 1.86), and
   the full 2017–26 run is 21.73% against 43% in-window.
   - Options: (a) keep it as a paper challenger; (b) measure its alpha on 2017–2026 (the 0001 run of record is
     already unsealed there).
3. **The blend.** Its net alpha is +2.7%/yr, not significant (t 0.75), and negative after tax relative to the static
   mixes. The 2026-11-18 decision stands: forward challenger only.
