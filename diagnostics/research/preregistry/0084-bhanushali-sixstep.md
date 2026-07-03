# 0084 — Bhanushali "six-step" owner variant: two-stage weekly→daily funnel, 2R/3R partial exits, 44-DMA-breach trail

- **ID:** 0084. **Status: PRE-REGISTERED** (spec frozen here BEFORE the run; no retuning under any outcome).
- **Registered:** 2026-07-03, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 101 → 102.
- **Anchor / data:** **corrected universe** (pinned `data/ohlcv.pkl` f8625a8f + `data/ohlcv_backfill.pkl` +
  `data/delisted_alias_map.json` via `corrected_universe()`), window 2017-01-01..2026, PIT Nifty-500
  membership. Script `scripts/run_bhanushali_sixstep.py`. Corrected universe is MANDATORY for this trial:
  it has no time cap (long holds), and finding 0025 measured survivorship bias scaling with holding period.

## Why this trial exists (lineage — what is NEW vs the closed 0022/0025 arc)
Owner-directed reconstruction of the taught "6-step" process from the source videos. The registry already
settled: 0022 (exact taught exits — candle-low stop, 1:2, 3–10d hold → break-even gross, cost-killed net),
0024 (practitioner process), 0025 (4×ATR geometry on corrected universe → net +0.397, 0.003 under its bar).
**This formulation differs precisely where 0025 located the live question — exit geometry:**
scaled partial exits (half at +2R, rest at +3R), a 3-consecutive-close 44-DMA-breach trail, **no time cap**,
**no rotation** (positions die only by exit), plus the explicit weekly-bucket→daily two-stage funnel
(44-WEEK SMA bucket, not the daily-only 0022 Engine-B gate). Not a relitigation of the killed spec.

## The FROZEN spec (locked — every parameter fixed before the run)

| Param | Frozen value |
|---|---|
| Weekly bar | `resample("W-FRI").agg({Close: last})` |
| Weekly bucket | weekly close > 44-week SMA AND `wsma > wsma.shift(4)` (house "rising"); ffilled to daily |
| Daily trend | `_rose(dsma44, 10)` (daily 44-SMA up over ~2 weeks) |
| Pullback touch | `low <= dsma*1.02 AND close >= dsma*0.98` (0022 BAND=0.02) |
| Touch→signal window | touch within the last 10 sessions, touch candle inclusive (`rolling(11).max()`) |
| Signal candle | green (`close>open`) AND `close >= dsma` AND daily trend AND weekly bucket, all at the candle; PIT member |
| Entry order | buy-stop at signal-candle high (exact); order lives 3 sessions (T+1..T+3); fill `max(open, trig)`; no gap-skip |
| Initial stop | signal-candle low × 0.999 (never moved — no breakeven floor; spec forbids additions) |
| Exit 1 | `low <= stop` → remainder out at stop (gap-through logged, faithful stop-fill convention) |
| Exit 2 | `high >= entry+2R` → sell 50% of initial qty at target; stop unchanged |
| Exit 3 | after half: `high >= entry+3R` → remainder out at target (same-bar with Exit 2 allowed); blended R = 2.5 |
| Exit 4 | 3 consecutive daily closes < daily 44-SMA (counted from fill session) → remainder out at NEXT open |
| Same-bar precedence | stop → tp2 → tp3 |
| Time cap / rotation / MAXPOS / notional cap | NONE (cash is the only capacity constraint); end-of-window force-close tagged `eos` |
| Sizing | 2% of current equity risk per fill, `qty = eq*0.02/(entry−stop)` (fractional); skip fill if notional+cost > cash (order stays live) |
| Fill priority | pending orders iterated sorted `(signal_date, ticker)` (determinism — 0025 lesson) |
| Costs per leg | `BROKERAGE_PCT + STT_PCT + leg_slippage(adv20 @ signal day, notional)` (ADV-tiered; adv NaN → SMALL_CAP); same adv both legs |
| Equity / window | EQ0 = ₹1,000,000; START 2017-01-01 |
| Stats | block bootstrap (block 63, n 5000, seed 12345); DSR at `cumulative_n_trials()` = 102; continuous-slice sub-periods only |

