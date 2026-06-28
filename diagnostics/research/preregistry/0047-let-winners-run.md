# 0047 — let-winners-run: is the trailing stop cutting winners? (CPCV confirmation of the 0042 surface)

- **ID:** 0047. Registered 2026-06-19, BEFORE the CPCV run. Cloud-run. Stage-3 (exit policy).
- **Type:** parameter-confirmation. Counts **+2** cumulative trials (trailing_off + trailing_8_4);
  n_trials 48 → 50 BEFORE the run. Default outcome = **KEEP the live 6/3 trailing.**
- **Builds on:** the 0042 walk-forward surface. The ONLY positive exit signal there was
  trailing-**OFF**: mean +3.31 / trade-IR **0.244** vs the live 6/3 trailing's +2.49 / 0.210
  (256 vs 287 trades, WR 52% vs 58%). The trailing stop appears to **cut winners** (the AUD-025
  "let winners run" tension). The surface CIs overlapped → it did NOT clear the gate; this run is
  the hardened confirmation.

## Hypothesis
The close-based 6%/3% trailing stop exits trends prematurely, costing right-tail return that
outweighs the volatility it saves. Loosening (8/4) or removing it lifts risk-adjusted return.
Skeptical prior: the surface delta (+0.034 IR) is within the ~0.041 noise floor → likely KEEP.

## Design (frozen)
`diagnostics/run_cpcv_exit.py` (dispatch `cpcv-exit.yml`). Same CPCV harness as the locked base
(45 splits / 9 LdP paths, window 2015-2024, embargo 14). The PredictionModel is trained ONCE per
split (exit cfg does not affect training) and every arm is simulated on the SAME models via
`engine.run` with a different exit cfg → byte-identical models, a clean PAIRED A/B. Arms (PINNED,
no sweep): **base** (live 6/3), **trailing_off** (`trailing_activate=999`), **trailing_8_4**
(looser — the plateau check). Per-path PAIRED delta Δ = arm trade-IR − base trade-IR (same paths).

## Frozen decision rule
ADOPT the looser/no trailing over the live 6/3 ONLY IF ALL hold:
1. **paired CI-low(Δ trade-IR vs base) > 0** (95%, over the 9 reconstructed paths);
2. **DSR > 0.95** at cumulative n_trials (=50);
3. **plateau** — BOTH trailing_off AND trailing_8_4 improve over base (a lone spike = overfit);
4. no regime/bad-year regression vs base.
Else → **KEEP the live 6/3 trailing.** A pass is a CANDIDATE — it then needs the skeptic agents
(`overfit-skeptic` + `backtest-validator`) + the manipulation-screened holdout before any live change.

## Result
**Status: COMPLETE — VERDICT: KEEP the live 6/3 trailing** (2026-06-19, run 27785718183, 45
splits / 9 paths, REPRODUCIBLE_MODE=1, n_trials=50). Result at `diagnostics/cpcv_exit.json`.

| Arm | trade-IR | paired Δ vs base | Δ CI | exp%/trade | gate |
|---|---|---|---|---|---|
| base (6/3) | +0.2042 | — | — | +2.62 | — |
| trailing_off | +0.1941 | −0.0101 | [−0.023, +0.003] (straddles 0) | +2.77 | ✗ |
| trailing_8_4 | +0.1978 | −0.0064 | [−0.012, −0.001] (all-negative) | +2.64 | ✗ |

Base reproduces (+0.204 ≈ locked 0.191). **Neither candidate beats the live trailing on
risk-adjusted return; trailing_8_4 is significantly worse. plateau=False → KEEP.** The walk-forward
surface signal (trailing-off IR 0.244) was overfit to those folds; the paired 9-path CPCV test
corrects it. **Nuance:** trailing-off DOES raise raw expectancy (+2.77 vs +2.62 — "let winners
run" captures more return) but LOWERS risk-adjusted IR — removing the stop adds enough
volatility/drawdown to wash out the extra return. The trailing stop earns its keep. Exit design is
now fully validated end-to-end (0042 + 0047); no exit lever improves it. Stage-2 + exits closed →
Stage-3 = capital reallocation (0048).
