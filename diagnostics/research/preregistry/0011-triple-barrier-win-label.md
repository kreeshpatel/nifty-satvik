# 0011 — Triple-barrier (path-aware) win label

- **ID:** 0011
- **Registered:** 2026-06-04
- **Holdout:** unseen-universe → forward-wall. Retrain-gated.
- **n_trials (cumulative):** ~56.
- **Status:** COMPLETE — **KILL** (2026-06-04). Strongest point-estimate
  near-miss on per-trade OOS (+0.68%/trade, +4pp WR) but sub-CI; AND the
  production walk-forward gate REJECTed it (3/9 fold Sharpe wins, −0.38 mean
  Sharpe, −26.5pp CAGR — selectivity bleeds CAGR in trend years). Briefly
  adopted as the training default then REVERTED. Do NOT deploy. See Result +
  "Walk-forward gate" below.

## Motivation

This is the first *method* (not data) experiment, chosen after lever #1
(cross-sectional normalization) was deprioritized: the codebase already
cross-sectionally ranks its highest-value features (`rs_rank_universe_20d` *is*
the CS percentile of `return_20d`), and MACD — the one clean scale-dependent
case — is already a top-tier feature as raw (`macd_signal` 2.36% importance). So
CS-ranking has thin headroom (verified via live importances, 2026-06-04).

The genuinely un-addressed defect is the **confidence label**. Today:

```
fwd_max_14d   = (max(high[i+1 : i+15]) - close[i]) / close[i] * 100   # the PEAK
hit_4pct_14d  = (fwd_max_14d >= 4.0)                                  # high EVER touched +4%
```

`hit_4pct_14d` is **path-blind**: it labels a setup a "win" if the high touches
+4% at any point in 14 days — *even if the price first fell to the stop*. The
confidence classifier therefore learns to favour setups that look good at the
peak, not setups that actually reach the target before stopping out. The
backtest applies the stop at *test* time, but the model was never *trained* to
prefer trades that survive the stop. (The return head's analogous optimism is
already handled post-hoc by `shrink_target` calibration — see 0007 — so this
experiment leaves the return head alone.)

## Hypothesis

Retraining ONLY the confidence head on a path-aware **triple-barrier** win label
— `tb_hit_14d` = 1 iff the +4% target is touched **before** the 2×ATR stop
within 14 days — lifts after-cost per-trade expectancy on the unseen universe vs
a same-everything baseline trained on `hit_4pct_14d`, because the model selects
setups that win under realistic path-dependent exits rather than setups that
merely spike.

## Design (isolation)

- **Only the confidence label changes.** Return head stays on `fwd_max_14d`
  (keeps the `min_predicted_return=8%` gate compatible — a path-aware return
  capped at the +4% barrier would clear zero trades).
- **Barriers match live execution:** upper = +4% (identical to the baseline
  target, so ONLY path-awareness changes — not the target level); lower =
  `stop_mult × atr_pct` = 2.0×ATR (the live `stop_type=atr`, `stop_mult=2.0`);
  vertical = 14 days.
- **Same-day both-touched → assume STOP first** (conservative; intraday order
  unknown, take the adverse assumption for a long).
- **Time-barrier exit → label 0** (target not reached before stop/time).
- Baseline and candidate train on the **same features, same window
  (2010-01-01..2024-12-31), same rows** (both labels NaN only in the last 14
  bars/stock). Unseen-universe OOS (2021-2025) through the **identical live gate
  (0.92 / 8%)** — only the confidence model differs.

## Primary metric

Delta in mean after-cost per-trade return (%) on the unseen universe, candidate
(path-aware label) vs baseline (`hit_4pct_14d`), 95% bootstrap CI. Honest costs.

## Secondary / diagnostic

- **Label-divergence rate** (computed before trusting the OOS): fraction of
  `hit_4pct_14d==1` rows that are `tb_hit_14d==0` (touched +4% but only *after*
  stopping out). If this is tiny (<~10%), the labels barely differ → expect a
  marginal result; if large (>~30%), the defect is material.
