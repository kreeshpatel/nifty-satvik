# 0042 — exit-design validation: are our exit params GOOD, or just bug-free?

- **ID:** 0042. Registered 2026-06-17, BEFORE any arm runs. Cloud-run (pandas/backtests).
- **Type:** parameter-validation / tuning study under the full anti-overfit gate. Default
  outcome is **KEEP STATUS QUO** — an arm replaces a live param only if it clears the gate
  AND sits on a stable plateau (overfit = fragile spike).
- **Numbering:** 0036–0041 are claimed by the `feat/risk-sizing-redesign` (#124) branch
  (0036 sizing, 0040 RR, 0041 reallocation). 0042 is the next free id on `main`.
- **Builds on:** 0022-exit-hold-ablation (base/let_run/let_mid — partial target-vs-let-run);
  EX-C below extends, does not duplicate, 0022.

## Motivation (corrected — NOT "the edge is in the exit")

`FINANCIAL_CORRECTNESS_FINDINGS.md` verified the exit code is **correct** (no look-ahead,
conservative fills). `EXIT_RESEARCH.md` (verified web pass, 2026-06-17) found the design is
**structurally literature-backed** (ATR stop + close-trailing/Chandelier + triple-barrier time
stop; 14d horizon matches the Indian momentum sweet spot; the 2.0× wiring fix is the *right*
end vs the dead 1.5×). **But "good" is unproven on our data** for three reasons, all of which
affect the trustworthiness of every regenerated stat:

1. Exit params (2.0× stop, 6%/3% trailing, d15/d45 time) have **no OOS tuning lineage** (W3).
2. **Target-vs-let-run is genuinely OPEN** — the literature neither condemns nor blesses a
   per-trade profit cap (the "let winners run" principle is about the ~12-month reversal
   horizon, not a per-trade target). AUD-025.
3. **India circuit-lock + illiquidity make backtested fills OPTIMISTIC** (a stop can fail to
   fill on a lower-circuit gap; smallcaps can't be exited in 3 days) — a stats-correctness
   issue, not just optimization.

> **Explicitly NOT motivated by** "the edge is in the exit" (Van Tharp) — verification showed
> that is folklore: his coin-flip confounds exits with position sizing and no rigorous
> entry-vs-exit decomposition exists. This study does not assume exits dominate.

## Hypotheses

- **H-A:** stop_mult forms a **plateau ≥ 2.0** (1.5 worse — too tight); 2.0 is on the plateau.
- **H-B:** trailing (close-based, Chandelier-style) adds risk-adjusted value vs none; 6%/3%
  is on a plateau (not a fragile peak).
- **H-C:** the fixed confidence-calibrated target neither materially helps nor hurts vs
  trailing-only (OPEN — could go either way; this is the AUD-025 decision).
- **H-D:** the d15/d45 hybrid time stop is not dominated by a simpler/longer variant.
- **H-E (measurement):** a non-trivial fraction of backtested exit edge is **optimistic fills**
  on circuit-prone / illiquid names.

## Method

Common base = the locked honest served baseline (`run_served_baseline.py` output, MD1/L2) on
the de-leaked pinned-744 cache, `REPRODUCIBLE_MODE=1`, expanding walk-forward, embargo-45,
**costs ON (delivery STT both legs + brokerage + slippage), India circuit-fill realism ON for
EX-E**. Every arm A/Bs against the SAME base; only the exit policy differs (sim-config-only
override → models byte-identical across arms, per the 0034 `--config-override` harness).

| Arm | Configs | Notes |
|---|---|---|
| **EX-A · stop plateau** | stop_mult ∈ {1.5, 2.0, 2.5, 3.0} | report the *surface*; look for plateau vs spike |
| **EX-B · trailing** | off; (activate, trail) ∈ {4,6,8}% × {2,3,4}% (subset on a coarse grid, refine near 6/3) | vs trailing-off baseline |
| **EX-C · target vs let-run** | A=current (target+trail); B=trailing-only/no fixed target; C=target-only | extends 0022; the AUD-025 decision |
| **EX-D · time stop** | d15/d45 (current); d10/d30; d20/d60; regime-conditional (→ T-REGIME) | |
| **EX-E · fill realism** *(measurement)* | re-price exits with circuit-lock no-fill + ADV/impact on the manipulation-screened universe (#153) | quantifies optimistic-fill drag; no PROMOTE |
| **EX-F · trend-deterioration / signal-decay exit** | add a thesis-break exit that fires when the *entry signal* is invalidated while the trade is flat/underwater — candidate triggers (test individually, not stacked): (i) close < EMA21; (ii) EMA21 crosses below EMA50; (iii) ADX < reeval_min_adx AND close < entry; (iv) MACD bearish cross while pnl ≤ 0; (v) make the d15 re-eval CONTINUOUS (run the existing pnl/adx/rsi check every day, not once at d15). Each gated so it only acts on a flat/losing trade (never cuts a winner — that's the trailing stop's job) | owner-flagged: "a negative trend must stop early to avoid big losses." The risk: whipsaw (we KILLed the 0005 persistence-latch and several react-more ideas). MUST separate thesis-break from noise + clear the gate. |
| **EX-0 · random-exit probe** *(secondary, sanity)* | random exit day ∈ [5,45], same entries, ≥200 seeds | floor check — edge should beat random; NOT a promote gate |

## Validation gate (every promote-bearing arm must clear ALL)

walk-forward → **CPCV (src/validation/cpcv.py) + PBO < 0.5** → manipulation-screened holdout
→ **DSR > 0.95** at cumulative n_trials → per-trade after-cost bootstrap CI-low → cost &
circuit-fill sensitivity → **parameter PLATEAU** (perturbation must not swing the verdict) →
regime + bad-year (2018/2022/2025) stability → `balanced_scorecard` PROMOTE/KILL.

## Frozen decision rule

For each arm, let Δ = pooled ≥2019 paired per-fold Sharpe (candidate − current live param),
bootstrap CI (seed 42, n=2000):

- **Replace a live param ONLY IF:** CI-low(Δ) > 0 **AND** DSR > 0.95 **AND** the winning config
  sits on a plateau (its ±1 grid-neighbours are within noise) **AND** no previously-passing
  regime/bad-year slice regresses. Otherwise → **KEEP the current live value.**
- **EX-C special:** adopt trailing-only (drop the fixed target) only under the same bar;
  default = keep the target (status quo), since the literature is genuinely split.
- **EX-E:** report optimistic-fill drag as a number; if material (> ~1pp CAGR), it gates the
  trust of absolute backtest stats AND feeds the 0041 reallocation gate (which raises turnover).
- **EX-F (two-sided rule — owner's "out in profit AND not too much loss"):** a deterioration
  exit is adopted ONLY IF it **shrinks the left tail** — primary downside metrics: avg loss on
  losing trades, worst-trade %, 5%-CVaR of trade returns, max-loss-per-trade — **WITHOUT**
  degrading the Sharpe/CAGR gate above (i.e. the whipsaw cost must not exceed the tail saved).
  Net per-trade after-cost CI-low must stay > 0. If it cuts the tail but bleeds CAGR (the 0005
  failure mode) → KILL. Report the loss-distribution histogram per arm, not just the mean.
- Default outcome for the whole study = **status-quo exit retained** unless an arm earns its
  replacement. Expect most arms to KILL — that is the gate working.

## n_trials accounting

Promote-bearing configs ≈ EX-A(4) + EX-B(~7 on the refined grid) + EX-C(3) + EX-D(3) +
EX-F(~5 candidate triggers) = **~22 trials**. EX-E (measurement) and EX-0 (fragility probe)
are **NOT trials** (no PROMOTE/KILL).
**The runner MUST bump `diagnostics/research/n_trials.json` cumulative_n_trials by the actual
promote-arm count BEFORE the confirmation run** (currently 46 on `main`; final exact count set
when the EX-B grid is fixed). DSR deflates against the cumulative budget.

## Interaction note

Run **EX-E + the turnover-cost analysis together with the 0041 reallocation A/B** — the India
round-trip cost ceiling (~120–150 trades/yr for ~1% edge) and optimistic-fill drag are the two
forces most likely to decide whether reallocation's extra turnover survives costs.

## Result

**Status: REGISTERED — build COMPLETE, awaiting cloud run.** (Owner executes; pandas backtests
hang locally.) Built + locally verified on `feat/exit-study-0042` (off `main`, fully additive —
**zero changes to any file in a running job's import graph**, so the in-flight LTR 0046 run is
untouched):
- `src/trading/exit_strategies.py` — EX-F deterioration triggers (5, individually dispatchable,
  winner-guarded) + EX-E fill realism (circuit-lock no-fill + sqrt market-impact) +
  `reprice_trade_on_deterioration` post-hoc helper. **19 unit tests pass, mypy --strict clean.**
- `diagnostics/run_exit_study.py` — EX-A/B/C/D as config-only overrides on the UNCHANGED engine
  (`_simulate` is called, never modified); EX-F + EX-E as post-hoc re-pricing of the base trades.
  Reports per-arm trade-IR + per-trade bootstrap CI + win rate + the loss-tail (avg loss / worst /
  5%-CVaR / histogram) the EX-F two-sided gate needs. Compiles; helper imports resolve.
- `.github/workflows/exit-study.yml` — manual dispatch (REPRODUCIBLE_MODE=1, `arms` input).

**Scope of this build (first-pass):** the runner produces the **surface + loss-tail** under
walk-forward. The frozen CPCV + PBO + DSR + plateau confirmation runs on the SURVIVORS (two-bar
discipline, as with the LTR).

---

## SURFACE RESULT (2026-06-19, run 27777585153, 5 folds 2015-2024, REPRODUCIBLE_MODE=1)

First run was INVALID (predict_batch hardcodes a 1.5xATR stop → config overrides were no-ops + a
broken −2%/35%-WR base); fixed by routing config arms through `engine.run(model=adapter)`
(commit c2e45fb). Re-run base is now sane: **287 trades, +2.49%/trade, 58.2% WR, trade-IR 0.210,
CI [+1.14,+3.87]** ≈ the CPCV base 0.191 → trustworthy.

| Arm | Result | Verdict |
|---|---|---|
| **EX-A stop** 1.5/2.0/2.5/3.0 | flat plateau, IR 0.210→0.226, overlapping CIs; tighter → marginally better worst-case (1.5: −23.8 vs 3.0: −28.7) | **KEEP 2.0** (H-A supported: plateau, not fragile) |
| **EX-B trailing** | trailing-**OFF** best (mean +3.31, IR **0.244** vs base 0.210, WR 52%); tighter 4/2 worse → trailing **cuts winners**. CIs overlap → not gate-clearing on the surface | **→ 0047 CPCV confirmation** |
| **EX-D time** | d10/30 & d20/60 **identical** to base (and EX-A *does* respond to cfg, so propagation works) → time stop **rarely binds** | **KEEP d15/d45** (H-D supported: inert lever) |
| **EX-F deterioration** | adx_collapse (4/287) + continuous_reeval (5/287): fire rarely, **neutral** (tail unchanged). macd_bear_cross (127/287): **harmful** (WR 42%, edge CI-low negative). close_below_ema21 / ema21_cross_ema50: **fired 0/287** — `ema21`/`ema50` absent from the per-ticker feature frame, so they did not evaluate (feature-availability, not "no help") | **Provisional KILL** (EMA arms need a feature-lookup fix to fully close) |

**EX-F / the owner's "negative-trend → stop early" mandate — answered:** it is ALREADY satisfied
by the 2.0×ATR stop (base avg loss −8.6%, 5%-CVaR −19.2%, worst −24.5% are stop-governed). A
deterioration overlay either fires on trades the stop already catches (neutral) or fires often and
cuts recoverers (macd: harmful). No trigger shrinks the tail → the two-sided EX-F rule is not met.
Same lesson as the 0005 latch KILL: the disciplined base already does the loss-cut.

**Net 0042 verdict: status-quo exit RETAINED** (stop 2.0 plateau, time inert, deterioration no
help). The single open improvement points the OTHER way — **loosen/remove trailing (let winners
run)** — promoted to the pre-registered **0047** CPCV confirmation. Surface result committed at
`diagnostics/exit_study.json`. Deferred: EX-C (target-disable needs an engine flag), EX-E (fill
realism — pairs with the reallocation round), the EMA EX-F arms (feature-lookup fix).
