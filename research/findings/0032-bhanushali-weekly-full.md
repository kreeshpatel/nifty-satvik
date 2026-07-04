# 0032 — Fully-weekly six-step (in-range entry + weekly exits): family-best Sharpe +0.63 / CAGR +11.8%, but −54% drawdown — UNDERPOWERED

- **Status:** TRIAL (pre-reg [0089](../../diagnostics/research/preregistry/0089-bhanushali-weekly-full.md),
  n_trials 106→107, params frozen before the run). **Verdict: UNDERPOWERED** (highest family Sharpe, but
  CI straddles 0, DSR 0.09; and the drawdown blew out).
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_full.py`; ledger
  `research/exports/bhanushali_weekly_full_0089_trades.csv` (280 trades). Same cell as 0084/0085.

## What was tested (owner-designed, corrects 0088)
Fully weekly. Weekly 44-EMA trend + a green weekly bounce off it (low within 7%) = signal week. Entry: the
next week, buy at the first day whose OPEN prints **inside** the signal week's [low, high] range (a cheaper
in-range fill — fixing 0088's expensive breakout). Stop = signal-week low. 0085 exit levels (half@+2R,
20-EMA −4% trail, 13-week cap) but every exit **decided at the weekly close, executed Monday open**.

## Result (corrected universe, real tiered costs)

| | trades | win | expR | CAGR | Sharpe | MaxDD | Calmar | mult |
|---|---|---|---|---|---|---|---|---|
| **0089 fully-weekly** | 280 (30/yr) | **45.0%** | +0.25 | **+11.8%** | **+0.626** | **−54.3%** | **0.22** | 2.88× |
| 0085 (best so far) | 432 | 39.6% | +0.23 | +11.5% | +0.587 | −37.5% | 0.31 | 2.80× |
| 0088 weekly-breakout | 440 | 38.0% | +0.11 | +2.3% | +0.215 | −41.3% | — | 1.24× |

Slices +0.05 / +1.29 / +0.34 (all positive). CI [−0.212, +1.368]; DSR@107 = 0.091. ΔSharpe vs 0085
**+0.039**, ΔCAGR **+0.3pp**. Exit mix: time 149, stop 102, trail 23.

## Root-cause readout (REQUIRED)
1. **The entry idea worked — win-rate jumped 40%→45%, expR held, and it's the first non-losing variant of
   the arc.** Buying in-range at the open (vs 0088's breakout-above-the-high) is genuinely a better fill,
   and the weekly confirmation raised trade quality. Credit where due: this is a real, correctly-reasoned
   improvement on 0088, and it nudged past 0085 on Sharpe and CAGR.
2. **But the drawdown blew out to −54% (from 0085's −37%) — Calmar is WORSE (0.22 vs 0.31).** The weekly-
   close exits act a full week late: on a fast reversal you give back the entire week's move before Monday's
   fill. The damage is concentrated — **2024 −₹12.0L, 2018 −₹6.3L** — years with sharp mid-trend reversals
   the weekly stop caught a week too slow, filled on a Monday gap. Time-cap dominates exits (149 of 280),
   so most positions ride to the 13-week cap and dump regardless.
3. **The Sharpe edge is partly a smoothing artifact.** 280 weekly-held trades → fewer daily transitions →
   a smoother daily return series → mechanically higher Sharpe, while the true tail risk (−54% DD) got
   worse. Sharpe up + Calmar down is the tell: this didn't reduce risk, it hid it in the daily series and
   concentrated it in the drawdown.
4. **The cheaper-entry-→-tighter-stop thesis only half-worked:** entry-to-stop width is still **13.1%**
   (stop at the weekly low is far), so positions are small and the CAGR barely moved despite the better
   win-rate. The wide weekly stop is the ceiling on this design.

## Verdict & next setup
**UNDERPOWERED — the best point-estimate of the family, but not a deployable improvement over 0085.** The
+0.04 Sharpe is inside the noise (CI [−0.21, +1.37], DSR 0.09), and the −54% drawdown is a worse real-world
risk than 0085's −37% — a −54% peak-to-trough is portfolio-ending for most. On a risk-adjusted (Calmar)
basis it is *behind* 0085. Honest read: the owner's in-range weekly entry is a genuinely good idea that
raises win-rate and matches return, but the weekly-cadence late exits trade that back as tail risk. **0085
remains the family's best on drawdown-adjusted terms; 0089 is the best on raw Sharpe.** Both go to the
2026-10-01 review as the two live candidates. The remaining lever is unchanged: the −54% (and 0085's −37%)
is a *portfolio-sizing* problem — vol-target the sleeve's deployed equity (O-009) to cap the drawdown, then
this higher-win-rate weekly book could become the better sleeve. That is the next test worth running, and
it is portfolio-level, not another trade-rule tweak.
