# 2026-11-03 — "In profit, never reaches 2R, ends at a full stop": how often, and does a breakeven stop help?

**Tier:** EXPLORE (`docs/PROCESS_TIERS.md`). No screen row, no `n_trials` change, nothing changes live. Standing
counts: screens 24 · sealed opens 3 · n_trials 2. Owner question: trades go into profit, never reach the target,
and come back as a loss.

## 1. How often it happens

Peak = the best intraday high between entry and exit, in units of initial risk (R). Live record from
`results/signals_history_weekly.json`, peaks rebuilt from Yahoo daily bars (the scan's own vendor). History =
the uncapped tracker, live config with PIT membership, train 2019-01-01..2024-06-30, degenerate stops excluded.

| peak before exit | history: share of trades | history: loss rate | history: mean R | live (closed + open) |
|---|---|---|---|---|
| never above +1R | 31% | 99% | −1.33 | **50%** (25 of 50) |
| +1R to +2R | 16% | **92%** | −1.07 | 28% (14 of 50) |
| reached +2R | 53% | 5% | +3.2 | **22%** (11 of 50) |

- **The pattern is real and structural, not new.** Historically 92% of trades that peak between +1R and +2R end
  at a full loss, and 30% of all losers had been up at least +1R. Live: 10 of the 31 closed losers peaked between
  +1.08R and +1.83R (32%), the same rate.
- **What changed live is the distribution, not the giveback.** Half of live trades never got to +1R (history: 31%),
  and only 22% reached the target (history: 53%). That is the weak tape of problem 1: pullbacks are not following
  through.
- **A second leak, after the target.** The 40% tranche books at +2R, but the stop on the remaining 60% stays at
  −1R. Four open trades booked +2R and are now negative overall: SAIL (peak +4.3R → blended +0.1R),
  USHAMART (+3.3R → −0.6R), TATATECH (+3.0R → −0.4R), SIEMENS (+2.4R → −0.3R). History says this is rare (15 of
  259 trades that booked 2R ended net negative); live it is 4 of 10 so far, still open.

## 2. Does raising the stop help? (0148's lever, `scaled_exit.lockin_mfe/lockin_at`, weekly-close trigger)

Reproduce: `python pipelines/diagnostics/explore_giveback_breakeven.py` →
`diagnostics/research/explore/2026-11-03_giveback_breakeven.json`. One path per arm (≈0.2 Sharpe path noise).

| arm | capped Sharpe | CAGR | MaxDD | 2019-21 / 2022-24H1 Sharpe | uncapped ΣR (per-trade book) |
|---|---|---|---|---|---|
| live (no ratchet) | 1.02 | 20.5% | −40.1% | 1.03 / 1.01 | 650 |
| breakeven once +1.0R | **1.34** | 26.4% | **−30.6%** | 1.43 / 1.22 | 632 |
| breakeven once +1.5R | 1.26 | 24.9% | −34.2% | 1.24 / 1.27 | 646 |
| breakeven once +2.0R | 1.15 | 21.2% | −32.3% | 0.93 / 1.44 | 656 |
| entry +1R once +2.0R | 1.30 | 25.2% | −33.3% | 1.31 / 1.26 | 585 |

- **Per trade, it is a wash.** In the uncapped book every arm lands within ±3% of the base R (the +1R lock-in
  loses 10%): the givebacks it saves are paid back by trades stopped at breakeven that would have gone on to win.
  This is the forensic's and 0148's result again.
- **On the ₹10L capital book it helps, in both sub-periods.** Breakeven at +1R: Sharpe +0.32, MaxDD 9.5pp
  shallower, both halves better. The gain is not better trades. A trade parked at breakeven frees its seat
  sooner (85 trades against 77), and the capped book is seat-starved. That is the same mechanism behind D6, the
  caps-off h5 lead, 0148's corrected capped result and the throttle's half-size rows.
- Single path, inside the ≈0.59 statistical half-width. **A lead to score on the ensemble, not a finding.**

## Next (cheapest test that would change the answer)

Ensemble-score breakeven at +1.0R and +1.5R against live (20 paths, paired), alongside D6. If the 5th-percentile
paired ΔSharpe stays above zero, it earns a pre-registered trial at the 2027-01-01 review. And because four
separate levers all work by freeing seats, the seat-utilisation question deserves its own direct measurement.
