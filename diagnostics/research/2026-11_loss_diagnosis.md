# 2026-11 — Why the live strategy loses, and under what conditions it works

**Tier:** MEASURE (diagnostic only). No live rule changed, nothing tuned, no trial, no screen row.
Reproduce: `python pipelines/diagnostics/diag_loss_diagnosis_2026_11.py` (set `LOSS_DIAG_CACHE` for the Yahoo price
cache) → this file's tables and `2026-11_loss_diagnosis.json`.

**Datasets, kept separate in every table**

- **A** = training window: the live configuration, entries 2019-01-01..2024-06-30, prices cut at 2024-06-30 (asserted).
  Per-trade rows are the uncapped book, every Grade-A signal (the same population the live tracker records). Account
  columns are the ₹10L capped book.
- **B** = the sealed 2024H2–2026H1 slice. **Not opened by this study** (owner decision, 2026-11-13). Reading B's trades
  for regime, anatomy and entry features would be a new sealed open (S5), and would remove B as a test for any future
  regime, entry-feature or stop-width rule, including the half-size candidate parked for the 2027-01-01 review. The
  only use of B here is the price-only integrity check in §5, which reads no trade outcome. Wherever the request asked
  for A vs B, this report shows A vs C and says so.
- **C** = the 55 live trades since 2026-07-06 (`results/signals_history_weekly.json`): 38 closed (at exit), 17 open
  (at the latest close, labelled). Initial stops come from `results/cards_archive.jsonl`, prices from Yahoo. Account
  columns are the live paper book (`results/portfolio_history_weekly.csv`), 2026-07-06..2026-11-08. Its CAGR is
  annualised from four months.

**Fixed definitions** (none fitted):
- Regime at the signal Friday:
  - Nifty vs its 40-week SMA, and the SMA's direction vs 4 weeks earlier;
  - Nifty 13-week return bucket;
  - midcap breadth: PIT Nifty-500 members ranked 101–250 by 63-session median traded value (an approximation; there is
    no midcap index list in the data), share closing above their own 200-day SMA;
  - India VIX: <15, 15–20, >20.
- Runner = R ≥ +2. Winner = R > 0. Grade is A for every trade in A and C by construction.
- "Results within 4 weeks" uses the NSE board-meeting calendar, PIT. That data ends with announcements on 2026-07-24,
  so it is blank for later live signals.

## 1. Headline

| dataset | n | n_closed | n_open | win_pct | avg_win_R | avg_loss_R | avg_R_closed | total_R | runner_pct | hold_wk_winners | hold_wk_losers | full_stop_pct_closed | acct_sharpe | acct_cagr_pct | acct_maxdd_pct | acct_window |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 525 | 441 | 84 | 42.90 | 3.14 | -1.26 | 0.62 | 650.20 | 32.20 | 42.20 | 7.90 | 44.40 | 1.02 | 20.50 | -40.10 | 2019-01-01..2024-06-28 |
| C | 55 | 38 | 17 | 5.30 | 1.57 | -1.38 | -1.23 | -17.30 | 14.50 | 10.50 | 5.10 | 71.10 | -1.03 | -17.30 | -13.90 | 2026-07-06..2026-11-08 |

## 2. Market regime at entry (per-trade metrics; account metrics are whole-book only)

### nifty_vs_40w

| dataset | bucket | n | n_closed | win_pct | avg_win_R | avg_loss_R | avg_R_closed | total_R | runner_pct | full_stop_pct_closed |
|---|---|---|---|---|---|---|---|---|---|---|
| A | above | 388 | 310 | 36.80 | 2.68 | -1.28 | 0.17 | 378.90 | 30.20 | 51.30 |
| A | below | 137 | 131 | 57.30 | 3.83 | -1.21 | 1.68 | 271.30 | 38.00 | 28.20 |
| C | below | 55 | 38 | 5.30 | 1.57 | -1.38 | -1.23 | -17.30 | 14.50 | 71.10 |

### sma40_slope

