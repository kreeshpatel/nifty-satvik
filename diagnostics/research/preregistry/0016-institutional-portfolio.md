# 0016 — Institutional portfolio construction (optimizer + risk model)

- **ID:** 0016
- **Registered:** 2026-06-07
- **Holdout:** embargo-45 walk-forward (dev/generation) → unseen-universe →
  forward-wall (confirmation). Reproducible-only verdicts (program rule from
  0012). DSR-gated.
- **n_trials (cumulative):** ~60 at program start (continues the 0012 ledger;
  increment by 1 per walk-forward candidate evaluated — each optimizer
  hyper-config, each factor variant).
- **Status:** IN PROGRESS — Stage 0 (measurement) + Stage A (optimizer) building.

## Context

Program 0012 rigorously KILLed all three *incremental* levers (regime/vol
exposure, mean-reversion sleeve, delivery-% feature): the per-stock
price-momentum model is at its **information ceiling**, and rules-based
portfolio tweaks don't add risk-adjusted edge. This program changes the
**architecture**, not the signal: cross-sectional alpha → factor risk model →
constrained portfolio **optimizer** → execution. Governing math — the
Fundamental Law of Active Management, `IR ≈ IC · √breadth · TC`. The bet is on
raising the **transfer coefficient** (TC) and controlling risk with **IC held
flat**, not on new alpha.

## ⚠️ Embargo correctness fix (lands first)

`run_walk_forward.py::main` never passed `embargo_days` to
`expanding_window_folds`, so every prior walk-forward (incl.
`baseline_wf_2026_06`) ran embargo=0 — a ~45-day forward-label leak across each
train/test boundary. Fixed (default 45). **The baseline must be re-locked under
embargo=45** before it gates any Stage A candidate. A comparison run
(`baseline_wf_2026_06_embargo45`) quantifies the leak's inflation; the locked
control is not overwritten until the user approves the re-lock.

## Stage 0 — Measurement (DESCRIPTIVE, no promote/kill)

`src/validation/factor_metrics.py` + `diagnostics/run_factor_metrics.py`:
per-fold OUT-OF-SAMPLE IC / IC-IR of the live architecture across embargo-45
folds. This is a **baseline measurement**, not a gated experiment — it does not
consume a DSR trial. It establishes:
  * `ic_alpha` — IC of `predicted_return × confidence` (the score Stage A ranks
    on). The number the optimizer must NOT degrade.
  * `ic_return` — IC of the raw return head (diagnostic).
Effective breadth + the heuristic's baseline TC are measured in Stage A (they
need the returns covariance + realized weights).

## Stage A — Portfolio engine (THE gated decision)

`portfolio_simulator.py` (weekly rebalance, daily mark-to-market, reusing the
backtest engine's execution-cost primitives) + `risk_model.py` (Ledoit-Wolf
covariance + light factor exposures) + `portfolio_optimizer.py` (CVXPY
mean-variance with long-only / position-cap / sector-cap / ADV-cap / turnover +
Almgren cost penalties; **HRP** robustness sibling). α = cross-sectional rank of
the existing ML score.

- **Control:** the top-N heuristic (current `backtest_engine` block), run
  through the SAME daily-simulator + costs, embargo-45, REPRODUCIBLE_MODE=1.
- **Candidate:** the optimizer (MV, then HRP), same folds, same costs, same seed.
- **Decision rule (PROMOTE a backend):** ALL of —
  (a) balanced composite (`run_balanced_scorecard.py`) > 0 vs the heuristic;
  (b) Deflated Sharpe > 0.95 at the current cumulative `n_trials`;
  (c) **TC up** vs the heuristic with **IC flat** (the Fundamental-Law thesis —
      a TC gain with degraded IC is not the win we claimed);
  (d) MaxDD ≤ heuristic MaxDD (the honest win is risk reduction, not return);
  (e) holdout (unseen-universe) does not contradict.
  Any breach → KILL that backend. If MV fails but HRP passes, ship HRP.
- **Honest prior (~55-65%):** win = **lower MaxDD + steadier Sharpe at similar
  return + real capacity**, NOT higher CAGR. A large return jump → suspect a
  covariance lookahead or capacity leak; investigate before celebrating.
- **#1 correctness risk:** the survivorship/membership ↔ rebalance interaction —
  the optimizer must only hold index members on date *t* and force-liquidate
  (booked sell leg) the week a name exits the index. Built test-first.

## Product note

The optimizer produces fractional rebalance weights, not the discrete
`signals_today.json` the user product wires. Per the locked decision, Stage A
runs for **own track-record / whitepaper first**; the user-facing product is
unchanged until the institutional book is proven on the forward wall.

## Result

**2026-06-07 — Embargo fix landed + baseline RE-LOCKED at embargo=45.** PR #68
merged. The embargo=45 comparison run (reproducible, bear-block, overlay off —
identical params to the original lock, only the purge differs) showed the
embargo=0 leak's impact is **small**:

| metric | embargo=0 (leaked, prior lock) | embargo=45 (honest, new lock) |
|---|--:|--:|
| mean Sharpe | 1.364 | **1.311** (−0.053, ~4%) |
| mean CAGR | 0.510 | 0.493 |
| mean WR | 0.510 | 0.492 |

