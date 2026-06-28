# 0069 — Breadth / position-size confirmation of the 0068 mechanism

- **ID** — 0069
- **Registered** — 2026-06-26 (BEFORE the cloud run; question + arms + decision rule fixed first).
- **Parent** — 0068 (portfolio vol-targeting). 0068 PROMOTED on the SHAPE gates (DD −45.6 → −38.8,
  CAGR up) BUT the instrumentation showed the mechanism is NOT Barroso–Santa-Clara de-gross: across
  the run `deploy%` barely fell (95.4 → 94.0) and `avg_positions` ROSE (13.4 → 13.9). Only COVID-2020
  showed a real ~5pp de-gross. So outside the sharpest crash the overlay REDISTRIBUTED capital into
  more names rather than holding cash — i.e. the DD benefit looked like **diversification of an
  under-diversified, concentrated book** (~13.4/15 names at ~7% each), not vol-timing.
- **Hypothesis** — If the 0068 benefit is really diversification, then DIRECTLY increasing breadth
  (more, smaller positions) reproduces the DD reduction WITHOUT any vol machinery, and DD is
  **monotonic in breadth**: a more-concentrated book draws DOWN deeper, a broader book shallower.
  Predicted: the best breadth arm clears the same SHAPE gates as 0068's best vol arm; CONCENTRATE_8
  deepens DD vs OFF; the two independent breadth levers (risk-path, cap-path) agree.
- **Why this is a clean test, and the parity fix it required** — `portfolio.simulate` already reads
  `max_positions` and `risk_per_trade_pct`, but it was IGNORING the cfg `max_position_pct` (it
  hardcoded the `base_risk_qty` default 15.0) while the LIVE scanner
  (`long_horizon_cron._size_position`) DOES pass `cfg["max_position_pct"]`. That is a latent
  **live/backtest sizing divergence** (masked only because the frozen cfg is 15.0). This change wires
  `simulate` to honor the cfg value (default 15.0 → golden master byte-identical, verified), which
  both closes the parity gap AND enables the cap-path breadth arms.
- **Grid (5 NEW arms + OFF base + the 0068 vol-winner as an in-run reference)** — frozen cfg, the
  only differences are the listed knobs:
  | arm | max_positions | risk/trade | cap | role |
  |-----|---------------|------------|-----|------|
  | OFF | 15 | 3.00% | 15% | baseline (~13.4 names) — NOT a trial |
  | V2_vol_ref | 15 | 3.00% +tv0.15 | 15% | 0068 winner re-run, SAME data — already counted under 0068 |
  | CONCENTRATE_8 | 8 | 3.00% | 15% | opposite-direction control: fewer names should DEEPEN DD |
  | BREADTH_RISK_25 | 25 | 1.80% | 15% | RISK path — more names at ~constant aggregate stop-risk (~45) |
  | BREADTH_CAP_25 | 25 | 3.00% | 4.5% | CAP path — smaller cap forces more, smaller names |
  | BREADTH_CAP_30 | 30 | 3.00% | 3.5% | push breadth furthest → reach −30%? |
  | COMBO_25_vol | 25 | 3.00% +tv0.15 | 4.5% | breadth + vol stacked (best-achievable probe, NOT clean attribution) |
- **Evaluation surface** — same as 0068: a single CONTINUOUS multi-year run per arm (frozen cfg,
  2017+, 2019+ reported separately), MaxDD/Calmar/Sharpe off the continuous curve, ≥2-crash-fold
  robustness on the same curve sliced by year. NOT a per-year-reset (which would mis-measure the
  multi-year MaxDD). Shared, audited implementation in `diagnostics/_lh_overlay_core.py`.
- **Decision rule** — the SHAPE gates are applied to the best BREADTH arm (best positive-CAGR Calmar
  among `{BREADTH_RISK_25, BREADTH_CAP_25, BREADTH_CAP_30}` — NOT the vol-ref / concentration control
  / combo): (a) Calmar > OFF; (b) paired block-bootstrap dSharpe CI-low > −0.10; (c) MaxDD ≤ 0.90×
  OFF MaxDD; (e) MaxDD improvement spread across ≥2 crash years. PASS ⇒ a direct breadth lever
  reproduces the DD reduction without the vol machinery, and is the cleaner thing to ship. The
  **attribution block** additionally reports: did the levers ENGAGE (avg_positions actually rose);
  is DD monotonic in breadth (CONCENTRATE_8 deeper, breadth shallower); do the risk-path and cap-path
  agree; does breadth match/beat the vol arm; does the combo reach −30%. DSR is REPORTED but NOT a
  gate (the 0068 amendment — DSR-on-absolute-Sharpe is the wrong instrument for a sizing knob).
