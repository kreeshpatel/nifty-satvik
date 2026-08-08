# 0134 — Capital-preservation timing: nine fronts, all null (and the screen was underpowered)

**Date:** 2026-08-06 · **Class:** PIT screen (row 19, appended BEFORE results were read)
**Standing counts:** screens 19 · sealed opens 1 · n_trials 138.
**Verdict:** **NULL on all nine fronts.** No PIT market-state variable flags the 0133 family's bad
periods in advance at the pre-committed bar. **But the screen was underpowered by construction, so
this is "not demonstrable", not "absent"** — a limitation of the study design, stated against its
own conclusion.

---

## 1. Why this was asked, and why the obvious version was refused

The owner asked for a capital-preservation mode that stands the book down before a downturn,
predicted "from different fronts". 0133 §6b had already shown the naive version is **wrong-signed**:

| year | strategies positive | Nifty-50 |
|---|---|---|
| 2018 | 0/10 | **+3.2%** |
| 2025 | 0/10 | **+10.5%** |
| 2026 | 5/10 | **−8.7%** |

A perfect downtrend predictor would have gated the book out of 2026 and left it fully exposed
through 2018 and 2025. So the study did not build a downtrend predictor; it asked whether *any*
state variable, across four genuinely different mechanisms, separates good forward periods from bad
ones for this family.

## 2. Design

Target: **forward 63-day return of the equal-weight family factor** of the nine 0133 strategies —
legitimate as a single factor because their annual returns correlate at ρ=0.678 with 0 of 45 pairs
negative. Nine trailing-only variables across four fronts: DIRECTION (`idx_above_200`,
`idx_dd_252`), BREADTH (`breadth_200`, `breadth_50`, `breadth_chg_21`), PERSISTENCE (`persist_63`,
`newhigh_pct`), VOLATILITY (`rvol_63`), DISPERSION (`disp_63`). Continuous 2016-2026, 2,280 usable
observations.

Bar, all three legs required, fixed before the run: **|rank-IC| ≥ 0.10**, **Q5−Q1 block-bootstrap
CIs separate** (63-day blocks, 5k draws — the overlap confound was named in advance), **sign
consistent in ≥ 7 years**.

## 3. Result

| variable | rank-IC | Q5−Q1 | CIs | years | verdict |
|---|---|---|---|---|---|
| `disp_63` | **+0.237** | +3.88pp | overlap | 5/9 | null |
| `breadth_50` | **+0.186** | +3.78pp | overlap | 6/9 | null |
| `rvol_63` | **+0.148** | +3.99pp | overlap | **7/9** | null (2 of 3 legs) |
| `breadth_chg_21` | +0.093 | +2.96pp | overlap | 5/9 | null |
| `idx_dd_252` | −0.094 | −3.05pp | overlap | **7/9** | null |
| `newhigh_pct` | +0.086 | +5.17pp | overlap | 5/9 | null |
| `breadth_200` | +0.068 | +2.96pp | overlap | 5/9 | null |
| `persist_63` | −0.051 | −1.86pp | overlap | **8/9** | null |
| `idx_above_200` | +0.040 | +1.30pp | overlap | 5/9 | null |

**Every quintile CI overlaps.** Three variables clear the IC bar, three clear the year bar, only
`rvol_63` clears two, none clears three.

**The session's stated prior was wrong in both directions.** `breadth_chg_21` was predicted most
likely to pass and came in at IC +0.093 / 5-9 years; `idx_dd_252`, from the front predicted least
likely, was among the best on year-consistency. Recorded because a prior that is only checked when
it wins is not a prior.

## 4. The power caveat — stated against this study's own conclusion

2,280 daily observations of a 63-day forward window are approximately **36 independent windows**.
At that sample size the CI-separation leg was close to unpassable no matter what was true: the
block bootstrap correctly widened the intervals to reflect the overlap, and correct intervals at
n≈36 are wide. This is the same wall finding 0008 hit (~34 independent 63-day windows) and the same
one that closed the in-sample programme.

**So this null is a statement about what can be demonstrated on this data, not about the world.**
It is strong enough to refuse a trial — which is its job — and too weak to assert that market state
carries nothing.

## 5. Residue worth keeping

`disp_63` (cross-sectional dispersion of 63-day returns) has the strongest IC (+0.237) and matches
the mechanism theory that cross-sectional momentum needs dispersion to work at all. Per-year: good
years 2017 **0.241** and 2021 **0.280**; bad years 2018 **0.163**, 2025 **0.146**, 2026 **0.142**.
Directionally exactly right — and then 2023, a **+32%** family year, sits at **0.174**, inside the
bad-year range, and the year leg comes in at 5/9. One counterexample of that size on 9 observations
is fatal to the claim.

Also recorded: 2017 was the family's **best** year (+42.8%) at the **lowest** `breadth_200` (0.175),
which breaks the breadth story outright, though the low reading is plausibly a lagged artifact of
the 2016 drawdown leaving names below their 200DMA into early 2017.

## 6. What this means for capital preservation

**Timing is not the available lever.** Six independent instruments have now been pointed at market
regime for this programme (O-001, 0056, 0086, 0090, 0103, and now 0134 on a wholly new family with
a pre-committed bar), and none has produced a tradeable switch.

What remains, and is honest:
- **Structural de-risking** — smaller size, fewer slots, lower gross. Costs return roughly linearly
  and works with certainty, which is the opposite trade-off from timing.
- **The mechanical −50% halt** already in `forward/prereg.md` — a floor, not a forecast.
- **The Nifty>200DMA gate** priced in 0133 §5: −12.4pp MaxDD for ~3pp CAGR. Note this screen found
  `idx_above_200` to be the *weakest* of nine variables (IC +0.040), so that gate should be
  understood as a blunt exposure reducer, not a regime detector.

## 7. Do not re-test unless

1. **A different instrument with more independent observations** — a longer history, a second
   market, or a panel design that does not spend its power on 63-day overlap. Re-running these nine
   variables on this data is refused relitigation: §4 shows the bar was near-unpassable.
2. **Dispersion specifically**, if and only if it arrives with (1). It is the single most promising
   residue and it is not licensed by this study.
3. **A candidate with near-zero annual correlation to the 0133 family** (per 0133 §6b's collision
   rule) — that is a diversification question, not a timing one, and it is the better problem.

## 8. Reproduction

`scripts/diag_market_state_screen.py` — state construction, screen, per-year table, block bootstrap.
