# PRE-REGISTRATION — lock-in ratchet on the LIVE discipline book (the HEG giveback fix)

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 123 -> 124.*

## Motivation (owner, HEG chart)

HEG entry 2025-12-29 @ 562.40 (1R=34.05) spiked to 672 (+3.22R / +19.5%) in week 1, then round-tripped
to a −1.24R stop. Nothing fired because the 2R half books on the weekly CLOSE (619.7 = +1.68R < 2R) and
the blow-off exit needs a lower-third close on a NEW high (week 1 closed upper-half; week 2 closed
lower-third but not a new high). The owner asks for a rule that protects a large intraweek gain.

The literal ask — sell at the intraweek high / a fixed % — is `tp_on_high`, **KILLED** (0.709 Sharpe /
−49.7% DD; it truncates the fat tail). The lock-in ratchet achieves the owner's GOAL (don't give a big
gain back to a loss) **without** capping the winner: it RAISES THE STOP once MFE is large and lets the
position keep running.

## The rule (frozen)

`lockin_mfe=2.5, lockin_at=1.5` — once a trade's intraweek MFE reaches **2.5R**, raise the stop to
**entry + 1.5R** (never lowered). These are the values from the prior per-trade exit forensic (+0.500
meanR on the base book), **not** chosen by inspecting this run's results (anti-cherry-pick).

## Not a relitigation

The ratchet was explored per-trade on the base/all-grades book (small positive, below the +0.10 bar).
It has **never** been run on the current LIVE book (A-only + `LIVE_DISCIPLINE` + P2 exit). New book =
new formulation. This is a genuine exit-lever question, distinct from the KILLED `tp_on_high` (fixed
target) and the KILLED fixed-R targets (0079/6040/small-candle).

## Arms (K=1)

**LIVE + lockin(2.5, 1.5)** vs the LIVE book (A-only + discipline + P2 exit, Rs10L, 2% risk).

## Pre-declared measurements

Sharpe · CAGR · MaxDD · **2022-26 slice** · trades · win% · meanR · mean/median MFE-captured ratio
(winners: kept R ÷ reached R) · exit mix. **HEG 2025-12-29 specifically:** does it now exit near +1.5R
instead of −1.24R?

## Skeptical prior

Every exit-truncation lever has lost. The ratchet is the ONE that helped per-trade before, because it
raises the stop rather than capping the target — but it was **small (+0.04 Sharpe)** and below the
promotion bar. On the discipline book (R already capped at 10%, so 2.5R is a ~25% move — rarer) it may
arm on fewer trades and do even less. **Most likely UNDERPOWERED. KILL/UNDERPOWERED is first-class.**
The one thing it must NOT do is help HEG while hurting the book — if the fat-tail runners give back
Sharpe, that is the truncation signature and it dies.

## Gate

2022-26 continuous slice (R3) vs the LIVE book **1.04** (A-only + discipline); random null **0.74**
(sd 0.24). Promotion needs ΔSharpe ≥ +0.10 AND DD not worse; anything less is a forward-wall candidate at
best. DSR bar acknowledged at trial 124. **Nothing ships in-sample (R11).**
