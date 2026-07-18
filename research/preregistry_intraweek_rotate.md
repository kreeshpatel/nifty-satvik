# PRE-REGISTRATION — intraweek 2R/3R booking for CAPITAL ROTATION (owner's rotation claim)

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 124 -> 126.*

## The owner's claim (distinct from the giveback question)

> *"if our 2R or 3R hits intraweek then why not sell. that how we can rotate the capital also get into
> new opportunities"*

The point is NOT profit protection — it is **capital velocity**. `FINDING_cash_starvation` measured
~19k abandoned fills (only ~2% of signals taken). If booking 2R/3R intraweek returns cash sooner, the
freed cash could take signals currently starved → more winners → offsetting the truncated runners.

## What is already known (registry-first)

- **`tp_on_high`** (book the 2R half at the intraweek HIGH via resting limit) — KILLED, 0.709 Sharpe /
  −49.7% DD, on the cash-constrained base book. **But the finding framed it as fat-tail truncation and
  did NOT report the rotation metric (skipped_cash, trade count).**
- **`scaled_exit` 60/40** (intraweek resting limits at 2R/3R) — KILLED at 0.64, but bundled with R-cap-5%
  + a 20% notional cap (`FINDING_owner_6040_poscap`), which confounded it.
- **Neither ran on the LIVE discipline book** (A-only + `LIVE_DISCIPLINE` + P2). New formulation.

## The explicit hypothesis this run tests

**If the rotation benefit is real, `skipped_cash` MUST fall AND trade count MUST rise, and that must be
enough to hold or lift Sharpe.** If skipped_cash barely moves, rotation is not the mechanism and the
kill is (again) fat-tail truncation. This is the mechanism check the prior kills omitted.

## Arms (K=2, frozen)

Both on the LIVE book (A-only + `LIVE_DISCIPLINE`, Rs10L, 2% risk):
1. **A: LIVE + tp_on_high** — book the 2R half at the intraweek high (resting limit) instead of the
   weekly close; the other half runs on the P2 exit. The minimal "book 2R intraweek" change.
2. **B: LIVE + scaled_exit(60%@2R, 40%@3R)** — full intraweek rotation: 60% off at 2R, 40% at 3R
   (resting limits), rest exits on the 44w-SMA weekly-close fallback. Replaces the P2 trend exit.

## Pre-declared measurements

Sharpe · CAGR · MaxDD · 2022-26 slice · trades · win% · meanR · **skipped_cash (THE rotation metric)** ·
mean hold · exit mix.

## Skeptical prior

Exit-truncation is 0-for-4. The rotation intuition is real but the cash-starvation finding already
showed the ~19k skipped fills are **the 98% of signals CRS is right to refuse** — so freed cash buys
*worse* signals (the `FINDING_more_slots` dilution result). Expect: skipped_cash falls, trades rise,
Sharpe FALLS anyway, because the rotated-into names are lower-CRS. **KILL/UNDERPOWERED first-class.**

## Gate

2022-26 slice (R3) vs LIVE **1.04**; null **0.74** (sd 0.24); promote bar ΔSharpe ≥ +0.10 & DD not
worse. DSR bar acknowledged at trial 126. **Nothing ships in-sample (R11).**
