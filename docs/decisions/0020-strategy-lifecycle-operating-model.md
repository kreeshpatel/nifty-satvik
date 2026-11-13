# ADR-0020 — Strategy-lifecycle operating model

**Date:** 2026-11-13 · **Status:** PROPOSED · **Decider:** owner
**Class:** infrastructure and process. No live trading rule, engine or sealed data is touched. Zero trials, zero
screens. Standing counts unchanged: screens 24 · sealed opens 4 · n_trials 3.

(ADR number 0019 is unused; 0020 was assigned by the owner.)

## Context

The 2026-11 inventory study (`diagnostics/research/2026-11_system_inventory.md`) found that:
- four books run side by side with different record formats and no shared rule for when a result means something;
- the live swing is being judged on 19 weeks of forward data, a period too short to tell a good strategy from a bad
  one. The standard error of a 3-month Sharpe estimate is about 2;
- cross-sectional momentum 0001, the strongest book in the backtest, has no forward record at all;
- rule changes and new research ideas arrive weekly, in response to the latest trades.

This ADR proposes one operating model for every strategy after research.

## Decision (proposed)

### A. The rules — `skills/strategy-lifecycle/SKILL.md`

- **Stages:** RESEARCH → PAPER → PILOT (10% of intended capital) → SCALE (25%) → FULL. Moves are one stage at a time.
- **Promotion:**
  - PAPER → PILOT needs at least 26 weeks of paper record, AMBER or better at week 26, and no RED in the last 8 weeks.
  - PILOT → SCALE and SCALE → FULL each need at least 13 weeks at the stage, AMBER or better, and execution tracking
    error under 1% a quarter.
- **Weekly status against frozen bands:**
  - GREEN: return at or above the 25th percentile, and drawdown within the band's 95th percentile.
  - AMBER: return between the 5th and 25th percentile.
  - RED: return below the 5th percentile, or drawdown deeper than 1.25 × the backtest's worst.
- **RED means a review, not a kill.** The review asks three questions in order: a data or execution fault; a regime
  the backtest contained; a structural change. A strategy may be demoted one stage. It may be retired only after RED at
  two consecutive monthly checks past week 26, or RED on the drawdown breaker.
- **No forward verdict before 26 weeks,** except the drawdown breaker.
- **Change control:** rule changes only at quarterly reviews, at most one per strategy per review, each with a dated
  amendment. The record continues with the change date marked; bands are rebuilt only for the changed version.
- **Benchmark rule:** every weekly report shows the Nifty Midcap150 Momentum 50 TRI over the same dates. Trailing its
  risk-adjusted return over 52 weeks flags the strategy for the next quarterly review.
- **Research freeze:** while any strategy is in PAPER or PILOT, new ideas go to `research/BACKLOG.md` and do not run
  without the owner's approval.

### B. Frozen expectation bands — `pipelines/lifecycle/build_bands.py`, `forward/bands/`

Cumulative return and max drawdown at 13 / 26 / 52 / 104 weeks, from a 20-path ensemble and from a stationary block
bootstrap (8-week mean block, 5,000 draws), using the wider of the two for each percentile. Files are write-once.
Bands dated 2026-11-13 exist for the live swing, momentum 0001, long-horizon and the 70/30 blend with the 15%
volatility target.

### C. Append-only forward records — `pipelines/lifecycle/update_records.py`, `forward/records/`

One row per week per strategy: date, NAV, weekly return, holdings, turnover, benchmark TRI. Momentum 0001 and the
blend start paper records at the next Saturday scan, on the scan's own price data. The live swing and long-horizon
keep their existing records, mirrored into the same format. A recorded week never changes (ADR-0018).

### D. Weekly report — `pipelines/lifecycle/weekly_status.py`, `results/lifecycle_status.json`

Stage, weeks, return, drawdown, band percentile, status, benchmark comparison and review triggers, printed on the
scan's run page each Saturday.

### F. Execution capture

The app's manual fill entry is already built, but it holds 0 fills. The weekly report shows tracking error (real
fill against model price, in basis points and in R) once fills exist. See
`docs/EXECUTION_CAPTURE_STATUS_2026-11.md`.

## Current stage of each strategy

| strategy | stage | since | forward record | status on 2026-11-13 |
|---|---|---|---|---|
| Live swing (Grade A) | **existing live** (predates this model) | 2026-07-06 | `forward/records/live_swing.csv`, 19 weeks | AMBER, provisional: −4.0%, between the 5th and 25th percentile of its 13-week band |
| Cross-sectional momentum (0001) | **PAPER** from its first record date | first Saturday scan after merge | `forward/records/xsec_momentum_0001.csv` | none yet |
| 70/30 momentum/swing, 15% vol target | **PAPER** from its first record date | first Saturday scan after merge | `forward/records/blend_70_30_vt15.csv` | none yet |
| Long-horizon trend | **PAPER** (forward-wall base arm) | 2026-08-12 | `forward/records/long_horizon.csv`, 13 weeks | GREEN, provisional: −0.7% |

The earliest date any of these can receive a forward verdict is 26 weeks after its record started: the live swing in
early January 2027, long-horizon in mid-February 2027, and momentum and the blend about 26 weeks after their first row.

## Quarterly reviews, 2027

The first trading day of January, April, July and October 2027: nominally **2027-01-01, 2027-04-01, 2027-07-01 and
2027-10-01**, moved to the next session if the exchange is closed. NSE has not yet published its 2027 holiday list.
The January agenda is `diagnostics/research/review_2027-01-01_agenda.md`.

## Research freeze

In force from the date this ADR is accepted, because momentum, the blend and long-horizon are in PAPER. The backlog
starts with the four ideas parked on 2026-11-13 (`research/BACKLOG.md`). Measurement of what is already running is not
frozen.

## Decisions needed from owner

1. **Capital per stage.** The rupee amount that "intended capital" means for each strategy, so that PILOT (10%) and
   SCALE (25%) are concrete numbers.
2. **Where core capital sits while momentum is in PAPER.** Whether it is held in a Nifty Midcap150 Momentum 50 index
   fund (the benchmark, and the nearest investable equivalent) until momentum earns a PILOT.
3. **The swing's capital.** Whether the live swing's capital is reduced while it is AMBER and before its 26-week mark,
   or left as it is until its first verdict date.
4. **The older paper gate.** `skills/portfolio-simulation` and `forward/prereg_swing.md` §3 allow real capital after 30
   closed trades and about 2 months. This model says 26 weeks. The skill applies the stricter rule until one of the two
   is amended by the owner.
5. **Whether the live swing is placed on the stage ladder** (for example as PILOT or SCALE) or stays "existing live"
   outside it.
6. **Fill entry.** Whether the 55 live trades' real fills are entered into the app, so tracking error can be measured.

## Consequences

- "Is it working?" has one answer, from one file, on one schedule.
- Nothing can be promoted, demoted or retired on a few weeks of results.
- Rule changes slow to at most four a year per strategy.
- The price is patience: momentum cannot receive capital under this model before about mid-May 2027.

## What this does not change

The live swing's rules, the engine, the trial counter, the sealed slice, the mechanical halts in `forward/prereg.md`
§4 and `forward/prereg_swing.md` §5, and the pre-registration and verdict procedures.
