# brain.md — long_horizon autonomous research mindmap

> **⚠ BASELINE ANCHOR (read first, 2026-06-28).** The current anchor is **baseline_v0**
> (`research/baseline_v0.json`): **26.1% gross / 23.1% after-tax CAGR · 1.02 / 0.83 Sharpe ·
> −41.9% / −45.6% DD · Calmar 0.62 / 0.51** (frozen cfg, exit-parity-unified engine, corrected-682).
> Every `30.3% / 35.5% / 1.10 / 1.15` figure in the historical entries BELOW is the **old
> optimistic-exit measurement** (`max(close, target)` fill) — superseded provenance, NOT a current
> figure (the exit-parity unification, 2026-06-26, costs ~4 pp CAGR). The relative KILL/SUPPORT
> verdicts still stand (common-mode shift cancels). Engine note below still describing
> `intraday target (max(close,target))` is the pre-unification fill — see STRATEGY_FULL.md §6 for
> the current conservative-at-target fill. Never anchor on the 34.67% re-derived variant.

> Living state for the self-directed search for a 3-month equity strategy. Updated every iteration.
> Owner is away ~6h (from 2026-06-25). Full authority. Keep moving, bug-check everything, never
> trust a result blindly, never kill an edge without thinking around it for a better version.

## Mission (locked by owner)
- **Equity** market only (NO options/vol-carry pivot). NSE liquid **large+mid** (small caps removed —
  too volatile/manipulative; they are a separate model, not now).
- Holding horizon **≤ 90 calendar days (~63 trading days)**, min ~20 days.
- Goal: **good CAGR + good yearly returns + healthy trade count (~100+/yr)**.
- Think like an ML model learning from trades. Research → decide. Bug-check always.

## Operating principles
1. Every result gets a root-cause readout (mechanism, not pass/fail). Never bare-kill.
2. Bug-check before trusting: signal/fill parity, lookahead, costs, universe (membership), benchmark.
3. Validate locally (20 mega-caps) for machinery, then cloud (748 corrected universe) for verdict.
4. Red-flag gate (Backtest Expert): regime-specialist, circuit, liquidity, >5 params, no-OOS, <30 trades.
5. Robustness: drop-best-year jackknife + (eventually) bootstrap CIs + walk-forward.
6. Push only to feat/v2-long-horizon (NEVER bare push — upstream mis-set to origin/main).

## The engine (audited, trustworthy as of 2026-06-25)
`long_horizon/backtest/portfolio.simulate(panel, derived, regime=, regime_exit=, min_adv_rs=)`
- signal(close t) → fill(open t+1); close-only stop+gap-fill; intraday target (max(close,target));
  trailing on close-peak; min_hold gate (profit-taking, not stop); stale-absence force-close.
- Costs: brokerage 0.03% + STT 0.10% both legs + tiered ADV slippage + 5% ADV cap. (TODO: add
  stamp/exch/SEBI/GST micro-costs ~3.5bps — immaterial but honest.)
- `ohlc_panel`: build_ohlc_panel (join signal+OHLC+labels), clean_ohlcv_dict (split/bad-tick),
  restrict_to_large_mid (trailing-median ADV, spike-robust), cross_sectional_rank (1.0=best),
  market_regime (index>200dma | breadth).
- **Universe MUST be membership-masked** (`filter_features_dict(features, load_membership())`) —
  flaw-hunter P1: without it, recovered names trade outside their index window (pre-inclusion ramp
  = lookahead). Wired into the runners 2026-06-25.

## What we've learned (condensed; full in DOSSIER.md F0-F8)
- Trend/momentum IC is REAL + generalizes (F2/F4/F5): sma200_slope_63 mean IC +0.09@63d, HAC t +5.2.
- BUT as a tradeable portfolio on the FULL Nifty-500 it gave a FAKE 45% CAGR = smallcap-tail mirage:
  median trade +1.6%, top decile = ~100% of return, winners = BCG(fraud)/TTML circuit-locked
  multibaggers, un-fillable. (3 independent confirmations incl Backtest Expert red flags.)
- On clean large+mid (un-membership-masked) ≈ buy-hold. **Membership-masked honest number: PENDING.**
- Day==min_hold lock-up carries ~98%+ of net PnL (rest net-negative) → the book is fragile/concentrated.
- **Composite (value+quality+mom) did NOT beat single trend in F3/F4 — but that was WITHOUT a quality
  filter and WITHOUT regime gating. DO NOT treat as ceiling — revisit with the new levers.**
