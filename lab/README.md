# Strategy Lab (v1)

A train-window playground for the weekly-swing engine: change a config, replay the real engine, read the
book four ways. It describes; it never decides.

## Run

```
streamlit run lab/app.py
```

Streamlit is a local convenience, not a project dependency (CI does not have it). Only `lab/app.py`
imports it. Needs the pinned price caches under `data/` (`ohlcv.pkl`, `ohlcv_backfill.pkl`).
The first run of a new config takes about half a minute to a few minutes; repeats load from `lab_cache/`.

## Rules

1. **Train window only.** Every price series is cut at `2024-06-30` before the engine sees it, and the cut
   is asserted (`nq.lab.runs.assert_within_cut`). Reported stats start no earlier than `2019-01-01`; earlier
   bars are warm-up. The sealed 2024H2+ slice is never loaded.
2. **Multiplicity meter.** Every *distinct* config run appends a row to `lab_runs.jsonl`
   (`config_hash, config, ran_at, sharpe`). The header shows `configs tried: N`, and the Sharpe is shown
   raw beside a Sharpe deflated by N (Deflated Sharpe, `nq.validation.dsr`). Re-running a seen config adds
   nothing - the meter counts ideas, not clicks. It is a lower bound: the program's own `n_trials` is larger.
3. **No live changes.** The engine and `LIVE_*` blocks are imported read-only. Nothing the lab does edits
   `config.py`, `models/`, `forward/` or `results/`.
4. **A promising result leaves the lab as a pre-registered screen**, via `/pre-register`, not as a config
   edit. UNDERPOWERED and KILL are valid outcomes; do not tune toward a pass.

## Config controls

`ext_cap` (skip fills too far above the signal-week SMA; empty = off), `grade_gate` (Grade-A only),
`uncapped` (fill every signal, NAV meaningless), `max_notional_pct`, `max_risk_pct`, `exit`
(`live` = config P scaled exit, `base` = engine default exit), `start` (>= 2019-01-01), `pit_membership`
(off reproduces the committed diagnostics' anchor; on is what the live cron applies - measured 1.03 vs 1.67
Sharpe on the same window, so choose deliberately).

## What each stat means

**Correlation & variance** (pick a Friday; trailing 63 sessions of the names then held)
- *avg pairwise corr* - mean off-diagonal correlation of the held names.
- *effective bets* - `N / (1 + (N-1) rho)`: how many independent bets the N seats really are (1 = one bet).
- *diversification ratio* - weighted sum of vols over portfolio vol (1 = move as one, sqrt(N) = independent).
- *variance share* - each position's share of portfolio variance (sums to 100%), split into own and covariance terms.
- *top eigenvalue share* - the first principal component's share of the correlation matrix.
- *systematic vs idiosyncratic* - share of portfolio variance explained by Nifty (R squared) vs the rest.

**Market exposure**
- *beta / alpha / R squared* - OLS of book daily returns on Nifty daily returns, full period.
- *rolling beta* - same, over a 63-session window.
- *drawdown vs normal-day correlation* - book/index correlation when Nifty is >= 10% under its 252-day high vs otherwise.

**Trade quality** (closed trades only; trades open at the cut are excluded)
- *R distribution* - mean, median, quantiles, skew, win rate of per-trade R.
- *MAE / MFE* - worst / best excursion between entry and exit, in R of the initial risk.
- *capture* - sum R / sum MFE: how much of the best-seen move the exit kept.
- *2R hit rate vs null* - share of trades reaching +2R before the stop price, against the driftless first-passage chance `b/(a+b)` over the same entries; only the excess is the entry's doing.
- *streaks* - longest win / loss run vs the expected longest run under independence, `(ln(n(1-p)) + gamma)/ln(1/p) - 1/2` (Schilling 1990).

**Return & tail**
- *Sharpe* - raw, rf = 0, daily, x sqrt(252). *Sortino* - same, downside deviation about 0.
- *CAGR* - calendar years. *Calmar* - CAGR / |MaxDD|. *Longest drawdown* - consecutive sessions below the running peak.
- *VaR95 / CVaR95* - 1-day historical 5th-percentile return and the mean of returns at or below it.
- *Sharpe CI* - 95% block bootstrap (63-session blocks), so autocorrelation is respected.

Every stat carries `n`; a cell under 30 trades or 126 sessions is flagged **uninformative**.

## Caveats

- The book NAV is a fresh-capital run from the chosen start. It is a description, not a gate number; sub-period
  gates are continuous slices of one full run (`nq.runner.research.evaluate_overlay`).
- The returns panel in the correlation tab uses raw closes (no demerger re-basing), so a corporate-action cliff
  can distort a window's correlation for the affected name.
- The deflation's cross-trial variance is a documented proxy (`1 / n_windows`) until the ledger has many runs.
