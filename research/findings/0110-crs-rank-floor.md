# Finding 0110 — Absolute CRS rank floor KILLs: the funding gap is real but un-harvestable

**Verdict:** **KILL.** Pre-reg [0110](../../diagnostics/research/preregistry/0110-crs-rank-floor.md).
n_trials 136->137. No engine edit (preprocessing filter); base byte-identical.

## Result (frozen 0094, corrected universe)
Floor = expanding 75th pct of prior signal ranks (PIT, min 100 prior). Removed 72% of signals, 255->215
funded trades — and expR FELL (+0.48->+0.39). Sharpe 1.132->0.836, CAGR 24.7->15.3%, MaxDD -42.4->-45.4.
Per-year: 2021 **-21.0pp**, 2022 **-22.9pp**, 2025 **-19.0pp**; 2023 +4.1. 4/4 bar FAIL; CI [-0.63,+0.07].

## Root cause — regime drift breaks any absolute threshold (failure-mode #2, exactly as pre-registered)
crs_dist LEVELS drift with market regime: in strong broad markets (2021/2022) everything rises together,
RS-vs-index dispersion compresses, and good signals carry moderate crs_dist — the expanding floor (anchored
on 2017-20 dispersion) over-blocked those entire years. The funded book's edge was never "absolutely high
rank"; it is WEEK-RELATIVE strongest-first + cash contention.

## The profound close — the funding-gap thesis, measured end-to-end
The gap is real: pool +0.16 -> funded +0.48 -> idealized global top-255 +0.72. But the +0.72 requires
knowing the FUTURE rank distribution (hindsight). The implementable approximation (absolute trailing floor)
loses the gap to regime drift and destroys week-relative selection. **Conclusion: the causal selection rule
(week-relative strongest-first under cash contention) is already near-optimal; the residual ~0.24 expR gap
is hindsight, not harvestable alpha.** Cash-timing "cost" is the price of causality, not an inefficiency.

## Program consequence
The SELECTION-side lever is now closed alongside entry (0104/0108/body/volume), exit (0105/0106/0109),
regime (5x), hedge (0100-0102), and ML-switch (0103). Every axis of the single book is measured to its
noise floor or its causal limit. The surviving levers remain: the 0107 blend (structural, forward-logging),
the barbell capital fraction (owner), and forward-wall evidence.