| dataset | bucket | n | n_closed | win_pct | avg_win_R | avg_loss_R | avg_R_closed | total_R | runner_pct | full_stop_pct_closed |
|---|---|---|---|---|---|---|---|---|---|---|
| A | falling | 120 | 116 | 56.90 | 4.37 | -1.33 | 1.92 | 261.60 | 41.70 | 33.60 |
| A | rising | 405 | 325 | 37.80 | 2.47 | -1.25 | 0.16 | 388.60 | 29.40 | 48.30 |
| C | falling | 55 | 38 | 5.30 | 1.57 | -1.38 | -1.23 | -17.30 | 14.50 | 71.10 |

### ret13_bucket

| dataset | bucket | n | n_closed | win_pct | avg_win_R | avg_loss_R | avg_R_closed | total_R | runner_pct | full_stop_pct_closed |
|---|---|---|---|---|---|---|---|---|---|---|
| A | -5..0% | 97 | 87 | 40.20 | 1.89 | -1.25 | 0.01 | 56.50 | 29.90 | 46.00 |
| A | 0..+5% | 127 | 93 | 38.70 | 2.10 | -1.32 | 0.00 | 116.40 | 29.90 | 48.40 |
| A | <-5% | 84 | 76 | 61.80 | 4.72 | -1.43 | 2.37 | 249.60 | 45.20 | 28.90 |
| A | >+5% | 217 | 185 | 38.40 | 3.23 | -1.20 | 0.50 | 227.80 | 29.50 | 48.10 |
| C | -5..0% | 20 | 15 | 0.00 | — | -1.39 | -1.39 | -14.60 | 5.00 | 80.00 |
| C | 0..+5% | 22 | 17 | 11.80 | 1.57 | -1.43 | -1.07 | -2.90 | 22.70 | 64.70 |
| C | <-5% | 8 | 2 | 0.00 | — | -1.23 | -1.24 | 3.20 | 12.50 | 50.00 |
| C | >+5% | 5 | 4 | 0.00 | — | -1.26 | -1.26 | -3.00 | 20.00 | 75.00 |

### breadth_bucket

| dataset | bucket | n | n_closed | win_pct | avg_win_R | avg_loss_R | avg_R_closed | total_R | runner_pct | full_stop_pct_closed |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 40-60% | 87 | 75 | 40.00 | 2.96 | -1.43 | 0.32 | 107.70 | 36.80 | 49.30 |
| A | <40% | 90 | 85 | 55.30 | 4.07 | -1.23 | 1.70 | 190.60 | 38.90 | 34.10 |
| A | >60% | 245 | 178 | 38.80 | 2.61 | -1.16 | 0.30 | 300.00 | 34.70 | 49.40 |
| A | nan | 103 | 103 | 41.70 | 3.08 | -1.34 | 0.50 | 51.90 | 16.50 | 40.80 |
| C | 40-60% | 14 | 10 | 0.00 | — | -1.64 | -1.64 | -11.60 | 7.10 | 90.00 |
| C | <40% | 5 | 0 | — | — | — | — | 3.30 | 0.00 | — |
| C | >60% | 36 | 28 | 7.10 | 1.57 | -1.28 | -1.08 | -8.90 | 19.40 | 64.30 |

### vix_bucket

| dataset | bucket | n | n_closed | win_pct | avg_win_R | avg_loss_R | avg_R_closed | total_R | runner_pct | full_stop_pct_closed |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 15-20 | 188 | 178 | 36.00 | 2.88 | -1.23 | 0.25 | 94.80 | 19.70 | 50.00 |
| A | <15 | 206 | 141 | 37.60 | 1.89 | -1.27 | -0.08 | 274.20 | 35.90 | 49.60 |
| A | >20 | 131 | 122 | 59.00 | 4.27 | -1.32 | 1.98 | 281.20 | 44.30 | 30.30 |
| C | 15-20 | 4 | 0 | — | — | — | — | 1.90 | 0.00 | — |
| C | <15 | 51 | 38 | 5.30 | 1.57 | -1.38 | -1.23 | -19.20 | 15.70 | 71.10 |

