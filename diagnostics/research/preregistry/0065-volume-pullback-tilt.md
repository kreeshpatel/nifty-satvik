# 0065 — volume-pullback selection TILT (Build A from the full sweep)

**Date:** 2026-06-23
**Status:** PRE-REGISTERED (frozen below). One DSR trial (n_trials +1).
**Parent finding:** the full multi-angle sweep on the high-vol-pullback signal (0064 follow-up).

## What the sweep concluded (the complete verdict, not piecemeal)
- **DEAD — the return/magnitude edge.** The "+20.7%/+13pp" headline is three coincident concentrations: **2019** (drop it → +2.33pp, CI through 0), **one stock** (JPPOWER = 50% of high-vol PnL), **one sector** (Energy = 63% of PnL). Pooled CI [−2.35, +38.1] never excluded 0. Retired.
- **ALIVE but unproven — a recent WIN-RATE / entry-quality edge.** Magnitude-robust, survives ex-2019 / ex-Energy / drop-top-1 / leave-one-year-out. Recent-5y (2021–25): WR **+16.8pp** [+5.0, +27.8], mean **+3.73pp** [+0.84, +6.52]; recent ex-Energy mean **+4.23pp [+1.09, +7.40]** (the most defensible number). **Orthogonal** to the model (partial corr vs the sort key = **+0.054**), in the **body** not the tail, concentrated at **high confidence + extreme ratios**, with **favorable downside** (HV worst −15.9% vs LV −65.5%; stop-out 3% vs 8%).
- **Honest flag:** in-sample, ~12 analyst cuts taken; adversarial permutation p≈0.011 **fails** the multiplicity-corrected bar (~0.004); "recent-5y" sits at the start-year fork optimum; effective-n thin (~35–49 clean trades). **Promising candidate to test FORWARD, not a proven edge.**

## The build (Build A — the safe, no-retrain vehicle to run the forward test)
An **additive rank-normalized selection tilt** on the daily candidate sort (`backtest_engine.py`): when `vol_pullback_tilt_lambda > 0`, sort by `base_key + λ·span·rank_norm(pullback_volume_ratio)` where `base_key = confidence·predicted_return`, `span = max(base)−min(base)`. It only **re-orders which candidates take the daily slots** — admits NO new trades, can't relax the 0.92 gate, can't blow up the book. `λ = 0` (default) runs the ORIGINAL sort exactly → **golden-master byte-identical (verified, 2 tests pass)**. `pullback_volume_ratio` is a **SIDECAR** in `data_store` (NOT in V1_FEATURES → model stays frozen 79f; dropped from the training frame by `filter_to_v1`, present at scoring via `ds.get_period`).

**Frozen parameters (no sweep):** threshold for "high-vol" = ratio ≥ 1.14; **λ = 0.10** (bonus spans 10% of the base-key range — a tie-breaker that bites only under slot contention).

## The PORTFOLIO test (this run, `run_cpcv_voltilt.py` + `cpcv-voltilt.yml`)
Paired CPCV A/B on the SAME per-split model: arm `base` (λ=0) vs arm `tilt` (λ=0.10), 45 splits / 9 LdP paths, 2015–2024, REPRODUCIBLE_MODE=1. Metric = paired (tilt − base) PORTFOLIO Sharpe per path, GROUP-level bootstrap CI (10k), full window + recent-5y, per-year + per-fold.

**PRE-COMMITTED gate — ADOPT iff BOTH:**
1. **Not-worse on the full window:** full paired dSharpe **CI-low > −NOISE_FLOOR (−0.3)**.
2. **Positive in the claimed regime:** recent-5y (2021–25) paired dSharpe **CI-low > 0**.

Else **KILL** (live sort stands). Judge on Sharpe/CAGR **shape**, not pooled per-trade. A PASS authorizes ONLY the forward-wall test below — never a live flip on this in-sample run alone.

## The decisive OOS test (the ungameable one — settles whether the signal is real)
Pre-committed, no more in-sample slicing: collect high-vol-pullback trades on the live **forward wall** (`HOLDOUT.md` WALL_DATE) until **n_hi ≥ 40**, require within-confidence **WR-uplift CI-low > 0** on those forward-only trades with **ZERO further sub-splits** (no era/sector/conf re-slicing). Ungameable: the data doesn't exist yet and the spec is frozen. Secondary: unseen-universe OOS per `HOLDOUT.md`.

## Concentration guard (mandatory for any SHIP)
Per-name and per-sector caps (Energy/power/telecom low-floats) so any harvested edge is the WR effect, not silent lottery-basket exposure — reuse the capacity-aware execution work.

## Governance
PASS authorizes research → shadow → forward wall before any live flip; flag-gated default-off (golden-master byte-identical); compliance-safe (a candidate change to a model-generated decision-support selection order; no guaranteed outcomes).

## Kill criterion
If the WR uplift fails to replicate ex-Energy on ≥40 forward-wall high-vol observations, retire it — the magnitude edge is already a known concentration artifact, so the recent WR is the only thing worth defending.
