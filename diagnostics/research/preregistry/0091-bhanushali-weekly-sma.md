# 0091 — All-SMA correction of the 0089 fully-weekly book (no EMA anywhere)

- **ID:** 0091. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 108 → 109.
- **Anchor / data:** identical cell to 0089 (corrected universe, PIT membership, tiered costs, 2017–2026,
  EQ0 ₹10L). Script `scripts/run_bhanushali_weekly_sma.py`.

## Why this trial exists
Owner spec correction: the strategy should use **simple moving averages everywhere — no EMA anywhere**.
0089 used EMA in two places (the weekly 44-line that drives the signal, and the 20-period runner trail).
This re-runs 0089 with both switched to SMA. One new configuration → one trial.

## The FROZEN spec (two deltas from 0089)

| Param | 0089 | **0091 (this trial)** |
|---|---|---|
| Weekly trend/touch/green line | 44-week **EMA** | 44-week **SMA** (`rolling(44).mean()` on weekly closes) |
| Runner trail line | 20-day **EMA** × 0.96 | 20-day **SMA** × 0.96 |
| Everything else | — | **exactly 0089**: green weekly bounce (low within 7% of the 44-week SMA, close above it, in an uptrend = close > rising 44-week SMA); in-range open entry the next week (buy at the first day whose open is inside the signal week's [low, high]); stop = signal-week low; half at +2R; runner trails the 20-SMA −4%; 13-week cap; all exits decided at the weekly close, filled Monday; 2% risk; no rotation; tiered costs |

Note: the 44-week SMA needs 44 completed weeks to produce a value, so signals begin ~10 months later than
the EMA version (later 2017-early-2018 start). Frozen, expected; pre-2SMA-warmup weeks produce no signal.
Pre-declared sensitivity: erratum-dropped INDIAMART bars.

## Primary metric + diagnostics
**Corrected-universe NET Sharpe** (one number); MaxDD co-reported. References (not gates): 0089
(EMA) +0.626 / +11.8% / −54.3%, 0085 +0.587 / −37.5%, baseline_v1 0.667, TRI +12.6%. Diagnostics: trade
count, win-rate, per-year, DD, Calmar — all vs the 0089 EMA version.

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@109 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
Informational: ΔSharpe / ΔCAGR / ΔMaxDD vs 0089-EMA. No retuning; 44-week SMA, 20-SMA trail, 7% band all
frozen.

## Skeptical prior (honest)
SMA vs EMA on a slow 44-week line is a small change — the SMA lags a touch more and is smoother, so
signals fire slightly later and the set shifts modestly; expect a result in the same neighbourhood as
0089-EMA (Sharpe ~0.5–0.7, DD ~−40s to −50s), inside its wide CI, → UNDERPOWERED most likely. The finding
0032 caveat stands (the weekly-close exits carry the −54% DD regardless of MA type; the DD is an exposure
problem, not an MA-choice problem — finding 0033). This trial is a correctness fix, not a new edge; a large
swing either way would itself be a flag to investigate.
