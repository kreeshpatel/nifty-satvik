# Pre-registration 0108 — Fundamental profit+sales growth universe filter on the swing book

**Status:** PRE-REGISTERED (before running; single arm, fixed). **Date:** 2026-07-26. **n_trials:** +1 → 134→135.

## Overlay
A PIT universe FILTER (owner idea, quality-momentum): a signal may activate ONLY if the name has POSITIVE
annual net-profit growth AND POSITIVE annual sales growth as-known-then. Applied at the entry-activation gate
(run_bhanushali_weekly_rank line 686) by intersecting `ticker_in_index_on` with fundamental eligibility. No
engine edit — the gate is a test-time wrapper; frozen 0094 unchanged when the wrapper is off.

## Data & authenticity (the owner's PIT concern)
`data/fundamentals_pit_depth.pkl` (653 names, Screener-sourced annual P&L, ~2018-2026). PIT-clean:
availability = period_end + 90d lag; eligibility at date t uses the most-recent report with avail STRICTLY
< t (searchsorted strict-before) — never current/restated data leaking backward. Caveat: Screener shows
current-restated annual figures, but for a SIGN filter (growth +/−) restatements ~never flip the sign.

## Params — FIXED
- Eligible iff `np_yoy > 0 AND rev_yoy > 0` (both annual, PIT). Names with NO fundamental data → EXCLUDED
  (conservative: can't confirm growth → don't trade). Refresh is automatic (annual reports flow in PIT).

## Hypothesis
Trading only fundamentally-improving companies avoids momentum-on-deteriorating-names blowups (Yes Bank /
DHFL had collapsing profits before the price break) — cutting the single-name-catastrophe tail and the
chop-year losses (2024/2025), at neutral-to-positive risk-adjusted return.

## Failure modes (≥2)
1. **Cash-redeploy inversion** (0095/0104): the filter shrinks the universe → freed cash pours into the
   next-best names → dilution, IF the excluded names were net-positive.
2. **Weak signal** (finding 0019: rev_yoy IC −0.036 weak, np_yoy ~0): the filter may barely bite or add noise.
3. **Coverage shrink:** ~135/788 names lack depth data → excluded outright, over-shrinking the universe.

## Pre-committed bar (universe-filter class; judged PER-YEAR per the 2026-07-26 methodology)
- **SHADOW → forward wall** iff continuous-slice: ΔSharpe ≥ 0 AND ΔMaxDD ≥ +2.0pp AND ΔCAGR ≥ −2.0pp AND
  the weak years (2024/2025) not worse. **PROMOTE:** forward-wall only. **KILL/UNDERPOWERED** otherwise.

## Method
Frozen 0094 base vs the fundamental-gated variant; report Sharpe/CAGR/MaxDD + FULL per-year table + trade
count + universe-shrinkage. Reproducible from the committed depth store + the test script.
