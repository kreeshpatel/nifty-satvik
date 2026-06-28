# 0003 — Forward-wall live expectancy of the production model

- **ID:** 0003
- **Registered:** 2026-05-30
- **Holdout:** forward-wall (Holdout #1 in `../HOLDOUT.md`) — the only leak-proof test.
- **n_trials (cumulative):** 1 (the live model is the existing production artifact, not
  selected via this program; this is a clean prospective test of it).
- **Status:** PENDING — accumulating (blocked on pipeline verification, see below).

## Hypothesis

The LIVE production model (`models/v1/`, 79-feature, + the live 0.92 gate / sweep
override) has **positive after-cost per-trade expectancy** on signals it generates
**strictly after WALL_DATE 2026-05-30** — i.e. on data that could not have informed
any model/gate/threshold decision. This is the decisive out-of-sample test the whole
honest-harness effort exists to feed; everything else (0001 unseen-universe, audits)
can only support or kill, never bless.

## Primary metric

**Mean after-cost per-trade return (%)** over post-wall **closed** paper trades
(status ∈ {HIT_TARGET, HIT_STOP, EXPIRED}, signal_date > 2026-05-30), with 95%
bootstrap CI (`bootstrap.bootstrap_metric`). After-cost = the realized paper-fill
return net of brokerage + STT + slippage as recorded by the live pipeline.

## Secondary

WR + CI; realized vs the unseen-universe baseline (0001) and the survivor-backtest
baseline (~+2.5%/trade, Sharpe ~1.4); per-trade vs the modeled cost; observed slippage
vs the backtest's tiered assumption.

## Decision rule (fixed in advance)

- **SUPPORT (the real one):** at ≥30 closed post-wall trades, per-trade mean CI lower
  bound > 0 → the live edge is real out-of-sample.
- **KILL:** at ≥30 closed post-wall trades, per-trade mean CI upper bound ≤ 0 → the
  backtested edge does not survive live; do not deploy real capital.
- **INCONCLUSIVE:** < 30 closed post-wall trades → keep accumulating; report interim
  point + CI but draw no conclusion.

First formal read at N ≥ 30 closed post-wall trades. Given the 0.92 gate fires rarely
(recent live: "0 entry + watchlist"), this may take **months** — that slowness is the
price of a leak-proof test and is expected, not a problem.

## Pipeline prerequisite (must hold or the test is silently dead)

This test depends on the observe-mode cron actually writing + persisting post-wall
data. As of 2026-05-30 the artifacts are NOT yet flowing (no `auto:` cron commit since
the PR #41 merge; `kill_state.json` / `kill_log.jsonl` absent; `portfolio_history.csv`
still a single stub row). Likely benign (cron hasn't run post-merge — wall is today),
but **verify on the first post-merge cron run** that it: seeds `kill_state.json`,
appends observe verdicts to `kill_log.jsonl`, writes a daily `portfolio_history.csv`
row, records any entries in `signals_history.json`, and PUSHES them to GitHub. If any
of these silently fail (the phantom-dep failure class from the kill-system audit), the
forward-wall evidence is lost and this test is void until fixed.

## Result

**Note (2026-05-30):** live is `NIFTYQUANT_STRATEGY=ensemble` (v1 + v1_7d + v1_30d),
confirmed from the cron env — so "the production model" above = the live **ensemble**,
and the 0.92 gate applies to its combined confidence. This test reads the live cron's
post-wall paper trades (the ensemble's outputs), which is correct. Manual run on
2026-05-30 was an idempotent no-op (weekend; last trading day 2026-05-29 already
processed), so the pipeline's first real post-merge execution — and the first chance
to verify the observe artifacts (kill_state.json / kill_log.jsonl / daily
portfolio_history row) — is the next trading day, **2026-06-01 (Mon)**.

_(results appended as trades accumulate — pre-registration above is immutable)_
