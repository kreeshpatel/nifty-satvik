# 0088 — Weekly-confirmation entry on the 0085 book: green weekly rebound off the 44-EMA, buy Mon/Tue near the prior week's high

- **ID:** 0088. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 105 → 106.
- **Anchor / data:** identical cell to 0084/0085 (corrected universe, PIT membership, tiered costs,
  2017–2026, EQ0 ₹10L). Script `scripts/run_bhanushali_weekly_entry.py`.

## Why this trial exists
Owner CAGR-hunt on the 0085 book. The literal ask ("enable a forward look on buying prices") is lookahead
and was refused — any CAGR from peeking at post-signal prices is fabricated (skills/leakage-audit §1). The
reframed, leak-free question: is a **weekly-timeframe entry** — confirm on a green weekly candle rebounding
off the weekly 44-EMA, then buy early the next week near the prior week's high — a better entry than the
current daily pullback+breakout? Entry-side change; exits are the family's best (0085), left untouched.

**How this differs from the current engine.** 0084/0085 confirm on the DAILY chart (daily pullback to the
daily 44-SMA + a daily green candle), using the weekly only as a coarse bucket, and buy at the DAILY
signal-candle high over T+1..T+3. This trial moves confirmation AND the entry/stop levels to the WEEKLY
candle. Coarser, far fewer signals — a genuinely new formulation, not a fill-convention tweak.

## The FROZEN spec (entry delta only; 0085 exits/sizing/universe/costs byte-identical)

| Param | Frozen value |
|---|---|
| Exits / sizing / universe / costs | **exactly 0085** — half at +2R, remainder rides EMA20 −4% ratchet trail (63d cap from entry), non-runner candle-low stop + 3-close daily-44SMA breach, 2% risk, no rotation, no caps, tiered costs |
| Weekly bars | `resample("W-FRI")` → wopen (first), whigh (max), wlow (min), wclose (last) |
| Weekly 44-EMA | `wclose.ewm(span=44, adjust=False)` (owner's "44 EMA on weekly") |
| Weekly bucket | `wclose > SMA44(wclose)` AND `SMA44 > SMA44.shift(4)` (the existing step-1 bucket, kept) |
| Weekly signal (on a COMPLETED week) | green (`wclose > wopen`) AND rebound-touch (`wlow ≤ wema44 × 1.04` AND `wclose > wema44`) AND bucket, all true on the just-closed W-FRI bar; PIT member |
| Entry order | activates on the FIRST trading session after the signal Friday (Monday); buy-stop at the signal week's HIGH; order valid **2 sessions (Mon + Tue)** then cancelled; fill = `max(open, trig)` if `high ≥ trig` |
| Initial stop | signal week's LOW × 0.999 |
| No rotation | held names get no new orders (as 0085) |

Pre-declared sensitivity line (not an arm): erratum-dropped INDIAMART bars, report both.

## Primary metric + diagnostics
**Corrected-universe NET Sharpe** (one number). References (not gates): 0085 +0.587, 0084 +0.477,
baseline_v1 0.667, TRI buy-hold CAGR +12.6%. Diagnostics: trade count vs 0085 (expected far lower),
median entry-to-stop % (weekly ⇒ wide), realized position size, hold distribution, per-year CAGR, fill
rate (how often the prior-week high is taken out Mon/Tue).

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@106 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
Informational: ΔSharpe / ΔCAGR vs 0085. Trade count is expected to be low → CI wide → most-likely
UNDERPOWERED regardless of point estimate. No retuning; the 4% weekly touch band and Mon+Tue window are
frozen.

## Skeptical prior (honest)
Buying near the weekly high is not a cheaper fill (it's usually higher than the daily pullback candle's
high), so the CAGR case rests entirely on the weekly filter selecting better trades. Against it: the
weekly stop (prior-week low) is wide → small positions for 2% risk → per-trade rupee P&L shrinks even if R
improves; weekly signals are sparse (likely 100–200 trades over 9.5y) → wide CI, near-certain
UNDERPOWERED; and requiring the breakout to clear the weekly high in just Mon+Tue will drop many setups
unfilled. For it: weekly confirmation is a stronger trend filter (less daily noise), which could raise
win-rate and cut the CHOP bleed (finding 0029). Expect: far fewer trades, higher win-rate, ambiguous
Sharpe, lower-or-flat CAGR. Genuinely new, leak-free, worth one arm.
