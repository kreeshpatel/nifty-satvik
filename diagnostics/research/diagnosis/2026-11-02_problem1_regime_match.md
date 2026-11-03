# Problem 1 — is the live loss regime, or is something broken? (2026-11-02)

**Class:** MEASURE (process tier 1, `docs/PROCESS_TIERS.md`). No pre-registration, no screen row, no
`n_trials` change. Standing counts: screens 23 · sealed opens 3 · n_trials 2. Train window only (prices cut
at 2024-06-30, asserted by `nq.lab.runs`); the sealed 2024-07-01..2026-06-30 slice is not read.

## Question

The live book lost 9.0% over 2026-07-06..2026-10-30 (MaxDD -13.9%) while the tracker closed 32 trades with
1 win and 31 losses (mean -1.26R). The Nifty fell 5.0% in the window and is about 15% off its January
high. Is that the signature of a trend-pullback book inside a correction, or is something broken?

## Verdict rule, committed BEFORE any number was computed

Fixed here; not revisited after the run.

**Episodes.** Nifty-50 drawdown from its trailing 252-session high >= 8% (primary) and >= 10%
(sensitivity), consecutive days merged into one episode (runs separated by fewer than 21 sessions are
merged). Episode start = first session at or beyond the threshold (the live book also began "inside" a
correction), end = last session at or beyond it.

**Comparison shape.** Primary = the equal-length window (116 calendar days, the live window) starting at
each episode's start, taken as a continuous slice of ONE live-config replay. Full-episode slices are
reported too, not used for the rule.

**Measures and the "inside the range" test**
- Book return: live (-8.96% on the 1,000,000 start) vs the capped book's window return in each historical
  episode. Inside = live is no lower than the worst historical episode.
