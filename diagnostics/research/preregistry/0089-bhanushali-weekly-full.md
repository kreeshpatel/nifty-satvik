# 0089 — Fully-weekly six-step: in-range open entry + weekly-close/Monday exits

- **ID:** 0089. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 106 → 107.
- **Anchor / data:** identical cell to 0084/0085 (corrected universe, PIT membership, tiered costs,
  2017–2026, EQ0 ₹10L). Script `scripts/run_bhanushali_weekly_full.py`.

## Why this trial exists
Owner-designed rework after the 0085 validation. It corrects the two things that sank the earlier weekly
attempt (0088): (a) 0088 entered on a buy-stop ABOVE the weekly high — the most expensive fill; this enters
INSIDE the prior week's range at the open — a genuinely cheaper fill (the real CAGR lever); (b) it makes
the whole system a true once-a-week routine — decide on Friday's weekly close, act Monday — matching how the
owner actually wants to trade it. Leak-free (the literal "forward look on buy prices" was refused as
lookahead; this uses only completed-week and same-day-open data).

## The FROZEN spec

| Param | Frozen value |
|---|---|
| Weekly bars | `resample` per ISO week from the daily series: wopen (first), whigh (max), wlow (min), wclose (last) |
| Weekly 44-EMA | `wclose.ewm(span=44, adjust=False)` — the owner's "44 EMA on weekly", used for trend + touch |
| Trend filter | `wclose > wema44` AND `wema44 > wema44.shift(4)` (uptrend, rising line) |
| Signal week | green (`wclose > wopen`) AND touch (`wlow ≤ wema44 × 1.07`, i.e. within **7%**) AND `wclose > wema44` AND trend filter — a green weekly bounce off the 44-EMA |
| **Entry** | the week AFTER the signal week: on each day, at the **open**, buy at the first day whose open is **> signal-week low AND < signal-week high** (inside last week's range). Fill = that open. If no day that week opens in range → cancel (one-week window). |
| Initial stop | signal-week **low** |
| Sizing | 2% equity risk, `qty = eq×0.02/(entry − stop)`, skip if cash short, no caps, no rotation |
| **Exit cadence** | evaluated only at each **weekly close** (the ticker's last trading day of the week); any triggered action **executes at the next session's open (Monday)**. Equity is still marked daily for family-comparable Sharpe. |
| Exit — sell half | if a weekly close ≥ `entry + 2R` (R = entry − stop) and not yet half-booked → sell 50% at Monday's open |
| Exit — runner trail | after the half-book, ratchet `trail = max(prev, EMA20_daily_at_Friday × 0.96)` each weekly close; if a weekly close < trail → sell the remainder Monday |
| Exit — stop | if a weekly close ≤ the initial stop → exit Monday |
| Exit — time cap | any position held ≥ **13 weeks (~3 months)** → exit Monday |
| Costs | brokerage + STT + ADV-tiered slippage, both legs (as 0084/0085) |

Frozen interpretations noted (owner enumerated "half@2R, 20-EMA trail, 3-month cap" as the 0085 exits):
the 20-EMA trail keeps 0085's **daily** 20-EMA level (sampled at Friday), ratcheted weekly; the 3-month
cap is applied to **all** positions (not runner-only), matching the owner's capital-lock concern; 0085's
daily-44SMA 3-close "ma_breach" is NOT carried (not in the owner's enumerated exit set). Pre-declared
sensitivity: erratum-dropped INDIAMART bars.

## Primary metric + diagnostics
**Corrected-universe NET Sharpe** (one number). References (not gates): 0085 +0.587 / CAGR +11.5%, 0088
+0.215 / +2.3% (the expensive-entry weekly), baseline_v1 0.667, TRI +12.6%. Diagnostics: median entry-to-
stop width (should be < 0088's 12.8% since we buy in-range), fill rate, trade count, exit mix, per-year.

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@107 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
Informational: ΔSharpe/ΔCAGR vs 0085 and vs 0088. No retuning; 7% band, Mon-fill, 13-week cap all frozen.

## Skeptical prior (honest)
For it: the in-range open entry is genuinely cheaper than 0088's breakout, and a tighter entry-to-stop
lifts R-per-trade and size — the one lever that could raise CAGR without lookahead. Weekly cadence also
cuts overtrading/whipsaw. Against it: weekly-close exits act a full week late — on fast reversals you give
back the entire week's move before Monday's fill (the 0029 tail lives in violent moves, both up and down);
the signal-week-low stop is still wide; and the whole entry-side arc (0086/0088 + the daily variants) says
this funnel resists entry re-engineering. Expect: cheaper fills and fewer trades, but the late weekly exits
likely eat the benefit → ambiguous Sharpe, UNDERPOWERED most likely; a genuine improvement over 0085 would
be a real (if uncertifiable) result worth the forward wall.
