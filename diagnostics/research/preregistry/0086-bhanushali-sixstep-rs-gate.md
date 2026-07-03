# 0086 — Comparative relative-strength entry gate on the six-step runner-trail book

- **ID:** 0086. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 103 → 104.
- **Anchor / data:** identical to 0085 (corrected universe, PIT membership, tiered costs, 2017–2026,
  EQ0 ₹10L) + the pinned house benchmark `research/exports/benchmark_nifty500_tri.csv` (Nifty-500 TRI,
  2017-09-14..2026-06-29). Script `scripts/run_bhanushali_sixstep_rs.py` (imports the frozen 0085
  engine unchanged; only the signal mask gains the gate).

## Why this trial exists
Finding 0027's 2025 diagnostic: the −26.8% year is signal failure in the Jan–Feb 2025 breadth collapse
(net −₹6.1L; ≈−₹4.3L even at zero cost; win 31%) — the 44-WEEK bucket stays stale-bullish for months
while dailies break, so the funnel buys pullbacks in downtrends. Owner hypothesis: require the stock to
be in structural OUTPERFORMANCE of the index before taking the signal. Comparative-RS gating of this
funnel is untested (O-001 killed an absolute index-level regime gate on the BASE; this is per-stock
relative strength on the swing funnel — different lever, different book).

**Owner phrasing → frozen formalization.** Owner asked for "stock relative strength compared to the
index above the 100 EMA". A price-ratio cannot be compared to the index's own price-EMA (units differ);
the frozen, dimensionally-consistent reading — confirmed as the recommended option — is: the RS LINE
above its OWN 100-day EMA.

## The FROZEN spec (only the entry gate differs from 0085)

| Param | Frozen value |
|---|---|
| Base configuration | **exactly 0085** (runner trail EMA20 −4% ratchet, 63d cap; non-runners = 0084 exits) |
| RS line | `RS_t = stock_close_t / tri_close_t` (TRI reindex-ffilled to the stock's calendar) |
| Gate | signal candle valid only if `RS_t > EMA100(RS)_t`, `ewm(span=100, adjust=False)` |
| Scope | ENTRY gate only — applied to the signal mask; open positions and exits untouched |
| Warmup / missing benchmark | gate evaluable from the 100th TRI session (~2018-02) onward; before that (and on any missing-benchmark date) the gate passes through (trade as 0085) — frozen, noted for the 2017-18 slice |
| Everything else | byte-identical to 0085 |

Pre-declared sensitivity line (not an arm): erratum-dropped (two pinned INDIAMART bars), report both.

## Primary metric
**Corrected-universe NET Sharpe.** References (not gates): 0085 +0.587, 0084 +0.477, baseline_v1 0.667.
Pre-declared diagnostics: 2025 calendar-year P&L vs 0085's (the motivating year), trade count retained
vs gated away, per-year table.

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@104 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
Informational: ΔSharpe vs 0085 same-cell. No retuning — in particular NO sweep of the EMA span (100 is
the owner's number, frozen).

## Skeptical prior (honest)
Registry rhymes both ways. For: the gate targets a demonstrated failure mode (2025), and RS is computed
per-stock (not the O-001 blanket gate). Against: every entry-side gate/filter tried on the base KILLed or
diluted (O-001, 0056, O-019 — "IC ≠ portfolio Sharpe"), momentum funnels self-select outperformers
already (the gate may mostly remove early-trend entries the trail needed), and cutting ~2025 losers also
cuts 2023-style early buys. Expect: fewer trades, better win rate, ambiguous Sharpe; UNDERPOWERED.

---

## RESULT (appended 2026-07-04 after the run of record — spec above untouched)

| cell | trades | win | expR | CAGR | Sharpe | MaxDD | mult |
|---|---|---|---|---|---|---|---|
| corrected GROSS | 460 | 39.3% | +0.18 | +14.7% | +0.687 | −36.9% | 3.68× |
| **corrected NET (primary)** | 458 | 40.2% | +0.18 | **+8.3%** | **+0.444** | **−40.8%** | 2.12× |
| 0085 reference (same cell) | 432 | 39.6% | +0.23 | +11.5% | +0.587 | −37.5% | 2.80× |
| erratum-dropped NET | 448 | 39.7% | +0.17 | +6.9% | +0.396 | −40.8% | 1.89× |

- Gate removed 14% of signal candles (14,253 / 103,861). Slices +0.22 / +0.63 / +0.41 (all ≥ 0).
- Bootstrap CI [−0.198, +1.007]; **DSR@104 = 0.138**. Gates: slices PASS, CI-low FAIL, DSR FAIL.
- **ΔSharpe vs 0085 (informational): −0.143.** The gate makes the book WORSE overall.
- **The motivating year IS fixed:** 2025 net −₹0.97L vs 0085's −₹6.09L (43 vs 48 trades) — the gate did
  exactly what it was designed to do in the breadth collapse. But the cost surfaces elsewhere: 2024
  −₹4.2L (0085's best runners get delayed/blocked or re-sequenced), 2022 −₹5.0L, and MaxDD deepens
  −37.5→−40.8. In a cash-constrained no-rotation book, removing 14% of entries reshuffles the entire
  fill sequence — the gate trades a known 2025 loss for a diffuse loss of early-trend entries, the
  funnel's bread and butter (RS crosses its 100-EMA well after the 44-SMA pullback fires).

**VERDICT: UNDERPOWERED/WEAK** by the pre-committed family rule (Sharpe > 0, slices ≥ 0, CI straddles
0) — and by the informational Δ, an unambiguous non-improvement: the fifth entry-side gate across the
program to fail (O-001, 0056, O-019 on the base; now RS on this funnel). Do NOT sweep the EMA span or
re-propose RS as a rank/tilt without a genuinely new formulation. 0085 remains the family's best book.
