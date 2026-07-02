# 0078 — Residual momentum as a COMPLEMENT: blend vs veto (retain trend return, buy down the factor-grind DD)

- **ID:** 0078 (successor to 0077; the productive reframe of the residual-momentum KILL). Owner-approved 2026-07-02.
- **Registered:** 2026-07-02, BEFORE the run. **TRIAL FAMILY, 4 arms, FIXED coarse params (NO sweep)** →
  **cumulative_n_trials 87 → 91, incremented BEFORE the run**.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg; FF-India factors
  `data/ff_india_factors.parquet` (Market + HML, PIT-safe); residual scores per `run_residual_momentum.residual_ranks`.

## Motivation (finding 0011 + the vol-matched check)
0077 KILLed residual momentum as a SOLE ranker (discards the trend return) but proved it cuts the
2024-25 factor-grind drawdown. The pre-0078 vol-matched diagnostic (`scripts/diag_volmatch_residmom.py`,
no trial cost) shows this is **localized, not universal**: vol-matched to base's 27% vol, resid's DD is
LIVE 22-26 **−33.6** (vs base −46.3, a real ~13pp reduction that survives vol-matching) but FULL-period
**−56.8** (WORSE than base — the full-period raw −44 was a low-vol artifact). So residual momentum is a
**targeted factor-grind-tail hedge**, not a general DD tool. This trial keeps the trend signal driving
selection/return and applies residual momentum only where its mechanism operates.

## Candidates (4 arms, params FIXED a priori — no post-hoc λ/q selection under this trial)
The rank column injected into `simulate` (both are recomputed as a cross-sectional [0,1] percentile):
- **BLEND λ=0.25** — `rank = pctile(trend_rank + 0.25·resid_rank)`.
- **BLEND λ=0.50** — `rank = pctile(trend_rank + 0.50·resid_rank)`. (Equal-weight λ≥1 excluded a priori — too
  aggressive given the 8.2% sole-ranker CAGR floor.)
- **VETO q=20%** — rank by trend as base, but make ineligible any name in the **bottom quintile** of that
  day's resid_rank ("don't buy a trend name whose trend is entirely factor beta"). Top of book untouched.
- **VETO q=10%** — same, bottom **decile** only (gentler).

Names lacking a residual score keep their base trend_rank (blend) / stay eligible (veto) — the veto only
*removes* the worst-scored, so no-score names are not vetoed. `simulate` frozen cfg; no engine change.

## Method
`scripts/run_residual_blend_veto.py`: each arm vs the `sma200_slope_63` base, paired 63d block bootstrap
(n=5000) ΔSharpe/ΔSortino, DSR at n_trials=91, continuous-slice 2022-26 (Sharpe + **DD**), skew,
≥2019 fold-pass, turnover, after-tax CAGR. Report all 4 arms; **primary metric identical across arms so
they race.**

## Decision rule (pre-committed BEFORE the run) — shape + localized-DD at a return floor, NOT DSR
An arm is a **SHADOW / forward-wall candidate** iff ALL:
  1. **LIVE 2022-26 MaxDD ≥ 8pp shallower** than base (−46.3 → ≤ −38.3). **Vol-guard (baked in, not
     post-hoc):** report each arm's realized ann book vol; if an arm runs **< 24%** (materially below
     base's 27%), vol-match its LIVE returns (k = base_vol/arm_vol) and credit criterion 1 on the
     **vol-matched** LIVE DD — so a DD win bought with lower vol (0077's artifact) cannot pass, AND
  2. **full-period GROSS CAGR ≥ 13.5%** — the return-protection floor = give up at most ~2pp off base's
     **15.5% gross** (NOT an after-tax gain requirement; the veto re-picks within the same daily
     cross-section so turnover ≈ flat and there is no mechanism to mint return — after-tax CAGR is
     reported for context, not gated), AND
  3. **skew not worse** and **Sortino not worse** than base.
Else **KILL**. A full-period DD improvement is **NOT** required (the vol-match showed the edge is
live-window-only). ΔSharpe CI / DSR are **reported but NOT gated** — ~34 windows cannot certify a
moderate edge (the 0076/0071/0077 lesson); this is graded on shape + localized DD + the return floor +
the **forward wall**. A PROMOTE would still need the full bar + forward wall + owner sign-off.

## Leakage contract (skills/leakage-audit)
Factors PIT-safe (HML `bp` via `value_quality_series` strict-before availability join); residual
regression trailing-only; scores applied strict-before (month-end t → dates > t). Same PIT-masked
universe as base. The veto/blend only re-order or drop within the already-eligible day cross-section.

## Known spec gap (stated up front, per the discipline)
**SMB (size) is omitted** — the residual is on `[mkt, hml]` only (the carried store lacks
shares/net_worth; full FF3 needs a Screener re-scrape). The size-tilt probe found corr(resid_rank,
logADV) = −0.059 (weak), so the residual is NOT a size bet in disguise — but the 2024-25 unwind had a
smallcap component, so a full-FF3 residual **might avoid the grind even better**. If any 0078 arm shows
promise, the SMB scrape + re-residualization is the sharpening follow-up (0079). Do NOT read a KILL here
as a KILL of *full-FF3* residual momentum.

## Skeptical prior (state it)
0077 (sole swap) KILLed; 0073/0020 (conviction sizing) KILLed; the edge is moderate (0008). Most likely:
the veto preserves more CAGR per unit of DD than the blend (the blend dilutes the paying years), and at
least one veto arm clears the localized-DD + return-floor bar → SHADOW, but ΔSharpe stays UNDERPOWERED.
A blend that beats base on nothing but the return floor is a KILL. Do NOT retune λ/q toward a pass —
the params are fixed above; a fifth value is a new trial number.
