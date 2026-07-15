# Pre-registration 0099 — Phase-2 EXIT change on the weekly-swing-0094 book (no-cap + blow-off-bar)

**Status:** REGISTERED (documenting the 3-phase trade-forensic exit result; adopted LIVE by owner-override).
**Date:** 2026-07-15. **n_trials cost:** +1 (single config) → cumulative 114 → 115, incremented before adoption.

## Registry gate (done before writing this)
The 0098 exit arc (~20 configs) was closed as a **pre-committed KILL** ("frozen 0094 is best; do not relitigate")
— see `forward/prereg_swing.md` §7 and overlay_registry O-022. Finding 0038 explicitly lists **"the 13-week cap
(exit-side)"** as a still-open lever. The distinguisher required by the KILL ledger — one of {new data, new
feature, new sub-period, **new formulation**} — is the **new formulation**: a BLOW-OFF-bar exit (a week that makes
a new high but closes in the lower third of its weekly range = exhaustion) combined with a no-cap trend-following
hold, derived from a chart-based visual forensic (5 text + 8 vision AI agents; an unbiased **random 60-trade exit
map**) not present in the 0098 set (which tested trend-hold caps and exit ladders, not the blow-off-bar tell).

## The config (FIXED)
`no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5` on the live 0094 book; half@2R, signal-week-low stop,
2% risk, entry, and CRS-rank fill all unchanged. Cfg-gated in `run_bhanushali_weekly_rank.backtest()` (default OFF
⇒ frozen 0094 byte-identical, verified 1.132/255).

## Hypothesis + predicted direction
The 13-week cap severs still-trending winners and the giveback cohort tops on a blow-off bar → removing the cap
and adding the blow-off exit should **lower drawdown and raise per-trade capture**, at a **portfolio Sharpe/CAGR
cost** (longer holds tie up capital). Predicted: this is a **defensive/selection variant, not a return upgrade.**

## Primary metric + decision rule (fixed here)
Because it is a defensive variant, the primary certification metric is **forward MaxDD / Calmar**, NOT Sharpe.
Holdout = the **swing forward wall** (dev/in-sample slices are NOT a valid confirmation). In-sample it FAILS the
standard ΔSharpe ≥ +0.10 promote gate (it is −0.10) — so under the discipline it is NOT a gate-clearing promotion.

## Outcome (in-sample; adoption is an owner-override, not a certification)
Sharpe 1.132→1.034, CAGR 24.7→21.2%, MaxDD −42.4→−34.8%, Calmar 0.58→0.61, per-trade meanR +0.481→+0.616,
trades 255→168, win 59→54%. **Owner (sole capital-at-risk) adopted it LIVE** (`P2_EXIT` in
`scripts/run_bhanushali_cron.py`), bypassing the forward-wall route. base-swing 0094 remains the WATCHED forward
reference. Finding: `research/findings/0099-swing-p2exit-nocap-blowoff.md`. ADR: `docs/decisions/0008-swing-exit-change.md`.

## Result
Defensive variant adopted LIVE by owner-override. Reversal = flip `P2_EXIT` OFF → live reverts to frozen 0094.
