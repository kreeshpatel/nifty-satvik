# 0074 — Vol-scaled / dynamic momentum (Daniel-Moskowitz): does a crash-forecast exposure scalar cut the DD?

- **ID:** 0074 (Stage-D risk overlay; the −46% DD lever). External candidate #1 from
  `research/external_edge_ideas.md`. Owner-pointed 2026-07-01.
- **Registered:** 2026-07-01, BEFORE the run. **TRIAL** → cumulative_n_trials 80 → 81 (bumped before run).
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`, sha `f8625a8f…52142`), frozen cfg,
  corrected universe, 2017-01-01..2026-06-30. Price-only signal (no new data needed). Byte-reproducible.

## Hypothesis
Momentum has rare, large, negatively-skewed crashes after bear markets / during high-vol rebounds
(Daniel-Moskowitz 2016, NBER w20439). A **continuous, forward-looking exposure scalar** that cuts the
book *pre-emptively* when crash risk is high reduces the −46% maxDD **without** proportionally killing
CAGR → ΔCalmar ≥ +0.05 and ΔSharpe CI-low > 0.

## Candidate (the distinct, untested construction — this is the §11 reopen condition)
A per-date sizing scalar `s_t ∈ [floor, 1]`, **lagged one day**, multiplied into `simulate`'s sizing
equity (the same flag-gated hook as 0068/0070; `None` → golden byte-identical). The NEW element vs
prior work is the Daniel-Moskowitz **forecast asymmetry**: `s_t` is driven by the interaction of
(a) a **bear-market state** (market index below its trailing peak by > X% / negative trailing market
return) AND (b) realized market volatility — i.e. cut exposure when momentum's *expected* return turns
negative (the post-bear rebound-crash), not merely when realized vol/drawdown is already high.
ONE pre-declared operating point (bear threshold + vol window + floor). Trailing-only, no lookahead.

## Method
Paired 63-day block bootstrap (n=5000) on the pinned panel: ΔCalmar (PRIMARY — it's a DD lever),
ΔSharpe + CI, ΔmaxDD, ΔCAGR; DSR(candidate) at n_trials=81; ≥2019 walk-forward folds; 2017-21 /
2022-26 sub-periods (must hold in BOTH crash regimes — 2018, 2020, 2022). `scripts/run_overlay_*`
pattern (a new `run_overlay_volscaled.py` + workflow), pinned.

## Decision rule (pre-committed)
PROMOTE only if ALL: **ΔCalmar ≥ +0.05** AND **ΔSharpe CI-low > 0** (do not make risk-adjusted return
worse) AND maxDD materially cut AND DSR > 0.95 AND ≥2 crash-folds improve AND turnover ≤ +30% AND
1-sentence mechanism. KILL if it merely trades DD for CAGR (the 0070 outcome) or reduces to the
already-promoted book-vol target. UNDERPOWERED if CI straddles 0 with the right sign.

## Skeptical prior (state it — this overlap is large)
**HEAVY overlap with already-done work:** 0068 (= O-009, **PROMOTED** portfolio book-vol target) and
0070 (systematic-crash exposure overlays — SEMIDEV / MKTDD / BREADTH — which **plateaued at ~−38%**
and could not beat the COVID-2020 systematic floor CAGR-free). The ONLY thing that makes 0074 a
legitimate reopen rather than relitigation is the **D-M forecast asymmetry** (pre-emptive cut on the
bear→rebound crash forecast) vs 0070's *reactive* market-state scalars. If the run shows 0074
collapses to the same ~−38 plateau / same CAGR-for-DD trade as 0070, it is relitigation → KILL.
Also: the external claims were **NOT adversarially verified** (the deep-research verify pass hit the
token limit). Honest expectation: HARD to beat the 0070 plateau; the dependable −30% likely still
needs the deferred Stage-G tail hedge, not another sizing overlay. KILL is a first-class outcome.
