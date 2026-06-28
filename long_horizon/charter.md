# `long_horizon/` — program charter

A from-the-ground-up **3-month (≈63 trading day) systematic equity strategy** for NSE
Nifty-500, built as an isolated package. This is a *separate program*, not a variant of
the live 14-day model.

## Why this exists

The 14-day model is at its **information ceiling for that horizon** — its 79 features are
all ≤50-day momentum derivatives, and every short-term tweak has been killed by honest
validation. The fix is not longer windows bolted onto the short learner. A 3-month hold is
a *different strategy*: different return drivers (value/quality fundamentals start to pay,
earnings drift, sector rotation), a different risk/exit/sizing regime, and a different
statistical regime (a 63d hold yields only ~4 non-overlapping trades/stock/year).

So we build it properly and **data-first**: research the drivers → compose real data sheets
→ **derive every operating value from the data** → vet features methodically → *then*
validate. The earlier `v2_long` work inverted that order (rushed to validation on a guessed
gate before the model was built); this program corrects it.

## Governing methodology

1. **Never just pass/fail a method.** Every experiment ends in a *root-cause readout*:
   the mechanism (why it works/fails, not just the metric) and the *next setup* the stats
   frame. "Underpowered" is a first-class outcome, never massaged into a pass.
2. **Reuse the architecture, change every value.** The short-term system's abstractions
   encode years of fixed mistakes — import them. But every *number* (risk, drawdown, R:R,
   win-rate, stop, target, hold, gate) is re-derived for 63d from the data, never inherited.
3. **Financial-modelling methods first.** A classical, interpretable multi-factor composite
   is the baseline and the permanent benchmark. ML is allowed only to add what it *provably*
   contributes on top — if it can't beat the transparent composite, we ship the composite.
4. **Honest data.** Anything that can't be reconstructed point-in-time (news sentiment, the
   LLM industry analyst) is **forward-only** — excluded from the backtest and the model
   contract, used only as a live overlay validated on the forward wall.

## Isolation invariants (non-negotiable)

- The live 14d model, the ensemble, `V1_FEATURES` (frozen at 79), and the golden master are
  **never touched**. `models/long_horizon/` is **never auto-loaded** by the live cron.
- This package **imports** horizon-agnostic kernels from `src/`; it **never writes** to
  `src/`, `models/v1/`, or the golden-master surface.
- The backtest's exit decision is the shared `engine.exit_logic.decide_exit` (the same function
  the live signal tracker uses) — so backtest and live exit byte-identically by construction
  (exit-parity unification, 2026-06-26). `decide_exit` is config-driven and unchanged by this
  package; the v1 golden master is unaffected (it pins the v1 engine, not `decide_exit`).
- Rollback = delete the package. No production state changes unless an env var is
  deliberately flipped after a clean, pre-registered promote.

## Reuse map (import, don't copy)

| Reused from `src/` (horizon-agnostic) | Defined here (horizon-specific) |
|---|---|
| `strategies/base` (Strategy/Signal/SignalTier), `models/base` + `lightgbm_two_head` | feature contract, labels + barriers, target-calibration buckets |
| `data/data_store` (OHLCV download/clean/cache + indicator kernels) | the master PIT data-sheet composition |
| `engine/backtest_engine` + `engine/exit_logic.decide_exit` (config-driven) | **all** config values (gate, stop, target, hold, sizing) |
| `trading/{position_sizer,risk_manager,trade_planner,execution_model}` | the value-derivation that *produces* those values from data |
| `validation/{cpcv,overfitting,bootstrap,power,factor_metrics,null_test}` | the research-bot orchestration + root-cause readouts |
| `engine/target_calibration` | re-fit at 63d |
| pre-registration discipline (`diagnostics/research/preregistry`, `n_trials.json`, `HOLDOUT.md`) | the long-horizon pre-regs |

## The three-way verdict (every validation)

- **PROMOTE-CANDIDATE** — clears the full pre-registered gate (paired-CPCV dSharpe CI-low>0
  & point>noise floor; deflated Sharpe>0.95 at cumulative n_trials; ≥ trade floor & every
  path traded; no per-group blow-up; drop-best-group + adjacent-pair jackknife>0). Authorizes
  only a flag-gated, golden-master-safe shadow + forward-wall accrual — never a live change.
- **UNDERPOWERED** — positive point estimate but below the minimum-detectable-effect or DSR
  bar on the thin sample. Reported as exactly that. Not shipped; not killed.
- **KILL** — point estimate ≤ 0, degenerate, blows up, or a single group is load-bearing.
  Followed by a root-cause readout of *why*, and the next setup it frames.

## Phased build (data-first)

0. **Charter & scaffold** — this package; re-home the `v2_long` scaffolding.
1. **Driver research** (measurement, no trial) — IC-decay curves for every candidate; the
   ranked dossier of what's horizon-live at 63d.
2. **Data composition** — the master PIT panel + 63d labels (incl. max-adverse-excursion).
3. **Research-bot feature vetting** — the frozen `LONG_HORIZON_FEATURES` contract.
4. **Model** — composite baseline + hybrid (factor scores → reduced-capacity two-head).
5. **Strategy & value derivation** — every operating value derived from the 63d excursion
   distributions and written to `config.py` with a data provenance comment.
6. **Full walk-forward + forward-wall holdout** — the pre-registered five-gate readout.

See `~/.claude/plans/we-havent-even-composed-swift-gray.md` for the full program plan.
