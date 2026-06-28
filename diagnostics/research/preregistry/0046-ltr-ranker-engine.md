# 0046 — Learning-to-Rank engine: does cross-sectional ranking beat the per-stock base?

- **ID:** 0046. Registered 2026-06-18, BEFORE the validation run. Cloud-run. Stage-2 **lead model lever (LTR)**.
- **Type:** model-architecture trial. Counts **+1** cumulative trial — bump `n_trials.json` before the run.
- **Skeptic gate:** `flaw-hunter` + `overfit-skeptic` + `backtest-validator` must clear before any PROMOTE.

## Hypothesis
The model is INFORMATION-LIMITED, not capacity-limited (0043): OOS rises with capacity, new alpha from the
same data is exhausted (long kill record). The remaining frontier is **better USE of the same information** —
a cross-sectional **Learning-to-Rank** head that orders names by relative attractiveness, vs the per-stock
absolute-return regression + 0.92 hard gate. Skeptical prior: same features → same information ceiling; the
ranking reframing may be null. Default = KILL.

## Design (frozen; Option B, #124-free)
- **Model:** `LGBMRankerModel` (`src/models/lgbm_ranker.py`) — a LambdaRank **rank head** + the REUSED,
  validated v1 return + confidence heads (the ONE new idea is ranking; magnitude/confidence unchanged).
- **Label:** cross-sectional **rank of `fwd_return_14d`** (`src/data/rank_label.py`, fixes AUD-025), graded
  0–9 within each date, de-leaked PIT.
- **Training:** `train_v1_ranker.py` — capacity pinned INSIDE the 0043 envelope (num_leaves 63, min_child 50,
  depth 8; do NOT exceed leaves 127), shared seed, `REPRODUCIBLE_MODE=1`.
- **Selection:** `V1RankerStrategy` (`src/strategies/v1_ranker_strategy.py`) — rank → **top-K per day**
  injected as the `engine.run` **grade_fn** (`grade_fn(test_panel)` precomputes per-day top-K membership and
  admits only those names, `("ltr", 1.0)`; the rest → `None`). This REPLACES the 0.92 confidence cliff (cfg
  `min_confidence`/`min_predicted_return` set ≈0 so the rank top-K is the gate). **EXISTING sizing**
  (size_mult 1.0 = the engine default; **no #124** — no reallocation / conv×RR). Momentum context filters
  (`require_uptrend`/`min_adx`/`min_rsi`) stay as live config — the ranker replaces the *confidence* gate,
  not the momentum premise. **K is PINNED** (one value, default 20 — no sweep, which would inflate n_trials).

## Method
**Runner: `diagnostics/run_cpcv_ranker.py`** (dispatch `cpcv-ranker.yml`) — a deliberate CLONE of
`run_cpcv_walkforward.py`: SAME 45 CPCV splits, SAME 9 LdP-reconstructed paths, SAME per-path
trade-IR/CI/DSR/noise-floor math → the two JSONs are directly comparable. The ONLY moving part is entry
SELECTION. **Leakage discipline: BOTH heads retrained PER SPLIT** on the split's train dates — the
return/confidence heads (a fresh `PredictionModel`, identical to the base runner) AND the rank head (a fresh
`LGBMRanker` on `rank_label_14d`, capacity in the 0043 envelope). Reusing the frozen v1 heads would leak
(they saw the test groups), so the A/B isolates "top-K-rank vs 0.92-cliff" with no other difference.
PLUS ranking-specific diagnostics: rank-IC of `predict_rank_score` vs realized `fwd_return_14d` with the
**matched-permutation null** (AUD-022), NDCG@K, and the top-K-minus-bottom-K decile return spread.

## Frozen decision rule
PROMOTE the LTR over the per-stock base ONLY IF ALL hold:
1. CPCV mean path trade-IR **uplift over the base (0.191) > the noise floor (0.041)** AND paired CI-low > 0;
2. **DSR > 0.95** at cumulative n_trials;  3. **PBO < 0.5**;
4. rank-IC significant vs the matched-permutation null (not a vol artifact);
5. regime / bad-year (2018/2022/2025) stability — no single-path dependence;
6. capacity stayed within the 0043 envelope (no overfit-zone wandering);
7. `flaw-hunter` + `overfit-skeptic` + `backtest-validator` clear it; golden-master untouched (research only).
Else → **KILL** (record the null — the gate working). No partial credit.

## Result

**Status: COMPLETE — VERDICT: KILL** (2026-06-18, run 27748586572, 4h, all 45 splits / 9 LdP paths,
`REPRODUCIBLE_MODE=1`, top_k=20, n_trials=47). Result committed at `diagnostics/cpcv_ranker.json`.

| Gate criterion (frozen rule) | Required | Measured | |
|---|---|---|---|
| 1. uplift over base (0.191) > floor 0.041 AND paired CI-low > 0 | > +0.041 | **−0.136** | ❌ |
| 2. DSR @ cumulative n_trials | > 0.95 | **0.534** | ❌ |

Ranker mean path trade-IR **0.0555** (CI [0.048, 0.063], dispersion 0.011) vs base **0.191** — ~3.5×
weaker per-trade. Fails gates 1 & 2 decisively → the rest is moot. **Default outcome = KILL** (skeptic
agents are PROMOTE-gates, not needed for a decisive KILL).

**Interpretation (not "ranking is broken"):** the ranker has a REAL, clean positive edge — all 9 paths
positive (+0.46%…+0.86%/trade), CI-low 0.048 well above the noise floor 0.010. It is simply far LESS
SELECTIVE: top-20/day → ~1,700 trades/path vs the 0.92-cliff's handful of high-conviction trades. More
trades, much lower per-trade quality. Same lesson as the 0005 persistence-latch KILL and the HFCL
"trade more" ideas: **the confidence-gate strictness IS the edge; broadening selection dilutes it.** The
cross-sectional reframing extracted no new information from the same data (the 0046 skeptical prior).

**Discipline (no rescue):** trade-IR was the *committed* primary metric — not swapped post-hoc; K was
PINNED — no sweep to manufacture a winner. **Honest caveat:** per-trade-IR structurally penalises a
high-turnover strategy; the ONLY legitimate revisit would be a SEPARATE, newly pre-registered
portfolio-level Sharpe/CAGR trial (capacity-aware), NOT a reinterpretation of this run. Per the frozen
rule + prior, **the KILL stands; do not revisit without new data.** Stage-2 model-architecture family
(ranking) is exhausted; remaining live levers = exit study (0042) + deja_vu (0044).
