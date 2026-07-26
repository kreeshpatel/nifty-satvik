# Pre-registration 0106 — Widen the stop a little on the weekly-swing book

**Status:** PRE-REGISTERED (written before the run; single arm, fixed, not retunable).
**Date:** 2026-07-26. Owner idea after the hard_stop KILL (0105): the close-only stop is protective because
it gives trades room to recover intra-week — so WIDEN the stop a little (more room, the *opposite* of
hard_stop). Prior support: 0025 (4×ATR geometry lifted the swing book +0.40 Sharpe / −12% DD). **n_trials:**
+1 → 133 → 134.

## Overlay
Push the stop `stop_widen_pct` further below entry: `stop = entry − (entry − low) × (1 + stop_widen_pct)`.
Position size stays risk-normalised (wider stop → smaller size → same rupee risk per trade). Single param
change vs frozen 0094; `stop_widen_pct=0.0` (default) reproduces 0094 byte-for-byte.

## Params — FIXED (single arm)
- `stop_widen_pct = 0.20` (the stop distance is 20% wider — e.g. a ~14% candle-low stop → ~17%). "A little"
  more room; a single pre-committed value, NOT a sweep.

## Hypothesis
More room lets more trades survive intra-week noise and ride to their exit (preserving the recoveries that
hard_stop destroyed), cutting the stop-out rate at roughly neutral rupee risk. Net: fewer/shallower losses.

## Predicted direction
- **stop-outs:** fewer. **ΔMaxDD:** better-to-neutral. **ΔSharpe:** ambiguous.
- **ΔCAGR:** ambiguous — fewer stops helps, but a wider stop pushes the +2R target further away (harder to
  fire) and smaller position sizes cap upside.

## Failure modes (≥2)
1. **2R target recedes.** A wider stop means +2R needs a bigger move; targets fire even less (0094 exit mix
   is already sma_break-heavy), so winners cap lower → CAGR give-up outweighs the fewer stops.
2. **Cash-redeploy neutrality / inversion.** Smaller per-name size frees cash the CRS loop redeploys into
   more marginal fills (the 0095/0104/0105 mechanism) — could dilute rather than help.
3. **Already-wide baseline.** The frozen 0094 stop is the candle low (~14% median), already wide; widening
   further may just add dead room with no recovery benefit.

## Pre-committed verdict bar (exit-improvement class — same as 0105)
- **SHADOW (forward wall)** iff continuous-slice: **ΔSharpe ≥ +0.05** AND **ΔMaxDD ≥ +2.0pp** AND
  **ΔCAGR ≥ −2.0pp** AND **2022-26 slice** not worse by >0.05.
- **PROMOTE:** forward-wall only. **KILL/UNDERPOWERED** otherwise. No retune of the 0.20 to rescue a miss.

## Method
Frozen 0094 (`run_bhanushali_weekly_rank`) corrected universe 2017-2026; baseline `stop_widen_pct=0.0`
(assert byte-identical 1.132/255) vs `stop_widen_pct=0.20`. Report Sharpe/CAGR/MaxDD/Calmar + `_slices` +
block-bootstrap ΔSharpe CI + DSR@134 + exit-reason mix + trade count. Reproducible.
