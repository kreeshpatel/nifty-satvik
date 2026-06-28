# 0012 — Results-focused improvement program (master + baseline lock)

- **ID** — 0012
- **Registered** — 2026-06-06
- **Hypothesis** — The current strategy's edge is REGIME-CONCENTRATED (walk-forward
  mean Sharpe ~1.21, std ~1.8; great in 2020/21 bulls, flat-to-negative in
  2018/19/22/25) and TRADE-COUNT-THIN in lean years. A staged program that
  (Phase 1) regime/volatility-manages gross EXPOSURE and (Phase 2) adds an
  uncorrelated mean-reversion SLEEVE will lift the BALANCED scorecard — more
  consistent risk-adjusted return (mean Sharpe ↑, std ↓), more trades in lean
  years, win rate held — without changing the momentum stock-selection gate.
- **Holdout** — `unseen-universe` (immediate) → `forward-wall` (WALL_DATE
  2026-05-30, accrues). Walk-forward dev folds are for GENERATION/tuning only;
  confirmation is on the holdouts.
- **Primary metric** — the **balanced composite** (`run_balanced_scorecard.py`):
  equal-weighted improvement across {trade-count, win-rate, risk-adjusted-return
  (mean Sharpe + consistency), drawdown} vs the locked baseline.
- **Decision rule (per phase)** — PROMOTE iff: (a) all `evaluate_candidate`
  floors hold (≥70% per-fold Sharpe wins, ≤10% mean Sharpe/CAGR regression, WR
  within 5pp, trade-count ≥50% of baseline); (b) the drawdown floor holds
  (candidate MaxDD ≤ 1.10× baseline); (c) composite > 0; (d) Deflated Sharpe
  > 0.95 at the current cumulative `n_trials`; (e) the holdout does not
  contradict. Any breach → KILL. No single axis may dominate.
- **n_trials (cumulative)** — **14** at program start (0001–0011b ≈ 11 prior
  pre-registered trials + the 2026-06 capacity-aware/cleaned-retrain trials).
  This is the running DSR ledger: **increment by 1 for every walk-forward
  candidate the program evaluates** (each Phase-1 tuning run, each sleeve
  variant, each Phase-3 factor). Sub-experiments run SERIALLY so the count is
  exact.
- **Status** — PENDING (baseline being locked)

## Baseline lock

The control for all gate comparisons is the frozen, post-capacity-aware ensemble
walk-forward, run with live-parity BEAR block and the exposure overlay OFF:

```
gh workflow run walk-forward.yml --ref feat/phase0-exposure-infra \
  -f out_name=baseline_wf_2026_06 -f reproducible=true \
  -f apply_bear_block=true -f apply_exposure_overlay=false
```

→ `diagnostics/research/baseline_wf_2026_06.json` (immutable once locked).

## Phase pre-registrations (separate files, written before each run)

- `0013-vol-managed-exposure.md` — Phase 1 (regime/vol gross-exposure overlay).
- `0014-mean-reversion-sleeve.md` — Phase 2 (uncorrelated MR sleeve).
- Phase 3 (orthogonal factors) reuses/extends `0010-delivery-pct-feature.md` +
  new files for sector-RS and low-vol, run strictly serially.

## Result

**2026-06-06 — BASELINE LOCKED.** `baseline_wf_2026_06.json` (run 27060898231,
reproducible + bear-block, overlay OFF). 10 folds 2017-2026: **mean Sharpe 1.36,
std 1.85** (regime-concentrated: 2020 3.97 / 2021 4.69 vs 2018 −0.28 / 2019 −0.43
/ 2022 −0.01 / 2025 −0.55). Per-fold MaxDD ranges −7% to **−34%** (2019), with
deep DD even in the +242% 2020 fold (−32%). This is the immutable control. The
deep bad-year drawdowns are the explicit Phase-1 target.

**2026-06-06 — Phase 1 (0013) KILL.** Regime/vol gross-exposure overlay: all 4
configs within noise (mean Sharpe ±0.08, DSR ≤0.28). Root cause: redundant with
the live BEAR block (risk already managed at entry), and the strategy's worst
year (2025) loses in CHOPPY/BULL regimes the overlay never touches — a signal
problem, not an exposure one. n_trials 14 → 18. **Program redirect:** the
residual bad-year alpha failures need a different SIGNAL, so prioritize Phase 2
(mean-reversion sleeve) over further exposure work.

**2026-06-07 — Phase 2 (0014) KILL (sub-threshold) — STRONGEST signal yet.** MR
sleeve repairs the non-BEAR bad years (2025 Sharpe −1.44→−0.67, 2023 +0.44),
+37% trades (→130/yr, clears the 120 target), better consistency (std 1.89→1.68),
balanced composite +0.115 (program best). KILL only on the per-fold-wins floor
(6/10) — it dilutes good years (the diversification trade-off; the floor is
calibrated for momentum upgrades, not sleeves). → 0015 refines via thin-book
gating (fire MR only when momentum is quiet) to capture the bad-year lift without
the good-year dilution. n_trials 19 → 21. (Two MR no-op gate bugs found+fixed en
route — PR #60, #61.)

**2026-06-07 — Phase 2 FINAL: MR sleeve KILL (reproducible).** The reproducible
sweep overturned the favorable-noise "strongest signal" — deterministic models
give 5/10 fold wins, mean Sharpe +0.025 (flat), DSR 0.05; +37% trades but no
risk-adjusted edge, and 2025 got WORSE. **Both bad-year levers (Phase 1 exposure,
Phase 2 MR) are KILLED** — the 2025-type losses are NOT fixable by portfolio
construction. PROGRAM RULE ADDED: every verdict uses REPRODUCIBLE_MODE (the
non-reproducible runs nearly promoted a worthless sleeve). Remaining lever: Phase
3 orthogonal alpha (genuinely new information). n_trials at 21.

_(per-phase results appended below as they complete; immutable fields above
never edited)_

**2026-06-07 — Phase 3 FINAL: delivery-% KILL (reproducible). PROGRAM COMPLETE.**
Delivery (the orthogonal-alpha lever) made the model WORSE (Sharpe −0.28, WR
−5.6pp, composite −0.02) — overfitting on the short 2020+ window. All THREE
levers tested are KILLed:
- Phase 1 (regime/vol exposure): KILL — redundant with the live bear-block.
- Phase 2 (mean-reversion sleeve): KILL — +37% trades, no risk-adjusted edge.
- Phase 3 (delivery-% orthogonal feature): KILL — degrades the model.

**Conclusion:** the frozen 79f ensemble is at its information + selectivity +
portfolio-construction ceiling. Better sizing, a second price signal, and
genuinely new orthogonal data all fail to add risk-adjusted edge — consistent
with the repo's entire prior track record. The validated edge, run at honest
capacity-aware size, IS the product. Remaining value: accumulate the forward-wall
track record (0003, the decisive live test) — not more alpha mining.

**What the program SHIPPED (the real wins):** (1) capacity-aware execution +
honest costs (PR #55) — corrected an inflated picture; (2) a fixed latent bug
(PR #66) that had silently blocked EVERY feature-set experiment (incl 0004);
(3) the reproducible-only verdict rule, which caught a false-positive MR
promotion; (4) a rigorous, pre-registered, reproducible gate that KILLed three
plausible improvements cheaply instead of shipping noise.
