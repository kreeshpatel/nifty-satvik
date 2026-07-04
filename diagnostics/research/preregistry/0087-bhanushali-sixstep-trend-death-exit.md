# 0087 — Trend-death exit: sell any held name whose daily 44-EMA stalls 2 weeks OR price falls 6.5% below it

- **ID:** 0087. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 104 → 105.
- **Anchor / data:** identical cell to 0084/0085 (corrected universe, PIT membership, tiered costs,
  2017–2026, EQ0 ₹10L). Script `scripts/run_bhanushali_sixstep_stall.py`.

## Why this trial exists
The book is chronically fully invested — capital sits in stalled positions while fresh signals go untaken
(findings 0026/0029: ~79k cash-skipped fills). Owner hypothesis: cut a held name the moment its trend
*dies* — the daily 44-line goes flat, or price breaks well below it — freeing capital without waiting for
the candle-low stop. Exit-side change on the only side that has improved this funnel (0025/0084/0085).

**Distinct from the withdrawn recycle idea (not a relitigation).** The owner's original phrasing also
included "buy strictly at T+1", which is the exact lever a prior withdrawn test showed collapses the book
(the day-2/3 breakout-confirmed fills are the good entries; T+1-only leaves stop-fodder). **This trial does
NOT change the entry** — the 0084 T+1..T+3 window is kept byte-identical. The only change is the
trend-death exit, and it uses a *daily EMA44* detector, not the weekly-SMA stall that fired only 4× before.

## The FROZEN spec (deltas from 0084 only; everything else byte-identical to pre-reg 0084)

| Param | Frozen value |
|---|---|
| Entry / stop / targets | **exactly 0084** — T+1..T+3 buy-stop at candle high, candle-low stop ×0.999, half at +2R, rest at +3R, 2% risk, no rotation, no caps, tiered costs |
| Exit line | daily **EMA44** = `ewm(span=44, adjust=False)` on daily closes (owner spec; the entry funnel still uses SMA44 — the exit detector is a separate line) |
| **Trend-death exit — applies to ALL open positions** | on any session, if **stall** OR **deep** is true at the close → set pending exit → sell the ENTIRE remaining position at the NEXT session's open (reason `stall` / `deep`), PIT-safe (flag at close t, fill at open t+1) |
| stall | `EMA44_t / EMA44_{t-10} − 1 < 0.005` — the 44-EMA rose less than 0.5% over the trailing 10 sessions (≈2 weeks flat) |
| deep | `close_t < EMA44_t × (1 − 0.065)` — close more than 6.5% below the 44-EMA (midpoint of the owner's "6–7%") |
| REMOVED | 0084's 3-consecutive-close-below-**SMA44** `ma_breach` rule (replaced by stall+deep) |
| Precedence | pending trend-death exit at open → stop → tp2 half → tp3 rest (0084 order, ma_breach slot reused) |

Pre-declared sensitivity line (not an arm): erratum-dropped INDIAMART bars, report both.

## Primary metric + capital-efficiency diagnostics
**Corrected-universe NET Sharpe** (one number). References (not gates): 0084 +0.477, 0085 +0.587,
baseline_v1 0.667, TRI buy-hold CAGR +12.6%. Diagnostics vs 0084 same-cell: cash-skipped fills, average
deployed %, average open positions, hold distribution, exit-reason mix (how often stall vs deep fires),
per-year.

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@105 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
Informational: ΔSharpe vs 0084/0085. The 0029 fragility finding applies — a single-cell result is read
as directional, never deployable. No retuning; thresholds (0.5% / 6.5% / 10d) are frozen.

## Skeptical prior (honest)
Two ways this cuts. Good: a flat-MA or deep-break exit gets out of dying trends before the candle-low
stop bleeds, and frees capital for fresher signals — exactly the 0029 lock complaint. Bad: 0029 also
showed profit lives in ~10 held trades whose big runs include multi-week *consolidations* — a 2-week-flat
rule may sell the SWANENERGY/IRFC class of winner mid-pause (the same trap the withdrawn weekly-stall
idea risked, now on a faster daily clock, so it will fire far more often than 4×). The deep-6.5% rule is
close to a wider stop and should be benign-to-helpful; the stall rule is the risk. Expect: more exits,
faster cycling, ambiguous Δ — plausibly worse if it clips winners' pauses. UNDERPOWERED at best.
