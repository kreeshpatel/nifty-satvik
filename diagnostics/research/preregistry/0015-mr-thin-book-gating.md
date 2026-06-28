# 0015 — MR sleeve, thin-book gating (Phase 2 refinement)

- **ID** — 0015
- **Registered** — 2026-06-07
- **Hypothesis** — The 0014 MR sleeve worked directionally (composite +0.115,
  +37% trades, repaired 2025/2023) but failed the per-fold-wins floor (6/10)
  because it ALSO added MR trades in active good years (2017/2020/2024),
  diluting their Sharpe. Gating MR to fire ONLY when the momentum book is THIN
  that day (≤ N momentum signals cleared the gate) keeps MR out of active days
  and confines it to the lean chop periods — lifting the bad folds WITHOUT
  diluting the good ones, converting 6/10 into a legitimate ≥7/10.
- **Holdout** — `unseen-universe` → `forward-wall`. Walk-forward folds generate;
  holdout confirms.
- **Primary metric** — balanced composite of the merged book (best thin-book
  variant) vs the matched momentum-only `off`, with the per-fold-wins floor as
  the specific bar 0014 missed.
- **Decision rule** — Pre-declared grid (thin-book threshold N ∈ {3, 5}; the
  un-gated `mr` is re-run as the 0014 control):
  PROMOTE the best thin-book variant iff: (a) `evaluate_candidate` floors hold
  INCLUDING `sharpe_wins_per_fold ≥ 7/10` (the 0014 failure); (b) drawdown floor
  holds; (c) composite > 0; (d) DSR > 0.95 at n_trials; (e) the good-folds
  (2017/2020/2024) are NOT diluted below their `off` Sharpe by more than a small
  tolerance (the dilution this refinement targets); (f) the bad-fold lift
  (2019/2022/2023/2025) is preserved across ≥2 folds. Else KILL — MR's value is
  real but uncapturable cleanly, log and move to Phase 3.
- **n_trials (cumulative)** — **21** (19 + 2 thin-book thresholds; the un-gated
  `mr` control was already counted in 0014).
- **Status** — PENDING

## Method

`merge_mr_predictions(..., thin_book_max=N)` counts momentum passers per DATE and
substitutes MR only on dates with ≤ N passers. `run_mr_sleeve.py` sweeps
{off, mr (0014 control), thin3, thin5} with shared per-fold models (clean
isolation). Balanced-gate each thin variant vs `off`; compare to the 0014 `mr`
to confirm the dilution is reduced.

## Result

**2026-06-07 — INCONCLUSIVE (refinement adds nothing) + a methodological finding
that supersedes the question.** Sweep run 27088531577 (`phase2_thin`, off / mr /
thin3 / thin5, shared per-fold models). Balanced scorecard vs `off`:

| cfg | composite | sharpe_wins | mean Sharpe | trades | verdict |
|-----|-----------|-------------|-------------|--------|---------|
| mr (0014) | +0.098 | **8/10** | 1.45→1.57 | +33% | PROMOTE |
| thin3 | +0.095 | 7/10 | 1.61 | +33% | PROMOTE |
| thin5 | +0.098 | 8/10 | 1.57 | +33% | PROMOTE |

Thin-book gating ≈ plain `mr` (no improvement). The good-year dilution 0015
targeted was largely v3-run-specific noise: in THIS run all variants dilute the
good folds by ≤0.06 Sharpe. **0015's specific hypothesis does not hold — and
wasn't needed.**

**The real finding:** the same un-gated `mr` scored **6/10** folds in the v3 run
(0014, → KILL) and **8/10** here (→ PROMOTE). Identical logic, opposite verdict —
because both sweeps use NON-REPRODUCIBLE per-fold models, so which folds MR beats
`off` in swings ±2 on model-fit randomness. **The `sharpe_wins_per_fold` gate
verdict is decided by noise, not the signal.** What IS robust across BOTH runs:
composite +0.10–0.12, trades +33% (→~130/yr), mean Sharpe +0.12, std down
(consistency), bad years (2018/19/22/23/25) lifted. The AGGREGATE signal is real;
the per-fold VERDICT is unstable.

**Resolution:** a REPRODUCIBLE-mode sweep (deterministic per-fold models) is the
only defensible way to settle promote/kill — added `reproducible` to mr-sleeve.yml.
Decisive MR verdict deferred to that run (`phase2_repro`). n_trials 21 (no new
variant; reproducible re-run of the SAME configs, not a new hypothesis).
