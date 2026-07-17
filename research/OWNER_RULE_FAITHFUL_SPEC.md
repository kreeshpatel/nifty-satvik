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

## The five observations → the levers

| # | Owner's observation (all verified TRUE) | Lever | Default |
|---|---|---|---|
| 1 | APOLLOHOSP — "enter only if the setup candle closes above the previous candle near the 44 SMA" | `require_progress` | False |
| 2 | RAINBOW — "never had a green candle that closed above the candle near the SMA" (signal closed 1444.8 vs prior 1454.3) | `require_progress` | False |
| 3 | SOBHA — "the next candle did not have a body; it should have been green as well as a body" | `entry_mode="buystop"` | `"in_range"` |
| 4 | RAIN — "was not even in a proper visible uptrend" | `slope_min` | None (=3%/13wk) |
| 5 | KENNAMET — "was already under the 44SMA" (fill −1.5%; NAVA −1.8%) | `ext_floor` | None |

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