## 3. Trade anatomy

### Peak R reached by trades that ended at the full stop

| dataset | basis | n_full_stops | peak <0R | peak 0-0.5R | peak 0.5-1R | peak 1-1.5R | peak 1.5-2R | peak >=2R |
|---|---|---|---|---|---|---|---|---|
| A | mfe_close | 196 | 108 | 47 | 30 | 7 | 4 | 0 |
| A | mfe_high | 196 | 4 | 95 | 49 | 35 | 12 | 1 |
| C | mfe_close | 27 | 20 | 4 | 2 | 1 | 0 | 0 |
| C | mfe_high | 27 | 1 | 15 | 5 | 5 | 1 | 0 |

### Losers that never got above +0.5R (failed immediately)

| dataset | losers | never_above_0.5R_intraweek_pct | never_above_0.5R_friday_pct |
|---|---|---|---|
| A | 252 | 40.50 | 65.90 |
| C | 36 | 47.20 | 75.00 |

### Winners vs losers at entry (closed trades; medians; Mann-Whitney p)

B is not opened, so a 'clear in both' flag is read as: p < 0.05 in A and the same direction in C (C has few closed winners, so C alone cannot confirm anything). results_4w rows give the share (%) with results due.

| feature | A_win_median | A_loss_median | A_p | C_win_median | C_loss_median | C_p | clear_in_A_same_sign_in_C |
|---|---|---|---|---|---|---|---|
| dist_52w_high_pct | -9.15 | -8.61 | 0.15 | -11.40 | -8.71 | — | False |
| pullback_depth_pct | 13.78 | 12.04 | 0.04 | 14.16 | 11.91 | — | True |
| ext_40w_pct | 12.90 | 12.04 | 0.07 | 7.24 | 9.89 | — | False |
| vol_vs_20d | 1.41 | 1.43 | 0.69 | 0.70 | 1.21 | — | False |
| stop_pct | 9.27 | 7.80 | 0.01 | 2.74 | 5.44 | — | False |
| beta | 0.77 | 0.82 | 0.14 | 0.94 | 1.09 | — | False |
| rs6m_pct | 15.02 | 11.43 | 0.01 | 13.94 | 21.05 | — | False |
| traded_value_cr | 17.11 | 17.07 | 0.47 | 306.02 | 128.01 | — | False |
| results_4w (share, A) | 13.20 | 17.10 | — | — | — | — | — |
| results_4w (share, C) | — | — | — | 100.00 | 20.00 | — | — |

## 4. What changed: A (train) vs C (live). B was not opened, so the requested A-vs-B comparison is A-vs-C

| dataset | trades_per_signal_week | dist_52w_high_pct | pullback_depth_pct | ext_40w_pct | vol_vs_20d | stop_pct | beta | rs6m_pct | traded_value_cr |
|---|---|---|---|---|---|---|---|---|---|
| A | 2.24 | -10.18 | 14.58 | 12.52 | 2.33 | 7.80 | 0.83 | 14.50 | 57.96 |
| C | 3.24 | -9.95 | 14.14 | 10.01 | 1.66 | 5.95 | 1.06 | 21.98 | 152.74 |

Stop-out rate, runner share and runner size are in the section 1 table (full_stop_pct_closed, runner_pct, avg_win_R). Sector mix is in section 6.

## 5. Execution and data

### Stop vs actual exit (the weekly-close stop fills at the next open), in R beyond the stop level

| dataset | full_stops | mean_exit_vs_stop_R | median_exit_vs_stop_R | worst_exit_vs_stop_R | share_worse_than_-0.5R_beyond_stop |
|---|---|---|---|---|---|
| A | 196 | -0.43 | -0.23 | -5.47 | 28.10 |
| C | 27 | -0.64 | -0.37 | -3.53 | 44.40 |

**Model entry vs your actual fill:** not measurable. The app's `execution_events` table has 0 rows (queried read-only 2026-11-13), so no real fill has been recorded. C's entries are the model's modelled fills.

