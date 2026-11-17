# 2026-11-13 — Regime cross-tab, minimum stop distance, confirmation entry, and why live stops are tighter

**Tier:** EXPLORE. No trial, no screen row, nothing live changes, and the sealed 2024H2+ slice (B) is not read.
Standing counts: screens 24 · sealed opens 4 · n_trials 3 (unchanged).

**Datasets.** A = the live configuration on 2019-01-01..2024-06-30 (PIT membership, prices cut at 2024-06-30 and
asserted), with closed trades and trades still open at the cut shown separately. C = the 55 live trades since
2026-07-06, replay only.

**Reproduce.** Run `pipelines/diagnostics/diag_loss_diagnosis_2026_11.py` first (it writes the per-trade table and the
price cache), then `LOSS_DIAG_CACHE=<dir> python pipelines/diagnostics/explore_stop_floor_and_confirmation.py` →
`2026-11-13_stop_floor_and_confirmation.json`.

## Verdicts

| idea | verdict | reason |
|---|---|---|
| 1. "Weak, fearful markets are the best entries" | **mixed: mostly one episode** | The best cell (Nifty below its 40-week SMA, VIX > 20, breadth < 40%) made +136.8R on 55 closed trades, and **90% of it is 2020**. The next best (above, VIX > 20, breadth > 60%) is 70% 2020. Outside 2020 the weak-market cells are small and close to flat. |
| 2a. Skip entries with a tight stop | **dead** | Average R per closed trade rises (+0.62 → +0.90 to +1.02), but only because trades are removed: total R falls from 650 to 633 / 583 / 498 / 425 at 6 / 7 / 8 / 9%, and 28 to 86 big winners are lost. The capped book swings between neighbouring settings (Sharpe 1.47 at 7%, 0.79 at 8%, 1.21 at 9%), which is the signature of noise. |
| 2b. Widen a tight stop to a minimum | **mixed** | The % version is the only arm that raises total R with almost no big winners lost: 670 and 660 at 6% and 7%, against 650, with 3 and 4 lost. Its capped single path is steady across neighbours (Sharpe 1.56 / 1.55 / 1.45 / 1.49). But the setting with the best single path (2.0 × ATR, Sharpe 1.83) is **inside noise on 20 paths**: +0.03 [−0.19, +0.82], 11 of 20 better, drawdown 3.3pp deeper. The % version has not been through the 20 paths. |
| 3. Confirmation entry | **dead on A** | It avoids 99 of the 102 immediate-failure losers and halves the stop-out rate (44% → 24–27%). But it drops 253 to 381 of 525 trades and loses 76 to 114 of the 169 big winners. Total R falls from 650 to 181 / 254 / 318 for 1 / 2 / 3 weeks, and average R per closed trade is no better (+0.52 to +0.62). |
| 5. The same rules on the 55 live trades | **helped live, against the history** | Confirmation would have skipped 30 to 36 of 55 trades and ended at −2.8 / +1.1 / +1.8R, against −18.9R. Widening would have ended at −15.7 / −14.4R. One four-month regime, and the opposite of what A says about confirmation. |

## 4. Why live stops are tighter (answer)

**It is the market and the stocks picked, not a code change.**

- **The rule is the same.** The stop is the signal week's low, raised to 10% below entry when the low is further away.
  A is simulated under today's rule, so a code change cannot create an A-vs-C gap. The engine's history shows no change
  to the stop rule since the 10% cap was added on 2026-07-16; only the first two live weeks predate it.
- **Signal weeks are narrower live.** Median signal-week range is 7.7% live against 10.4% in A. The fill lands in the
  same place in that range (0.80 vs 0.77 of the way up), so a narrower week gives a tighter stop.
- **The 10% cap rarely binds live.** 38.5% of A's stops sat at the 10% cap; 5.5% of live stops do.
- **Live stocks are less volatile.** Median daily ATR is 2.85% of price live against 3.45% in A. The live picks are
  also much larger and more liquid (median traded value ₹153 cr vs ₹58 cr; loss-diagnosis report).
