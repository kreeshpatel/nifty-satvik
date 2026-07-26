# Pre-registration 0105 — Intraday hard stop on the weekly-swing book

**Status:** PRE-REGISTERED (written before the run; params fixed, not retunable).
**Date:** 2026-07-26. Motivated by the best-vs-worst discriminant: the stop touches **only losers (66/66
stop exits are losses, 0 winners)**, and 55/57 stop-outs are **intra-week grinds** (only 2 true gaps), so
~**19.8R (≈16% of book total R)** is bled to the close-only stop overshooting −1R — recoverable, by
construction, without touching a single winner. The one open question is the whipsaw cost, which only this
backtest nets. Entry-side levers are exhausted (body-frac null; ext_cap-tighten KILL, 0104) → the exit/stop
is the remaining asymmetric lever. **n_trials cost:** +1 → 132 → 133.

## Overlay
Turn ON the existing `hard_stop` lever: a REAL daily standing stop that exits AT the stop when a session
trades through it intraday, or at the OPEN on a gap-through — instead of the default close-only weekly stop
(decided Friday's close, filled next Monday's open, which routinely blows past −1R). Single param change vs
the frozen 0094; `hard_stop=False` (default) reproduces 0094 byte-for-byte.

## Params — FIXED
- `hard_stop = True`. Stop LEVEL unchanged (signal-week low); only the FILL timing changes. No other change.

## Hypothesis
Capping the 55 intra-week blow-throughs at ~−1R recovers ~19.8R of realized loss and shrinks the −42% DD,
because the deep losers (JSL −5.36R, AARTIIND, the COVID/Adani grinds) traded *down through* the stop
during the week — a daily stop catches them; the close-only stop waits and fills far lower.

## Predicted direction
- **ΔMaxDD:** better (losses capped near −1R).  **ΔSharpe:** ambiguous-to-positive (recovery vs whipsaw).
- **ΔCAGR:** ambiguous (recovery lifts; whipsaw + cash-redeploy drags).

## Failure modes (≥2) — the whipsaw is the whole question
1. **Whipsaw stop-outs.** A daily stop also exits trades that dip below the stop intraday but would have
   RECOVERED by Friday's close (survived under close-only) — turning would-be winners into −1R losers. If
   whipsaw loss > the +19.8R recovery, net worse. Invisible to the discriminant; this is what the run nets.
2. **Cash-redeploy inversion.** Earlier/more stops free cash the CRS-rank loop redeploys into weaker fills
   (the 0095/0104 mechanism) — could dilute the concentrated winners.
3. **Gaps still hurt** (2/57): a daily stop can't beat an overnight gap.

## Pre-committed verdict bar (exit-improvement class)
- **SHADOW (forward wall)** iff, continuous-slice on the corrected universe: **ΔSharpe ≥ +0.05** AND
  **ΔMaxDD ≥ +2.0pp** AND **ΔCAGR ≥ −2.0pp** AND **2022-26 slice** not worse by >0.05.
- **PROMOTE:** forward-wall only. **KILL/UNDERPOWERED** otherwise. No retune / partial-hard-stop rescue.

## Method
Frozen 0094 (`run_bhanushali_weekly_rank`) on the corrected universe 2017-2026; baseline `hard_stop=False`
(assert byte-identical 1.132/255) vs candidate `hard_stop=True`. Report Sharpe/CAGR/MaxDD/Calmar + `_slices`
+ block-bootstrap ΔSharpe CI + DSR@133 + exit-reason mix shift + trade count. Reproducible.