Pre-declared sensitivity line (not an arm, not a tune): re-run dropping the two pinned INDIAMART bad-tick
bars (2019-10-27, 2020-11-14 — the 0025 erratum); report both numbers.

## Primary metric
**NET Sharpe on the corrected universe** (ONE number). Everything else — CAGR, MaxDD, win rate, expR,
exit mix, hold distribution, realized-risk distribution — is secondary/diagnostic. The survivor-only NET
run of the same frozen config is printed as an informational universe-axis reference (0025 precedent),
not a second arm. 0025's corrected-net +0.397 (atr4 geometry) printed as a reference line, NOT a gate.

## Decision rule (pre-committed)
- **PROMOTE → forward-wall watched sleeve** iff ALL of: DSR@102 > 0.95, block-bootstrap Sharpe CI-low > 0,
  AND all three continuous slices (2017-18 / 2019-21 / 2022-26, sliced from the ONE run) > 0.
- CI-low > 0 and Sharpe > 0 but DSR ≤ 0.95 (or a slice marginal) → **UNDERPOWERED**.
- Sharpe ≤ 0 or any negative slice → **KILL**.
- A PROMOTE routes to the forward wall (multi-sleeve fork), never to the frozen cfg. **No retuning.**

## Skeptical prior (honest)
The candle-low initial stop is the component 0022 identified as the killer (noise-stopped at 36–37% win).
The MA-breach trail + partials may rescue expectancy the way 0025's wide stop did, but the entry funnel is
tighter than 0024's (bucket + touch window), so trade count may be low → wide CI. Most likely outcome:
**UNDERPOWERED or KILL**. If it beats 0025's +0.397 net with the candle-low stop intact, that is genuinely
new information about the exit-geometry lever. Verdict recorded as-is; params frozen.

---

## RESULT (appended 2026-07-03 after the run of record — spec above untouched)

| cell | trades | win | expR | hold med/p90 | CAGR | Sharpe | MaxDD | mult |
|---|---|---|---|---|---|---|---|---|
| corrected GROSS | 492 (52/yr) | 39.2% | +0.20 | 22/54d | +18.3% | **+0.838** | −39.4% | 4.91× |
| **corrected NET (primary)** | 476 (50/yr) | 38.7% | +0.18 | 22/55d | +8.6% | **+0.477** | −37.2% | 2.19× |
| survivor-only NET (ref) | 440 | 38.6% | +0.16 | 23/57d | +6.3% | +0.394 | −43.7% | 1.79× |
| erratum-dropped NET (sensitivity) | 494 | 39.7% | +0.19 | 20/55d | +9.3% | +0.502 | −34.6% | 2.33× |

- Continuous-slice Sharpe: 2017-18* **+0.05** | 2019-21 **+0.94** | 2022-26 **+0.33** (all ≥ 0).
- Bootstrap 95% CI **[−0.219, +1.177]** (straddles 0). **DSR @ n_trials=102 = 0.085.**
- Gates: DSR>0.95 **FAIL** | CI-low>0 **FAIL** | all slices>0 **PASS**.
- Exit mix: ma_breach 177 + 30 half | stop 163 + 2 half | target3 99 | eos 5. Realized risk = 2.000% on
  every fill (p5=p95=2.000; the 0022 under-sizing bug provably absent). Gap-through stops: 24 (logged).
  Cash-skip retries 79,116 — the book is chronically fully invested; capacity, not signal supply, binds.
- Determinism: two consecutive runs byte-identical on all headline lines.

**VERDICT: UNDERPOWERED** (per the pre-committed rule: Sharpe > 0, no negative slice → not a KILL; CI
straddles 0 and DSR 0.085 ≪ 0.95 → not certifiable). Point estimate sits ABOVE the 0025 atr4 sleeve
(+0.477 vs +0.397) with the candle-low stop retained — the MA-breach trail + scaled exits are doing the
work 0025's wide stop did — but the difference is far inside noise. No cfg change; candidate routes to the
2026-10-01 review alongside the Path-B sleeve proposal, forward wall the only certifier.
