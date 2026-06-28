# 0048 — capital reallocation (RS-01): reallocate from soured holdings to better live opportunities

- **ID:** 0048. Registered 2026-06-19, BEFORE any run. Cloud-run. **Stage-3 headline lever.**
- **Type:** structural portfolio-mechanics change (NOT same-data alpha). Counts cumulative trials
  at RUN time (bump `n_trials.json` by the actual arm count before the A/B run, not at build).
- **Skeptic gate:** `overfit-skeptic` + `backtest-validator` + `flaw-hunter` must clear before PROMOTE.
- **Clean rebuild** of the RS-01 idea — NOT the dropped #124/0041 branch (pre-gate base, 91 commits
  behind). Gate-native, flag-gated OFF by default, golden-master byte-identical when off.

## The gap (RS-01 headline finding)
Today the portfolio is **first-come**: `backtest_engine._simulate` fills slots in
confidence×return order and, once `len(positions) >= max_positions`, **`break`s** — new candidates
are dropped, and a slot frees ONLY when a held position exits on its own stop/target/time
(`backtest_engine.py:1300`). There is **no reallocation of capital** from a position whose edge has
decayed to a fresh, higher-edge opportunity. This is the owner's core vision and it is absent.

## Hypothesis
When the book is full and a candidate's CURRENT model edge materially exceeds the weakest held
position's CURRENT edge (by more than the round-trip cost), evicting the soured holding and
entering the candidate raises risk-adjusted return. Skeptical prior: India round-trip cost (STT
both legs + brokerage + slippage + tax) + whipsaw may eat the gain (the EX-E turnover ceiling,
~120–150 trades/yr for ~1% edge). Default = KILL.

## Design (frozen)
- **Edge for held positions = the model's CURRENT predicted_return** (re-scored daily on today's
  features), NOT the frozen entry target (0041 learning: frozen-target upside sold winners).
- **Decision (pure):** `src/trading/reallocation.py::reallocation_candidate(candidate, held, cfg)`
  — when full, find the weakest *eligible* held position by current edge; evict it for the
  candidate ONLY IF ALL **4 guardrails** hold:
  1. **cost-covered edge gap:** `candidate.predicted_return − weakest.current_predicted_return >
     realloc_min_edge_gain` where `realloc_min_edge_gain ≥ round_trip_cost_pct` (statutory: STT
     both legs + 2× brokerage + slippage; default conservative);
  2. **min holding period:** `weakest.days_held ≥ realloc_min_hold_days` (anti-churn, default 3);
  3. **donor must be soured, not winning:** `weakest.pnl_pct ≤ realloc_donor_max_pnl` (default
     0% — never evict a green/trending name; that's the trailing stop's job);
  4. **daily churn cap:** `reallocations_used_today < realloc_max_per_day` (anti-overtrading).
- **Wiring:** flag `reallocation_enabled` (default **False** → the `break` path is unchanged →
  golden-master byte-identical). When True, the eviction is atomic (sell donor at today's close +
  full round-trip costs, then enter candidate) at `backtest_engine.py:~1300`.
- **A/B harness:** `diagnostics/run_reallocation_ab.py` — train once per fold, simulate
  reallocation-OFF vs ON on the SAME models (paired), AFTER-COST + after-tax, CPCV path-IR + the
  turnover/cost accounting. Pre-register the exact arms before the run.

## Frozen decision rule
PROMOTE reallocation-ON over OFF ONLY IF ALL hold:
1. paired CPCV trade-IR (or portfolio-Sharpe) uplift **> the 0.041 noise floor AND CI-low > 0**,
   **AFTER** statutory round-trip costs + tax;
2. **DSR > 0.95** at cumulative n_trials;  3. **PBO < 0.5**;
4. turnover stays within a defensible band (report trades/yr; the extra turnover must pay for
   itself — EX-E interaction);  5. regime/bad-year stability (no single-path dependence);
6. `overfit-skeptic` + `backtest-validator` + `flaw-hunter` clear it; golden-master off-path intact.
Else → **KILL** (record the null). Live untouched until PROMOTE → shadow → reversible cutover (R5).

## Result
**Status: COMPLETE — VERDICT: KILL (structurally INERT)** (2026-06-19, run 27808877673, paired CPCV,
REPRODUCIBLE_MODE=1, n_trials=51). Result at `diagnostics/reallocation_ab.json`.

`realloc_on` is **byte-identical to base — 0 reallocated exits across 4,429 trades.** The mechanism
NEVER FIRED. Reason: it only acts when the book is full (`len(positions) >= max_positions=30`), but the
book runs ~27% deployed and **the 30-slot cap never binds** (independently established in 0028) → the
full-book precondition never occurs. **The RS-01 premise is FALSIFIED for this system:** the binding
constraint is NOT slot scarcity (there are always free slots) but **signal scarcity** (the selective
0.92 gate admits few names) + under-deployment. Capital reallocation cannot help a
capacity-UNconstrained portfolio. 

**Disposition:** flag stays OFF; the (golden-master-verified-inert) code stays on `main`. Do NOT revisit
unless the cap is deliberately made to bind (concentration) — and 0028 showed deployment is symmetric
leverage (more return AND risk, not free risk-adjusted return). **Program reframe:** selection (LTR),
exits (0042/0047), AND portfolio mechanics (RS-01) are now all validated/ceilinged on the same data —
the engine is comprehensively at its DATA ceiling (the gate discipline working). The only genuine
ceiling-breakers left: the **forward wall (0003)** + **NEW DATA** (options-OI — see 0049). No skeptic
agents needed for an inert null.