- Candidate vs baseline positive-rate (tb_hit will be rarer than hit_4pct).
- Candidate trade count `n` (a stricter, more-honest label may clear the fixed
  0.92 gate less often — report it; very low n is itself a finding).
- WR + Sharpe delta.

## Decision rule (fixed in advance)

- **SUPPORT:** candidate per-trade CI lower bound ≥ baseline point estimate AND
  candidate n ≥ 30 AND WR not down >3pp AND DSR>0.95 → escalate to forward wall
  (and consider recalibrating the 0.92 gate for the new label base-rate).
- **KILL:** candidate per-trade ≤ baseline (no improvement) OR candidate
  produces too few trades (n<30) to matter at the live gate.
- **INCONCLUSIVE:** overlapping CIs.

## Priors

More hopeful than the redundant-feature experiments (0002/0004): this is a
genuine, un-calibrated training-label defect, and the mechanism (train the model
to prefer stop-surviving setups) is sound. BUT a real counter-prior: `hit_4pct`
and `tb_hit` may rank setups very similarly (a setup that hits +4% usually does
so without a deep prior dip), in which case retraining changes little — the
backtest already penalises stop-outs at test time. The label-divergence
diagnostic will tell us which world we're in before the OOS is even trusted.

## Procedure

1. Rebuild features (full universe) → compute `tb_hit_14d` from forward OHLC
   paths (lookahead-safe: bar i uses only [i+1, i+14]) → inject as a column.
2. Train baseline (`PredictionModel`, default `hit_4pct_14d`) AND candidate
   (same, but `config["confidence_label"]="tb_hit_14d"`) **inline in the runner**
   — no `train.py` subprocess, so a mid-run worktree branch-flap can't disturb
   the run. Same window, same features, identical save format
   (`LightGBMTwoHeadModel`-loadable `model.pkl`). 0011 touches NO production code.
3. Unseen-universe OOS both through the live gate → primary metric +
   diagnostics. DSR-correct. Forward-wall if SUPPORT.

## Result (2026-06-04)

Rebuild (497 stocks, 2010-2024) → inject path-aware `tb_hit_14d` → inline-train
baseline (`hit_4pct_14d`) + candidate (`tb_hit_14d`), same features/window/rows →
unseen-universe OOS (145 smallcaps, 2021-2025) through the live 0.92/8% gate.
`diagnostics/data/0011_triple_barrier.json`.

**Label divergence (the decisive diagnostic): 6.2%.** Of 907,669 setups that
touched +4% in 14d, only 56,298 (6.2%) stopped out first. So the path-blind
`hit_4pct` label is "wrong" only 6% of the time → the lever's ceiling is low by
construction. Positive rate 64.7% → 61.0%; train conf-AUC 0.7276 → 0.7295 (flat).

| metric | baseline (hit_4pct) | candidate (tb_hit) | delta |
|---|---|---|---|
| per-trade | +3.74% | **+4.42%** | **+0.68%** |
| 95% CI | [2.46, 5.02] | [2.90, 5.88] | overlap |
| win rate | 65.9% | **69.9%** | +4.0pp |
| Sharpe | 2.45 | 2.54 | +0.09 |
| trades (n) | 343 | 266 | −77 |

**Verdict — INCONCLUSIVE/KILL per the rule:** candidate CI-low 2.90 < baseline
point 3.74 (overlapping CIs). No deploy.

**But it's the strongest point-estimate near-miss of the program** (+0.68%/trade
> 0010's +0.36%; +4pp WR; Sharpe up). The mechanism is real and the *right kind*:
the path-aware label made the model MORE selective (266 vs 343 trades — it stopped
trusting setups that only spike after stopping out) and the surviving trades were
better. Same "re-score quality, trade fewer-but-better" signature as 0010 — NOT
the "trade more / lower-conf" failure of 0004/0005.

**Why it can't clear the bar:** the 6.2% divergence caps the room, and dropping 77
trades widens the candidate CI — so a genuine +0.68% point lift still overlaps the
baseline. Discipline holds: a sub-CI single-window result on a 6%-divergence label
is not deployable.

