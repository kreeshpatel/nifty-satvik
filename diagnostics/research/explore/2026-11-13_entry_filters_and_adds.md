# 2026-11-13 — Entry filters, a +1R add, and half size in a weak market (live rules)

**Tier:** EXPLORE. No screen row, no `n_trials` change, nothing changes live. Standing counts: screens 24 · sealed
opens 3 · n_trials 2. Window 2019-01-01..2024-06-30, PIT membership, prices cut at 2024-06-30 and asserted.
Reproduce: `python pipelines/diagnostics/explore_entry_filters_and_adds.py` → `2026-11-13_entry_filters_and_adds.json`.

Per-trade = the uncapped book: mean R over closed trades, total R with open trades marked at the cut, worst drawdown
of cumulative R by exit date. Capped = the ₹10L book, **one path**, so about ±0.2–0.3 Sharpe of path noise (see the
20-path ensembles). Big winners = live uncapped trades at or above +2R: 169 trades, +861R (open trades marked at the
cut included).

| arm | closed trades | mean R / closed trade | total R | worst R drawdown | capped Sharpe | capped MaxDD | capped CAGR | big winners skipped (R) |
|---|---|---|---|---|---|---|---|---|
| **live** | 441 | +0.62 | 650 | −60 | 1.03 | −40.1% | 20.5% | — |
| (a) add one unit at +1R (Friday close) | 441 | +0.82 | **851** | **−86** | not measured | — | — | 0 (adds 309 units) |
| (b1) skip if midcap breadth < 40% | 359 | +0.34 | 466 | −57 | 1.00 | **−26.7%** | 16.9% | **30 (186R)** |
| (b2) skip if stock below its own 40w SMA | 441 | +0.62 | 650 | −60 | 1.03 | −40.1% | 20.5% | 0 — **removes nothing** |
| (b3) skip if 6-month RS vs Nifty < 0 | 395 | +0.66 | 609 | −75 | 1.07 | −35.1% | 20.9% | 10 (38R) |
| (b4) skip if results within 4 weeks | 391 | +0.68 | 602 | −63 | **1.28** | −31.2% | 25.6% | 20 (107R) |
| (c) half size when Nifty < 40w SMA | 441 | +0.37* | 515* | −58 | **1.23** | −39.5% | 25.7% | 0 skipped; 52 at half size (153R given up) |

\* Size-weighted: R at half size counts half. 26% of entries fall in that state.

## Reading

- **(a) Adding a unit at +1R adds R but deepens the drawdown by more.** The 309 adds earn +0.65R each on average:
  +271R on the big winners and −70R on the rest. Total R rises 31% (650 → 851), and the worst cumulative-R drawdown
  rises 44% (−60 → −86). It is "more risk on trades that confirmed", priced per trade only. Its capital-book effect
  needs an engine lever (adds compete for cash with new entries), and it falls under program-laws Law V
  (adding on in-flight state, closed): `KILL (pre-scaled-exit epoch, base book) — not re-tested under the current
  harness`. A real test needs the capped book and the 20 paths before it means anything.
- **(b1) Midcap breadth is the S1 throttle again.** It cuts the capped drawdown to −27% and cuts return and per-trade R.
  It skips 30 big winners worth 186R. It is a risk dial, not an edge. The midcap set is an approximation (§ below).
- **(b2) cannot fire on this book.** Every Grade-A signal closes above its rising 44-week SMA, so above its own
  40-week SMA too (minimum +0.7% over 1,524 signals).
- **(b3) Weak 6-month RS** removes 223 signals for a small per-trade gain (+0.66 vs +0.62), skips 10 big winners, and
  deepens the R drawdown. Inside noise.
- **(b4) Skipping signals with results due within 4 weeks** is the most interesting single-path number: capped Sharpe
  1.28 and MaxDD −31%, against 1.03 and −40%. But per-trade total R falls (602 vs 650) and it skips 20 big winners
  (107R). A capital-book gain alongside a per-trade loss is the funding-channel pattern seen with h5 and the half-size
  throttle, and single paths have misled before (breakeven at +1R). Prior: earnings (0121) was "banked, screen-real,
  decision-margin-negative" as a deferral. **Worth one 20-path check before anything else.**
- **(c) Half size when the Nifty is below its 40-week SMA** keeps every trade and lifts the capped single path to
  1.23 Sharpe at a similar drawdown. The zero-size version (S1) was robustly worse on 20 paths. This half version has
  not been through the ensemble. Also worth one 20-path check.

## Approximations and limits

- **Midcap breadth:** the data holds Nifty-500 membership only. "Midcap" = PIT Nifty-500 members ranked 101–250 by
  trailing 63-session median traded value. Breadth = the share of them closing above their own 40-week SMA, on the
  signal Friday.
- **Results dates:** NSE board-meeting calendar (`nq.data.earnings`), counting only meetings announced on or before the
  signal Friday (PIT), with an event inside the next 28 days.
- **6-month RS:** the stock's 26-week return minus the Nifty's, on the signal Friday.
- **Add unit:** filled at the next open after the first Friday close at or above +1R. It has the same rupee risk as the
  parent (sized on the distance to the parent's stop), shares the parent's stop and exits, and sells in proportion to
  the parent's remaining shares. Priced from the engine's own exit events, with no engine change.
