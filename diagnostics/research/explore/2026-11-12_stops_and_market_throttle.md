# 2026-11-12 — "Half our trades hit stop": stop size, and the market-trend throttle across 20 paths

**Tier:** EXPLORE (`docs/PROCESS_TIERS.md`). No screen row, no `n_trials` change, nothing changes live.
Standing counts: screens 24 · sealed opens 3 · n_trials 2. Window 2019-01-01..2024-06-30, PIT membership,
prices cut at 2024-06-30. Builds on `2026-11-02_problem1_throttle_bound.md` and `2026-11-03_giveback_solution_map.md`.

## The question

The owner observed that wins and stops are about equal live, with roughly half of all trades hitting the stop.

## 1. A stop rate near half is the design, not the defect

Live rules, uncapped book, 441 closed trades:

| exit | share | mean R |
|---|---|---|
| runner exit (weekly close under the 44w SMA) | 48% | +2.59 |
| full stop | 44% | −1.43 |
| stop after the 2R tranche | 7% | +0.12 |

Win rate is 42.9% and mean is +0.62R per trade. The book loses often and small, and wins less often and large.

The live closed record (38 trades, 27 full stops) looks worse than it is because of time censoring. Losers
close in weeks, while winners are still open. At 2026-11-12, 15 of the 17 open trades are in profit, 6 are above
+1R, and together they hold about +21.5R. Live, all 55 trades combined (open ones marked to market) average about −0.46R.

## 2. Tighter stops re-measured on the current live exit

Reproduce with `2026-11-12_stop_size_arms.json`.

| arm | uncapped mean R | uncapped ΣR | avg loss | capped Sharpe (1 path) |
|---|---|---|---|---|
| live | +0.62 | 650 | −1.26 | 1.02 |
| daily hard stop | +0.31 | 500 | −1.01 | 0.95 |
| disaster floor 3% | +0.47 | 581 | −1.22 | 1.35 |
| disaster floor 5% | +0.58 | 631 | −1.24 | 1.01 |
| disaster floor 10% | +0.61 | 644 | −1.28 | 1.00 |

A daily hard stop holds losses to about −1R but halves per-trade R, because it shakes out the intra-week piercings
that recover. This is the 0105 result, now confirmed on the scaled exit. The 3% floor's capped 1.35 conflicts with
its per-trade loss, and it is one path inside about 0.2 Sharpe of noise. It is not a lead.

## 3. Why live differs from history: the market

Every one of the 55 live signals (July to October 2026) was taken with the Nifty's weekly close below its 40-week SMA.
The Nifty closed back above it on 2026-11-06.

## 4. The S1 throttle across 20 paired paths

S1 means no new entries when the signal-week Nifty close is below its 40w SMA. It blocks 59 of 287 entry weeks.
Reproduce with `python pipelines/diagnostics/explore_ensemble_s1_throttle.py 20`, which writes
`2026-11-12_ensemble_s1_throttle.json`. The rule was fixed before the run: robustly better if the 5th percentile of the
paired delta is above 0, robustly worse if the 95th percentile is below 0.

| candidate | ΔSharpe median [p5, p95] | ΔMaxDD pp median [p5, p95] (+ = shallower) | ΔCAGR pp median | reading |
|---|---|---|---|---|
| S1 | −0.30 [−0.47, −0.08] | **+9.7 [+5.4, +21.2]** | −4.6 | drawdown robustly shallower, Sharpe robustly lower |
| h5 | **+0.27 [+0.12, +0.71]** | −1.9 [−5.6, +14.9] | +8.3 | Sharpe robustly better (second ensemble to agree) |
| S1 + h5 | −0.51 [−0.67, −0.28] | +4.8 [−6.8, +7.5] | −13.9 | robustly worse |

Live band: Sharpe 1.25, CAGR 26.1%, MaxDD −37.5% (medians).

## Reading

- **S1 is a pure risk dial.** On every path it cuts the worst drawdown (median by about 10pp) and on every path it
  costs Sharpe and usually return, because it also sits out the rebounds that start below the line. It does not pass
  the Sharpe bar. Whether it is worth having is the owner's risk-preference call, not a statistical one. In-sample,
  it would have skipped the whole live period so far.
- **h5 holds a second time.** It is the only change that raises risk-adjusted return robustly.
- **S1 and h5 do not combine.** Together they are worse than either alone.
- **Cheapest next tests:** S1 at half size (0.5) instead of zero, to see whether part of the drawdown cut can be kept at a
  smaller Sharpe cost; and a pre-registration of h5 for the 2027-01-01 review.
