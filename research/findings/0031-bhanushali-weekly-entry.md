# 0031 — Weekly-confirmation entry on the 0085 book: CAGR HALVED-and-more (+11.5%→+2.3%), the opposite of the goal — KILL

- **Status:** TRIAL (pre-reg [0088](../../diagnostics/research/preregistry/0088-bhanushali-weekly-entry.md),
  n_trials 105→106, params frozen before the run). **Verdict: KILL** (negative continuous slice; and it
  *lowered* the CAGR it was built to raise).
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_entry.py`; ledger
  `research/exports/bhanushali_weekly_entry_0088_trades.csv` (440 trades). Same cell as 0084/0085.

## What was tested
0085 exits/sizing/universe/costs byte-identical; the DAILY pullback+green signal replaced by a WEEKLY
setup: a completed green weekly candle rebounding off the weekly 44-EMA within the weekly bucket → buy-stop
at that week's HIGH, valid Mon+Tue only, initial stop = that week's LOW. Owner CAGR-hunt (the literal
"forward look on buying prices" was refused as lookahead; this is the leak-free reframe — is a weekly
entry a *better* entry?).

## Result (corrected universe, real tiered costs)

| | trades | win | expR | CAGR | Sharpe | MaxDD | mult |
|---|---|---|---|---|---|---|---|
| **0088 weekly entry** | 440 (46/yr) | 38.0% | +0.11 | **+2.3%** | **+0.215** | −41.3% | 1.24× |
| 0085 reference (same cell) | 432 | 39.6% | +0.23 | +11.5% | +0.587 | −37.5% | 2.80× |

Slices **−0.58** / +0.84 / **+0.05** (2017-18 negative, 2022-26 ≈ flat → gates FAIL). CI [−0.522, +0.780];
DSR@106 = 0.025. **ΔSharpe vs 0085 = −0.372; ΔCAGR = −9.2pp.**

## Root-cause readout (REQUIRED) — both pre-registered risks fired
1. **The weekly stop is ~2× wider → positions ~half the size.** Median entry-to-stop width **12.8%** vs
   0085's daily ~7%. Sizing is `2% ÷ (entry−stop)`, so a doubled risk-per-share halves the share count for
   the same 2% risk → each trade's rupee P&L shrinks. This alone caps CAGR regardless of trade quality —
   exactly the pre-reg's flag #2.
2. **Buying near the weekly high is a WORSE (higher) entry, not a cheaper one — flag #1 confirmed.** The
   entry sits far above the pullback, so far fewer trades ever reach +2R: the runner engine barely engages
   (only 55 trail + a handful of target exits), and **288 of 440 trades die on the daily 44-SMA breach**
   before the half-book — small chop losses. expR collapsed 0.23→0.11.
3. **Fill rate 3%** (440 fills from 13,607 weekly activations): requiring the breakout to clear the weekly
   high inside Mon+Tue drops most setups — and the ones that DO clear it are buying strength at a premium,
   the worst of both worlds (few trades AND expensive entries).
4. Net: a stronger trend filter (weekly) bought at a worse price with smaller size = lower return on every
   axis. The CAGR *fell* to near the risk-free rate.

## Verdict & next setup
**KILL.** The weekly-entry hypothesis is falsified in the direction that matters: it *reduced* CAGR to
+2.3% (from 0085's +11.5%), below even a fixed deposit. The lesson generalizes the whole entry-side arc:
on this funnel, **cheaper/earlier entries help and later/higher entries hurt** — the daily pullback-candle
high (0084/0085) is already a good entry, and moving *up* a timeframe moves the fill *up* the price.
Combined with the twice-killed exit-acceleration (0087 + withdrawn recycle) and five dead entry gates
(0086 latest), the six-step funnel's trade rules are now comprehensively mapped: **0085 is the ceiling**,
and every lever off it is flat-to-worse. The only unspent CAGR/DD lever is **portfolio-level** (O-009
vol-target on deployed equity, O-018 multi-sleeve sizing) — the 2026-10-01 review question. No more
single-arm entry/exit variants on this funnel without a genuinely new mechanism.
