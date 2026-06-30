# 0072 — Conviction within the top-15: does an inspectable quality score rank per-trade P&L?

- **ID:** 0072 (Stage C — ROADMAP). Owner-approved design 2026-07-01 (4-factor composite).
- **Registered:** 2026-07-01, BEFORE the run (question + score formula + decision rule fixed first).
- **Type:** **C2 = MEASUREMENT** (rank-IC of a score vs realised per-trade return; no trade/sizing
  decision) → **NOT an n_trials trial** per `diagnostics/research/n_trials.json` (cf. 0021). The
  *trial* (n_trials bump) is the later **C3** application (conviction-weighted sizing → PROMOTE/KILL).
- **Anchor / data:** pinned `baseline_v1` (corrected universe, `dataset-pin-20260701`, sha
  `f8625a8f…52142`), frozen cfg, window 2017-01-01..2026-06-30. Byte-reproducible.

## Hypothesis

Among the names actually traded (the selected top-15 book), a higher **conviction score** —
stronger trend, lower volatility, deeper liquidity, higher quality — predicts a higher **realised
per-trade return** (return_pct, which embeds the +22.52% target / 3.67×ATR stop / trailing
convexity). If real, conviction can later DRIVE sizing/exits (Stage D); if not, it KILLs here.

## The score (fixed, owner-approved — no post-hoc changes)

Per date, among the rank-gated selectable pool (`trend_rank ≥ 1 − gate_quantile`, gate 0.5),
z-score four PIT-safe factors and average (a name missing a factor is averaged over those it has):

    conviction = mean[ z(sma200_slope_63), z(−atr_pct_63), z(log adv_rupees_20d), z(roe) ]

(`nq/research/conviction.py::add_conviction_score`; equal-weight, inspectable, NO ML.)

## Method

1. Run the frozen-cfg backtest on the pinned panel → trades.
2. Attach each trade's conviction at its ENTRY date (within that day's pool) — no lookahead.
3. **Primary metric:** Spearman rank-IC(conviction_at_entry, realised return_pct) across all trades.
4. **Significance:** matched-permutation null (`nq/validation/factor_ic.py`, n_perm=5000) → two-sided
   p = P(|null IC| ≥ |observed IC|). Inspect per-quintile mean return + WR (Q1…Q5 monotonicity).

## Decision rule (pre-committed)

- **SUPPORT** — IC > 0 AND p < 0.05 (ranking beats chance, right direction). A LEAD to C3; note
  tradeability wants |IC| ≳ 0.3–0.5 (0021), so a small significant IC is weak, not a green light.
- **INCONCLUSIVE** — IC > 0 AND 0.05 ≤ p < 0.10.
- **KILL** — otherwise (p ≥ 0.10 or IC ≤ 0). Recorded as a finding; C3 not pursued unless C2 leads.

## Skeptical prior (state it)

Finding **0021**: the technical base has ~0 *directional* IC at all horizons on this universe — the
edge is vol-selection + asymmetric payoff (convexity), not directional stock-picking; §11/O-006
(low-vol blend) and O-007 (ROE screen) were REJECTED as selection levers. This is a DIFFERENT test
(conditioned on the selected book; target = realised P&L incl. convexity, not raw direction), so it
is not a relitigation — but the honest expectation is KILL/weak. KILL is a first-class outcome
(ROADMAP tradeoff 4): if conviction can't earn its place, the pinned base ships on its own.
