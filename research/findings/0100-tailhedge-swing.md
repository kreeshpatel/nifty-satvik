# Finding 0100 — Options-OI-triggered tail hedge on the swing book: KILL (made DD *worse*)

**Verdict:** **KILL** (adequate power, not merely underpowered). Pre-reg
[0100](../../diagnostics/research/preregistry/0100-tailhedge-swing.md); harness
`scripts/run_0100_tailhedge_swing.py`; data `data/options_oi_pit.parquet` + `data/_fo_oi_raw.parquet`
(`nq.data.options_oi`, PIT-tested `tests/test_options_oi_pit.py`). n_trials 129→130 (counted before run).

## Result (corrected universe 2017–2026, NET, continuous-slice)
Engine invariant OK — the book leg reproduces the 0094 record byte-for-byte (Sharpe +1.132, DD −42.4%).

| | Sharpe | CAGR | MaxDD | Calmar | 2022-26 slice Sh |
|---|---|---|---|---|---|
| book only | +1.132 | +24.7% | −42.4% | 0.58 | +1.19 |
| **book + tail hedge** | **+1.072** | **+23.9%** | **−43.9%** | 0.55 | +1.09 |
| Δ | **−0.060** | −0.75pp | **−1.49pp (deeper)** | −0.03 | **−0.104** |

ΔSharpe block-bootstrap 95% CI **[−0.146, +0.019]** (straddles 0), n_independent ≈ 37 → **adequate power**;
this is a real non-improvement, not a small-sample shrug. Pre-committed bar: **3/4 FAIL** (only ΔCAGR≥−2pp
passes; ΔMaxDD, ΔSharpe, and the 2022-26 slice all fail).

## Root cause — every pre-registered failure mode fired
- **19 hedge cycles, only 32% premium-positive**; total debit ₹1.22L → payoff ₹0.77L = **net −₹0.45L drag**.
- **The MaxDD got WORSE (−42.4→−43.9).** The book's deepest drawdown is not a sharp vol-spike event, so
  the coincident `IV z>2` trigger did not arm into it; instead premium drag from unrelated cycles bled NAV
  during the drawdown → deeper trough. This is **failure mode #2** (wrong-shape signal: a hedge can't fix a
  drawdown whose mechanism it doesn't match — the same lesson 0090 taught for regime gates).
- **Arming after the spike buys expensive, mostly-worthless protection** (failure mode #1): 2019/2022/2023/
  2024/2025 all net-negative-R years; the spread expired into recoveries. Only 2018 (+1.4R) and 2026 (+1.3R)
  paid.
- **COVID paid only +0.7R** — the 5%-wide put-spread capped out early in a >30% crash (**failure mode #3**:
  the defined-risk cap under-hedges the deep tail exactly when it matters most).

## Registry consequence
Confirms the program-wide prior on this book: a **coincident-IV, buy-after-the-spike** hedge does not cut
its drawdown — it adds cost. Combined with 0090 (regime gate KILL) and 0095 (de-gross KILL), the swing
book has now rejected all three "react to stress" DD levers (gate / de-gross / coincident hedge). The
**data layer itself is validated and reusable** — the KILL is of this *formulation*, not the OI signal.

## Next setup (do NOT retune 0100 — params were frozen)
The KILL is specific to `{coincident IV z>2, 5%-wide put-spread, hedge_frac 1.0}`. Genuinely-distinct,
NOT-yet-tested formulations (each needs its own pre-reg, ≥+1 n_trials, and is skeptical-prior given this
result):
1. **Leading trigger** — arm on a PCR/OI-buildup *bearish-positioning* extreme (the owner's other option),
   which fires *before* the IV spike so protection is bought cheap. Distinct signal + distinct timing.
2. **Wider / naked deep put** — remove the 5% cap (failure mode #3) to catch the fat tail; trades more
   premium drag for deeper-tail convexity.
3. **Sleeve-level, not sidecar** — hold the hedge continuously as a small fixed % (the O-018 ERC / forward-
   wall allocation lever), decided on forward evidence, rather than timing it at all.

Owner call whether any is worth a new trial; the honest read is that timing a hedge off a coincident stress
signal is a documented dead end, and continuous cheap convexity (option 3) is the only shape with an
un-refuted prior.