Per-fold reshuffles (2018 −0.28→−0.82, 2023 −0.01→+1.26, 2024 1.21→0.28, 2026
2.99→2.20) but the net is a modest honest reduction — the leak did **not**
manufacture the edge, so the 0012-program KILL verdicts STAND.
`diagnostics/research/baseline_wf_2026_06.json` is now the embargo=45 control
(the embargo=0 version is in git history at this file's prior revision). Stage A
gates against this honest baseline.

**2026-06-08 — Stage A FIRST run = KILL (confounded).** Ran portfolio-backtest.yml
MV (run 27100436530) + HRP (27100437245) vs the in-run top-N control,
reproducible. Headline looked strong (MV Sharpe 1.21→1.39, CAGR 0.40→0.84) but
hit the pre-committed "big return jump → investigate" trap. A 5-agent adversarial
verification (KILL_BUT_CONFOUNDED_RETEST, conf 0.86) found: **(d) MaxDD worse in
10/10 folds** (mean −0.33 vs −0.18, breaches the coded DD floor) → KILL decisive.
The "win" was NOT alpha: (1) EXPOSURE CONFOUND — candidate always ~100% invested
(fully_invested=True) vs cash-gated + bear-blocked control; (2) SAME-BAR
LOOKAHEAD LEAK — `rets.loc[:d]` inclusive of d + same-bar fill; (3) TC only
0.22/0.29 (deploys more capital, doesn't transfer signal better; gave up half of
2020).

**FAIR RE-TEST — PRE-REGISTERED (2026-06-08, params fixed BEFORE the run).**
Fixed all three confounds in `portfolio_simulator.py` + `make_portfolio_backtest_fn`
(PR pending). The fair-test configuration, locked here before looking at OOS:
- **Execution**: T+1-open fills (decision at d's close → fill at d+1 open),
  matching the control's clock — removes the same-bar leak. Covariance through d
  is now legitimate (known at the decision moment, filled later).
- **Exposure-match**: candidate's universe GATED to the heuristic's primary entry
  gate (confidence ≥ 0.92 AND predicted_return ≥ min_predicted_return) +
  `fully_invested=False` (sum(w)≤1, per-name cap 12%) so it holds CASH on the same
  selective days the heuristic does. (Bear-block / momentum sub-filters not
  replicated — second-order to the binding 0.92 gate.) A gross-exposure series is
  reported to confirm parity.
- **λ scale**: covariance annualized (×252) so risk_aversion is O(1–50).
- **PRIMARY config — MV**: `risk_aversion=5`, `turnover_penalty=0.01`,
  `rebalance_every=5`, gate on, fully_invested=False, embargo=45, reproducible.
  (HRP can't hold cash — it normalises to sum(w)=1 — so it is NOT a clean
  exposure-matched candidate; if run, it is "100% invested within the gated
  names" and reported with that caveat. MV is the decisive fair test.)
- **Decision rule unchanged** (a)–(e); MaxDD-floor first. Honest expectation:
  with exposure matched + the leak removed, most of the +110% CAGR collapses; the
  question is whether MaxDD now ≤ heuristic with Sharpe/TC up. n_trials += 1 (MV
  fair) [+1 if HRP fair run].

**2026-06-08 — Stage A FAIR re-test = KILL (decisive, clean). PROGRAM LEVER CLOSED.**
After fixing all three confounds (T+1 fills, exposure-match via gate +
fully_invested=False, annualized-cov λ; PR #71) and a gated-score KeyError
(pivot drops all-NaN date rows → reindex fix), the fair MV run (run 27103007390,
λ=5, τ=0.01, reproducible, embargo=45) vs the in-run top-N control:

| metric | control (top-N) | candidate (optimizer) |
|---|--:|--:|
| mean Sharpe | 1.303 | **1.993** (+53%) |
| Sharpe std (consistency) | 2.110 | **1.512** (steadier) |
| mean CAGR | 0.537 | **0.453** (−15.7%) |
| mean MaxDD | −0.173 | −0.177 (~tied) |
| worst MaxDD | −0.386 | −0.525 (deeper tail) |
| **mean TC** | — | **0.855** (was 0.22 confounded) |

The transfer-coefficient thesis **partially worked**: TC 0.86 (signal faithfully
transferred), mean Sharpe +53%, consistency up, and the BAD years were repaired
(2018 −1.54→+0.39, 2019 −0.46→+0.26, 2025 −0.85→+0.78 Sharpe — a genuine
distribution reshape, NOT a scaling artifact). **BUT the pre-registered
`run_balanced_scorecard` gate KILLs** (composite +0.11 but floors fire):
- **`mean_cagr_regression` FAIL** — CAGR −15.7% (floor −10%): the diversification
  gives up the momentum signal's concentrated big-year upside (e.g. 2021 CAGR
  +2.36→+0.74). DECIDING criterion.
- **DSR 0.264** (advisory, n_trials=62) — the Sharpe gain is NOT deflation-robust.
- mean-DD floor OK (within 1.10×), but worst-case tail DD deeper (2019 −0.53).

**Conclusion:** the institutional portfolio-construction layer (optimizer + risk
model), fairly tested, does **not** beat the balanced gate on this momentum
signal — it's a real Sharpe-smoother that trades away too much CAGR and isn't
deflation-robust. Consistent with the entire 0012/0016 kill-record: the signal
is at its ceiling; construction can't rescue it. Further λ/exposure tuning to
chase a pass would be p-hacking against DSR 0.26 — NOT pursued. **Stage A lever
CLOSED (fair KILL).** n_trials → 63. Remaining institutional lever = Stage C
(PIT fundamentals → orthogonal value/quality alpha), per the roadmap.

_(further results appended below; immutable fields above never edited)_
