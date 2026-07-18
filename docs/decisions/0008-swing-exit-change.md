# ADR-0008 — Weekly-swing (Bhanushali) EXIT change: no-cap + blow-off-bar exit (Phase-2, owner-override)

**Status:** Accepted (owner-override, sole capital-at-risk)
**Date:** 2026-07-15
**Author:** kreeshpatel
**Source files:** `scripts/run_bhanushali_cron.py` (`P2_EXIT`), `scripts/run_bhanushali_weekly_rank.py`
(cfg-gated exit levers), `models/bhanushali_weekly/config.json`, finding `research/findings/0099-*.md`,
`research/config_CHANGELOG.md`, `research/losers_analysis/LOCKED_STRATEGY.md`

---

## Context
A three-phase, trade-by-trade research program on the live weekly-swing book (0094) used AI text + vision agents
(5 exit-forensic agents over 255 hold-paths; 8 vision agents over marked charts incl. an **unbiased random
60-trade exit map**) plus dozens of cfg-gated measurements. It concluded:
- **Entry** and **sizing** are robustly optimal — no change (every attempt to beat them was a tradeoff or a
  knife-edge overfit the discipline caught, e.g. a maxpos-10 result that collapsed one position either side).
- The only supported change is the **EXIT**: the 13-week time cap severed still-trending winners (the #1 capture
  loss — 45% of winners on the random map exited mid-trend, several ran 4–27R after), and the giveback cohort
  topped on a **blow-off bar** (a new high closing in the lower third of its weekly range).

## Decision
Change the LIVE exit only. Replace the 13-week time cap + 20-day-SMA trail with:
1. **No time cap** — hold while trending (52-week safety backstop).
2. **Blow-off-bar exit after 2.5R** — exit on an exhaustion week (new high, close in the lower third of range).
3. **20-week-close −4% backstop** (the existing 20-day-SMA ratchet trail is retained as the primary trail).
Half@2R, signal-week-low stop, and 2% risk are unchanged. Implemented as
`P2_EXIT = dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)` on both `backtest()` calls in the cron;
`backtest()` defaults stay OFF so the frozen 0094 research run is byte-identical (1.132/255).

## Consequences (in-sample, corrected universe 2017–2026, ₹10L)
| | 0094 | P2 exit |
|---|--:|--:|
| Sharpe | 1.132 | 1.034 ↓ |
| CAGR | 24.7% | 21.2% ↓ |
| MaxDD | −42.4% | −34.8% ↑ |
| Calmar | 0.58 | 0.61 ↑ |
| per-trade meanR | +0.481 | +0.616 (+28%) ↑ |
| trades | 255 | 168 |
| win rate | 59% | 54% |

A **more defensive strategy**: −8pp drawdown, higher Calmar, +28% per-trade capture, fewer/longer-held trades
(which ease the capital-contention/selection bottleneck Phase-3 identified), in exchange for lower portfolio
Sharpe/CAGR. The Sharpe give is a capital-efficiency cost (longer holds ⇒ 168 vs 255 completed trades).

## Why this is an owner-override, recorded honestly
This change **fails the house promotion bar** (`docs/LIVE_OVERLAY_PROTOCOL.md` §4 requires ΔSharpe ≥ +0.10; this
is −0.10) and touches an exit area the registry closed as KILL (0098: "0094 is the best config"). The
disciplined route would be a forward-wall WATCHED variant decided on forward drawdown evidence at a quarterly
review. The owner (sole capital-at-risk) chose to adopt it LIVE now on the drawdown + per-trade + fewer-trades
basis. This ADR records that it bypasses forward-wall certification. The base-swing 0094 remains the WATCHED
forward reference; **reversal** = flip `P2_EXIT` OFF in `run_bhanushali_cron.py` → live reverts to frozen 0094.

## Corrections recorded (found during code-mapping)
- The adopted config **keeps** the existing 20-DAY-SMA (`ema20`) trail; the 20-week trail is only a backstop —
  the drivers are **no-cap + the blow-off exit**, not a "20-week replaces 20-day" swap.
- There is **no golden/determinism test** guarding the swing book (`tests/test_stage2_golden.py` pins the
  long-horizon engine); the frozen 0094 is protected only by the default-OFF-levers convention, so the
  pre-registration process — not a red test — is the load-bearing safeguard here.
