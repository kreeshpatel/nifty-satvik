# 0095 — Vol-target de-gross KILLS the weekly-swing book: the arc's last-deferred lever does not transfer

- **Status:** KILL per pre-reg `diagnostics/research/preregistry/0095-voltarget-swing.md` (bar fixed
  before the run; n_trials 112→113 incremented before the run).
- **Date:** 2026-07-09. Script `scripts/run_0095_voltarget_swing.py` (engine change: one cfg-gated
  `vol_target` kwarg in `scripts/run_bhanushali_weekly_rank.py::backtest`, default None → byte-identical).
- **Owner-selected lever** (L1 of `research/RESEARCH_PLAN_swing.md`).

## What was tested
Port the PROMOTED base overlay **O-009 vol-target de-gross** (pre-reg 0068 V2, params
`target_annual=0.15, window=42, floor=0.40`, reused verbatim — not tuned) to the live
`weekly-swing-0094-rank` book. Mechanism: scale the SIZING equity by
`vol_target_scalar = clip(0.15/realised_book_vol, 0.40, 1.0)` (de-gross only, never levers), so
fills shrink when the book's trailing 42-day realised vol is above 15% annual.

## Result (deterministic, NET after tiered real costs, corrected universe 2017–2026)
| | Sharpe | CAGR | MaxDD | Calmar | win | trades (/yr) | expR |
|---|---|---|---|---|---|---|---|
| baseline (0094, vol_target OFF) | **+1.132** | **+24.7%** | −42.4% | 0.58 | 59.2% | 255 (27) | +0.48 |
| overlay (vol_target ON) | +0.734 | +13.8% | −40.3% | 0.34 | 51.3% | 349 (37) | +0.33 |
| **Δ** | **−0.398** | **−10.87pp** | **+2.10pp** (shallower) | −0.24 | −7.9pp | **+94 (+37%)** | −0.15 |

Continuous-slice Sharpe (base → overlay): 2017-18 +1.17→+0.47 · 2019-21 +1.05→+0.78 · 2022-26
**+1.19→+0.81** (Δ −0.385). ΔSharpe block-bootstrap 95% CI **[−0.749, +0.002]**; n_independent ≈ 37
(63-day windows) → **adequately powered — a real KILL, not "can't tell."**

**Engine invariant verified:** with the overlay OFF the baseline reproduces the 0094 run of record
byte-for-byte (Sharpe +1.132, DD −42.4%, Δ = 0.000).

## Verdict — KILL (all four pre-committed criteria fail)
- ΔMaxDD +2.10pp < the +3.0pp bar (the *only* thing it improved, and it still misses)
- ΔSharpe −0.398 ≪ −0.05 · 2022-26 slice −0.385 ≪ −0.05 · ΔCAGR −10.87pp ≪ −2.0pp

No retune, no re-run (the 0025 rule). The params are the promoted-base params by pre-registration.

## Root-cause readout (REQUIRED)
1. **The mechanism INVERTS on a cash-constrained book.** On the fully-invested momentum base,
   de-grossing is a pure gross reduction → CAGR-neutral, DD-reducing (O-009's promoted signature).
   The swing book funds signals **strongest-CRS-first until cash runs out**, so shrinking every
   position **frees cash that the fill loop immediately redeploys into MORE, weaker signals**:
   trades **255→349 (+37%)**, win **59.2%→51.3%**, expR **+0.48→+0.33**. The de-gross became a
   *quality-dilution* engine — the exact opposite of the intended effect. (Failure mode #2 of the
   pre-reg, stronger than predicted.)
2. **It also shrinks the concentrated winners.** The book's edge lives in a few strong trend names
   sized at the full 2% risk; sizing them down in high-vol windows (which precede the sharpest
   recoveries) caps the upside — CAGR −10.9pp for a 2.1pp DD gain. (Failure mode #1.)
3. **This is the O-006 / 0069 family lesson again:** anything that redistributes this book's risk
   toward breadth dilutes the concentrated trend edge. The DD relief is real but trivial and
   nowhere near paying for the return destroyed.

## Disposition — closes the arc's last-deferred lever
Findings **0088 / 0089 / 0090 / 0091** all signposted **O-009 vol-target as the swing book's one
remaining unspent CAGR/DD lever**. 0095 tests it directly and settles it: **portfolio vol-target
does not transfer to this cash-constrained, concentrated weekly book** — it dilutes quality faster
than it caps drawdown. Do **not** re-propose intra-book position de-grossing on the swing family.

The only DD lever now left for the swing sleeve is **at the SLEEVE level** — allocate a smaller
fraction of *total* capital to the whole book (the O-018 ERC / portfolio-sizing mechanism, decided
on the forward wall), never intra-book resizing. This mirrors 0087's lesson ("capital-efficiency
routes to portfolio-level allocation, never intra-sleeve churn"). The live book remains the
frozen 0094 (Sharpe 1.13, DSR 0.894); its fate is the 2026-10-01 review + the forward wall.
