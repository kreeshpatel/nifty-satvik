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

## EXIT (locked = Phase-2 visual exit)
- Book **half at +2R** (`tp2 = en + 2×risk`).
- **NO time cap** (`no_time_cap=True`; 52-wk safety backstop) — the 13-wk cap severed live trends (the #1
  capture loss, validated on the random 60-trade map: 45% of winners cut early).
- **Trail the remainder on the 20-WEEK close** (`wk20_trail_pct=0.04`) — exit on weekly close < 20wk-SMA×0.96
  once up ≥2R. (Fixes the real bug: the base trailed on `ema20` = a 20-DAY SMA.)
- **Blow-off-bar exit after 2.5R** (`blowoff_arm_r=2.5`) — exit when a week makes a new high but CLOSES in its
  lower third (long upper wick = exhaustion) — banks the giveback cohort near the peak.

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
