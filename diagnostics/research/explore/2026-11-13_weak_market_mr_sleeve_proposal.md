# 2026-11-13 — Proposal: a weak-market mean-reversion sleeve, paper-traded forward

**Tier:** EXPLORE proposal. Nothing is backtested, tuned or traded by this note, and no counter moves. Standing counts:
screens 24 · sealed opens 3 · n_trials 2. Owner request: sketch it as a paper-trade proposal and do not backtest-tune it yet.

## Why a sleeve, and why only in weak markets

All 55 live swing trades (July–October 2026) were signalled with the Nifty below its 40-week SMA, and the swing book
lost money there. History says the same about that state: blocking new swing entries in it cuts the worst drawdown on
every one of 20 paths, but costs Sharpe on every path, because rebounds also start there (2026-11-12 ensemble). The
swing book is a trend follower, so a weak tape is the wrong environment for it. A small, separate book that is active
only in that state, and earns from short rebounds instead of trends, would diversify by **time**: it works when the
swing book is idle or losing.

## Registry confrontation

- **Reversal / RSI-oversold: KILL (0020/0022/0024, v1 epoch, 7–14-day base book). Not re-tested under the current
  harness.** Under the 2026-08-08 amendment those verdicts set priority, not closure. This proposal differs on three
  axes those studies did not have:
  1. a regime gate (only when the Nifty is below its 40-week SMA);
  2. a strength filter (only stocks that are leaders on 6-month relative strength and still above their own 40-week SMA);
  3. a wide disaster stop and a time exit, not a signal exit.
- **Indicator zoo at 63 days** (O-015/0079: RSI-family IC ≈ 0) is a different horizon. This sleeve holds 10 sessions.
- **Sleeves:** STAGE4 (no sleeve beat the touch-only book under the cap) and 0115 (low-USD-beta sleeve, KILLED on
  correlation) were capital-competing sleeves. This one is regime-switched, so it should rarely compete for cash. The
  blend-hybrid low-vol book is the standing WATCHED sleeve.
- **Specification uncertainty is a multiplicity axis** (0133). "Oversold" has several faithful readings, so all three
  below are logged together as one family and judged as a family, never by the best reading.

## The rule (frozen for paper; no parameter below was fitted)

| part | rule |
|---|---|
| when it can open trades | the Nifty's last weekly close is below its 40-week SMA (the same state as the S1 throttle) |
| universe | PIT Nifty-500 members on the day |
| "strong" | 26-week return minus the Nifty's 26-week return in the top 20% of the universe, **and** the stock's weekly close above its own 40-week SMA |
| "oversold" (logged as a family of three readings) | R1: close at least 8% below its 10-session high · R2: RSI(2) below 10 · R3: close below the lower Bollinger band (20, 2) |
| entry | next session's open |
| time exit | the close of the 10th session after entry |
| disaster stop | 15% below entry, standing daily: fill at the stop, or at the open if it gaps through |
| size | equal notional, 5% of sleeve capital per position, at most 8 open; ₹2,00,000 notional paper capital, separate from the swing book |
| costs | the swing book's cost model |
| no re-entry | a stock cannot re-enter within 10 sessions of its last exit |

Stop, horizon and thresholds are round, conventional values chosen before looking at any data, and they stay fixed for
the paper period. A sweep would be tuning.

## How it would be run

- A forward-only daily logger (a new `scripts/run_mr_sleeve_paper.py`, run in the daily monitor job) writes
  `results/mr_sleeve_paper.json`: signals, fills, exits, and a NAV per reading R1/R2/R3.
- `forward/prereg_swing.md` §2 caps the forward-logged books, so starting this needs an **owner-written §2 amendment**,
  as the blend-hybrid book had. No live money; cards are not shown in the product.
- The evaluation rule is pre-registered **before** the first read: about 40 closed trades per reading, or 12 months,
  whichever comes later. It is judged against (a) the Nifty over the same holding windows and (b) cash; plus its
  correlation with the swing book's weekly returns. It is decided as a family: the median reading must pass, not the best.

## What would kill it early, and the leaks to avoid

- A sleeve that loses in the regime it was built for is worse than idle cash. A family-median drawdown beyond −15% of
  sleeve capital before the evaluation point halts it (mechanical, no discretion).
- **Falling knives:** in a 2020-style crash the strength filter thins the universe but does not stop a gap through the
  disaster stop. That is the tail this sleeve sells, and the paper period may not contain one. Read a calm-period pass
  with that in mind.
- **PIT:** the strength rank and the membership are computed on data up to the signal day only; RSI and Bollinger use
  closes up to that day; the entry is the next open.

## Cheapest steps from here

1. Owner decides whether to start paper logging (§2 amendment).
2. Optional, train window only, before or alongside paper: an **activation bound**, not a backtest-tune. Run the frozen
   rule once on 2019..2024-06 for the family-median R1–R3 and report whether it clears the ±10R/yr noise floor at all. If
   it cannot, paper-logging it is not worth the slot. Not run here, per the owner's instruction.
