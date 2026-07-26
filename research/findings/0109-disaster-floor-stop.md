# Finding 0109 — Disaster-floor stop KILLs: book-path reshuffle noise swamps even a zero-whipsaw edge

**Verdict:** **KILL.** Pre-reg [0109](../../diagnostics/research/preregistry/0109-disaster-floor-stop.md);
engine `scripts/run_bhanushali_weekly_rank.py` (cfg-gated `disaster_floor_pct`, default 0.0 = byte-identical,
verified in-run). n_trials 135->136.

## Result (frozen 0094, corrected universe)
| | Sharpe | CAGR | MaxDD | trades | win |
|---|---|---|---|---|---|
| base | 1.132 | 24.7% | -42.4% | 255 | 59% |
| **floor = stop x 0.90** | 1.061 | 22.8% | **-43.7%** | 257 | 58% |

dSharpe -0.071 [-0.203,+0.070] | dCAGR -1.9pp | dMaxDD -1.3pp (worse). 17 disaster exits fired (14+3 gap).
Per-year: 2020 **+11.4 -> -2.0 (-13.3pp)**, 2024 +9.9 -> +23.0 (+13.1pp!), 2025 -6.8pp, 2023 -3.3pp.
Bar 4/4 FAIL ("no year worse >2pp" fails hard).

## Root cause — the book is chaotic w.r.t. exit-timing perturbations
The cohort measurement was correct: at stop x 0.90, ZERO winners pierced in 9y and the floor saves +4.3R
per-trade. But exiting 17 positions days earlier reshuffles the cash path: in Mar-2020 the freed cash
re-entered the falling market (new fills from still-open entry windows) and those stopped too — 2020
flipped from +11.4% to -2.0%. The +-13pp/yr composition swings dwarf the +4.3R (~3.5% of book R) edge.
Same trade-substitution mechanism as 0104/0105, now demonstrated at its purest: **a strictly per-trade-
positive, zero-whipsaw change still loses to path noise on a 4-5-name cash-constrained book.**

## Program consequence — the exit-lever program is now CLOSED at machine precision
0105 (tighten fill) / 0106 (widen level) / 0109 (catastrophe floor, the best-shaped candidate possible):
all KILL. There is no exit modification small enough to keep the edge and large enough to beat the
composition noise. Micro-edges below ~ +-10R cannot be certified on this book — the noise floor of the
concentrated structure exceeds them. Only STRUCTURAL changes (sleeve blend 0107) clear the floor.

## Operational nuance (owner decision, not a cfg claim)
A live broker GTT at stop x 0.90 may still be rational as UN-MODELED fraud/black-swan insurance (the
2017-2026 sample contains no single-name fraud in the book; the backtest cannot price that tail). Cost:
live would diverge from the certified paper book (composition drift). If wanted, adopt at a quarterly
review as an operational risk control with the divergence caveat — never as a backtest-certified edge.
