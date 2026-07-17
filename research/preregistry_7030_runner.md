# PRE-REGISTRATION — 70% @ 2R + 30% runner to the 44w SMA (owner's tail-preserving hybrid)

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 126 -> 127.*

## The rule (owner)

> *"keep 2R and 70 percent but keep 30 percent as runners till its above the 44 weekly SMA"*

Book **70% at 2R** (intraweek resting limit), keep **30% running** until a weekly close below the **44w
SMA**. `scaled_exit(tp1_r=2.0, tp1_frac=0.70, tp2_frac=0.0)` — the 30% is `frac_left`, exits on the
scaled runner's `wsma_at` (verified = the 44w SMA, engine line 312) or the stop. On the LIVE book
(A-only + LIVE_DISCIPLINE).

## Why this is a genuinely NEW formulation

Directly answers the objection to arm B (`FINDING_intraweek_rotate`): B (60%@2R/40%@3R) capped EVERY
winner at 2.4R and passed no fat-tail — the reason it did not ship. This keeps a **30% runner with NO
upper target**, so the fat tail is PARTIALLY preserved (a 16R move still pays 0.70*2R + 0.30*16R = 6.2R
instead of B's 2.4R). Distinct from:
- B (60/40, no runner) — tail fully capped.
- LIVE P2 (50% half + 20wk/blowoff trend trail) — different runner rule and fraction.
- FINDING_owner_6040_poscap 60/40 (KILLED, confounded by R-cap-5%).

## The explicit question

Does a 30% runner restore enough fat tail to lift the 2022-26 slice (where B was FLAT, 1.03), while
keeping B's consistency/rotation benefit? The mechanism check: **max R must rise well above B's 2.4R**;
if it does not, the runner is not preserving the tail.

## Arms (K=1)

**LIVE + scaled(70%@2R, 30% runner-to-44wSMA)** vs LIVE (P2) and B (60/40) as reference points.

## Pre-declared measurements

Sharpe · CAGR · MaxDD · **2022-26 slice (the gate)** · trades · win% · **max R & count R>=3 (tail check)**
· mean hold · exit mix.

## Skeptical prior

The runner helps ONLY if the 30% catches enough tail to matter; but 30% of a 16R move is 4.8R, while
the 70% booked at 2R is the bulk. The book may end up between LIVE and B: some tail back, some
consistency lost. And it still books 70% at a fixed target — a partial version of the truncation killed
4x. Most likely: 2022-26 slice between 1.03 (B) and 1.04 (LIVE), i.e. still ~flat, no promote.
**KILL/UNDERPOWERED first-class. Nothing ships in-sample (R11).**

## Gate

2022-26 slice (R3) vs LIVE **1.04**; null **0.74** (sd 0.24); promote bar dSharpe>=+0.10 & DD not worse.
DSR bar acknowledged at trial 127.
