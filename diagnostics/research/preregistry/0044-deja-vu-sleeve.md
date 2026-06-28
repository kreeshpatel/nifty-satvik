# 0044 — deja-vu sleeve: does historical-analogue conviction add orthogonal edge?

- **ID:** 0044. Registered 2026-06-17, BEFORE any run. Cloud-run. Stage-4 Phase-2 lever **L-DV**.
- **Type:** orthogonal-signal SLEEVE trial (1 arm). Counts **+1** cumulative trial
  (DSR deflation) — bump `diagnostics/research/n_trials.json` before the verdict run.
- **Skeptic gate:** the `overfit-skeptic` + `flaw-hunter` agents must clear the result
  before any PROMOTE (auto-checks for noise / leakage).

## Hypothesis
The deja-vu engine's historical-analogue conviction (`dv_hit_rate`, `dv_avg_return` from
the nearest fingerprint neighbours) is **orthogonal information** to the trailing-momentum
model (which is at its information ceiling, P1). As an isolated **sleeve** (not a feature —
the 0010/0004 lesson: orthogonal-as-feature overfits the short window), it produces a
thin, low-correlation edge that survives the noise floor.

Skeptical prior: deja_vu was built but never tested; every prior orthogonal-data bet on
this engine's class has been INCONCLUSIVE/KILL. Default expectation = KILL.

## Method
`diagnostics/run_sleeve_walkforward.py --sleeve deja_vu` (cloud, `--reproducible`).
Sleeve = `strategies.deja_vu_sleeve.build_deja_vu_sleeve(ds.features)` — a `RulesSleeve`
over the fingerprint index, validated against the locked honest base on the shared
walk-forward stack, **then through the hardened gate** (CPCV via `run_cpcv_walkforward`,
PBO, DSR at cumulative n_trials, power-checked CI).

**Frozen gate + design (no mid-run tweaks):**
- entry: `dv_hit_rate ≥ 0.55` AND `dv_avg_return ≥ 2.0%` AND `n_matches ≥ 20`; k=50.
- **lookahead guard (mandatory):** matches restricted to analogues whose 14d outcome is
  realized — `exclude_after = query_date − embargo` (embargo = ceil(14·7/5) = 20 cal days),
  NOT the raw query date — and `exclude_ticker` (no same-stock autocorrelation).
- exit: live-parity (stop 2.0×ATR, time 15/45); hold 14d.

## Frozen decision rule
PROMOTE the sleeve to the composer (Part 2B) ONLY IF ALL hold:
1. per-trade after-cost bootstrap **CI-low > 0** AND the mean uplift **> the measured
   noise floor** (`min_detectable_effect` from the CPCV run — V4);
2. **DSR > 0.95** at cumulative n_trials;
3. **PBO < 0.5**;
4. **breadth corr < 0.30** vs the momentum daily-return series (sleeve_contract guard);
5. regime / bad-year (2018/2022/2025) stability — no single-fold dependence;
6. `overfit-skeptic` + `flaw-hunter` agents return no blocking finding.
Else → **KILL** (record the null; do not revisit without new data). No partial credit.

## Result
**Status: REGISTERED — awaiting cloud run.** (Owner executes after the base CPCV noise
floor lands; pandas + the BallTree index build hang locally.)
