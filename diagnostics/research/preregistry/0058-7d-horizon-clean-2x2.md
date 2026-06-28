# Pre-registration 0058 — Clean 2×2 decomposition of the 7d-engine win (gate × horizon)

**Date:** 2026-06-20
**Track:** B (model-internal) — CPCV-backtestable
**Status:** PRE-REGISTERED (frozen below); awaiting owner merge + cloud dispatch
**Holdout type:** paired CPCV on the locked honest base (de-leaked 744 universe), REPRODUCIBLE_MODE=1
**n_trials:** +2 (arms B + C are new configs) → 53 → 55. Bump BEFORE the run. (A = base yardstick, not a
trial; D = the original 0051 arm, already counted.)

## Why
0051 said the 7d engine PROMOTE-CANDIDATE (dSharpe +0.344, DSR 0.952), but the skeptic gate
(overfit-skeptic NOT REAL + backtest-validator CAVEATED, 2026-06-19) overturned it: the 7d arm ran a
**looser entry gate** (min_conf 0.88 / min_ret 5.0) than the 14d base (0.92 / 8.0), so "+0.344" measured a
**7d + loose-gate BUNDLE**, not the horizon. Also: DSR assumed normal returns (skew 0 / kurt 3 → at
realistic fat tails DSR ~0.87); turnover was 1.14× not the registered 2.4×; and 2021 carried ~41% of the
gross edge. This trial isolates the horizon by making the gate a CONTROLLED variable.

## Design (FROZEN — 2×2, exits stay native per model)
| arm | model | entry gate | role |
|---|---|---|---|
| A_14d_tight | 14d | 0.92 / 8.0 | base / yardstick (== locked 0051 14d arm) |
| B_14d_loose | 14d | 0.88 / 5.0 | gate effect on 14d |
| **C_7d_tight** | **7d** | **0.92 / 8.0** | **PRIMARY: 7d vs 14d at the SAME gate** |
| D_7d_loose | 7d | 0.88 / 5.0 | the original 0051 arm |

Only `min_confidence` + `min_predicted_return` are overridden; `prediction_days` / exits stay native to
each model (validated parity-clean). Decomposition: original (D−A) = gate (B−A) + horizon-at-loose (D−B);
the clean horizon test is **(C − A)**.

## Primary metric (ONE) + frozen rule
**Primary:** paired CPCV **portfolio Sharpe** of **C − A** (7d-package vs 14d-package at the SAME tight gate).

**PROMOTE the 7d horizon iff ALL:**
1. (C − A) paired dSharpe **CI-low > 0 AND point > 0.3** noise floor, AND
2. **arm C non-degenerate**: `n_trades_C ≥ 0.5 × n_trades_A` — if the 7d model can't fill the disciplined
   0.92/8.0 gate, the horizon doesn't help AT the gate we actually trade → KILL, AND
3. **DSR(C) > 0.95** with **EMPIRICAL** skew/kurtosis of C's pooled daily returns at **n_trials ≥ 53**, AND
4. no per-group blowup, AND
5. **robust to dropping the 2021 group**: (C − A) dSharpe CI-low still > 0 with 2021 excluded, AND
6. **skeptic-agent clearance** (overfit-skeptic + backtest-validator).

**Else → KILL the horizon claim** — the 0051 win was the gate (B−A captures it), not the hold. Record the
decomposition either way (it tells us whether the lever is "loosen the gate" — itself a separate,
kill-record-laden question — vs "shorten the hold").

## Interpretation guide (pre-stated)
- If **(B − A) ≈ (D − A)** and **(C − A) ≤ 0**: the entire 0051 win was the LOOSE GATE; the 7d horizon is
  inert. (Most likely per the skeptics.)
- If **(C − A) CI-low > 0** and **(D − B) CI-low > 0**: the 7d horizon adds value independent of the gate →
  real; proceed toward shadow.
- If **arm C is degenerate** (fill_ratio < 0.5): the 7d model only works at a loose gate → the lever is
  gate-loosening, not horizon → defer to a separate gate-loosening pre-reg with its own skeptical prior.

## What ships (pre-run)
`diagnostics/run_cpcv_7d_2x2.py` (validated, no blocking bugs) + `.github/workflows/cpcv-7d-2x2.yml` +
n_trials 53→55. No engine/live change (research-only; golden-master untouched).
