# ADR-0020 — Strategy-lifecycle operating model

**Date:** 2026-11-13 · **Status:** ACCEPTED 2026-11-14 · **Decider:** owner
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
| Live swing (Grade A) | **PILOT** from 2026-11-14 (owner decision 5); live since 2026-07-06 | 2026-07-06 | `forward/records/live_swing.csv`, 19 weeks | AMBER, provisional: −4.0%, between the 5th and 25th percentile of its 13-week band |
| Cross-sectional momentum (0001), a component of the system | **PAPER** from its first record date | first Saturday scan after merge | `forward/records/xsec_momentum_0001.csv` | none yet |
| 70/30 momentum/swing, 15% vol target (**the target system**, ₹20,00,000) | **PAPER** from its first record date | first Saturday scan after merge | `forward/records/blend_70_30_vt15.csv` | none yet |
| Long-horizon trend | **PAPER** (forward-wall base arm) | 2026-08-12 | `forward/records/long_horizon.csv`, 13 weeks | GREEN, provisional: −0.7% |

The earliest date any of these can receive a forward verdict is 26 weeks after its record started: the live swing in
early January 2027, long-horizon in mid-February 2027, and momentum and the blend about 26 weeks after their first row.

## Quarterly reviews, 2027

The first trading day of January, April, July and October 2027: nominally **2027-01-01, 2027-04-01, 2027-07-01 and
2027-10-01**, moved to the next session if the exchange is closed. NSE has not yet published its 2027 holiday list.
The January agenda is `diagnostics/research/review_2027-01-01_agenda.md`.

## Research freeze

In force from 2026-11-14, because momentum, the blend and long-horizon are in PAPER. The backlog
starts with the four ideas parked on 2026-11-13 (`research/BACKLOG.md`). Measurement of what is already running is not
frozen.

## Owner decisions (accepted 2026-11-14)

1. **Target system and capital.** The target system is the **70/30 momentum/swing blend with the 15% volatility
   target**. Stage percentages apply to **total system capital of ₹20,00,000**: PILOT is ₹2,00,000, SCALE ₹5,00,000,
   FULL ₹20,00,000. Momentum 0001 is tracked as a **component** of that system, with its own record and bands, not as
   a separately funded strategy.
2. **Core capital while momentum is in PAPER.** Core capital goes into a **Nifty Midcap150 Momentum 50 index fund**,
   bought in **three equal monthly parts**. The owner places these purchases; nothing in this repo trades.
3. **The swing's capital.** **No change and no additions** before the swing's 26-week mark. The decision is taken at
   the January 2027 review.
4. **Paper gate.** The **26-week paper gate replaces** the older gate of 30 closed trades and about 2 months
   (`skills/portfolio-simulation`, `forward/prereg_swing.md` §3).
5. **The live swing's stage.** The live swing **joins the ladder at PILOT** from 2026-11-14.
6. **Real fills.** Yes. The Saturday scan reads recorded fills **for tracking error only, never for a model
   decision**: no signal, size, stop or exit may depend on a fill.

**Deferred:** the This Week section for the weekly status.

**Open points these decisions leave, for the January 2027 review**
- The swing is at PILOT with its capital unchanged (decision 3), while PILOT is nominally ₹2,00,000 of system capital
  (decision 1). Whether the swing's capital is brought to that figure is part of the January decision.
- The rupee amount of "core capital" for the index-fund purchases (decision 2) is the owner's to set.
- The scan can only read fills once it has read access to the app's database: a read-only connection string stored as
  the repository secret `LIFECYCLE_FILLS_DB_URL`. Until then the report says tracking error is not measurable. Only
  aggregates are published; individual fills are never written to this public repository.

## Consequences

- "Is it working?" has one answer, from one file, on one schedule.
- Nothing can be promoted, demoted or retired on a few weeks of results.
- Rule changes slow to at most four a year per strategy.
- The price is patience: the target system cannot move from PAPER to PILOT before about mid-May 2027, 26 weeks after its
  first record. Until then core capital sits in the benchmark index fund (decision 2).

## What this does not change

The live swing's rules, the engine, the trial counter, the sealed slice, the mechanical halts in `forward/prereg.md`
§4 and `forward/prereg_swing.md` §5, and the pre-registration and verdict procedures.