- Win rate: live 1/32 closed (win = R > 0) vs the per-episode win rate of Grade-A signals (uncapped
  replay) entered in the window and CLOSED by the window end (the censoring-matched analogue of the
  tracker's closed-only record). Episodes with fewer than 10 such trades are shown but not used for the
  range. Inside = live is no lower than the lowest qualifying episode.
- Binomial: p = pooled closed-within-window win rate of uncapped Grade-A signals entered in primary
  episode windows; P(X <= 1 | n = 32, p). Pass if P >= 0.05.

**Verdicts**
- **REGIME** — live is inside the range on book return AND on win rate AND binomial P >= 0.05.
- **WORSE THAN REGIME** — live is outside the range on book return or win rate, or binomial P < 0.05.
  Then the next step is a defect hunt (universe/data drift, fills, stops), listed in the readout.
- **INCONCLUSIVE** — fewer than 3 episodes at the primary threshold, or fewer than 3 qualifying episodes
  for the win-rate range.

**Caveats fixed in advance.** Few episodes (each is one path). The live book trades the post-2026-10-16
universe union while research uses `corrected_universe`. 19 live winners are still open (mark-to-market
-0.27R), so the live closed record is biased toward losses; the censoring-matched win rate removes that
bias from the historical side. Signals in one window are cross-correlated, so the binomial (independent
trials) is optimistic about how surprising 1-in-32 is. Eventual-outcome win rates are reported as a
secondary column and are not used in the rule.

---

# Result (everything above this line was written before the run)

Script `pipelines/diagnostics/diag_problem1_regime_match.py`; numbers in
`diagnostics/research/diagnosis/2026-11-02_problem1_regime_match.json`. One continuous live-config replay
(PIT membership, 2019-01-01..2024-06-28): Sharpe 1.025, MaxDD -40.1%, CAGR 20.5%, 77 trades (matches the
standing anchor). Uncapped Grade-A replay: 526 signals (1 degenerate stop excluded, 84 end-of-sample rows
dropped as censored). Data cut asserted at 2024-06-30; the sealed slice was not read. The live record comes
from `results/paper_portfolio_weekly.json`, `portfolio_history_weekly.csv` and `signals_history_weekly.json`
(history file ends 2026-10-23, 79 sessions; -8.96% on the 1,000,000 start).

**Verdict (pre-committed rule, primary threshold 8%): REGIME.** Narrowly, and with a threshold caveat below.

## Correction episodes found (Nifty >= 8% under its trailing 252-session high)

| start | trough | end | depth | note |
|---|---|---|---|---|
| 2019-01-02 | 2019-02-19 | 2019-02-28 | -9.7% | truncated: begins at the replay start, inside the late-2018 fall |
| 2019-07-30 | 2019-09-19 | 2019-09-19 | -11.4% | |
| 2020-02-28 | 2020-03-23 | 2020-09-30 | -38.4% | COVID; stays >= 8% under the high through September |
| 2021-11-30 | 2021-12-20 | 2021-12-22 | -10.1% | |
| 2022-02-14 | 2022-06-17 | 2022-07-28 | -17.2% | |
| 2022-09-28 | 2022-09-29 | 2022-10-11 | -9.0% | |
| 2023-02-28 | 2023-03-24 | 2023-03-29 | -9.9% | |

Seven episodes at 8%, six at 10% (the 2019-01 and 2022-09 episodes drop out; 2020 and 2022 each split in
two). 2020 Q1 and 2022 H1 are there as expected; so are 2019 H2, 2021 Q4 and 2023 Q1.

## The live record beside the 116-day window from each episode start

Continuous slices of the one capped run; trade columns are the uncapped Grade-A signals entered in the
window **and closed by the window end** (the censoring-matched analogue of the live closed-only tracker).

| window from | Nifty | book | book - Nifty | book MaxDD | book Sharpe | closed n | win rate | mean R | share < -1.5R |
|---|---|---|---|---|---|---|---|---|---|
| 2019-01-02 | +8.9% | +9.1% | +0.2pp | -6.3% | 2.15 | 12 | 0% | -1.33 | 17% |
| 2019-07-30 | +7.5% | +7.9% | +0.4pp | -4.2% | 1.44 | 5 | 0% | -1.52 | 60% |
| 2020-02-28 | -6.5% | +0.1% | +6.6pp | -30.9% | 0.20 | 12 | 8% | -1.85 | 42% |
| 2021-11-30 | +1.0% | -2.2% | -3.2pp | -20.0% | -0.10 | 24 | 12% | -1.08 | 21% |
| 2022-02-14 | -3.8% | **-10.5%** | -6.6pp | -14.4% | -1.15 | 13 | 8% | -1.16 | 38% |
| 2022-09-28 | +6.9% | +3.4% | -3.5pp | -9.1% | 0.76 | 11 | 9% | -1.26 | 27% |
| 2023-02-28 | +7.9% | +12.5% | +4.6pp | -2.6% | 3.77 | 3 | 0% | -1.41 | 33% |
| **pooled, unique signals (7 windows)** | | | | | | **78** | **7.7%** | **-1.30** | **28.2%** |
| **LIVE 2026-07-06..10-23** | **-5.0%** (to 10-30) | **-9.0%** | **-4.0pp** | **-13.9%** | **-2.20** | **32** | **3.1% (1/32)** | **-1.26** | **28.1% (9/32)** |

Capped-book trades are too few per window to read (2 to 11 entered; per-window numbers are in the JSON).
Share of stop exits among those closed trades: pooled 91% (live 81%); mean loss beyond the 1R stop on stop
exits: pooled 0.60R (train all-period 0.45R for the uncapped book).

## Where live sits

- **Book return:** range across episodes -10.5% .. +12.5%; live -9.0% is inside, and 1 of 7 episodes
  (2022 H1) was worse. Book MaxDD -13.9% is inside the -2.6% .. -30.9% range. Book minus Nifty -4.0pp is
  inside -6.6pp .. +6.6pp.
- **Only two of the seven windows had a falling Nifty** (2020 Q1 at -6.5%, 2022 H1 at -3.8%), which is the
  live shape (-5.0%). The book returned +0.1% and -10.5% in them. The live -9.0% is close to the 2022 H1
  slice, the nearer analogue.
- **Win rate:** qualifying windows (>= 10 closed signals; 5 of them) run 0% to 12.5%; live 3.1% is inside.
  Pooled closed-by-window-end win rate is 7.7% (6 of 78). **P(<= 1 win in 32 | p = 7.7%) = 0.28**, well above
  0.05.
- **The same signals, read by eventual outcome, win 45.6%** (98 of 215, mean +0.89R). The gap between 7.7%
  and 45.6% is the censoring effect itself: in a correction the quick losers close inside the window and the
  winners are still running. At the eventual rate, 1-in-32 would have P of about 1e-7, but that is the wrong
  comparison for a closed-only record.
- **Loss shape matches too.** Pooled closed signals: mean -1.30R, median -1.23R, 28.2% worse than -1.5R,
  91% stop exits. Live: mean -1.26R, median -1.19R, 28.1%, 81%. The "losses larger than designed" pattern
  (Problem 2) is already in the historical correction windows; it is not new in the live book.

## Sensitivity: the 10% threshold flips the book-return test

At >= 10% (6 episodes) the same pre-committed rule returns WORSE THAN REGIME: the range of window book
returns narrows to -6.9% .. +25.1% (the 2022 window that read -10.5% at 8% now starts on 2022-02-24 and
reads -6.9%), so live -9.0% sits 2.1pp below the worst; the lowest qualifying win rate becomes 6.3% (3
qualifying windows) against live 3.1%. The binomial still passes (pooled 6.8%, P = 0.35). The flip is a
range-edge effect: it moves with where one episode's window begins by a few days, on a range set by a handful
of paths. It is a warning that the REGIME call rests on the 2022 H1 episode being the live analogue, not
evidence that a defect exists. The primary rule was fixed at 8% before the run and is reported as the
verdict.

## What this does and does not say

- **Says:** a 1-in-32 closed record, a -1.3R mean, a 28% share of losses beyond -1.5R and a -9% window are
  each reproduced by the live config in the train window's own corrections (7.7% pooled closed win rate,
  mean -1.30R). Nothing in the closed-trade statistics needs a defect to explain it.
