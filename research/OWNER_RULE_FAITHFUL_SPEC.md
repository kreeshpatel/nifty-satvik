# Owner rule-faithful variant — FROZEN SPEC (built 2026-07-16, NOT yet tested)

*Status: **SPEC FROZEN — awaiting the owner's go to test.** Every lever is cfg-gated OFF; the live book and
all guards are byte-identical (verified: golden 1.1319/255 · live P2 1.0342/168/−34.8% · A-only 1.0038/171
· `tests/test_stage2_golden.py` 3 passed).*

## Why this exists

The owner reviewed the worst trades on TradingView against the **taught** rule and found the engine
deviates from it in five ways. **All five observations were factually correct** (verified against the data,
`research/substrate/OWNER_CHART_REVIEW.md`). This spec implements the rule-faithful strategy the owner
actually intends, as ONE coherent variant, to be tested ONCE at the end — not lever-by-lever.

**Why one test, not five:** testing each guard alone and killing it is precisely the cherry-picking trap.
Worse, we measured that this book is **chaotic under fill perturbation** — G1 alone scored 0.47, G2 alone
0.42, yet G1+G2 together 0.97. Individual verdicts on this book are close to noise. **A coherent spec,
tested once, is the only honest read.**

## Review round 2 (2026-07-16) — 4 more observations

| # | Observation | Verdict |
|---|---|---|
| 6 | **TARIL "entry was not fulfilled"** | **Correct per rule, not a bug.** Signal-wk high 486.85; Mon/Tue/Wed opened 497.79/514.59/516.79 (all ABOVE, so no in-range fill), Thu 3/27 opened 480.80 — inside (373.84, 486.85) → filled. Under the taught buy-stop you'd have entered Monday ~497.79. Same in-range-vs-buystop deviation (lever C3). |
| 7 | **KAYNES "exit should be at next week's open 5510, not 4409"** | **NOT a bug — our fill is exactly right.** 2025-12-08 (Monday) OPEN **= 4409.50**, precisely what we booked. 5510 was the open of **2025-12-01**, the *previous* Monday. Stop hit at Fri 12-05's close (4353.50 < stop 5405) → filled Mon 12-08 open. **BUT the underlying point is real** — see "the stop is not a stop" below. |
| 8 | **ZFCVINDIA "already below our SMA and one candle we bought it"** | **CORRECT — a genuine structural flaw.** → lever **C5**. |
| 9 | **RCF "price was below the SMA, how did the setup happen"** | **CORRECT — same flaw.** → lever **C5**. |

### C5 — the cleanest flaw found (verified)

The touch rule is `low <= SMA*1.07 AND close > SMA`. It **cannot distinguish**:
- a genuine **PULLBACK** — price *above* the SMA, dips to touch it, bounces ← the intent
- a **RECOVERY THROUGH** the SMA from below — price *under* the line for weeks, one big candle crosses up

Both satisfy it. And the 44w SMA **lags**, so `slope` still reads "rising" after weeks of price below it.

| case | prior 6 weeks (close vs SMA) | signal week |
|---|---|---|
| **ZFCVINDIA** 2024-05-31 | −7.0, −6.9, −9.1, −10.3, −9.1, **−9.8%** (6 straight BELOW) | ONE **+30%** candle (2231.9→2894.6) closes **+15.0%** above → fires, slope reads +6.2% |
| **RCF** 2024-11-29 | +1.6, −12.3, −4.3, −3.0, −8.0, **−9.3%** (5 of 6 BELOW) | ONE **+15%** candle (153.3→176.1) closes **+6.0%** above → fires, slope +4.4% |

**Lever `prior_above_n` / `prior_above_lookback`** — require ≥ n of the prior lookback weeks to have CLOSED
**ABOVE** the SMA (i.e. we were already in an uptrend above the line). Distinct from the existing
`base_min`, which requires closes NEAR/below the SMA within a band — the opposite concept. **Verified: at
`prior_above_n=2, lookback=4` it KILLS both the ZFCVINDIA and RCF signals**, and is inert at 0.

### "The stop is not a stop" — a real modelling property (no lever; recorded)

