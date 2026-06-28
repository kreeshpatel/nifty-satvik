# Pre-registration 0059 — Deployment-family re-readout on PORTFOLIO metrics (0046b + 0047b)

**Date:** 2026-06-20
**Track:** B (model-internal) — CPCV; RE-MEASUREMENT of already-counted arms (NOT new trials)
**Status:** PRE-REGISTERED (frozen below); awaiting owner merge + cloud dispatch
**Holdout:** paired CPCV on the locked honest base (de-leaked 744), REPRODUCIBLE_MODE=1
**n_trials:** NOT bumped — this re-scores arms already counted at 0046 (LTR) + 0047 (exits) on a DIFFERENT
metric. DSR uses the current cumulative count (55, which already includes these arms) — the conservative
choice (re-testing a prior arm is multiple-testing, so we do NOT under-deflate).

## Why
The 2026-06-20 meta-audit found 0046 (LTR ranker) and 0047 (trailing-off exit) were judged on PER-TRADE
IR — a metric that structurally penalises trade-ADDING / longer-hold levers — and their runners discarded
`res.equity_curve`. On a chronically ~27%-deployed book (0028/0048), such a lever can LIFT portfolio
Sharpe/CAGR via deployment + diversification even as per-trade IR falls (exactly what 0058 showed for
gate-loosening). This re-reads the SAME arms on the metric that matters.

## Design (FROZEN — `run_cpcv_deployment_readout.py`, backtest-validator-cleared)
One base 14d model trained ONCE per split (shared by all arms); 4 arms scored on PORTFOLIO Sharpe + CAGR
+ DEPLOYMENT (mean open positions, mean invested/equity), paired CPCV (9 LdP paths):
- **base** — live cfg (0.92/8.0, 6/3 trailing) = yardstick
- **trailing_off** (`trailing_activate=999`) — 0047b candidate
- **trailing_8_4** (`8/4`) — 0047b plateau arm
- **ranker** — top-20/day V1RankerStrategy grade_fn, min_conf/min_ret = 0 (rank IS the gate) — 0046b candidate

## Primary metric + frozen rule (per candidate, vs base)
A lever **BEATS base on portfolio metrics iff ALL:** paired **dSharpe CI-low > 0 AND point > 0.3** floor
AND **DSR(empirical skew/kurt) > 0.95** at n_trials 55 AND no per-group blowup.

- **0046 ranker:** if it BEATS → the per-trade-IR KILL was the wrong metric; resurrect for a full
  pre-registered portfolio trial. Else → the KILL stands on portfolio metrics too (genuinely worse, not
  just mis-measured).
- **0047 trailing_off:** if it BEATS → revisit the "KEEP live trailing"; else KEEP stands.

**Interpretation guard (pre-stated, against over-rotation):** a candidate that is **Sharpe-flat but
CAGR-up purely via higher deployment** is reported as a *deployment* lever, NOT auto-promoted — higher
CAGR from more capital deployed is only real risk-adjusted improvement if Sharpe also clears. The
deployment columns (mean_open, deploy_frac) make this explicit. Promote NOTHING here — a "BEATS" verdict
only earns a fresh, fully-guarded pre-registered trial (drop-2021, bad-year decomposition, cost-sanity
at the higher turnover, per-trade EV CI).

## Kill/relevance risks (pre-stated)
- Both could be Sharpe-flat (the per-trade-IR view was right after all) → confirms the kills, useful either way.
- The ranker doubles+ the trade count → portfolio Sharpe up while deployment up is the classic
  "deployment ≠ alpha" trap; the deploy_frac column is the check.
- Bull-year (2021) concentration not yet decomposed here (that's the follow-on trial's job).

## What ships (pre-run)
`run_cpcv_deployment_readout.py` (validator-cleared) + `.github/workflows/cpcv-deployment-readout.yml`.
No n_trials bump. No engine/live change; golden-master untouched.