- **Does not say:** the book is fine. The book was fully deployed throughout, and the historical slices show
  the same exposure problem (2022 H1: -10.5% vs Nifty -3.8%, MaxDD -14.4%). That is Problem 1 as written: no
  capital-at-risk response to the tape.
- **Caveats (fixed in advance, confirmed):** seven episodes, each one path; the 2019-01 episode is truncated
  at the replay start; windows that begin at the threshold crossing often catch a rebound (5 of 7 Nifty
  windows are positive), so the falling-tape sample is two paths; the live book trades the post-2026-10-16
  universe union while research uses `corrected_universe`; 19 live positions are open (MTM -0.27R) so live
  closed stats are censored (handled on the historical side only); signals within a window are
  cross-correlated, so the binomial treats 78 correlated signals as independent and the P of 0.28 is
  indicative, not exact.
- **Pooling note:** a first pass pooled the windows without removing signals that fall in two overlapping
  windows (2021-11-30 and 2022-02-14 overlap); that double-counted 2 closed signals (P 0.297). It was fixed to
  count each signal once (n 80 to 78, P 0.283) before this note was written. The verdict is unchanged.

## Defect hunt (not triggered at the primary threshold; the next checks if more evidence is wanted)

(1) Universe/data drift: difference the live top-5 against a `corrected_universe` replay week by week (33 to
41% of weeks already differ). (2) Fills: compare live fill prices with next-open prices for the 32 closed
trades. (3) Stops: check the 9 trades worse than -1.5R for gap-through vs a stop-width defect (CHOLAFIN
-3.76R, CANFINHOME -2.94R, LINDEINDIA -2.32R, CCL -2.18R lead). The decisive but sealed-slice test (one read
of the live config through 2024H2-2026H1) is an owner decision, not made here.

**Next step that follows from REGIME:** Problem 1 stands as an exposure problem. The cheapest test is a
breadth- or drawdown-based capital-at-risk throttle measured as an activation bound first (Law VII: it buys
drawdown with return), at the screen tier, not here.
