# 0079 — Technical-signal battery: do chart patterns / oscillators / breakout / volume have 63d edge?

- **ID:** 0079 (Entry-Signal Arc — the long-horizon test of the technical-analysis zoo). Owner-approved 2026-07-02.
- **Registered:** 2026-07-02, BEFORE the run.
- **Two stages:** (A) **IC screen = MEASUREMENT, no trial cost** (per research-log: pure rank-IC diagnostics
  make no trade decision) over a comprehensive battery; (B) **backtest** the IC-meaningful + canonical
  signals as sole-ranker swaps = **TRIALS**, `n_trials` incremented by the arm count BEFORE the backtests.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg, corrected universe, 2017-2026.

## Motivation (the correction that opened this)
The registry's technical kills are **v1, not long-horizon**: chart-structure features = pre-reg 0004
(**V1_FEATURES 84f model**, INCONCLUSIVE); the "RSI/MACD Sharpe<0.5 / −60..−81% DD" numbers are
short-horizon/v1 (our LH DD is −46%). The LH registry O-005 (reversal) is a **reasoned** reject, not a
63d harness test — and §11's own **re-open condition for reversal is "IC evidence on the 63d label
specifically."** This provides exactly that. Chart-structure/breakout have **no** LH kill → genuinely new.

## Hypothesis
If any technical / chart / oscillator / volume signal carries 63d cross-sectional predictive power
comparable to `sma200_slope_63`, it will show a **meaningful, consistent rank-IC vs the forward-63d
return** and beat-or-tie the slope as a sole ranker (C4 protocol). Falsifier: every technical signal
has **weaker IC than the slope AND loses as a sole ranker** → confirms the slope and **closes the
technical-signal family at 63d** with actual evidence (not a v1 inference).

## Battery (comprehensive; trailing-only, PIT-safe; ranked cross-sectionally each day)
- **Momentum/trend:** ROC 21/63/126, 12-1 (mom_252_21), close/SMA50−1, close/SMA200−1, MACD histogram.
- **Oscillators (BOTH directions — momentum tilt AND reversal tilt):** RSI-14, Stochastic %K-14,
  Williams %R-14, CCI-20, Bollinger %b(20,2).
- **Breakout / structure:** 52-week-high proximity (close/252d-high), Donchian-63 position, 20d-vs-63d
  breakout.
- **Volume:** volume ratio (vol / 20d avg), OBV-63 slope, MFI-14.
- **Volatility:** realized-vol-63 (low-vol tilt), ATR%-63.
- **Benchmark:** `sma200_slope_63` (the incumbent) computed the same way, so IC/backtest are like-for-like.

## Method
**Stage A (IC screen):** per day, Spearman rank-IC of each signal vs the forward-63d return over the
eligible panel; report mean IC, IC-IR (mean/std), sign consistency, vs the base signal's IC. Both signal
directions for oscillators. No trades, no trial.
**Stage B (backtest):** each signal whose |mean IC| ≥ ~0.5× the base's IC, plus the canonical TA names
(RSI both ways, MACD, 52w-high, breakout) regardless, run as a sole-ranker swap (inject as the rank
column) through `simulate`; paired 63d block bootstrap ΔSharpe/ΔSortino, DSR at the cumulative count,
continuous-slice 2022-26, ≥2019 fold-pass, turnover, after-tax. `scripts/run_technical_battery.py`.

## Decision rule (pre-committed) — the 7-gate promotion bar; per signal
PROMOTE only if ALL: ΔSharpe CI-low > 0 AND point > 0.30, DSR > 0.95, ΔCalmar ≥ +0.05, 2022-26 (sliced)
ΔCAGR > 0, ≥2019 fold-pass ≥ 60%, turnover ≤ +30%, one-sentence mechanism. Positive-but-CI-straddles-0 →
UNDERPOWERED. Else KILL. **Kill criteria (≥2, pre-committed):** (i) sole-ranker ΔSharpe CI-low ≤ 0 →
KILL; (ii) 2022-26 sliced ΔCAGR ≤ 0 → KILL. A frozen-cfg ranker change would be the heavy path (WF
re-derivation + owner sign-off) — this run is EVIDENCE only.

## Pre-screen
Mechanism per signal is a one-line TA rationale; parameters are the standard indicator settings (no
decimal tuning); all trailing-only (no lookahead — leakage-audit §1); >30 opportunities/yr (whole-
universe ranker). Skeptical prior: C4 already showed alt-momentum formulations (12-1/6-1/Donchian) LOSE
to the slope, and the mechanism says oscillators/reversal fight the multi-month drift a 63d trend book
harvests — expect most IC ≈ 0 or < base and most sole-rankers to KILL. A surprise survivor is a real
discovery; the expected outcome CLOSES the family at 63d with evidence. Do NOT retune toward a pass.
