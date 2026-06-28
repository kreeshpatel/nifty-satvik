# 0045 — contagion sleeve: does cross-stock lead-lag flow add orthogonal edge?

- **ID:** 0045. Registered 2026-06-17, BEFORE any run. Cloud-run. Stage-4 Phase-2 lever **L-CG**.
- **Type:** orthogonal-signal SLEEVE trial (1 arm). Counts **+1** cumulative trial — bump
  `diagnostics/research/n_trials.json` before the verdict run.
- **Skeptic gate:** `overfit-skeptic` + `flaw-hunter` must clear the result before PROMOTE.

## Hypothesis
Cross-stock contagion (`src/data/contagion.py`) — "when leader A makes a big move, its
historical followers B/C tend to move with it in 1-3 days" — is **orthogonal** to the
single-stock trailing-momentum model (at its information ceiling, P1). As an isolated
sleeve, the multi-leader confirmation signal produces a thin low-correlation edge that
clears the noise floor. Skeptical prior: built but never tested; lead-lag is often
regime-unstable → default expectation = KILL.

## Method
`diagnostics/run_sleeve_walkforward.py --sleeve contagion` (cloud, `--reproducible`).
Sleeve = `strategies.contagion_sleeve.build_contagion_sleeve()` (a fit-per-fold
`ContagionSleeve`), validated vs the locked base on the shared walk-forward stack, then
through the hardened gate (CPCV via `run_cpcv_walkforward`, PBO, DSR at cumulative
n_trials, power-checked CI over reconstructed paths).

**LOOKAHEAD GUARD (mandatory, the L-CG-specific one):** `ContagionMap.build()` has no
point-in-time filter, so the influence graph is **rebuilt per fold on TRAIN data only**
(`requires_training=True` → the harness calls `fit(train_panel)` each fold). The
recent-return cross-section at predict time uses only same-/prior-date closes (1d
returns ≤ the query date). Both verified by test + the flaw-hunter before any verdict.

**Frozen gate + design (no mid-run tweaks):**
- entry (long-only): `contagion_signal ≥ 0.60` AND `n_active_leaders ≥ 2`; a leader
  counts only if it moved `≥2%` (1d) AND has `≥60%` historical directional hit-rate.
- target `+5%`, stop `2.0×ATR` (live parity), hold 14d.

## Frozen decision rule
PROMOTE to the composer (Part 2B) ONLY IF ALL hold (identical bar to 0044):
1. per-trade after-cost CI-low > 0 AND mean uplift > the measured noise floor
   (`min_detectable_ir` from the CPCV run — currently ~0.13);
2. DSR > 0.95 at cumulative n_trials;  3. PBO < 0.5;
4. breadth corr < 0.30 vs the momentum daily-return series AND < 0.30 vs the deja_vu
   sleeve (sleeves must be mutually orthogonal too);
5. regime / bad-year (2018/2022/2025) stability;
6. `overfit-skeptic` + `flaw-hunter` return no blocking finding.
Else → **KILL** (record the null). No partial credit.

## Result
**Status: REGISTERED — awaiting cloud run.** (Owner executes; pandas + the per-fold
graph build hang locally.)
