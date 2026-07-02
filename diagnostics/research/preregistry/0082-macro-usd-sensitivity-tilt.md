# 0082 — USD/INR-sensitivity as a rank-component tilt: does the first PIT-clean orthogonal feature ADD to the momentum ranker?

- **ID:** 0082. **Status: PRE-REGISTERED** (written BEFORE the run; params fixed here, not to be retuned toward a pass).
- **Registered:** 2026-07-02, BEFORE the run. **TRIAL, 2 arms** → cumulative_n_trials 98 → 100; family_level 51 → 52.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg. Macro from the PIT-clean
  `data/macro_pit.parquet` (`nq.data.macro`, truncation-tested). Primary window **2019-01-01 → 2026-06-30**
  (clean membership); 2017-2026 reported for context only.

## Why this is new (not a relitigation)
This is the ONE genuinely-new, PIT-clean, mechanism-backed orthogonal feature the program has produced. It is
distinct from every prior KILL:
- **NOT a macro entry GATE** (O-001 dual-momentum/regime gate KILLED; market-timing is a §11 KILL) — this is a
  cross-sectional selection *tilt*, not a market-state on/off.
- **NOT conviction SIZING** (0073 KILLED — a mean-preserved size redistribution cannot lift the mean) — this
  changes *which names* are selected, not how much risk each gets.
- **NOT a sole ranker** (O-016 low-vol, the C4 horse-race, the 52-week-high all lose as sole rankers: small IC
  loses as a ranker) — momentum stays the dominant ranker; USD-sensitivity is a small additive component.
- **NOT the price-derived zoo** (0079/O-015: RSI/MACD/… IC≈0) — USD/INR-sensitivity is orthogonal, non-price
  information (how a stock co-moves with the rupee), confirmed real on a clean rebuild in **finding 0017**.
- **Crude is EXCLUDED** — 0017's gate showed crude-beta IC collapsed +0.027 → +0.002 on the clean series (a
  lookahead artifact of the un-audited `macro_data.pkl`). Only USD/INR survives (−0.034 → −0.0295, IR −0.28).

## Hypothesis
Tilting the momentum selection *away from* high-USD/INR-sensitivity names (which underperform over the forward
quarter as the rupee weakens — the confirmed NEGATIVE cross-sectional IC of 0016/0017) raises the risk-adjusted
return of the top-15 book vs momentum alone. Falsifier: ΔSharpe point ≤ 0, OR 2022-26 sub-period ΔCAGR ≤ 0.

## Candidate (FIXED, no sweep — sign taken from the confirmed IC, not fit in-sample)
- Per-(date,ticker) `usd_beta` = trailing rolling-126d (min_periods 63) beta of the stock's daily return on the
  clean `usd_trend` factor (63d trailing ROC of INR=X) — the **identical** construction that carried the
  confirmed IC in 0016/0017.
- `usd_beta_rank` = per-day cross-sectional percentile of `usd_beta`.
- Because the IC is **negative**, the favorable direction is LOW beta: `macro_score = 1 − usd_beta_rank`
  (high score = low USD-sensitivity = favorable). **This sign is fixed by 0016/0017, not chosen in-sample.**
- Blended ranker: `trend_rank ← pctile( trend_rank + λ·macro_score )`, re-percentiled per day. Momentum stays
  dominant (λ small). **Two arms: λ ∈ {0.15, 0.25}.** Same universe / exits / caps; a panel re-ordering only
  (no engine change, no new trades admitted beyond re-ranking), so the golden master is untouched.

## Method
`scripts/run_macro_feature.py` — the `run_lowvol_filter.py` panel-overlay pattern (NOT `evaluate_overlay`,
which is for cfg-level overlays): base = `run_backtest(panel, cfg)`, candidate = `run_backtest(blended_panel,
cfg)` over the SAME full window. Paired 63d block bootstrap (n=5000, seed=12345) of ΔSharpe & ΔSortino
(candidate − base); DSR at n_trials=100; **continuous-slice** 2022-26 via `_subperiod_cagr` on the one full
equity curve (never a fresh-capital re-run — the phantom-gate rule); ≥2019 walk-forward fold-pass. Reports
gross Sharpe/Sortino/CAGR/MaxDD/Calmar + after-tax for candidate vs base.

## Decision rule (pre-committed) — the 7-gate promotion bar
PROMOTE only if ALL: ΔSharpe CI-low > 0 AND point ≥ +0.10, DSR > 0.95, ΔCalmar ≥ +0.05, 2022-26 sub-period
ΔCAGR > 0, ≥2019 fold-pass ≥ 60%, turnover not materially worse, mechanism one sentence. Positive-but-CI-
straddles-0 → **UNDERPOWERED**. ΔSharpe ≤ 0 or 2022-26 ΔCAGR ≤ 0 → **KILL**. A PROMOTE routes USD-sensitivity
to the **forward wall** as a watched feature (a `forward/prereg.md` §7 swap + §10 amendment — owner decision at
the quarterly review), **never** the frozen cfg on this in-sample run.

## Skeptical prior
|IC| ≈ 0.03 is half the base `sma200_slope_63` |IC| 0.062, and the wall is ~34 independent 63-day windows. So
the most likely honest outcome is a **positive-but-small ΔSharpe with a CI that straddles 0 → UNDERPOWERED** —
in which case USD-sensitivity earns a forward-wall watch slot, not a cfg change. It *may* add (unlike the
zero-IC zoo — it is real, clean, orthogonal information), which is the one reason it earns this trial. Do NOT
retune λ or flip the sign toward a pass; the two λ arms are the whole experiment.
