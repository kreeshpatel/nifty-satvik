# 0096 — Sector-relative CRS denominator KILLS the swing book: residualising the sector strips the trend edge

- **Status:** KILL per pre-reg `diagnostics/research/preregistry/0096-sectorrel-crs-swing.md` (bar fixed
  before the run; n_trials 113→114 incremented before the run).
- **Date:** 2026-07-09. Script `scripts/run_0096_sectorrel_swing.py` (engine: one cfg-gated
  `index_provider` kwarg in `prep_weekly_rank`, default None → Nifty-50 → byte-identical).
- **Owner-selected lever** (L2 of `research/RESEARCH_PLAN_swing.md`).

## What was tested
Swap the CRS denominator from **Nifty-50** to the stock's **own sector equal-weight index**
(`config.SECTOR_MAP`), so RS = stock ÷ own-sector index and both the entry gate `RS > SMA40(RS)` and
the fill rank use sector-relative (idiosyncratic) strength. 550/814 names got a sector index (15
sectors ≥ 8 members); the 264 "Others" (30%) fell back to Nifty-50. **N500-TRI was NOT tested — it
already lost** (0093-TRI 0.677 vs 0093-N50 0.900, finding 0037); this is the genuinely-new denominator.

## Result (deterministic, NET after tiered real costs, corrected universe 2017–2026)
| | Sharpe | CAGR | MaxDD | win | expR | trades (/yr) |
|---|---|---|---|---|---|---|
| baseline (0094, N50 CRS) | **+1.132** | **+24.7%** | −42.4% | 59.2% | +0.48 | 255 (27) |
| overlay (sector-relative) | +0.460 | +7.6% | −45.0% | 49.2% | +0.20 | 248 (26) |
| **Δ** | **−0.672** | **−17.11pp** | **−2.66pp** (deeper) | −10.0pp | −0.28 | −7 |

Continuous-slice Sharpe (base → overlay): 2017-18 +1.17→+0.17 · 2019-21 +1.05→+0.50 · 2022-26
**+1.19→+0.55**. ΔSharpe block-bootstrap 95% CI **[−1.098, −0.311] — entirely below zero**;
n_independent ≈ 37 → **confidently worse, not noise.** Engine invariant verified (overlay OFF
reproduces the 0094 run of record: Sharpe +1.132, DD −42.4%).

## Verdict — KILL (all four pre-committed criteria fail)
ΔSharpe −0.672 ≪ +0.10 · 2022-26 slice worse · MaxDD −2.66pp worse · CI-low −1.098 < 0. No retune.

## Root-cause readout (REQUIRED)
1. **The prediction held: residualising the sector strips the book's edge.** Trade count barely
   moves (255→248) — this is **worse SELECTION, not fewer trades**: expR **+0.48→+0.20**, win
   **59.2%→49.2%**. Ranking on sector-relative strength surfaces different, worse names.
2. **Why:** the swing book is a **trend-momentum** book whose edge IS riding strong sectors/mid-cap
   trends (0037: N50 works precisely because it admits stocks beating the large-cap tape). Dividing
   by the own-sector index **removes exactly that common-factor tailwind**, leaving intra-sector
   idiosyncratic noise — which does not drive the returns. CAGR collapses 24.7%→7.6% and DD gets
   *worse* (−45.0%), so it isn't even a risk-reducing trade-off.
3. **O-002 transfers.** Single-**market**-beta residual momentum was killed ("no improvement over raw
   trend; most residual benefit is market residualisation"). 0096 is the **sector**-residualisation
   analogue and it is *worse* than neutral — residualising a trend book destroys the factor it lives
   on. NOT O-004 (sector *selection*): this neutralised sector beta rather than selecting sectors,
   and still lost.

## Disposition
**KILL — do not re-propose sector-relative / residualised RS on the swing family.** Combined with
0037 (N500-TRI lost) and this, the CRS-denominator axis is now mapped: **market-relative RS vs the
large-cap Nifty-50 is the right denominator** — broadening it (N500-TRI) or residualising it (sector)
both lose, because the book profits from market/sector-relative *outperformance*, not idiosyncratic
strength. The live book stays the frozen 0094 (N50 CRS, Sharpe 1.13, DSR 0.894); its fate is the
2026-10-01 review + the forward wall. Two swing levers are now spent (L1 vol-target 0095, L2
denominator 0096), both confirming the book's edge is concentrated and factor-driven and resists
intra-book re-engineering.
