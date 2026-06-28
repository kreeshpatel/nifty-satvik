# 0043 — bias-variance operating point: is the live model lazy, overfit, or balanced?

- **ID:** 0043. Registered 2026-06-17, BEFORE the sweep runs. Cloud-run.
- **Type:** **MEASUREMENT diagnostic, NOT a trial.** It locates the existing
  model on the bias-variance curve and selects the *capacity envelope* for the
  P2 Learning-to-Rank build. It makes no PROMOTE/KILL decision on a tradeable
  candidate, so it does **NOT** increment `n_trials` (excluded_non_trials, same
  basis as 0021 IC / 0028 CAGR-bridge). The LTR candidate it informs IS gated +
  counted in its own prereg.
- **Scope guard:** thresholds + selection rule are frozen here so the operating
  point can't be cherry-picked after seeing results (that would be exactly the
  overfit this diagnostic exists to prevent).

## Question
Where does the current served model sit on the **bias-variance tradeoff**, and
what is the BALANCED operating point ("not overfit, not lazy")?
- **Lazy / UNDERFIT (high bias):** weak in-sample score even at full data → more
  capacity/features, not more data, is the lever.
- **OVERFIT (high variance):** large in-sample↔OOS gap, high per-fold dispersion,
  fragile.
- **BALANCED:** strong OOS with a controlled gap — the target.
Plus the codebase-specific *deployment* laziness (under-trading / movers missed),
tracked separately via trade count (orthogonal to statistical bias).

## Method
`diagnostics/run_learning_curve.py` (cloud, `REPRODUCIBLE_MODE=1`), pure
decomposition in `src/validation/learning_curve.py` (unit-tested, mypy-strict).
For each capacity setting in the grid, per expanding-window fold (2018–2024):
- **in-sample score** = backtest the trained model on the most-recent **OOS-length
  slice** of its own train window (the calendar year ending at `train_end`) — NOT
  the full multi-year history. Matching the in-sample and OOS window LENGTHS isolates
  overfit from window-length artifacts (a 9y-IS vs 1y-OOS gap conflates the two), and
  keeps the sweep tractable. Still in-sample: the model trained on this slice.
- **OOS score** = backtest the same model on the held-out test window;
metric = **Sharpe** (live `config.json` parity — stop 2.0, gate 0.92, W2). Method
refinement registered BEFORE any results (the prior cancelled run produced none).
The runner checkpoints after every fold (crash-safe partial output).
Aggregate: mean in-sample, mean OOS, per-fold OOS paths (dispersion), Σ trades.
Capacity axis = LightGBM flexibility (num_leaves↑ / min_child_samples↓ = more
capacity). **Independent Octave/MATLAB recompute** of the gap + dispersion as a
differential check of the decomposition (Stage-3 P1 cross-check).

## Frozen thresholds + selection rule
- `MIN_IN_SAMPLE_SHARPE = 0.30` — in-sample below this ⇒ **UNDERFIT**.
- `GAP_THRESHOLD = 0.75` — (in_sample − OOS) above this ⇒ **OVERFIT**.
- `MIN_TRADES = 80` (pooled across folds) — below ⇒ **deployment-LAZY** flag (auxiliary, not a fit class).
- **Operating point** = among BALANCED capacities, the highest mean OOS Sharpe;
  ties within an OOS noise band → the **SIMPLEST** (lowest capacity) — Occam /
  anti-overfit tie-break. If none are BALANCED, report the regime (all-underfit
  → add capacity; all-overfit → regularize/more data) and select nothing.

## Decision / deliverable
- `diagnostics/bias_variance_profile.json` + `BIAS_VARIANCE_FINDINGS.md`: the
  per-capacity table, fit classification, the selected operating point (or the
  no-balanced-point verdict), and the deployment-laziness read.
- **Feeds P2:** the LTR ranker is built + tuned to live INSIDE the balanced
  capacity envelope found here (it does not get to wander into the overfit zone).
- No live change. No `n_trials` increment.

## Result
**Status: REGISTERED — awaiting cloud run.** (Owner executes; pandas hangs locally.)
