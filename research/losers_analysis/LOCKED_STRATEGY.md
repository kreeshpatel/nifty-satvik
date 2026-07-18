# Locked strategy after Phase 1 (entry) + Phase 2 (exit) — the trade engine going into Phase 3 (sizing)

Owner decision 2026-07-15: lock the Phase-2 exit and proceed to Phase-3 sizing (implemented on the live/paper
book). This freezes the **per-trade trade engine** (entry + exit); **sizing/portfolio management is Phase 3**
and is the ONLY thing still open. All levers below are cfg-gated in `scripts/run_bhanushali_weekly_rank.py`;
the frozen 0094 golden run stays byte-identical with them off (1.132/255).

## ENTRY (locked = base 0094; Phase-1 verdict)
Weekly bars, decided on the completed weekly close, executed next-Monday first daily open in `[siglow,sighigh]`.
1. **Trend** — 44-wk SMA rising: `slope_63 = SMA/SMA[13wk] − 1 ≥ 0.03`.
2. **Pullback touch** — `wlow ≤ wsma×1.07` AND `wclose > wsma`.
3. **Quality green** — `close>open`, close in upper half of range.
4. **RS** — `RS > SMA40(RS)`, `RS = close/Nifty50`; fills strongest-CRS-first under the cap.
Stop = signal-week low.
> Phase-1 note: the deep-near-SMA touch (<5% ext, +1.0R core), the flat-base BOX breakout, and the pivot S/R
> breakout are all **positive-expectancy entries** but are **Phase-3 SIZING levers** (overweight / sleeves),
> NOT entry-filter changes — a hard <5% filter DEGRADES the capped book (CRS-rank already selects). So the
> locked ENTRY is the base touch; box/S/R/deep-near-SMA enter in Phase 3 as sleeves/weights.

## EXIT (locked = Phase-2 visual exit; adopted LIVE 2026-07-15, see ADR-0008 / finding 0099)
- Book **half at +2R** (`tp2 = en + 2×risk`).
- **NO time cap** (`no_time_cap=True`; 52-wk safety backstop) — the 13-wk cap severed live trends (the #1
  capture loss, validated on the random 60-trade map: 45% of winners cut early). **This is the main driver.**
- **Blow-off-bar exit after 2.5R** (`blowoff_arm_r=2.5`) — exit when a week makes a new high but CLOSES in its
  lower third (long upper wick = exhaustion) — banks the giveback cohort near the peak. **The second driver.**
- **20-week-close backstop** (`wk20_trail_pct=0.04`) — a *rarely-firing* wider backstop.
  **CORRECTION:** the config KEEPS the existing **20-DAY-SMA (`ema20`) ratchet trail** as the primary trail (it is
  the `elif p["half_done"]` branch, always active after the half books); the 20-week line is only a backstop. So
  this is NOT a "20-week replaces the 20-day bug" swap — the real drivers are **no-cap + the blow-off exit.**

**Reproduce (per-trade engine of record for Phase 3):**
```
P = prep_weekly_rank(ohlcv)                      # base entry
backtest(P, mem, start='2017-01-01', no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)
```
Trade-level result (size-independent): **168 trades, win 54%, meanR +0.616 (+28% vs base +0.481),
tradeSharpe 0.33**; amplifies trending years (2023 +1.80R), higher year-to-year variance (leans into the tape).
Per-year scorecard in `FORENSIC_FINDINGS.md`.

## PHASE 3 — SIZING & RISK (open; implemented on the live/paper book)
The trade engine is fixed; Phase 3 tunes HOW MUCH capital each trade gets. Levers to work through:
1. **Per-trade risk** (2% base) + a **max-stop / risk cap** (wide-stop blow-offs).
2. **Conviction overweight** — size UP the deep-near-SMA (<5% ext) touches (the +1.0R core); size down extended.
3. **Sleeve allocation** — separate capital buckets for touch / box-breakout / S/R so the additive setups
   diversify instead of starving the 15-slot cap (the recurring per-trade≠portfolio bottleneck).
4. **Capacity for longer holds** — the no-cap exit holds ~2× longer (168 vs 255 trades); needs more concurrent
   slots or faster rotation so good signals aren't skipped for cash.
5. **Vol-target de-gross** (O-009 / `vol_target`, already built) — shrink gross when trailing vol is high.
Phase 3 is judged on the **portfolio** (Sharpe/CAGR/MaxDD/Calmar) — sizing is exactly the entry→portfolio bridge.

## PHASE 3 — RESULT (2026-07-15): sizing is 2% risk, no caps — every other lever fails robustly
Wired `risk_pct` + `max_positions` sizing knobs (default off ⇒ 1.132/255). Locked-engine portfolio baseline
(2% risk, ₹10L): **Sh 1.034 / CAGR 21.2% / MaxDD −34.8% / Calmar 0.61** (vs base 0094 1.132/24.7/−42.4/0.58 —
already 8pp shallower DD, higher Calmar). Every sizing lever tested against it:
- **Per-trade risk:** 2% is optimal. Lower (1.0–1.5%, fit more trades) → Sh 0.79–1.01 (the ~19.7k skipped
  signals are LOW-CRS-rank noise; the fill already takes the best, so fitting more dilutes). Higher (2.5%) → 0.77.
- **max_positions:** KNIFE-EDGE OVERFIT — Sharpe jumps 7→1.155, 8→0.917, 9→0.928, 10→1.118, 11→0.940, 12–14→0.855.
  A 0.24-Sharpe swing per 1-position change = noise. REJECTED (do not tune).
- **Box/S/R sleeve (with capital):** dilutes Sharpe (0.855 in the stable maxpos range vs 1.034 touch-only);
  only helps DRAWDOWN (−32.5 vs −34.8, stable). A drawdown-only option, not a Sharpe edge.
- **Vol-target de-gross (O-009):** tighter targets (20/25%) → WORSE (0.85/0.94, cut returns > DD); loosest (30%)
  ≈ off. No lever.

**PHASE-3 VERDICT: sizing = 2% risk on the ₹10L book, no artificial position cap, no vol-target, no
Sharpe-sleeves — the disciplined answer, reached by rejecting the knife-edge overfits (reproduce-before-trust).**
The three-phase arc's net gain is a MORE DEFENSIVE strategy: DD −42.4→−34.8, Calmar 0.58→0.61, for a small
Sharpe/CAGR give — **the EXIT did the work; entry and sizing were already robustly optimal.** Box/S/R sleeve
remains a live/forward-wall DRAWDOWN option (−2pp DD at a Sharpe cost). Sizing DECISIONS (which of the
capital-constrained signals to take in real time) are the live-portfolio-management layer, per owner. New cfg:
`risk_pct`, `max_positions`. STRATEGY COMPLETE across all 3 phases; forward wall certifies live.
