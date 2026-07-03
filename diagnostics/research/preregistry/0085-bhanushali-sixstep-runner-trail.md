# 0085 — Six-step runner management: ride the post-2R remainder on a 20-EMA −4% trail, 63d cap

- **ID:** 0085. **Status: PRE-REGISTERED** (spec frozen here BEFORE the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 102 → 103.
- **Anchor / data:** identical to 0084 — corrected universe (pinned + backfill + aliases), PIT membership,
  ADV-tiered real costs, window 2017–2026, EQ0 ₹10L. Script `scripts/run_bhanushali_sixstep_runner.py`
  (imports the frozen 0084 `prep`/funnel unchanged; only runner exits differ).

## Why this trial exists (lineage)
0084 showed the 44-SMA funnel's edge is exit-determined (0022 taught exits −1.6 → 0025 atr4 +0.397 →
0084 scaled+MA-breach +0.477) but its +3R cap truncates every winner at blended +2.5R while 2023-class
trends ran multiples further. Owner hypothesis: **let the post-half-book remainder ride a 20-EMA trail
instead of capping it at +3R.** This is a runner-management formulation not previously tested (0071/0076
tested let-run on the 63d momentum book, not this funnel; 0084's remainder was target-capped).

## The FROZEN spec (only the runner rules differ from 0084 — everything else byte-identical)

| Param | Frozen value |
|---|---|
| Entry funnel / sizing / costs / universe / no-rotation | **exactly 0084** (see pre-reg 0084 table) |
| Half-book | unchanged: first touch of +2R sells 50% of initial qty at the target |
| **Runner** | the remaining half after the +2R booking (positions that never reach +2R are NOT runners) |
| Runner target | **NONE** — +3R target removed for the runner |
| Runner MA-breach rule | **disabled** after the half-book (the trail replaces it) |
| Runner trail | stop = `max(stop_prev, EMA20_daily × 0.96)`, ratchet-only (never lowers), active from the session AFTER the half-book; exit at stop when `low <= stop` (gap-through logged, same fill convention) |
| EMA20 | `ewm(span=20, adjust=False)` on daily closes |
| Runner time cap | **63 trading days from ORIGINAL entry**; if still open, exit remainder at that session's close, reason `time` |
| Non-runners | exactly 0084: candle-low stop + 3-consecutive-close 44-SMA breach + no time cap |
| Same-bar precedence | stop/trail → tp2 (as 0084; trail checked in the stop slot) |
| Stats | block bootstrap (63, 5000, seed 12345); DSR at `cumulative_n_trials()` = 103; continuous slices |

Pre-declared sensitivity line (not an arm): drop the two pinned INDIAMART bad-tick bars, report both.

## Primary metric
**Corrected-universe NET Sharpe** (one number). References printed, not gates: 0084 +0.477 (same funnel,
target-capped runner), 0025 atr4 +0.397, baseline_v1 0.667. Secondary diagnostics: maxR distribution
(does the trail actually capture >+3R runners?), hold distribution, exit mix, per-year.

## Decision rule (pre-committed)
Same family rule as 0084: **PROMOTE→forward-wall watch** iff DSR@103 > 0.95 AND bootstrap CI-low > 0 AND
all three continuous slices > 0. Sharpe > 0 with CI straddling 0 or DSR ≤ 0.95 → **UNDERPOWERED**.
Sharpe ≤ 0 or any negative slice → **KILL**. Additionally recorded (informational, no gate): ΔSharpe vs
0084 on the identical universe/costs. No retuning; params frozen above.

## Skeptical prior (honest)
A 20-EMA −4% trail is TIGHT relative to this book's names (63d ATR ≈ 6–10%): the trail may give back less
but also cut runners at the first normal pullback, converting the +3R bank into many ~+2.2R exits — 0076
found trail-width is the sensitive knob and tight trails underperform. The 63d cap also truncates the very
tail the change is meant to capture. Expected: small |Δ| vs 0084, UNDERPOWERED either way. Worth one arm
because runner management is the owner's live question and the maxR distribution answers it directly.

---

## RESULT (appended 2026-07-04 after the run of record — spec above untouched)

| cell | trades | win | expR | hold med/p90 | CAGR | Sharpe | MaxDD | mult |
|---|---|---|---|---|---|---|---|---|
| corrected GROSS | 457 (48/yr) | 38.9% | +0.21 | 26/62d | +18.0% | +0.820 | −38.9% | 4.80× |
| **corrected NET (primary)** | 432 (46/yr) | 39.6% | **+0.23** | 29/60d | **+11.5%** | **+0.587** | −37.5% | **2.80×** |
| 0084 reference (same universe) | 476 | 38.7% | +0.18 | 22/55d | +8.6% | +0.477 | −37.2% | 2.19× |
| erratum-dropped NET | 432 | 39.6% | +0.23 | 29/60d | +11.5% | +0.587 | −37.5% | (no INDIAMART trade intersects the bad bars) |

- Slices: 2017-18* **+0.25** | 2019-21 **+0.73** | 2022-26 **+0.63** (all ≥ 0; 2022-26 nearly doubles 0084's +0.33).
- Bootstrap 95% CI **[−0.137, +1.188]**; **DSR@103 = 0.211**. Gates: slices PASS, CI-low FAIL, DSR FAIL.
- **ΔSharpe vs 0084 (informational): +0.110.** Exit mix: stop 149 | ma_breach 148 | trail 100 | time 29 | eos 6.
- Runners: 132/432; runner blended R mean **+2.12** (below the +2.5 the old cap guaranteed) but max **+8.37**
  and 33 runners > +2.5R — the tail more than pays for the trail's early cuts. Runner hold med 42d, max 97d
  (63 trading days ≈ 91 calendar; all < 365d → still pure STCG).

**VERDICT: UNDERPOWERED** (pre-committed rule: Sharpe > 0, all slices > 0, CI straddles 0, DSR ≪ 0.95).
Fourth exit-geometry datapoint on the funnel: taught KILL → atr4 +0.397 → scaled+MA-breach +0.477 →
runner-trail +0.587. Directionally the strongest yet and the 2022-26 slice improves most, but the
uncertifiability wall is unchanged. No cfg change; joins the Oct-1 review packet with 0084.