- **Measured in the stock's own volatility, stops are only slightly tighter:** 1.94 × ATR live against 2.15 × in A.

How much is "calm market" and how much is "bigger stocks" cannot be separated with 55 trades.

## Notes on reading the tables

- **Open trades carry most of A's R.** Of A's 650R, 274R is in closed trades and 376R is in the 84 trades still open
  at the cut. The calm-market cell (Nifty above, VIX < 15, breadth > 60%) shows −2.3R closed and +235R open, so
  closed-trade averages understate it.
- **Capped-book columns are one path each,** with about ±0.2–0.3 Sharpe of path noise. Only the 20-path rows are
  noise-aware.
- **Confirmation entry is a per-trade simulation,** because the engine cannot re-time an entry. Its base (`sim_base`)
  reproduces the engine on A: total R 650.4 against 650.2, per-trade correlation 0.999. It has no account-level result.
- **Cheapest next test:** the 20-path check on widening to 6% and 7%, the one arm here with a steady single-path
  result.

**Engine:** `min_stop_pct` / `min_stop_atr20` / `min_stop_mode` is a new research option in
`scripts/run_bhanushali_weekly_rank.py`, off by default. Both golden masters are byte-identical;
`tests/test_min_stop_distance.py` covers off-identity, skip and widen.

---

# Tables

## 1. Regime cross-tab (A): Nifty vs 40-week SMA × VIX × midcap breadth

Closed trades and trades open at the 2024-06-30 cut are separate columns. `by_year` lists year:closed trades:R. `top_year_share_of_R` is the share of the cell's closed-trade R that its single largest year contributes (above 1 or below 0 means the other years net the opposite way).

| cell | n_closed | avg_R_closed | total_R_closed | runner_pct | n_open_at_cut | open_R_marked | top_year | top_year_share_of_R | by_year (n:R) |
|---|---|---|---|---|---|---|---|---|---|
| above | VIX <15 | breadth >60% | 86 | -0.03 | -2.30 | 41.00 | 58 | 235.00 | 2023 | -5.87 | 2020:2:-2.9 2021:18:+0.4 2022:8:-2.6 2023:47:+13.6 2024:11:-10.8 |
| above | VIX 15-20 | breadth >60% | 60 | -0.41 | -24.80 | 15.60 | 4 | 6.70 | 2022 | 0.37 | 2020:10:-7.9 2021:26:-1.8 2022:18:-9.1 2023:1:-0.8 2024:5:-5.2 |
| below | VIX >20 | breadth <40% | 55 | 2.49 | 136.80 | 46.60 | 3 | 29.10 | 2020 | 0.90 | 2020:39:+123.4 2022:16:+13.3 |
| above | VIX >20 | breadth >60% | 32 | 2.51 | 80.40 | 43.20 | 5 | 5.10 | 2020 | 0.70 | 2020:18:+56.6 2021:14:+23.7 |
| above | VIX 15-20 | breadth 40-60% | 29 | 0.12 | 3.40 | 21.20 | 4 | 27.30 | 2022 | 0.96 | 2021:2:+1.7 2022:26:+3.2 2023:1:-1.6 |
| below | VIX 15-20 | breadth <40% | 21 | 0.44 | 9.20 | 30.40 | 2 | 16.90 | 2023 | 0.47 | 2019:8:+4.3 2022:11:+0.5 2023:2:+4.4 |
| above | VIX >20 | breadth 40-60% | 15 | -0.00 | -0.00 | 37.50 | 1 | 5.30 | 2022 | 133.19 | 2020:6:+4.9 2022:9:-4.9 |
| below | VIX >20 | breadth 40-60% | 14 | 1.41 | 19.80 | 57.10 | 0 | 0.00 | 2020 | 1.00 | 2020:14:+19.8 |
| above | VIX 15-20 | breadth <40% | 8 | -1.30 | -10.40 | 0.00 | 0 | 0.00 | 2019 | 1.00 | 2019:8:-10.4 |
| above | VIX <15 | breadth 40-60% | 8 | 0.15 | 1.20 | 57.10 | 6 | 45.50 | 2023 | 1.00 | 2023:8:+1.2 |
| below | VIX <15 | breadth 40-60% | 6 | 0.48 | 2.90 | 42.90 | 1 | 5.40 | 2023 | 1.00 | 2023:6:+2.9 |
| below | VIX 15-20 | breadth 40-60% | 3 | -0.99 | -3.00 | 0.00 | 0 | 0.00 | 2019 | 1.00 | 2019:3:-3.0 |
| above | VIX >20 | breadth <40% | 1 | 8.95 | 8.90 | 100.00 | 0 | 0.00 | 2022 | 1.00 | 2022:1:+8.9 |

