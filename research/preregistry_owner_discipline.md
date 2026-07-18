# PRE-REGISTRATION — the owner's discipline config (ext cap 20% + R cap 10% + position cap 20%)

*Status: **PRE-REGISTERED**. Frozen by the owner 2026-07-16 BEFORE the run. No retuning under any
outcome (R4/R11). Trial counter incremented 115 → 116 before running.*

## This is a RISK-APPETITE decision, not an edge hunt

The owner's instruction, verbatim:

> *"i dont care even if it gave good returns, then our book is badly traded. we have be according to
> rules or else we will suffer later max 20 percent is fine, if more than 10 percent then our R is
> distorted and that can create big positions and big profits as well as big losses and longer holding
> period"*

**The owner has pre-accepted a return cost.** So the gate is NOT "does it beat 1.29". The question is
*what does the discipline cost*, reported honestly, for the owner to accept or reject. A Sharpe below
baseline is an expected outcome here, not a KILL.

## The frozen spec (one conjunction)

| param | value | meaning |
|---|---|---|
| `ext_cap` | **0.20** | skip any fill priced more than 20% above the signal-week 44w SMA |
| `max_risk_pct` | **0.10** | stop = max(signal-week low, entry × 0.90) — R capped at 10% |
| `max_notional_pct` | **0.20** | no name may exceed 20% of sizing equity |
| exit | **live P2** | unchanged (`no_time_cap`, `wk20_trail_pct=0.04`, `blowoff_arm_r=2.5`) |
| grade | all-grades | as per the baseline of comparison |

Everything else is the live 0094 book (2% risk, Rs10L, in-range fill, CRS rank order).

## A correction the owner accepted, recorded for the record

The stated rationale — *"R … can create big positions"* — is **inverted**. Notional per name is
`risk% ÷ R%`, so a **wide** stop makes positions **small**:

| R% | notional per name |
|---|---|
| 14.2 (base today) | **14%** |
| 10.0 (this spec) | **20%** |
| 5.0 (killed arm) | **40%** |

Capping R makes the book **more** concentrated, which is why the 5% R cap drove MaxDD −34.8% → −54.5%
(`FINDING_owner_6040_poscap.md`). `max_notional_pct=0.20` is included specifically to contain this, and
it binds on any trade whose natural R is below 10%.

Second recorded caveat: `max_risk_pct` **breaks the rule it is meant to enforce**. The rule says the stop
is the signal-week low; the R cap lifts the stop off the candle to an arbitrary −10% line. `ext_cap` is
the rule-faithful half of this spec (a pure selection filter — the stop stays the candle low). The owner
chose both anyway, with the trade-off stated. That is a legitimate owner call.

## Pre-declared measurements (reported whatever the outcome)

Sharpe · CAGR · MaxDD · **2022-26 continuous slice** · trades · win% · meanR · median R% ·
**`meanR × R%` (the actual move captured)** · notional per name · **mean & median holding weeks**
(the owner named long holds as a defect) · exit mix · trades removed by `ext_cap`.

## Pre-declared expectation — written before the run

1. **Sharpe falls.** `ext_cap` removes the 15-25%/>25% extension buckets, which contribute **69% of the
   book's R** (`EXT_IS_THE_ENGINE.md`). Prior measurement of a defensive ext_cap ~20%: **−0.15 Sharpe,
   DD −42% → −32%**.
2. **Drawdown improves** — that is the point of the trade.
3. **The R cap pushes the other way on DD** (concentration). The net DD is genuinely uncertain: ext_cap
   helps, R cap hurts. This is the one thing the run actually tells us that arithmetic cannot.
4. **Holds shorten** — 2R at R=10% is a 20% move rather than 28%.

## Gates

Reported against baseline all-grades **1.29** and the random null **0.74** (sd 0.24) on the 2022-26
continuous slice (R3) — **as reference points, not pass/fail**. The decision is the owner's, on the
cost/benefit table.

**Nothing ships from this run automatically (R11).** The live config stays FROZEN until the owner reads
the cost and says otherwise.

## Guard

All three levers default `None` ⇒ byte-identical. Verified before the run: golden **1.1319/255** ·
live P2 **1.0342/168**.
