# 0067 — Long-horizon capital reallocation (Top-K-Drop "smarter filling")

**Status:** PRE-REGISTERED 2026-06-25 (before the cloud run). **Family:** deployment / slot-filling.
**Runner:** `diagnostics/run_long_horizon_reallocation_ab.py` via `cpcv-research.yml` (corrected 682-name universe).

## Hypothesis
The live long-horizon strategy fills a free slot only when a holding exits on its own
(stop/target/trailing/63d). When the 15-slot book is full, a much stronger new signal is dropped.
RS-01 / Top-K-Drop reallocation evicts the weakest **soured** holding (re-scored on TODAY's
`trend_rank`, not its entry rank) for a materially-stronger candidate. On the corrected 682-name
universe the 15-slot cap binds (~150–200 eligible/day), so reallocation can fire — UNLIKE v1 (0041),
where the 30-slot cap never bound and the lever was INERT.

**Directional prediction:** `realloc_on` improves risk-adjusted return out-of-sample by recycling
capital from dead/soured holdings into fresher trends, at the cost of higher turnover.

## Arms (walk-forward, params re-derived per expanding-train fold)
- `base`: `reallocation_enabled=False` (the live strategy today).
- `realloc_on`: `reallocation_enabled=True`, `realloc_min_edge_gain=0.10` (trend_rank percentile gap),
  `realloc_min_hold_days=10`, `realloc_donor_max_pnl=0.0` (evict only flat/losing), `realloc_max_per_day=2`.

## Pre-committed gate (≥2019 OOS folds) — decided BEFORE seeing results
PROMOTE to live wiring (Phase 4c) only if ALL hold:
1. **The cap binds**: `total_reallocations >> 0` (else the lever is structurally INERT here = the v1
   0041 outcome → KILL, no further analysis).
2. **Beats base**: `delta_mean_sharpe > 0` AND a MAJORITY of evaluated folds win on Sharpe.
3. **Not a turnover mirage**: `realloc_on` still beats `base` at 2× transaction costs (re-run arm).
4. **No fold blow-up**: no single ≥2019 fold regresses materially (Sharpe delta < −0.3).

If ANY fails → **KILL**: the lever stays flag-OFF research code, is recorded in `STRATEGY_FULL.md §11`
(tested-and-rejected), and the live scanner is NEVER touched. A pass authorizes only the flag-gated,
golden-master-safe live wiring (4c) + a paper-trade window before real capital.

## Skeptical priors
The identical lever was KILLed for v1 (0041, INERT). The 0.10 trend-rank edge gap is a first guess; if
the cap binds but the delta straddles 0, that is a KILL — NOT a "tune the threshold" invitation (a
threshold sweep would be a fresh pre-registration, multiple-comparisons-counted). Evicting "soured"
names assumes current rank predicts forward return better than the holding's own exit logic already
does — which the let-winners-run design may already capture.
