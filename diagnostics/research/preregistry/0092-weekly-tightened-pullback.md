# 0092 — Tightened weekly six-step: pullback to a VISIBLY-rising 44-week SMA (owner chart-QA spec)

- **ID:** 0092. **Status: PRE-REGISTERED** (spec frozen before the performance run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 109 → 110.
- **Anchor / data:** identical cell to 0091 (corrected universe, PIT membership, tiered costs, 2017–2026,
  EQ0 ₹10L). Script `scripts/run_bhanushali_weekly_tight.py`.

## Why this trial exists
Owner QA of the 0091 live signals against real charts (360ONE, Aadhar HFC, Bajaj Finance, Asian Paints,
ALKEM, Ashok Leyland) found 0091's filters too loose by eye: sideways/rolling MAs pass, and extended names
15%+ above the MA count as "pullbacks." The owner drew the intended setup — price **dips down to a clearly
rising** 44-week SMA and bounces (circles), reject when the **MA is flat/rolling** (arrow). This trial
encodes that exact visual as a tightened variant and asks the only honest question: does "fewer, cleaner"
actually beat 0091's loose +18.2% / +0.87, or just trade less?

## The FROZEN spec (three signal tightenings vs 0091; everything else byte-identical to 0091)

| Component | 0091 (loose) | **0092 (this trial)** |
|---|---|---|
| Trend / "visibly rising" | 44w-SMA > 44w-SMA 4 weeks ago (any uptick) | `close > 44w-SMA` **AND** 44w-SMA up **≥ 3% over the last 13 weeks** (`wsma/wsma.shift(13)−1 ≥ 0.03`) — a visible quarter-long climb; rejects flat/rolling MAs |
| Pullback "touch" | week low ≤ 44w-SMA × 1.07 (7%) | week **low ≤ SMA × 1.03** (dips to the line) **AND** **SMA < close ≤ SMA × 1.06** (closes near the line, not extended) |
| Green candle | close > open (bare green) | **quality green** — `close > open` AND `(close − low) ≥ 0.5 × (high − low)` (closed in the upper half; a decisive bounce) |
| Entry / stop / exits / sizing / universe / costs | — | **exactly 0091** — in-range open entry the next week, stop = signal-week low, half at +2R, 20-day-SMA −4% trail, weekly-close/Monday exits, 13-week cap, 2% risk, no rotation |

Threshold provenance (frozen a priori, NOT tuned to performance): the 3% slope floor mirrors the existing
practitioner `strong` filter's slope-floor idea; the 3%/6% band tightens 0091's 7% toward 0084's 2% daily
touch; quality-green is the existing `qgreen`. Signal-**frequency** calibrated only (loose 24,263 →
tightened 5,109 signal-weeks) to confirm non-degenerate; performance unseen at freeze time.

## Primary metric + diagnostics
**Corrected-universe NET Sharpe** (one number); CAGR / MaxDD / win-rate co-reported (the point is
better-quality trades). References (not gates): 0091 +0.869 / +18.2% / −41.5% / win 52%, TRI +12.6%.
Diagnostics: trades vs 0091 (expect far fewer), signals/week (expect ~10 not ~50), per-year, exit mix,
2023-concentration (does tightening reduce the 49%-in-one-year dependence?).

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@110 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
**Head-to-head vs 0091 (informational, decides the live book):** if 0092 matches-or-beats 0091 on
risk-adjusted terms (Sharpe and/or Calmar) at materially fewer/cleaner trades, it replaces 0091 as the
live forward book (it's the owner's actual intended strategy). If it's clearly worse, 0091 stays and we've
learned the loose net was carrying hidden winners. No retuning; the 3% / 3% / 6% thresholds are frozen.

## Skeptical prior (honest)
Tightening entries has hurt twice in this arc (0086 RS gate, 0088 weekly-breakout) — fewer trades removed
edge, not just noise. But those were *different-axis* gates; this is the *core setup* made stricter to
match a coherent, well-understood pattern (pullback-to-rising-MA), which is more principled than a bolt-on
veto. Plausible outcomes: (a) similar Sharpe at ~1/3 the trades and lower 2023-dependence → a cleaner,
more robust book worth promoting; (b) lower return because the loose net caught early-trend entries the
tight band misses. Expect fewer trades → wider CI → likely UNDERPOWERED on the absolute gate regardless;
the head-to-head vs 0091 is the decisive read.
