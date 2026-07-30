# Finding 0112 — Phase 2: the model selector's per-trade lift does NOT transfer to the return book; what emerges is a defensive variant

**Verdict:** **KILL** per the pre-committed selection-class bar (3/4 FAIL). Pre-reg
[0112](../../diagnostics/research/preregistry/0112-model-selector-swap.md); spec
`research/SELECTION_MODEL_SPEC.md` (study now CLOSED per its own Phase-2 rule). n_trials 137->138.

## Result (frozen 0094, capped book; base byte-identical)
| | Sharpe | CAGR | MaxDD | trades | win |
|---|---|---|---|---|---|
| base (CRS order) | 1.132 | 24.7% | -42.4% | 255 | 59% |
| model order (GBM) | 1.035 | 20.9% | **-33.5%** | 238 | 55% |

dSharpe -0.097 [-0.450,+0.343] | dCAGR -3.8pp | **dMaxDD +8.8pp** | 2022-26 slice 1.19->1.12.
Per-year: **2025 -13.0 -> +8.0 (+21.1pp — the fade year FIXED, exactly as the pool study predicted)**;
but 2019 -19.0pp, 2023 -16.2pp, 2026 -22.2pp (fold instability materialized, failure-mode #3).
**The model book has ZERO losing years** (min year +8.0%) vs base's one (-13.0%).

## Root cause — pool-to-book transfer failure (failure-mode #1, as pre-registered)
The +0.215 per-trade lift was measured on top-5-per-EVERY-week; under the cash gate the model's reordering
changes WHICH weeks consume capital, and expR actually fell (+0.48->+0.44). What survived the transfer is
the model's RISK dimension: it systematically deprioritizes the signals that blow up in stress years
(2025 flipped, DD -42->-34) at the cost of trend-year upside (2019/2023/2026 diluted) — the same
defensive-variant signature as 0093, 0099, and the 0107 blend: return down, robustness up.

## Program consequence
- **The selection-model study CLOSES** per its own spec: the CRS heuristic stands for the RETURN book;
  the trained selector is not a return upgrade under capital constraints.
- The observed profile (Sharpe 1.03 / DD -33.5 / no losing year, single-book, no second sleeve needed) is
  logged as a DEFENSIVE-variant observation for the forward-wall / Oct-1 context — the same class as
  0099/A-only decisions: owner-risk-preference territory, never a bar-passing promotion, and NOT to be
  relitigated in-sample (a KILL is a KILL; the params stay frozen).
- Adds the sixth confirmation of the house law: on this cash-constrained concentrated book, every lever
  that improves robustness pays in return; nothing in-sample clears both. Certification remains forward.