### B data integrity (prices only; no trade outcome read, so not a sealed open)

- PIT Nifty-500 members over 2024-07..2026-06 (quarterly sample): 637
- members with no bars at all in the slice: 0 []
- series that stop before 2026-06 (possible delisting / suspension): 10 ['AKZOINDIA', 'GSPL', 'INFIBEAM', 'ISEC', 'LTIM', 'PEL', 'SWANENERGY', 'TATAMOTORS', 'TATAMTRDVR', 'TV18BRDCST']
- one-day moves above 40%: 8 ['SKFINDIA 2025-10-15 55%', 'QUESS 2025-04-15 51%', 'TMPV 2025-10-14 40%', 'VEDL 2026-04-30 65%', 'RAYMOND 2025-05-14 65%', 'ABFRL 2025-05-22 67%', 'BCG 2025-07-14 102%', 'ALLCARGO 2025-11-12 65%']
- of those tickers, registered demergers: ['ABFRL', 'RAYMOND', 'SKFINDIA', 'VEDL']

## 6. Sector and concentration

| dataset | sector | n | n_closed | win_pct | avg_R_closed | total_R |
|---|---|---|---|---|---|---|
| A | Others | 72 | 68 | 30.90 | -0.04 | 17.20 |
| A | Consumer | 62 | 50 | 34.00 | 0.50 | 71.10 |
| A | Pharma | 48 | 41 | 65.90 | 2.54 | 124.30 |
| A | Finance_NBFC | 42 | 38 | 44.70 | 0.17 | 18.60 |
| A | Industrials | 42 | 28 | 50.00 | 1.35 | 98.10 |
| A | Chemicals | 38 | 35 | 45.70 | 1.02 | 46.40 |
| A | Energy | 37 | 31 | 38.70 | 0.47 | 56.00 |
| A | Infrastructure | 35 | 26 | 38.50 | -0.17 | 58.60 |
| A | FMCG | 29 | 24 | 58.30 | 1.11 | 44.30 |
| A | Banking | 28 | 22 | 27.30 | -0.20 | 27.70 |
| A | IT | 27 | 22 | 50.00 | 0.44 | 22.20 |
| A | Metals | 19 | 18 | 44.40 | 0.29 | 6.80 |
| A | Auto | 18 | 13 | 38.50 | 0.52 | 32.90 |
| A | Diversified | 8 | 7 | 57.10 | 0.56 | 8.20 |
| A | Cement | 7 | 7 | 42.90 | 0.93 | 6.50 |
| A | Paints | 5 | 5 | 40.00 | 0.62 | 3.10 |
| A | Telecom | 5 | 3 | 33.30 | 0.13 | 8.80 |
| A | Media | 2 | 2 | 0.00 | -1.73 | -3.50 |
| A | Realty | 1 | 1 | 100.00 | 2.71 | 2.70 |
| C | Finance_NBFC | 11 | 8 | 0.00 | -1.93 | -10.70 |
| C | Banking | 7 | 4 | 0.00 | -1.21 | 0.70 |
| C | Metals | 7 | 5 | 20.00 | -0.99 | -0.40 |
| C | Pharma | 6 | 5 | 0.00 | -1.21 | -6.10 |
| C | Industrials | 5 | 2 | 0.00 | -1.09 | 3.90 |
| C | Infrastructure | 5 | 4 | 0.00 | -1.10 | -2.80 |
| C | Chemicals | 3 | 2 | 0.00 | -2.13 | -2.60 |
| C | Energy | 3 | 2 | 0.00 | -1.13 | 1.20 |
| C | Auto | 2 | 1 | 100.00 | 3.12 | 4.80 |
| C | FMCG | 2 | 2 | 0.00 | -1.69 | -3.40 |
| C | IT | 2 | 1 | 0.00 | -0.53 | -0.40 |
| C | Diversified | 1 | 1 | 0.00 | -0.57 | -0.60 |
| C | Realty | 1 | 1 | 0.00 | -0.83 | -0.80 |

