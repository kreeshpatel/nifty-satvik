# 0149 — Sleeve allocation, swing × low-vol: the owner's 0.60 barbell is the best rule tested

**Class:** activation bound, screen ledger row 22. **No trial.** Standing counts: **screens 22 · sealed
opens 3 · n_trials 2.** Pre-registration: `diagnostics/research/preregistry/0149-sleeve-allocation-bound.md`
(committed `5cb57cf`, before the diagnostic existed). Reproduce:
`python pipelines/diagnostics/diag_sleeve_allocation_0149.py` → `diagnostics/research/sleeve_allocation/result.json`.

## Question

The live barbell puts 0.60 of capital in swing and the rest in low-vol, a weight the owner fixed rather
than measured. Does a standard allocation rule beat it?

## Result

Train window 2019-01-01..2024-06-30; `blend_hybrid_returns.csv` read only through 2024-06-30 (last row
used 2024-06-28). Quarterly rebalance, weights from strictly earlier data, zero rebalancing cost.

| rule | mean swing weight | Sharpe | MaxDD | CAGR | worst year |
|---|---|---|---|---|---|
| **fixed 0.60 (control)** | 0.61 | **1.501** | −36.4% | **27.8%** | +16.9% |
| fixed 0.50 | 0.51 | 1.470 | −34.8% | 25.5% | +12.6% |
| inverse-vol 126d | 0.38 | 1.367 | −33.0% | 21.8% | +5.9% |
| max-diversification 126d | 0.38 | 1.367 | −33.0% | 21.8% | +5.9% |
| minimum variance 126d | 0.08 | 1.040 | −28.6% | 14.8% | −6.8% |

Against the control, every rule has **lower Sharpe in both sub-periods** (−0.02 to −0.61) and a
shallower drawdown (+1.5 to +7.8pp) bought with CAGR (−2.3 to −12.9pp). Family PBO **0.165**
(selection informative): the ranking is stable, and the control sits at its top.

**Reading, as pre-committed: BOUND RECORDED. The 0.60 control stays.** No rule clears ΔSharpe ≥ +0.10.

## What it means

On this window the allocation question is a **risk dial, not an edge.** Moving weight from swing to
low-vol buys a shallower drawdown at a worse Sharpe; no rule finds a better risk-adjusted mix than the
owner's fixed weight. The estimated rules lean hard into low-vol (inverse-vol averages 0.38 swing,
minimum variance 0.08), because low-vol's lower volatility dominates their inputs.

This does **not** contradict 0107. 0107 found the blend beats *each sleeve alone* over 2017-09..2026-06,
a window that includes the chop years 2024H2–2025 where low-vol carried the blend. On the train window
alone, trend years dominate and the swing-heavier mix wins. Which mix wins depends on the regime mix of
the window, and the forward book is where that gets decided.

## Notes

- With two assets, maximum diversification reduces exactly to inverse-vol (w ∝ Σ⁻¹σ is proportional
  to 1/σ when n = 2), so the family has four distinct members, not five. The identical rows confirm the
  implementation rather than adding information.
- Absolute levels (Sharpe 1.50, CAGR 27.8%) are bull-heavy-window figures and are **not certified**;
  only the comparisons are read. Any ΔSharpe here is inside the ≈ 0.59 half-width (n_eff ≈ 37).
- Not run, by design: a vol-targeted cash sleeve (0095) and a third sleeve (0115).

## Closes

`BOUND (2026-10-13, train window)`: no standard allocation rule beats the fixed 0.60 barbell on Sharpe.
The barbell weight stays an owner risk preference, revisited only at a review with the forward blend's
record (`results/blend_hybrid_paper.json`).
