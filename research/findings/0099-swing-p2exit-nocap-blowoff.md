# Finding 0099 — Phase-2 EXIT change on the weekly-swing-0094 book (no-cap + blow-off-bar exit)

**Date:** 2026-07-15. **Pre-reg:** 0099. **n_trials:** 114→115 (incremented before adoption).
**Status:** ADOPTED to LIVE by owner-override (NOT forward-wall-certified). **Verdict class:** defensive/selection
variant — FAILS the standard ΔSharpe≥+0.10 gate (−0.10); adopted for drawdown + per-trade capture + fewer trades.

## What was tested
A three-phase trade-by-trade research program (entry → exit → sizing; AI text + vision agents over 255 trades +
an unbiased random 60-trade exit map) concluded ENTRY and SIZING are robustly optimal (no change) and the only
supported change is the EXIT. New exit: **replace the 13-week time cap + 20-day-SMA trail with a TREND-FOLLOWING
no-cap hold (52-week backstop) + a BLOW-OFF-bar exit @2.5R MFE** (a week that makes a new high but CLOSES in the
lower third of its weekly range = momentum exhaustion) **+ a 20-week-close −4% backstop**. Half@2R, signal-week-low
stop, and 2% risk unchanged. Cfg-gated: `no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5`.

## Result (in-sample, corrected universe 2017–2026, ₹10L capped)
| | 0094 (reference) | P2 exit (live) |
|---|--:|--:|
| Portfolio Sharpe | 1.132 | 1.034 |
| CAGR | 24.7% | 21.2% |
| MaxDD | −42.4% | **−34.8%** |
| Calmar | 0.58 | **0.61** |
| per-trade meanR | +0.481 | **+0.616 (+28%)** |
| trades | 255 | 168 |
| win rate | 59% | 54% |
Per-year scorecard: `research/losers_analysis/FORENSIC_FINDINGS.md`.

## Root-cause readout (why it behaves this way)
- **Root cause of the leak it fixes:** the AI exit forensic (5 text agents on hold-paths + 2 vision agents on
  marked charts + a random 60-trade map) found the 13-week cap severed still-trending winners (the #1 capture
  loss — 45% of winners on the random map exited mid-trend, several ran 4–27R AFTER exit), and the giveback
  cohort topped on a blow-off bar (new high, close in the lower third). Removing the cap lets trends run; the
  blow-off-bar exit banks the giveback near the peak.
- **Why Sharpe DROPS despite +28% per-trade R:** the no-cap hold occupies a capital slot ~2× longer, so the book
  completes 168 vs 255 trades — a capital-efficiency cost. Portfolio Sharpe/CAGR fall while per-trade capture and
  drawdown improve. This is a defensive/selection trade, not a return upgrade.
- **Two corrections to earlier notes:** (1) the config KEEPS the existing 20-DAY-SMA trail (`ema20`, the
  `elif half_done` branch); the 20-week trail is only a rarely-firing backstop — the drivers are no-cap + blow-off,
  NOT a "20-week replaces 20-day" swap. (2) There is NO golden test guarding the swing book; the frozen 0094 is
  protected only by the default-OFF-levers convention (verified: `backtest(prep_weekly_rank(ohlcv))` = 1.132/255).
- **Discipline note:** the 0098 exit arc (~20 configs) was a pre-committed KILL ("0094 is best"). This is
  registerable as a NEW formulation (the blow-off-bar / visual-forensic exit, finding 0038's still-open
  13-week-cap lever) but as a defensive variant, not a gate-clearing promotion. Adopted LIVE by owner-override
  (sole capital-at-risk), recorded in config_CHANGELOG + ADR; the base-swing 0094 remains the WATCHED reference.

## Next setup
Forward-monitor the live A-only book (now P2 exit) vs the base-swing 0094 reference on the swing forward wall,
tracking **forward MaxDD/Calmar** (the metric this variant is adopted on), not Sharpe. Revisit at the quarterly
review. If forward DD does not hold up, revert (flip `P2_EXIT` off in `run_bhanushali_cron.py`).
