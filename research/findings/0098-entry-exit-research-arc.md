# 0098 — Entry/exit research arc: the strategy resists every "make it safer" tweak

**Date:** 2026-07-14
**Type:** MEASUREMENT arc (exploratory; no promote/kill decision on the locked base → **not trials**;
n_trials stays 114).
**Book:** Bhanushali weekly-swing, ranker of record `0094`, corrected universe, NET, 2017-01 → 2026-06.
**Motivation:** owner-driven, chart-led search (DELHIVERY, HEG, LTF, SUZLON) for an entry/exit rule
that improves the book. ~20 configurations tested.
**Skills:** `backtest-rigor` (§C1b plateau-not-peak, §C4 concentration, per-trade-vs-portfolio),
`leakage-audit` (survivorship on the midcap list), `quantitative-research`.

## The single result

**No entry or exit rule robustly improves *returns* in-sample. The frozen strategy (all-grades,
weekly signal, current half@2R+trail exit) is the best config found.** The edge is *buying strength*
and it resists every attempt to make it "safer." One idea survives as a **drawdown** lever only
(max-stop cap), non-certifiable on returns.

## Verdict ledger (portfolio-level, NET, PIT-clean unless noted)

| Lever | Result | Why |
|---|---|---|
| Buy near the SMA / tight candle | **✗** | near-SMA is the *worst* return quintile (win 23% vs 36%) |
| Reject wide candles | **✗** | wide candles are the *winners* (survivorship-tainted, but robust direction) |
| Daily-uptrend gate (+weekly) | **✗** CAGR 24.7→11-15% | delays entry into extended fills — *caused* the HEG −22.8% (blocked the ₹442 touch, forced the ₹563 spike) |
| Volume filter / HVC ranker | **✗** (0097) | selection already absorbs volume |
| Body-gain cap (skip >8% spike weeks) | **✗** on the clean book (0.88→0.73) | spike weeks are net winners; only "helped" the already-broken daily-gate combo |
| Trend-hold exit (6mo cap / 9%-below-dSMA) | **✗** Sharpe 0.91→0.49 | per-trade "win" is a mirage — capital lock-up kills the portfolio; per-trade ≠ portfolio |
| Exit ladder 25%@2R / 25%@3R / 50% trail | **✗** neutral-to-worse | most 2R trades don't reach 3R and give it back; current 50%@2R+trail wins |
| All-grades (drop A/B top-5 cap) | **✗** win 55%→30% | floods the book with weak signals |
| **Max-stop-distance cap (skip fills >X% above stop)** | **~ DD only** | consistently cuts MaxDD (−40→−30%); **but return response is NON-MONOTONE** (12%→0.955, 15%→0.760, 18%→0.938 Sharpe) = §C1b peak-not-plateau → return "win" is noise |

## Root-cause readouts (the transferable lessons)

1. **The edge is unfilterable right-tail runners.** Return = the ~20% of trades that trend for
   months (exit `time6m`: 94% win, +34%); the other 80% are small stops (0% win). No entry feature
   separates them (best quintile spread win 23%→36%). You cannot know at entry which becomes a runner.
2. **"Confirmation" delays you into worse entries.** The daily-uptrend gate blocks the cheap
   near-SMA touch (trend not up yet) and only fires *after* the spike — the concrete mechanism behind
   HEG's ₹563 wide-stop entry and the −22.8% loss.
3. **Per-trade ≠ portfolio.** The trend-hold exit and midcap both looked great per-trade (+8.2%),
   then collapsed at the portfolio level (capital lock-up) or under survivorship correction.
4. **Wide stops are the real risk.** Stops = setup-week low; on wide/extended fills that is 15-23%
   below entry (HEG 22.8%), and gaps blow through it (NAVA/ERIS −14% below stop on the 2025-04-07
   crash). With 2% sizing a wide-stop loss is still ~2% of capital; the gaps are the uncapped tail.
5. **Survivorship inflation is huge.** Today's Nifty-Midcap-100 list on 2017-26 doubled the apparent
   edge (+8.2% vs clean +3.7%) and manufactured the "extended-wins-big" pattern (SUZLON +300% etc.).
   No PIT midcap membership exists → a clean midcap test is not possible today.

## Disposition
- **Grading + entry + exit all stay as the frozen `0094` book.** Entry/exit research is CLOSED.
- **The one survivor — the max-stop-distance cap — is a DRAWDOWN overlay candidate, not a return
  edge.** Its return curve is non-monotone (uncertifiable in-sample); its DD benefit is mechanical.
  Routed to the forward wall (`forward/prereg_swing.md`), param fixed by *mechanism* (≤15%, not the
  in-sample-peak 12%), judged on OOS drawdown only.

## Next setup
None in-sample. The next unbiased bit is the forward wall. Do not relitigate any row above without a
genuinely new lever (new PIT data — e.g. real midcap membership — a new feature, or a new sub-period).
