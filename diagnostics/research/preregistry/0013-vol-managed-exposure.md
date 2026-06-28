# 0013 — Regime + volatility-managed gross exposure (Phase 1)

- **ID** — 0013
- **Registered** — 2026-06-06
- **Hypothesis** — Scaling PORTFOLIO gross exposure by (a) market regime and
  (b) inverse trailing realized volatility raises the walk-forward mean Sharpe,
  **lowers its across-fold std** (consistency), pushes the negative/flat folds
  (2018 0.16, 2019 −0.72, 2022 0.30, 2025 −0.57) toward ≥0, and reduces MaxDD —
  WITHOUT changing stock selection. Predicted direction: mean Sharpe +0.1–0.4,
  std −0.3+, MaxDD shallower. Trade count and per-trade win rate are **unchanged
  by construction** (the overlay only resizes positions; it does not change which
  trades are taken or their per-trade returns), so those two floors pass trivially.
- **Holdout** — `forward-wall` (WALL_DATE 2026-05-30) is the ultimate confirmation
  (accrues live). NOTE: a pure SIZING overlay does not change per-trade/per-stock
  returns, so the `unseen-universe` holdout is **N/A** for this experiment — it
  can't distinguish overlay-on from overlay-off. The walk-forward is therefore
  both the generation AND the primary evaluation surface here; overfitting is
  controlled by (i) a small PRE-DECLARED coarse grid, (ii) Deflated-Sharpe
  deflation by the grid size, (iii) a single-fold-robustness requirement, and
  (iv) the live forward wall.
- **Primary metric** — the balanced composite (`run_balanced_scorecard.py`) of the
  best grid config vs `baseline_wf_2026_06.json`, with the across-fold Sharpe-std
  reduction carrying the "consistency" half of the return axis.
- **Decision rule** — pre-declared grid (exactly these 4, no fine-tuning):
  | cfg | regime caps {BEAR,CHOPPY,BULL} | target_vol | isolates |
  |-----|------------------------------|-----------|----------|
  | C1 | {0.5, 1.0, 1.0} | none | regime leg only |
  | C2 | {0.5, 1.0, 1.0} | 0.25 | regime + vol |
  | C3 | {0.3, 1.0, 1.0} | 0.20 | stronger de-risk |
  | C4 | {1.0, 1.0, 1.0} | 0.20 | vol leg only |
  PROMOTE the single best-composite config iff: (a) all `evaluate_candidate`
  floors hold; (b) drawdown floor holds (MaxDD ≤ 1.10× baseline); (c) composite
  > 0; (d) **DSR > 0.95 at n_trials = 14 + 4 = 18**; (e) the Sharpe improvement
  is spread across **≥2** of the four weak folds (2018/19/22/25), not driven by a
  single fold. Else KILL (→ "sizing already near-optimal", itself informative).
- **n_trials (cumulative)** — **18** (14 program-start + 4 grid configs, run in
  one sweep).
- **Status** — PENDING (blocked on `baseline_wf_2026_06.json` locking)

## Method (cheap + clean isolation)

A single-process SWEEP harness trains each walk-forward fold's model **once**,
then backtests that identical model under overlay-OFF + the 4 configs. Because
the per-fold models are the same objects across configs, the ONLY difference is
the exposure overlay — perfect isolation, no `REPRODUCIBLE_MODE` needed, one
features rebuild. Requires threading an `exposure_config` (regime_caps,
target_vol) through `run()`/`_simulate` → `portfolio_exposure_scalar`.

```
gh workflow run walk-forward.yml --ref feat/phase1-vol-exposure \
  -f out_name=phase1_sweep -f apply_exposure_overlay=true ...   # (sweep variant)
```

## Result

**2026-06-06 — KILL (all 4 configs).** Sweep run 27061924669 (train-once /
backtest-many; each config shares per-fold models with the `off` pass → clean
isolation). Balanced scorecard, each config vs the sweep's own `off`:

| cfg | mean Sharpe | std | worst MaxDD | composite | DSR@18 | verdict |
|-----|-------------|-----|-------------|-----------|--------|---------|
| off | 1.482 | 1.884 | −37.9% | — | — | (control) |
| C1  | 1.534 | 1.949 | −38.4% | +0.007 | 0.26 | KILL (floor: sharpe_wins) |
| C2  | 1.530 | 1.868 | −34.2% | +0.021 | 0.26 | KILL (floor: sharpe_wins) |
| C3  | 1.433 | 1.829 | −33.4% | +0.019 | 0.19 | KILL (floor: sharpe_wins) |
| C4  | 1.563 | 1.911 | −36.8% | +0.008 | 0.28 | KILL (floor: sharpe_wins) |

Every config's effect is within noise: mean Sharpe moves ±0.08, std barely
shifts, DSR 0.19–0.28 (≪0.95). C2/C3 trim the worst-fold MaxDD a few points
(−38%→−34%) but at flat/lower mean Sharpe; no config wins ≥70% of folds vs `off`,
no config improves ≥2 of the weak folds. Composites marginally positive but the
floors + DSR + robustness bars all fail. **Do NOT promote.**

**Why (the valuable learning):**
1. **Redundant with the live BEAR block.** The baseline already runs
   `apply_bear_block=True` (live policy), which gates entries OUT of BEAR
   regimes. By the time a regime/vol EXPOSURE overlay runs on top, the BEAR
   periods are already largely absent from the book — there's little left to
   re-scale. Risk is already managed at the ENTRY level; managing it again at
   the SIZING level adds ~nothing.
2. **2025 is unchanged by every config** (−0.99 Sharpe, −16% MaxDD, identical
   across off/C1-C4). 2025's losses occur in CHOPPY/BULL-classified periods, not
   BEAR — so neither bear-block nor the overlay touches them. **2025 is a SIGNAL
   problem in a "good" regime, not an exposure problem.** Exposure management
   cannot fix it.
3. Vol-targeting alone (C4) lifts mean Sharpe marginally but worsens drawdown/
   consistency — the Barroso–Santa-Clara crash-protection effect is weak here
   precisely because bear-block already removed the momentum-crash windows.

**Redirect for the program:** the residual bad-year losses (esp. 2025) are
ALPHA/signal failures in non-BEAR regimes. Phase 2 (mean-reversion sleeve — a
DIFFERENT signal for the chop where momentum fails) and Phase 3 (orthogonal
factors) are the right levers; more exposure management is not. Possible narrow
follow-up (not scheduled): overlay REPLACING bear-block (overlay-on + block-off)
rather than stacking — but the live policy keeps the block, so this verdict
stands for the live config. n_trials advances 14 → 18.