## 2. Minimum stop distance (A)

Per-trade = uncapped book (the live tracker's population). Capped = ₹10L book, one path. `big_winners_lost` = live A trades at or above +2R that the arm drops or that end below +2R under it. `immediate_failures_avoided` = live losers that never traded above +0.5R intraweek and that the arm does not take.

| arm | n_closed | n_open_at_cut | avg_R_closed | total_R_closed | total_R_open_marked | runner_pct | full_stop_pct_closed | mean_slip_beyond_stop_R | big_winners_lost | immediate_failures_avoided | capped_sharpe | capped_maxdd_pct | capped_cagr_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 441 | 84 | 0.62 | 273.90 | 376.30 | 32.20 | 44.40 | -0.43 | 0 | 0 | 1.02 | -40.10 | 20.50 |
| skip_pct_6 | 349 | 77 | 0.90 | 315.30 | 318.00 | 35.70 | 41.50 | -0.35 | 28 | 32 | 1.26 | -28.50 | 23.90 |
| skip_pct_7 | 318 | 68 | 0.97 | 308.80 | 274.40 | 36.80 | 41.20 | -0.34 | 45 | 41 | 1.47 | -30.10 | 31.50 |
| skip_pct_8 | 279 | 62 | 0.94 | 262.60 | 235.40 | 37.00 | 38.70 | -0.34 | 66 | 55 | 0.79 | -30.00 | 13.80 |
| skip_pct_9 | 239 | 54 | 1.02 | 243.40 | 181.10 | 36.50 | 36.80 | -0.36 | 86 | 66 | 1.21 | -33.40 | 23.60 |
| skip_atr_1.0 | 429 | 84 | 0.58 | 249.10 | 376.30 | 32.60 | 44.50 | -0.40 | 4 | 6 | 1.23 | -30.10 | 24.60 |
| skip_atr_1.5 | 383 | 83 | 0.65 | 250.40 | 356.90 | 33.70 | 43.60 | -0.36 | 25 | 24 | 1.59 | -35.30 | 39.10 |
| skip_atr_2.0 | 287 | 78 | 0.59 | 168.30 | 340.60 | 35.30 | 44.30 | -0.38 | 62 | 49 | 1.15 | -22.90 | 19.30 |
| widen_pct_6 | 431 | 86 | 0.69 | 296.60 | 373.60 | 33.70 | 42.50 | -0.38 | 3 | 1 | 1.56 | -39.90 | 37.10 |
| widen_pct_7 | 427 | 86 | 0.70 | 300.50 | 359.40 | 33.90 | 40.50 | -0.36 | 4 | 2 | 1.55 | -40.70 | 37.50 |
| widen_pct_8 | 425 | 88 | 0.68 | 287.30 | 351.70 | 33.30 | 37.90 | -0.39 | 9 | 2 | 1.45 | -45.10 | 35.20 |
| widen_pct_9 | 424 | 88 | 0.65 | 274.00 | 334.10 | 32.80 | 36.30 | -0.36 | 13 | 2 | 1.49 | -41.50 | 34.30 |
| widen_atr_1.0 | 442 | 84 | 0.60 | 264.60 | 376.30 | 32.10 | 44.30 | -0.41 | 0 | 0 | 1.08 | -40.00 | 21.20 |
| widen_atr_1.5 | 437 | 85 | 0.61 | 265.00 | 382.20 | 32.80 | 43.70 | -0.38 | 2 | 1 | 1.33 | -43.20 | 30.80 |
| widen_atr_2.0 | 430 | 87 | 0.59 | 251.90 | 375.60 | 32.70 | 40.50 | -0.41 | 7 | 2 | 1.83 | -31.20 | 41.20 |

### 20 paired paths: the best single-path setting (`widen_atr_2.0`) and its neighbours

| arm | dSharpe median | p5 | p95 | paths better | dMaxDD pp median | verdict |
|---|---|---|---|---|---|---|
| widen_atr_1.5 | -0.01 | -0.19 | 0.34 | 9 | -1.79 | inside path noise |
| widen_atr_2.0 | 0.03 | -0.19 | 0.82 | 11 | -3.31 | inside path noise |

## 3. Confirmation entry (A, per-trade simulation)

Simulated with the live-exit replay. `sim_base` is the same replay of the current entry, so the comparison is like for like. The replay vs the engine on A: total R 650.4 vs 650.2, per-trade correlation 0.999. The engine cannot re-time an entry, so there is no capped-book or 20-path result for this rule.

| arm | taken | dropped | n_closed | avg_R_closed | total_R_closed | total_R_open_marked | runner_pct | full_stop_pct_closed | mean_slip_beyond_stop_R | big_winners_lost | immediate_failures_avoided |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sim_base | 525 | 0 | 441 | 0.62 | 274.10 | 376.30 | 32.20 | 44.20 | -0.43 | 0 | 0 |
| confirm_1w | 144 | 381 | 109 | 0.52 | 56.40 | 124.30 | 38.20 | 23.90 | -0.30 | 114 | 99 |
| confirm_2w | 221 | 304 | 175 | 0.53 | 92.60 | 161.10 | 36.20 | 26.90 | -0.33 | 90 | 99 |
| confirm_3w | 272 | 253 | 216 | 0.62 | 133.60 | 184.80 | 34.60 | 25.90 | -0.33 | 76 | 99 |

## 4. Why live stops are tighter

Stop = the signal week's low, raised to entry × 0.90 when that is further than 10% (`max_risk_pct = 0.10`). So stop distance = entry position above the week's low, as a share of entry. It is driven by how wide the signal week was (`week_range_pct`) and where in that range the fill landed (`entry_pos_in_week_range`, 0 = at the low, 1 = at the high). `atr20_pct` is the stock's daily volatility before entry.

| dataset | n | median_stop_pct | median_week_range_pct | median_entry_pos_in_week_range | median_atr20_pct | median_stop_in_atr20 | share_capped_at_10pct |
|---|---|---|---|---|---|---|---|
| A | 525 | 8.55 | 10.36 | 0.77 | 3.45 | 2.15 | 38.50 |
| C | 55 | 5.88 | 7.74 | 0.80 | 2.85 | 1.94 | 5.50 |

The engine commits since 2024 that mention stop, risk, band, entry or fill are listed in the JSON (`engine_commits_touching_stop_or_entry`). None changes the stop rule after 2026-07-16.

## 5. Rules 2 and 3 replayed on the 55 live trades

Same replay as `sim_base` (it reproduces the closed live record within about 1R). Open trades are marked at the latest close in the price cache. Skipped or dropped trades count as zero.

| arm | taken | skipped_or_dropped | total_R_all_marked | total_R_closed | skipped |
|---|---|---|---|---|---|
| sim_base | 55 | 0 | -18.90 | -46.60 |  |
| widen_atr_2.0 | 55 | 0 | -15.70 | -42.40 |  |
| widen_atr_1.5 | 55 | 0 | -14.40 | -42.10 |  |
| confirm_1w | 19 | 36 | -2.80 | -9.30 | 3MINDIA, AARTIIND, ABCAPITAL, ADANIPORTS, ANGELONE, APARINDS, ASTERDM, BANDHANBNK, BIOCON, CANFINHOME, CCL, CHOLAFIN, ENGINERSIN, GESHIP, GLENMARK, GRAPHITE, GVT&D, HINDALCO, HINDZINC, IDFCFIRSTB, IKS, LINDEINDIA, LTF, MANAPPURAM, MRPL, NATCOPHARM, NESTLEIND, NLCINDIA, OBEROIRLTY, PHOENIXLTD, POWERINDIA, PTCIL, SIEMENS, STARHEALTH, TATATECH, ZYDUSLIFE |
| confirm_2w | 23 | 32 | 1.10 | -10.50 | 3MINDIA, AARTIIND, ABCAPITAL, ANGELONE, APARINDS, ASTERDM, BIOCON, CANFINHOME, CCL, CHOLAFIN, ENGINERSIN, GESHIP, GLENMARK, GVT&D, HINDALCO, HINDZINC, IDFCFIRSTB, IKS, LINDEINDIA, LTF, MANAPPURAM, MRPL, NATCOPHARM, NESTLEIND, NLCINDIA, OBEROIRLTY, PHOENIXLTD, POWERINDIA, SIEMENS, STARHEALTH, TATATECH, ZYDUSLIFE |
| confirm_3w | 25 | 30 | 1.80 | -11.90 | 3MINDIA, AARTIIND, ABCAPITAL, ANGELONE, APARINDS, ASTERDM, BIOCON, CANFINHOME, CCL, CHOLAFIN, GESHIP, GLENMARK, GVT&D, HINDALCO, HINDZINC, IDFCFIRSTB, IKS, LINDEINDIA, LTF, MANAPPURAM, MRPL, NATCOPHARM, NESTLEIND, NLCINDIA, OBEROIRLTY, PHOENIXLTD, POWERINDIA, STARHEALTH, TATATECH, ZYDUSLIFE |

## Addendum (same day): 20 paths on widening to a minimum % stop

Owner request. Same 20 paired paths and reading rule as every ensemble. Reproduce with
`python pipelines/diagnostics/explore_ensemble_widen_stop.py 20` → `2026-11-13_ensemble_widen_stop.json`.
Live band (medians): Sharpe 1.25, MaxDD −37.5%.

| widen stops tighter than | ΔSharpe median [p5, p95] | paths better | ΔMaxDD pp median [p5, p95] (+ = shallower) | ΔCAGR pp median | reading |
|---|---|---|---|---|---|
| 6% | +0.04 [−0.13, +0.52] | 12/20 | −0.8 [−5.5, +12.6] | −1.2 | inside path noise |
| 7% | +0.21 [−0.07, +0.51] | 18/20 | −2.4 [−6.6, +3.6] | +7.7 | inside path noise (narrow miss) |
| 8% | **+0.37 [+0.12, +0.70]** | **20/20** | +3.1 [−3.8, +16.1] | +8.6 | **Sharpe robustly better**; drawdown inside noise |

**This updates verdict 2b from "mixed" to "promising at 8%, with caveats".**

- The effect grows steadily with the level (6% < 7% < 8%), which is the opposite of the spike seen with the first
  target at +1R. 9% and 10% have not been run on 20 paths, so where it tops out is unknown.
- Per trade it is roughly neutral: total R 639 against 650 at 8%, average R per closed trade +0.68 against +0.62, and
  9 big winners lost. The gain is in the capital book. A wider stop means a smaller position for the same 2% risk, so
  more seats get funded. That is the same funding channel as h5, and h5-30 failed on unseen data (finding 0151).
- With the live 10% cap, an 8% floor squeezes every stop into an 8–10% band. In effect this is a near-fixed stop
  distance.
- This is the 16th stop-floor setting looked at today, so some of the +0.37 is selection.
- On the 55 live trades, widening to 2.0 × ATR or 1.5 × ATR ended at −15.7R / −14.4R against −18.9R. The % version was
  not replayed live.

It is train-window evidence only. A live change would need a pre-registration; the sealed slice has already been read
for sizing and cap questions by 0151.
