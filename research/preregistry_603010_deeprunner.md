# PRE-REGISTRATION — 60%@2R / 30%@3R / 10% deep runner (6R or 15% below the 44w SMA)

*Status: PRE-REGISTERED, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 127 -> 128.*

## The rule (owner)

> *"keep 2R at 60 percent and 3R at 30 percent, if not 3r then sell at 2R and for the remaining 10
> percent runners till 6R or 15 percent below the 44SMA"*

Diagnosis behind it (owner, correct): the 70/30 runner failed because it sold AT the 44w SMA touch, and
the SMA is ~14% below entry, so the runner gave the tail back. Fix: keep only 10% as a runner, let it
ride THROUGH SMA touches (exit at 6R or 15% BELOW the SMA, not at it).

`scaled_exit(tp1_r=2.0, tp1_frac=0.60, tp2_r=3.0, tp2_frac=0.30, runner_cap_r=6.0,
runner_sma_buffer=0.15)`. New engine knobs (default-off, golden byte-identical verified 1.1319/255):
- `runner_cap_r=6` — book all remaining shares at 6R (resting limit).
- `runner_sma_buffer=0.15` — runner exits only on a weekly close below wsma*(0.85).

## Honest approximation (recorded up front)

"if not 3R then sell at 2R" is NOT literally implementable (cannot re-sell at 2R after the week passes).
In this run the 30% that misses 3R rides with the runner (6R / 15%-below-SMA), NOT a 2R re-sale. So the
book carries up to 40% on the deep runner when 3R is missed. If the result bleeds, THIS is why, and it is
disclosed before the run, not after.

## Why not a relitigation

New formulation: the deep-runner knobs (6R cap + 15%-below-SMA) did not exist until this commit. Distinct
from B (60/40, no runner, KILLED-on-gate), 70/30->at-SMA (KILLED, bled), and P2 (20wk trail + blowoff).

## Arm (K=1)

LIVE + scaled(60/30/10, runner_cap_r=6, runner_sma_buffer=0.15) vs LIVE (P2) and B as references.

## Measurements

Sharpe · CAGR · MaxDD · **2022-26 slice** · trades · win% · **max R & R>=3 (tail)** · mean hold · exit mix
· fraction of trades whose 30% missed 3R and rode the runner (the disclosed approximation's footprint).

## Skeptical prior

This is the 6th exit variant (trial 128); the multiple-testing bar is high and every prior target scheme
either capped the tail (B, gate-flat) or bled the runner (70/30). The 15%-below-SMA buffer is ~29% below
entry — very loose — so the up-to-40% runner-when-3R-missed may bleed like the 70/30 did, just less often.
Most likely lands between B (1.03) and the 70/30 (0.29) on the gate; **no promote expected. KILL/
UNDERPOWERED first-class. Nothing ships in-sample (R11).**

## Gate

2022-26 slice (R3) vs LIVE 1.04; null 0.74 (sd 0.24); promote dSharpe>=+0.10 & DD not worse. DSR bar
acknowledged at trial 128.