KAYNES exited at **−2.03R**, not −1R. Our stop is checked at the **weekly close** and filled at the
**Monday open**, so an intra-week collapse blows straight through it: a hard stop order at 5405 would have
filled ~5405 on **Dec 3** (that day's low was 5274). This is why the worst list is full of R worse than −1
(DHFL −4.49, MANPASAND −2.56). **The backtest therefore takes losses a real hard stop would not** — it is
pessimistic, not optimistic. Whether to model an intra-week hard stop is a separate question, and the
repo's own appendix warns the tight candle-low stop "exits on 2-3% noise" — the classic trade-off.

## The five observations → the levers

| # | Owner's observation (all verified TRUE) | Lever | Default |
|---|---|---|---|
| 1 | APOLLOHOSP — "enter only if the setup candle closes above the previous candle near the 44 SMA" | `require_progress` | False |
| 2 | RAINBOW — "never had a green candle that closed above the candle near the SMA" (signal closed 1444.8 vs prior 1454.3) | `require_progress` | False |
| 3 | SOBHA — "the next candle did not have a body; it should have been green as well as a body" | `entry_mode="buystop"` | `"in_range"` |
| 4 | RAIN — "was not even in a proper visible uptrend" | `slope_min` | None (=3%/13wk) |
| 5 | KENNAMET — "was already under the 44SMA" (fill −1.5%; NAVA −1.8%) | `ext_floor` | None |
| 8,9 | ZFCVINDIA / RCF — "already below our SMA and one candle we bought it" | `prior_above_n` / `prior_above_lookback` | 0 (off) |

## The levers as implemented (`scripts/run_bhanushali_weekly_rank.py`)

- **`require_progress`** (`prep_weekly_rank`) — adds `wclose[k] > wclose[k-1]` to the signal conjunction.
  `qgreen` only checks close>open, so today a green candle inside a *downswing* qualifies. PIT-safe
  (signal-week condition).
- **`slope_min`** (`prep_weekly_rank`) — overrides the `SLOPE_MIN = 0.03` floor (3% over 13 weeks — weak).
  A *visible* uptrend needs a higher bar. **Value not yet chosen — must be frozen before the run (R4).**
- **`ext_floor`** (`backtest`) — skips a fill whose price is not above `sma × (1+ext_floor)`. The signal
  requires close>SMA but the 0089 in-range fill can still land *below* the line. PIT-safe (the open is
  observed before we buy).
- **`entry_mode="buystop"`** (`backtest`) — the taught rule: fill only if the week trades **through the
  signal-week high**, at `max(open, trigger)`. Today's in-range fill enters on the next open regardless —
  which is why **every** reviewed trade filled below the signal high.

All default OFF ⇒ byte-identical. `ext_cap`/`ext_floor` are honoured inside the buystop branch too.

## Known costs — recorded up front, so no one is surprised

- **`entry_mode="buystop"` is pre-reg 0088's rule, and 0088 was KILLED**: Sharpe +0.215 (Δ −0.372), CAGR
  +2.3% (Δ −9.2pp). Cause: entry at the **high** with the stop at the **low** makes the whole candle the
  risk — **12.8% vs ~7%** — which halves position size and destroys the R-multiple. **0089 introduced the
  in-range fill precisely to fix this** and became family-best. If the buystop is in the final spec, expect
  this; a compensating stop rule (e.g. an ATR stop rather than the signal-week low) is the untested
  counter-move and would be a *new* formulation.
- **`slope_min` tightening ≈ pre-reg 0092** ("visibly-rising MA") which was KILLED.
- **`ext_floor` / `require_progress`** were measured alone (0.47 / 0.42 on the 22-26 slice) — but see the
  chaos caveat above; those numbers are near-noise and are NOT a verdict on the coherent spec.

## Open decisions before the run (must be frozen — R4, no sweeps)

1. **`slope_min` value.** 0.03 is the current weak floor. "Visible" needs a declared number.
1b. **`prior_above_n` / `prior_above_lookback`.** Verified that (2, 4) kills ZFCVINDIA + RCF. Freeze the pair before the run.
2. **Stop rule under buystop.** Keep the taught signal-week low (accepting ~12.8% risk width), or pair the
   buystop with a tighter/ATR stop (a new formulation that addresses 0088's actual failure cause)?
3. **Which levers are IN.** All four, or a subset?
4. **Grade filter.** A-only (live) or all-grades?

## Test protocol when the owner says go (ONE run, pre-registered)

- Freeze the params above **in writing first**; no retuning afterwards (R4/R11).
- Judge on the **2022-26 continuous slice** (R3). Baselines: all-grades **1.29** / A-only **1.17** /
  random-selection null **0.74**.
- Report the null percentile too — given the chaos finding, "beats the baseline" is weaker evidence than
  "beats the null distribution".
- UNDERPOWERED/KILL is a first-class outcome. Nothing ships in-sample (R11).