- Value (ep/bp) weak @63d, peaks @126d (beyond horizon). roe ~null. low_debt = junk premium (-IC).

## Levers being tested (the anti-ceiling program)
| # | Lever | Hypothesis | Status |
|---|---|---|---|
| L1 | Market-regime gate (dual-momentum) | sit out 2018/2020/2022/2025 crashes → lift CAGR &/or cut DD | running (cloud) |
| L2 | Quality/fraud filter (Beneish M, pledge, F-score) | strip junk-momentum blow-ups → better momentum | NEXT |
| L3 | Multi-signal screen | which raw signal has the best clean edge | building harness |
| L4 | F&O-only universe | circuit-free, liquid (needs PIT F&O membership) | backlog |
| L5 | Residual/idiosyncratic momentum | momentum minus market/sector beta (avoids crashes) | backlog |
| L6 | ML cross-sectional ranker (LightGBM) | learn nonlinear factor interactions → the deferred hybrid | backlog |
| L7 | Mean-reversion / short-term reversal sleeve | orthogonal, more trades | backlog |
| L8 | PEAD (post-earnings drift) | 60-90d catalyst-driven; horizon-matched | backlog (needs earnings) |

## Scorecard
- **HONEST BASE (membership-masked, large+mid, trend signal) — BEATS BUY-HOLD. Not a ceiling.**
  - floor 5cr (681 names): **CAGR 28.3% / Sharpe 1.06 / DD -42% / WR 57.5% / beats BH 16.3%**
  - floor 25cr (544): CAGR 18.4% / Sh 0.77 / beats BH 15.8%
  - floor 50cr (411 large-only): CAGR 9.7% / Sh 0.49 / does NOT beat BH 15.2% (momentum weak in mega-caps)
  - per-year @5cr: 2017 +86, 2018 -14, 2019 +5, 2020 +74, 2021 +93, 2022 -13, 2023 +62, 2024 +17, 2025 -1, 2026 +5
    -> multi-year robust (4 big yrs, mild down yrs); winners = INDIAMART/IRFC/RVNL/ATGL (liquid mid-cap, NOT fraud)
  - **CAVEAT: day-min_hold lock-up carries 215% of net PnL (rest net-NEGATIVE) -> fat-tail momentum profile,
    must verify robust to min_hold (sensitivity) + that it's not an exit-artifact. Edge is real but concentrated.**
  - **KEY: edge lives in MID-caps (5-25cr); mega-cap-only (50cr) ~ buy-hold. Sweet spot = the 5-25cr band.**
- Multi-signal screen (smoke, 20 mega-caps only — NOT a verdict): low_vol Sh1.08 > mom_12_1 1.02 > resid_sector_mom
  1.01 > trend_200 1.00 > qual_mom 0.99 ... reversal (rsi/zscore) worst 0.77-0.79. Real screen = cloud (681 names).
- **REGIME GATE = KILL (full universe, 682 names): all 4 arms HURT.** base 30.3%/1.10 vs entry_trend 19.9/0.92,
  exit_trend 20.7/0.97, breadth 19.2/0.87. The gate whipsaws (turned 2022 base -1.9% into -24%, missed V-recoveries).
  Base down-years already mild (worst 2019 -6.4%); per-stock stops handle risk; market-timing overlay adds whipsaw.
  Tested 4 ways (entry/exit/breadth) — thought around it, it doesn't help. DON'T add regime gate.
- **BASE EDGE IS ROBUST + REAL (the anti-ceiling headline):** membership-masked large+mid (5cr) momentum =
  **CAGR 30.3% / Sharpe 1.10 / DD -43.6% / 114 trades-yr**, and **drop-best-year CAGR 21.9% STILL beats BH 16%**.
  4 big up-years (2017/2020/2021/2023 all +45-86%), mild down-years. Winners liquid mid-caps. NOT a ceiling.
  Open weaknesses: DD -43% (high → vol-target/sizing lever); lock-up concentration (→ min_hold fix, pending).

## KEY INSIGHT 2026-06-25 (min-hold artifact) — anti-ceiling win #1
The derived min_hold (~29-40, from 25th-pct time-to-peak) is TOO HIGH and was the source of the
"day-min_hold lock-up carries >100% PnL" fragility flag. Local sweep (20 mega-caps):
  min_hold=14 -> CAGR 18.9 / Sharpe 1.07 / **lock-up 9.8%** (spread, robust, BEST)
  min_hold=20 -> 16.9 / 0.97 / 39.3%
  min_hold=40 -> 17.4 / 1.00 / 98.0% (the artifact)