**Live open trades (17) by sector:** Banking 3, Industrials 3, Finance_NBFC 3, Metals 2, Auto 1, Energy 1, Infrastructure 1, IT 1, Chemicals 1, Pharma 1

**60-session daily-return correlation among open trades:** mean 0.12; pairs above 0.6: none

## 7. Simple regime responses (fixed thresholds, descriptive only; A only, B not opened)

| rule | entries_at_full | entries_skipped | entries_half | total_R_sized | avg_R_closed_sized | acct_sharpe | acct_cagr_pct | acct_maxdd_pct | big_winners_skipped | big_winners_halved |
|---|---|---|---|---|---|---|---|---|---|---|
| live | 525 | 0 | 0 | 650.20 | 0.62 | 1.02 | 20.50 | -40.10 | 0 | 0 |
| skip_below_40w | 388 | 137 | 0 | 378.90 | 0.12 | 0.92 | 21.40 | -26.60 | 52 | 0 |
| half_below_40w | 388 | 0 | 137 | 514.60 | 0.37 | 1.23 | 25.70 | -39.50 | 0 | 52 |
| skip_40w_falling | 405 | 120 | 0 | 388.60 | 0.12 | 0.66 | 9.80 | -25.20 | 50 | 0 |
| skip_breadth_lt_40 | 339 | 186 | 0 | 406.50 | 0.17 | 0.96 | 15.10 | -26.20 | 52 | 0 |

Per-trade R is the live A ledger re-weighted by each rule's size for the entry week (0 = skipped, 0.5 = half). Account columns are full engine runs of the capped book with the same rule (single path). Big winners = A trades at or above +2R.

### Live trades (C) that each rule's state covered (descriptive; no rule was applied live)

| live trades in state | n | their_total_R | of_all_live |
|---|---|---|---|
| nifty_vs_40w = below | 55 | -17.30 | 55 |
| sma40_slope = falling | 55 | -17.30 | 55 |
| breadth_bucket = <40% | 5 | 3.30 | 55 |


## What the data says (facts only)

**Headline**
- **A (2019–2024H1):** 525 trades, 42.9% winners. The average winner was +3.14R and the average loser −1.26R, giving
  +0.62R per closed trade and +650R in total. 32% of trades became runners. Winners were held 42 weeks on average,
  losers 8. Account: Sharpe 1.02, CAGR 20.5%, worst drawdown −40.1%.
- **C (live, July–November 2026):** 55 trades. 2 of 38 closed trades were winners (5.3%). The average loser was
  −1.38R, giving −1.23R per closed trade and −17.3R in total with the 17 open trades marked. 14.5% are runners, versus
  32% in A, and 71% of closed trades ended at the full stop, versus 44% in A. Paper account: Sharpe −1.03, worst
  drawdown −13.9%.
- **Both things moved between A and C:** the stop-out rate rose (44% → 71%) and the runners shrank (runner share 32%
  → 14.5%; average winner +3.14R → +1.57R, on 2 live winners).

**Market regime**
- **In A, the best entries came from weak, fearful markets.** Per closed trade:
  - Nifty below its 40-week SMA: +1.68R and 57% winners, vs +0.17R and 37% above;
  - 40-week SMA falling: +1.92R, vs +0.16R rising;
  - 13-week Nifty return below −5%: +2.37R;
  - India VIX above 20: +1.98R;
  - midcap breadth below 40%: +1.70R.
- **In A, the calm, rising buckets earned close to nothing per closed trade:** VIX below 15 −0.08R; 13-week return 0
  to +5% 0.00R. They still added total R through open runners.
- **All 55 live trades were entered with the Nifty below its 40-week SMA and that SMA falling** — the state that was
  best in A. They lost.
- **The live period differed from A's weak markets on two measures:**
  - VIX was below 15 at 51 of 55 live entries;
  - midcap breadth was above 60% at 36 of 55 and 40–60% at 14.

  A weak index with a calm VIX and broad midcap strength was not the kind of weak market that produced A's best trades.
