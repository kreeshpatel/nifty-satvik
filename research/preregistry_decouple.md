# PRE-REGISTRATION — `decouple_touch_green`: the owner's TOUCH-then-GREEN sequence

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 118 -> 120.*

## The rule (owner, chart review r3 clarification)

> *"i am saying to buy after the red candle, a green candle forms and we buy at the next open. I am also
> telling to buy at the pullback… if the setup week opens below the prior weeks open then that should be
> considered the setup week until its near the 44SMA or touching it actively"*

The taught rule is a **SEQUENCE across two candles**, not one candle:
1. price pulls back and **touches** the 44w SMA (that week may be **red** and may **close below** the line),
2. **then** a green week forms and closes back above,
3. buy at the next week's open.

The live engine requires **touch AND green on the SAME bar**, which pushes the fire onto the explosive
reclaim week — the extended one.

**Status check: `decouple_touch_green` exists in the engine and has NEVER been tested** (no record in
`research/`, `diagnostics/research/`, `models/`). Not a relitigation — a first run.

## Why this is NOT the killed `open_progress`

`open_progress` (KILLED, `FINDING_open_progress.md`) applied "open > prior open" to the **green** week,
which filtered out the pullback itself and removed 82% of the book's R. This lever does the **opposite**:
it *accepts* the red/low-opening pullback week as the arming event and moves the *fire* to the following
green week. **Additive/timing, not subtractive.** The owner's clarification is an explicit correction of
my misreading.

## The frozen spec

| param | value |
|---|---|
| `decouple_touch_green` | **True** |
| `green_wait` | **3** — the engine's pre-existing default, NOT chosen by inspecting results (anti-cherry-pick) |

Arm semantics (as implemented): arm when `wlow <= SMA*1.07 AND slope >= 0.03` (no green, no close>SMA
required); fire on the first week within `green_wait` that is `qgreen AND close>SMA AND slope>=0.03 AND
RS>SMA40(RS) [AND base_ok]`; the arm is consumed on fire.

## Arms (K=2)

1. **BASE + decouple** — isolates the timing change on the live book.
2. **SPEC + decouple** — with the owner's discipline caps (`ext_cap=0.20, max_risk_pct=0.10,
   max_notional_pct=0.20`). **THE candidate** (owner's standing rule: test it combined).

## Pre-declared measurements

Sharpe · CAGR · MaxDD · **2022-26 continuous slice** · trades · win% · meanR · median R% ·
**mean/median entry extension vs the signal-week SMA** (the mechanism check — this lever should fire
NEARER the line) · `meanR x R%` · skipped_cash · exit mix.

## Pre-declared expectation

**Mechanism:** entry extension should FALL (firing on the first green after the touch, not the reclaim
blow-off). Whether that helps is the open question — `EXT_IS_THE_ENGINE` found extension is where 69% of
the book's R sits, and `POOL_vs_SELECTION` found the near-SMA pool is unreachable *by selection*. This
lever reaches it by **timing** instead, which no prior test has done.

**Skeptical prior:** entry-side changes are 0-for-10. But every one of those was *subtractive*; this is
the first timing change. Genuinely uncertain. **KILL / UNDERPOWERED is a first-class outcome.**

## Gate

2022-26 continuous slice (R3) vs BASE **1.29** / SPEC **1.21** / random null **0.74** (sd 0.24).
DSR bar acknowledged at trial 120. **Nothing ships in-sample (R11).**