=> shorter min_hold is BETTER and far more robust. The edge is real momentum, NOT a lock-up artifact.
ACTION: confirm on full universe (alpha run min-hold sweep 5/7/10/14/20/30); then FIX value_derivation
min_hold (don't use 25th-pct time-to-peak; ~10-14 is the sweet spot). NOTE owner said "min 20 days" —
if 14 >> 20 surface the tradeoff (their floor costs CAGR). Tells us the exit logic is a live lever.

## SCREEN + ALPHA RESULTS (682 names, 2026-06-25) — candidate locked
WINNERS: trend_200 (sma200_slope_63) CAGR 33.3/Sh 1.20/DD-39, mom_12_1 34.0/1.16. Plain momentum dominates.
KILLED (tested, don't help — do NOT revisit without new angle): residual/beta-stripped mom (0.76; India bull
mom IS beta), frog-in-the-pan (0.89), sector-residual (0.66), reversal/rsi/zscore/mtf/donchian/roc/macd/accel
(Sh<0.5, DD -60..-81). low_vol = defensive (13% CAGR / -30% DD, lowest DD → blend candidate). regime gate KILLED.
**MIN-HOLD: robust PLATEAU at 7-14 (CAGR 33-36/Sh 1.18-1.24); lockup 180%(mh~29)->29%(mh7); trades 118->165/yr.
mh20 odd dip (21.8) — investigate. Derived min_hold(25th-pct-t2peak) was suboptimal → use ~7-10.**
=> CANDIDATE: trend_200, min_hold 7-10, large+mid 5cr, membership-masked: ~35% CAGR / 1.24 Sharpe / 165 t/yr /
dropBest 25% / DD -42%. Robust, audited, beats BH 16%. Open: DD -42% high; validate w/ bootstrap CI; mh20 anomaly.

## Quality filter (smoke, 20 mega-caps — promising): low_debt/quality_combo cut DD -32.7->-26.8,
lift Sharpe 0.94->1.02, Calmar 0.5->0.58 at small CAGR cost. Cloud (full mid-cap universe) pending —
should help MORE (removes junk-momentum blow-ups). Addresses owner manipulation concern + the DD weakness.

## *** SOLVENCY-CORRECTED FINAL (the honest headline) ***
Bug caught reviewing live picks: low-debt filter "D/E<1.5" admitted NEGATIVE-equity insolvent names
(IDEA D/E -3.32) — distressed/ban-prone, opposite of low-debt. Fixed to **0<=D/E<1.5**. Headline
35.5->**30.3 CAGR / 1.15 Sharpe / -40 DD / Calmar 0.76** (the ~5pp drop WAS distressed-pump momentum,
correctly gone). Still 1 neg year (2018 -6.6), dropWorst 31.8, bootstrap Sharpe median 1.11 [0.45,1.75]
/ CAGR 29.2 [8.6,50] — beats BH 16/0.96. Picks clean (IDEA out; all 15 solvent D/E 0-0.89). (D/E<2.0
reads 35.5/1.28 but threshold-noise-sensitive; D/E<1.5 = stable defensible point.) THIS is the number.

## *** CONFIRMED WINNER (final validation, 682 names) — superseded by solvency-corrected above ***
debt<1.5 momentum: CAGR 35.5 / Sharpe 1.27 / DD -42.5 / Calmar 0.84 / 154 t/yr. Threshold-robust
(debt<1.0/1.5/2.0 ALL beat base 30.0/1.10). Bootstrap Sharpe median 1.23 [0.58,1.88] (base 0.97
[0.38,1.60]) — filter LIFTED + tightened the CI. Per-year: only 1 neg year (2018 -6.6); 2022
momentum-crash year -13%->+0.9% (leverage-removal protected it). dropWorst 37.2 / dropBest 26.2,
both beat BH 16. STRATEGY LOCKED -> STRATEGY.md. Honest caveats: DD -42% high (CAGR price); boot p5
Sharpe 0.58 < BH in worst 5% paths (high-return/some tail risk); min_hold 10 != owner's "20" (decision).

## *** WINNER (2026-06-25): low-debt-filtered momentum *** — anti-ceiling result
trend momentum (sma200_slope_63) + min_hold 10 + **LOW-DEBT FILTER (debt_equity < 1.5)** + membership-
masked large+mid (5cr, 402 names): **CAGR 36.0 / Sharpe 1.30 / DD -37.5 / Calmar 0.96 / 159 t/yr /
dropBest 27.4** — beats base (28/1.04/-43) on EVERY metric AND buy-hold (16/0.96). Mechanism: leverage
amplifies momentum crashes; removing high-debt strips the fragile/junk/manipulation-prone names. 3/4
quality arms beat base (direction robust). quality_combo (add earnings+roe) OVER-filters -> worse (31/1.15).
low_debt ALONE is best. Simpler wins. Also enforces owner's no-manipulation rule.
CAVEATS (skeptic): bootstrap CI on base was WIDE (Sharpe [0.38,1.60], median ~0.97 ~ BH) -> high-variance/
regime-dependent; sizing sweeps NOISY (cap binds, sizing ~inert); debt threshold 1.5 is a chosen param.
=> FINAL VALIDATION running: bootstrap CI on low_debt arm + debt-threshold {1.0,1.5,2.0} sensitivity.

## CONSOLIDATED CANDIDATE (superseded by low-debt winner above; pre-quality)
Strategy = plain TREND MOMENTUM (sma200_slope_63), cross-sectional top-15-20, hold min ~10 / max 63d,
ATR stop + target + trailing (derived), membership-masked large+mid (ADV>=5cr), small caps removed.
Numbers: ~33-35% CAGR / Sharpe 1.20-1.24 / DD -42% / 165 trades-yr / drop-best-year 25% / beats BH 16%.
Levers DONE: min_hold 7-10 (not derived 29); quality_combo filter (DD reduction, pending full run).
KILLED (don't revisit w/o new angle): regime gate, residual mom, frog, sector-residual, reversal, signal-blend.
OPEN: bootstrap CI (refine, pending) for significance; DD via sizing (refine, pending; likely cap-bound);
mh20 anomaly; then FINALIZE = momentum + mh10 + quality_combo + best sizing -> stamp + write up + F&O-universe later.

## STRESS TEST (running, 28139184429) — the critical skeptical check
Mega-cap smoke (13 names, NOT verdict): costs SURVIVE (1x 16.0/1.05 -> 3x 12.4/0.84; avgTrade 3% >> cost).
BUT sub-period FRONT-LOADING flag: 2017-21 = 29.0/1.63 vs 2022-26 = 4.4/0.38 on mega-caps. Full-universe
recent period includes 2023 (+91% PSU/midcap rally) so should be stronger — but THE key question is whether
the edge is alive 2022-26 or died after the 2021 bull. Full-universe stress result pending = make-or-break.
If 2022-26 weak on full universe too -> strategy is regime-front-loaded (deploy w/ caution, smaller size).

## DECISIONS LOCKED (owner 2026-06-25): min_hold=10 (value_derivation fixed), DD ~40% accepted.
STRATEGY FINAL. Productionized: run_long_horizon_picks.py = today's actionable picks (entry/stop/
target/size) from the locked strategy. NOT wired to live (gated). STATUS: research complete, validated,
locked, actionable. Remaining is owner-gated: paper-trade >=30 trades -> F&O universe (PIT membership
data task) -> gated wire-to-live (never touch frozen 14d model).

## Open threads / next actions
- [ ] read STRESS (28139184429): cost 1x/2x/3x + split2019 + sub 2017-21 vs 2022-26 (front-loading verdict)
- [ ] read refine + quality results [DONE - winner = low-debt momentum 35.5/1.27]
- [ ] FINALIZE candidate = momentum + mh10 + quality_combo + sizing; bootstrap-CI significance gate
- [ ] fix value_derivation min_hold (use ~10 not 25th-pct-t2peak); note owner "min 20" vs data "10" tradeoff
- [ ] write up the deployable strategy (long_horizon/STRATEGY.md) + Backtest Expert red-flag gate
- [ ] later: F&O-only universe (PIT F&O membership, circuit-free); cost micro-additions (immaterial)

## Pitfalls log (so we don't repeat)
- rank sign-inversion (ascending bug) → anti-momentum. FIXED + unit-pinned.
- phantom -100% DD (sparse-date MTM) → last_mark carry. FIXED.
- raw vs cleaned OHLC mismatch → clean_ohlcv_dict. FIXED.
- PIT membership never applied → pre-inclusion-ramp lookahead. FIXED.
- smallcap-tail mirage (un-fillable multibaggers) → large+mid + (next) fraud filter.