**Follow-up (0011b):** raise the win bar +4%→+7% (gate-aligned). At +7% the
divergence from the live label is far larger → a bigger swing (running; watch n
for gate starvation). The pure threshold effect = (0011b − 0011) delta vs the
shared baseline.

## Walk-forward gate (2026-06-04) — the decisive portfolio-level test → KILL

After the per-trade OOS near-miss, the label was briefly adopted as the
production training default (commit bdf74e5) under the "correctness fix → adopt
if not-worse" bar, with promotion still gated by the `retrain_ensemble` 14d
walk-forward. Running that gate end-to-end (the authoritative promotion guard)
settles it. Two infra blockers had to be fixed first:

1. The local `features.pkl` had been clobbered to **58/79 features**
   (unenriched) by a background job → re-enriched offline from the macro/sector
   caches back to 79f (tb labels preserved).
2. **Real bug introduced by the 0011 merge:** `diagnostics/run_walk_forward.py`
   hardcoded the kept label columns to `(fwd_max_14d, hit_4pct_14d)`, so every
   fold's `train_fn` KeyError'd on the filtered-out `tb_hit_14d` → all folds
   "missing" → spurious REJECT. Fixed (commit 908b3bc) to derive the kept
   labels from the model config (drift-proof, label-agnostic). **This bug would
   have made the live monthly auto-retrain gate REJECT every candidate
   regardless of merit** had tb_hit stayed the default.

Valid gate result (candidate `tb_hit` vs incumbent `hit_4pct` baseline,
`diagnostics/walk_forward_results.json`, 10/10 folds populated):

| year | base Sharpe/CAGR/n | cand Sharpe/CAGR/n | ΔSharpe |
|---|---|---|---|
| 2017 | 2.36/+38%/71 | 2.85/+41%/47 | +0.48 |
| 2018 | 0.47/+8%/114 | 1.15/+19%/73 | +0.69 |
| 2019 | 0.55/+11%/102 | 0.57/+8%/61 | +0.02 |
| 2020 | 4.15/+226%/169 | 1.90/+66%/135 | **−2.26** |
| 2021 | 4.21/+182%/169 | 3.83/+119%/122 | −0.38 |
| 2022 | 0.55/+10%/126 | 0.36/+5%/93 | −0.19 |
| 2023 | 1.37/+16%/47 | 0.40/+2%/17 | −0.96 |
| 2024 | 0.64/+9%/89 | 0.29/+3%/63 | −0.34 |
| 2025 | −0.54/−5%/21 | −1.01/−5%/8 | −0.47 |

**Sharpe wins 3/9 (gate needs ~7/9) · mean ΔSharpe −0.38 · mean ΔCAGR −26.5pp →
REJECT.** Coherent economic story (not a data artifact): the candidate trades
~35% fewer in EVERY fold (the path-aware selectivity, consistent with the
266-vs-343 OOS). It WINS the choppy years (2017/2018/2019) but LOSES the
strong-trend years badly (2020 COVID-rebound −2.26) — demanding "+4% before the
2×ATR stop" filters out volatile names that gap into the biggest runners, so it
leaves large CAGR on the table in raging bulls. **Per-trade quality improves but
does NOT survive the portfolio-level Sharpe/CAGR gate.**

**Decision: KILL + REVERT.** confidence_label restored to `hit_4pct` in all 3
train siblings (commit 0c5d82f) — keeps the auto-retrain pipeline able to
promote (a tb_hit default would dead-end it: every candidate gate-REJECTed
forever). `tb_hit_14d/30d` stay COMPUTED in `data_store` (research infra) and
the drift-proof walk-forward filter fix stays. **Lesson: a "more correct" label
≠ a better model** — the path-blind label's permissiveness acts as a useful
volume/upside booster in trend years, and the walk-forward gate (portfolio
CAGR/Sharpe) is a stricter, more honest bar than per-trade OOS expectancy.
