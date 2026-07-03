# 0025 — Path-1: the 4×ATR stop geometry triples the swing book, but on the corrected universe it misses the pre-committed bar by 0.003

- **Status:** MEASUREMENT per pre-reg `diagnostics/research/preregistry/0025-bhanushali-path1-atr-geometry.md`
  (2×2 grid and verdict bands fixed before any run; no n_trials cost, no cfg change).
- **Date:** 2026-07-03. Script `scripts/run_bhanushali_path1.py`. One mechanical change to the practitioner
  config (0024): initial stop candle-low → **fill − 4×ATR(14)**. Second axis: the survivor-only pinned cache
  vs the **corrected universe** (pinned + delisted backfill + validated alias map — 788 names; see
  `diagnostics/research/backfill_readiness.md`).

## Result (deterministic run of record; NET after tiered real costs)
| NET Sharpe / CAGR / MaxDD | survivor-only (pinned) | corrected (+ backfill) |
|---|---|---|
| candle-low (0024 config) | +0.20 / +1.6% / −24.0% | +0.16 / +1.1% / −26.9% |
| **4×ATR initial stop** | **+0.58 / +4.3% / −12.7%** | **+0.397 / +2.8% / −12.1%** |

Gross: candle +0.49→+0.43, atr4 +0.76→+0.57 (survivor→corrected). Trades ~20–22/yr in every cell.
Sub-periods (atr4 corrected, net): 2017-18 +0.01 / 2019-21 +0.54 / 2022-26 +0.42.

## Verdict — the pre-committed bar is NOT met (and is not being relitigated)
The pre-reg fixed: "meaningful lift = 4×ATR net Sharpe **≥ +0.40 on the corrected universe**." The cell
came in at **+0.397**. The band between the lift bar (0.40) and the no-lift bar (0.30) was left undefined
in the pre-reg — an authoring gap recorded here — but the committed bar is the committed bar: **missed by
0.003.** No retune, no re-run, no rounding. The v1.5 Path-B sleeve proposal (which already named this
geometry) goes to the 2026-10-01 review carrying exactly these numbers; the owner decides with the honest
figure, not a gamed one.

## Root-cause readout (REQUIRED)
1. **The deployment mechanism is CONFIRMED.** Same signals (~20/yr), stop ~8–12% wide → ~20–25% notional
   deploys the full 2% risk under the 30% cap. Net Sharpe rises +0.16→+0.40 (corrected) purely from
   geometry; MaxDD *improves* −26.9%→−12.1% because the candle-low stop had been converting the −6.6%
   median MAE into realized noise-losses; cost drag halves (whipsaw round-trips vanish).
2. **Survivorship bias scales with holding period — the headline data lesson.** The corrected universe cut
   the candle config by −0.04 Sharpe but the 4×ATR config by **−0.18**: wide stops ride the recovered
   corpses (DHFL, RCOM, JETAIRWAYS, the PSU banks) down before exiting, tight stops eject them fast.
   Direction DOWN in all four cells → no CA red flag on the backfill. **Implication for the program: the
   63-day-hold baseline_v1 (0.667, survivor-only) is exposed in the same direction and its corrected re-run
   is now unblocked** (owner/governance action — it re-anchors the pin).
3. **Determinism fix (recorded, not a tune):** fill priority previously followed Python set iteration
   (hash-randomized per process, ±0.05 net-Sharpe wobble across runs). Now fills follow watchlist-rank
   order (strongest candidate first — the faithful reading); byte-identical across processes (verified).
   The pre-reg did not specify fill priority; this closes that gap.
4. 2017-18 is flat (+0.01) in the corrected atr4 cell — the strategy's net edge is concentrated in ≥2019,
   consistent with the program's trust-≥2019 rule.

## Erratum (2026-07-03, trade-level forensic audit — `diagnostics/research/audit_0025_tradelog.md`)
The pinned cache contains exactly **2 bad-tick bars** (INDIAMART Diwali-Muhurat sessions 2019-10-27 and
2020-11-14, price doubled then fully reversed). One 0025 trade half-booked on the phantom price.
**Sensitivity with the bars dropped: net Sharpe +0.393 / CAGR +2.55%** (record +0.397 / +2.82%) — verdict
unchanged (still below the bar); the honest CAGR is ~2.55%. baseline_v1 has one small INDIAMART trade whose
target exit plausibly fired on the same phantom bar (negligible to 0.667). Fix routes to the next dataset
pin (bad-tick screen), never to frozen f8625a8f. The audit otherwise verified timing, fills, sizing, and
cost accounting per-trade (all PASS) and logged the structural findings: half-book leg inert under 4×ATR
(8% ever book), 52% of P&L in 3 names, gap-through stop optimism ~0.3%/yr.

## Disposition
Swing-book work is COMPLETE: no experiment remains that could change this verdict in-sample (the next knob
is trial #2 of a search — forbidden). The strategy of record: **net ~+0.40 Sharpe, ~+2.8% CAGR, −12% MaxDD,
ρ~0.57 to base — a genuine low-drawdown partial diversifier that earns too little to stand alone.** Its
fate is the Oct-1 review (v1.5 Path-B proposal, promote/kill pre-committed) and the forward wall. The
arc's larger deliverable stands: the corrected universe itself, and the finding that survivorship bias
grows with holding period — which points the next honest measurement at baseline_v1.