- **Whether the strategy makes money in rising markets in B cannot be answered here** (B not opened). In A, entries
  with the Nifty above its 40-week SMA made +0.17R per closed trade and +379R in total, including open runners.

**Trade anatomy**
- **Most full stops never showed a profit at a weekly close.** In A, 108 of 196 never closed a week above entry; in C,
  20 of 27.
- **About half the losers failed at once.** 40.5% of A's losers and 47.2% of C's never traded above +0.5R
  intraweek; on Friday closes, 65.9% and 75.0%.
- **Three entry features separate winners from losers in A (p < 0.05):**

  | feature | winners | losers | p |
  |---|---|---|---|
  | pullback depth | 13.8% | 12.0% | 0.04 |
  | stop distance | 9.3% | 7.8% | 0.01 |
  | 6-month strength vs the Nifty | +15.0 pts | +11.4 pts | 0.01 |

  Only pullback depth points the same way in C, which has 2 closed winners and so cannot confirm anything.
- **Not different in A:** distance from the 52-week high, extension over the 40-week SMA, signal-week volume, beta,
  liquidity.

**A vs C at entry** (the request's A vs B is not available):

| | A | C |
|---|---|---|
| trades per signal week | 2.24 | 3.24 |
| stop distance | 7.80% | 5.95% |
| extension over the 40-week SMA | 12.5% | 10.0% |
| beta | 0.83 | 1.06 |
| 6-month strength vs the Nifty | +14.5 pts | +22.0 pts |
| median traded value (same Yahoo volume source) | ₹58 cr | ₹153 cr |
| signal-week volume vs 20-day average | 2.33× | 1.66× |

**Execution and data**
- **Exits filled beyond the stop by more live than in A:**

  | | mean | median | stops filled >0.5R past the stop |
  |---|---|---|---|
  | A | −0.43R | −0.23R | 28% |
  | C | −0.64R | −0.37R | 44% |

- **Real fills cannot be compared:** the app has recorded 0 executions.
- **B prices** (no outcomes read):
  - 637 PIT members, none with missing bars;
  - 10 series stop before June 2026;
  - 8 one-day moves above 40%, of which 4 are registered demergers (ABFRL, RAYMOND, SKFINDIA, VEDL) and 4 are not in
    the demerger register (QUESS, TMPV, ALLCARGO, BCG).

**Sector and concentration**
- **A:** Pharma was strongest (+2.54R per closed trade). Banking (−0.20R) and unmapped "Others" (−0.04R) were negative.
- **C:** every sector with a closed trade lost except Auto. Finance/NBFC had 11 trades and −10.7R.
- **The 17 live open trades are spread over 10 sectors.** Mean 60-day return correlation between them is 0.12; no pair
  is above 0.6.

**Simple regime responses** (A only, fixed thresholds, account columns on one path):

| rule | account Sharpe | CAGR | worst drawdown | big winners skipped or halved |
|---|---|---|---|---|
| live | 1.02 | 20.5% | −40.1% | — |
| skip entries below the 40-week SMA | 0.92 | 21.4% | −26.6% | 52 skipped |
| half size below it | 1.23 | 25.7% | −39.5% | 52 halved |
| skip when the 40-week SMA is falling | 0.66 | 9.8% | −25.2% | 50 skipped |
| skip when midcap breadth < 40% | 0.96 | 15.1% | −26.2% | 52 skipped |

In C, the first two states and "40-week falling" covered all 55 live trades (−17.3R). Breadth below 40% covered 5
(+3.3R).

## Limits

- **C is small:** 38 closed trades, 2 winners. Its rates have wide uncertainty, and its account CAGR is annualised
  from four months.
- **Midcap breadth is an approximation;** the live version uses current PIT membership with Yahoo prices.
- **The A account numbers are one path,** with about ±0.2–0.3 Sharpe of path noise, as the 20-path ensembles showed.
- **B was deliberately not used,** so every "A vs B" question is answered with A vs C, which is a different and much
  smaller sample.

Standing counts: screens 24 · sealed opens 4 · n_trials 3 (unchanged by this study).
