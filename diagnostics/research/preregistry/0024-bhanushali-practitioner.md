# 0024 — Bhanushali PRACTITIONER-faithful backtest (weekly watchlist + no-overtrade process)

- **Status:** COMPLETE (2026-07-03) → `research/findings/0024-bhanushali-practitioner.md`.
- **Class:** MEASUREMENT / external-strategy analysis (same class as 0022/0023 — not an overlay trial on
  the momentum sleeve, no cfg change, no n_trials increment; the DSR family is unaffected). Judged on its
  own gross/net economics vs baseline_v1, never promoted from this test.
- **Motivation.** Owner audit (2026-07-03): the 0022/0023 tests ran the *entry/exit mechanics* but skipped
  the *portfolio process* a real trader runs — the weekly frozen watchlist, the trade throttle, scaling
  out, the index regime check. Those omissions caused the 260-trades/yr overtrading that made costs the
  story. This test implements the process as a practitioner actually runs it. Owner decisions (recorded
  from AskUserQuestion): watchlist rank = trend+volatility+volume; exits = half at 1:2 then swing-low
  trail; NIFTY regime filter = pause new entries; throttle = 5 positions / 3 new per week.

## Frozen spec (no retuning after results — UNDERPOWERED/negative is a first-class outcome)

**Universe & data.** PIT Nifty-500 membership, 2017-01-01..2026-06, `data/ohlcv.pkl` (sha f8625a8f — known
survivor-only for 103 delisted members; results are therefore OPTIMISTIC and flagged as such in the finding).
Tiered real costs (brokerage+STT 0.13%/leg + slippage 0.05% large / 0.22% mid by ADV≥50cr), ADV≥5cr skip.

**Weekend watchlist (rebuilt on the first trading day of each ISO week, data strictly before that day, frozen
for the week).** Eligible: PIT member, clearly-rising daily 44-SMA (rose over 22/44/66d AND close>SMA AND
66d SMA slope ≥ +8%), ADV20 ≥ 5cr, ATR(14)/close ≥ 1.5% (volatile enough to reach 1:2 in days). Rank =
z(66d 44-SMA slope) + z(ADV20/ADV60 volume expansion — the "in the news" proxy; no historical news feed
exists, and his own §8 "price+volume move before news" endorses the proxy). Keep top 50.

**Setups (only from the frozen watchlist, signal day t-1 → entry day t..t+3):**
- B (pullback): low ≤ 44SMA×1.02 AND close ≥ 44SMA (touch-and-HOLD, no knife-through), quality green candle
  (close>open AND close in upper half of range), volume ≥ 1.5× 20d average (HVC confirm).
- A (RSI): weekly 44-SMA sustained-rising, daily RSI(14) crossed back ≥35 from below, same quality-green +
  volume confirm.
- Baseline arm = A OR B combined (a practitioner uses both on one watchlist).

**Entry order.** Buy-stop at signal high ×1.001, live 3 trading days; if it gaps >1.5% above the trigger,
skip that day (no chasing); fill = max(open, trigger).

**Initial stop.** Signal-candle low ×0.999; if the candle range ≥6% of close, stop at candle midpoint (his
§13 big-candle rule).

**Exits.** Half the position at +2R (limit); after the half-book, stop floors at breakeven; the remainder
trails his §12 swing-low ratchet — the stop rises to each newly *confirmed* higher swing low (pivot low,
2 bars each side, usable only 2 bars after the pivot — PIT-safe). Safety time-stop 60 trading days. Stop
checked before target within a day (conservative).

**Regime.** No NEW entries while the Nifty-500 TRI benchmark is below its rising daily 44-SMA (close>SMA and
SMA up over 10d). Open positions run to their exits.

**Throttle.** Max 5 concurrent positions, max 3 new entries per ISO week, 10-trading-day re-entry cooldown
per name after any exit. Risk 2% of equity per trade, notional cap 30%/position.

**Pre-declared arms (ALL will be reported):** combined A+B (headline); B only; A only; regime OFF ablation;
volume-confirm OFF ablation; throttle OFF ablation (15 positions, unlimited weekly entries). Gross and net
for the headline; net for ablations. Metrics: Sharpe, CAGR, MaxDD, trades/yr, win%, expR, maxR, exit mix,
continuous-slice sub-periods (2017-18 / 2019-21 / 2022-26).

**Known limitations recorded up front:** survivor-only price cache (optimistic); no earnings-calendar
avoidance (no historical earnings-date data); gap-through stops filled at the stop (optimistic); weekly
watchlist uses Monday-open information only (PIT-safe).

**Amendments (2026-07-03, owner-caught, before any conclusion was anchored):**
1. Watchlist eligibility required the strong DAILY trend for all setups — near-mutually-exclusive with
   daily RSI<35 (41 joint events in 1.4M ticker-days) → engine A showed 3 trades/9.5y, an artifact.
   Fixed: eligibility = strong-daily OR sustained-weekly trend.
2. The daily-slope rank buried the surviving RSI candidates (7% of 2,637 signals made the list). Added a
   pre-declared arm: engine A on its own weekly-slope-ranked list (his RSI-system watchlist is weekly).

**Success criteria (fixed):** interesting = net Sharpe > 0 with trades/yr ≤ ~80 and DD shallower than the
2023-26 base; NOT tradeable/promotable regardless of outcome — the forward wall remains the only certifier.
