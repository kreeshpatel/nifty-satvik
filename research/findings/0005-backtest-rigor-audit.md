# 0005 — Backtest-rigor audit: short-horizon contamination + harness significance gaps

- Status: **AUDIT (5-agent, code-verified).** Two real fixes found; no past verdict overturned.
- Date: 2026-07-01   Prompted by: owner ("are we backtesting smartly? are some kills old short-horizon data?").

## A. Short-horizon contamination — VALID concern, but changes no conclusion
The v1 predecessor was a SHORT-HORIZON model (7–14d hold, 79-feature LightGBM, `fwd_max_14d` labels) —
a different strategy. Its results do NOT transfer to the 63d rule. Classification:
- **Trust (long-horizon 63d, `sma200_slope_63`, `portfolio.simulate`, dataset-pin-20260701):** 0066-0075,
  C4/finding 0001, 0071, A5, C2/finding 0002, C3/finding 0004, registry O-001…O-012 / U / S / R / SL.
- **Reference-only (v1 7-14d — do NOT cite as binding 63d priors):** 0001-0018, **0020, 0021, 0022**,
  0023-0031, 0034, 0035, 0044, 0046-0058, 0063, 0065.
- **A5 / C2 / C3 all SURVIVE** stripping the v1 priors — each rests on its own pinned-baseline_v1 63d
  measurement; 0020/0021 were cosmetic framing, not load-bearing. (See finding 0002/0003/0004.)
- **One real hygiene item:** do NOT let 0022 ("let winners run is dead", v1) transfer to the 63d
  Stage-D conviction-EXIT lead. That is genuinely untested at 63d (0071 is its correct LH analogue).

## B. Are we rigorous? — code-verified scorecard
**Strong (keep):** 63d overlapping block bootstrap (block=one cycle); paired `bootstrap_delta` CI-low>0;
correctly diagnosing CPCV as DEGENERATE for a frozen rule and using the block bootstrap instead;
pinned sha-verified data + PIT membership + seed; golden-master byte-exact; pre-reg + `n_trials` + DSR;
1x/2x/3x cost sweep + ±20-50% parameter-plateau discipline.

**Present-but-weak (all confirmed against source):**
- **DSR uses daily n, not effective n** — `research.py:84` passes `n_observations=rets.size` (~2300
  daily) when independent 63d windows are only ~20-40. DSR z-stat scales `√(n-1)` → significance
  OVERSTATED. *The single most pervasive optimism in the harness.*
- **C2 IC null is anti-conservative** — `factor_ic.py:47` `rng.shuffle` treats overlapping/clustered
  63d trades as exchangeable → C2's p=0.043 is optimistic.
- **DSR `sharpe_variance` is a proxy** — `research.py:81-82` uses the bootstrap CI width (within-arm
  sampling variance), not the Bailey-LdP cross-trial Sharpe dispersion.
- **`n_trials=82` assumes independent trials** — most are correlated re-probes → over-deflates the
  other direction (the two n-errors offset but on different decisions; fix both).
- **The "7-gate bar" is ~3 gates in code** — `evaluate_overlay` computes only ΔSharpe-CI + DSR +
  noise_floor; ΔCalmar / 2022-26 / fold-pass / turnover applied MANUALLY per pre-reg.
- `run_cpcv.py` mis-named (no CPCV path-distribution produced anywhere); CI lint/type advisory (`|| true`).

**Missing:** PSR + Minimum Track Record Length (is 9y even enough for Sharpe 0.667?); canonical
effective-N; portfolio-level randomized-entry null; per-name/per-year/drop-1-block jackknife module;
Ulcer Index; mechanized sub-period engine; full-ENGINE golden master (current covers panel only).

## C. Adopt (prioritized) — fits a FROZEN rule with overlapping trades
- **P0:** (1) one canonical effective-N (`n_days/63`) fed to DSR `n_observations` (`research.py:84`);
  (2) block/date-grouped permutation in `factor_ic.py:47` + re-run C2 under the correct null.
- **P1:** PSR + MinTRL in `nq/validation/` (emit from `evaluate`); fix DSR `sharpe_variance` + sync the
  dsr.py 79→82 docstring; reusable jackknife (per-year / drop-1-block); mechanize the rest of the 7-gate
  bar into `evaluate_overlay`.
- **P2:** portfolio-level randomized-entry null (does `sma200_slope_63` beat random top-15 at equal
  turnover?); Ulcer/UPI in `metrics`; Harvey-Liu haircut Sharpe (cross-check).
- **P3:** implementation-risk fill sweep; full-engine golden master.

**Cargo-cult — do NOT adopt (frozen-rule mismatch):** CPCV path-distribution / PBO on the frozen rule
(degenerate); vectorbt as a 2nd backtester (parity risk); tick/Lean event engine (overkill at 63d);
GAN synthetic markets (unauditable); naive per-trade Monte-Carlo reshuffle (destroys 63d serial
structure); full walk-forward RE-optimization of the shipped arm (re-introduces overfitting).

## D. Top action
Fix P0 first — effective-N + the block-grouped IC null — then **re-run C2**: confirm the conviction
IC 0.0559 survives a CORRECT null before any further conviction work leans on it. Then refresh the
stale `skills/backtest-rigor` to long-horizon-only + baseline_v1 (it still anchors baseline_v0 26.1% +
v1 paths). Full agent briefs: workflow run wf_fa141676-4c6.

## E. P0 DONE (2026-07-01) — and it changed a result
- **`nq/runner/research.effective_n`** = max(2, n_days/63); `_dsr_from_bootstrap` now feeds the DSR
  the EFFECTIVE sample (~34), not the raw daily count (~2162). Lowers every DSR (more conservative);
  verdicts unchanged (A5/C3 KILLs stay KILL; baseline_v1's recorded DSR 0.246 was optimistic and is
  now lower — it was never a promote decision).
- **`nq/validation/factor_ic.permutation_ic_pvalue(block=…)`** = block permutation preserving the
  serial structure of overlapping trades; `run_conviction_c2.py` time-orders trades + passes
  block ≈ trades/63d-window and reports both nulls.
- **OUTCOME: C2 downgraded SUPPORT → INCONCLUSIVE** (p_block 0.058 vs the old anti-conservative IID
  0.043/0.051). The audit's #1 fix immediately corrected a borderline result — exactly its purpose.
  See finding 0002 CORRECTION. 89 tests green.
- Still open (P1+, not done): PSR + MinTRL; DSR `sharpe_variance` proxy; mechanize the 7-gate bar;
  jackknife module; randomized-entry null; refresh the stale rigor skills.