- **Expected failure modes (honest priors)** — (i) the levers DON'T engage: the book is cash/slot-
  bound in a way `risk_per_trade`/`max_positions` don't move (the harness flags this via
  avg_positions — the cap path is the backstop, which DIRECTLY shrinks positions); (ii) breadth
  shallows DD but BLEEDS CAGR past some point (the ladder shows where); (iii) breadth does NOT
  reproduce the vol arm and CONCENTRATE_8 doesn't deepen → the −45% DD is closer to structural and
  the COVID-conditional vol-timing was the real 0068 driver after all.
- **n_trials (cumulative)** — **68** (63 + 5 new arms). V2_vol_ref is not re-counted.
- **Status** — COMPLETE. Cloud run 28245124436 (2026-06-26, corrected 397-name universe).
- **VERDICT — KILL as a DD lever (gate b fail), with a sharp mechanism finding.** Breadth IS real
  diversification (avg_positions 13.5 → 24-29 at MAINTAINED ~95% deploy — the deploy% confound guard
  confirms it is NOT de-gross) and it DOES cut MaxDD (OFF −45.6 → BREADTH_CAP_25 −37.0 → CAP_30 −36.0),
  BUT it COSTS CAGR (−4 to −6pp: OFF 26.2 → 20-22) because the momentum edge is concentrated in the
  top-ranked names; diluting into more names bleeds return. Best breadth arm BREADTH_CAP_25 fails
  gate (b): paired dSharpe CI [−0.224, +0.257], CI-low < −0.10 (Sharpe statistically flat, not a
  reliable improvement). The cleaner finding is **CONCENTRATE_8**: 8 names keeps the HIGHEST CAGR
  (26.8) at ~the SAME DD (−45.1) → the DD axis is ASYMMETRIC: widening the book dilutes the crash,
  but narrowing below ~13 does NOT deepen it — because the −45 floor is the **COVID-2020 SYSTEMATIC
  crash**, not idiosyncratic concentration (every arm's 2020 DD sits at its global MaxDD). No arm
  reaches −30 (shallowest COMBO_25_vol −34.6 at a big CAGR cost + de-gross). 2018/2022 ARE reducible
  below −30 (CAP_30: 2018 −19.4, 2022 −30.6); COVID-2020 is the binding ~−35 floor.
- **Conclusion** — diversification is a REAL but CAGR-COSTLY DD lever (lower DD, lower return — the
  textbook trade-off), so it does NOT meet the owner's "−30 keeping CAGR up". The only CAGR-neutral
  DD lever found is the 0068 vol-target (crash-time de-gross, DD ~−39 at neutral CAGR). −30 with CAGR
  intact is NOT achievable via sizing/breadth — the COVID-style systematic crash is the binding
  constraint and needs targeted market-risk management (regime / vol / tail), not diversification.
  CAVEAT: the OFF arm's absolute CAGR differs from the 0068 run (23.1 vs 26.2) — yfinance universe-
  rebuild noise across the two cloud builds (MaxDD byte-identical −45.59 both runs, so the COVID path
  is stable; the tail-year returns differ). WITHIN-run arm deltas are clean (common universe); only
  cross-run ABSOLUTE CAGR carries the ~±3pp rebuild noise.

## How to run
```
gh workflow run cpcv-research.yml --ref <branch> -f runner=run_breadth_long_horizon
```
Output: `diagnostics/cpcv_breadth_long_horizon.json` + a printed table (per-arm CAGR/Sharpe/MaxDD/
Calmar/deploy%/avgPos/trades), the per-crash-year DD, the gates → PROMOTE/KILL on the best breadth
arm, and the attribution block (breadth vs de-gross vs vol, lever-engagement, monotonicity, −30%).
