# Unit resolution — which unit is money for this book

**Date:** 2026-08-06 · **Class: VERIFICATION/MEASUREMENT.** Zero trials, no new hypothesis, no
verdict reversed. **Counts frozen: screens 16 · sealed opens 1 · n_trials 138.**
Producer: [`scripts/diag_unit_resolution.py`](../../scripts/diag_unit_resolution.py) ·
evidence: `foundation_audit_2026Q3/unit_resolution.json`.

---

## The identity, and it is exact

Under risk-parity the engine solves `shares = sizing_eq × risk ÷ (entry − stop)` and **asserts** the
result on every fill (`run_bhanushali_weekly_rank.py:884, 889` pin risk at 2.00% ± 0.02%). Multiply
through by the price move:

```
gross P&L = shares × (exit − entry)
          = sizing_eq × risk × (exit − entry) ÷ (entry − stop)
          = sizing_eq × risk × R
```

> **Gross equity return = R × risk_fraction, exactly. Under this sizer R is not a ratio awaiting
> conversion to money — it IS money, at 2% of equity per R.**

Measured on the 6,245-signal population:

| cohort | N | corr(gross equity %, R × 2%) | max abs difference |
|---|---:|---:|---:|
| **never booked the +2R half** | **4,104** | **0.9999999970** | **0.056 pp** |
| booked the half | 2,141 | 0.9979716236 | 99.02 pp |
| all | 6,245 | 0.9980078381 | 99.02 pp |

The residual on the first row is R being stored to three decimals. **On 65.7% of the population the
identity is exact to floating point.**

### The one place it breaks — and it breaks in the book's favour

The engine credits the booked half at a **notional 2.0R**, not at the price it filled
(`R94:487-490`). The half is triggered by a weekly *close* at or above target and filled at the
*next session's open*, so in a trending week it routinely fills far above target:

| | value |
|---|---:|
| trades booking the half | 2,141 (34.3%) |
| R credited for the half | **2.0000** |
| R the half **actually** achieved (mean) | **3.0407** |
| median | 2.5577 |
| understatement per half-booked trade | **≈ 0.52 R** |

**Published R therefore UNDERSTATES realised money on a third of the population.** The engine is
conservative on winners, not flattering. This is the opposite of the direction the R-denominator
worry assumed, and it has never been written down.

### Cross-check against 0130

| | |
|---|---:|
| funded `sum_R` | +127.46 over 9.4867 yrs = **13.436 R/yr** |
| × 2% ⇒ implied **gross** equity return | **26.872 %/yr** |
| 0130's measured **net** equity return | **26.546 %/yr** |
| difference = cost drag | **0.326 pp/yr** |

Two independently computed routes agree to a third of a percentage point, and the gap is exactly the
cost the identity does not include.

---

## The three lenses on the same trades

| ext band | N | mean **R** | mean net % of **POSITION** | mean net % of **EQUITY** | median stop width |
|---|---:|---:|---:|---:|---:|
| `<0` | 93 | **+2.977** ① | **+5.098** ① | **+7.081** ① | 4.57% |
| `0–5` | 1,104 | +0.755 ② | +2.695 ③ | +1.678 ② | 4.97% |
| `5–10` | 2,498 | +0.256 ⑤ | +1.034 ⑤ | +0.442 ⑤ | 4.81% |
| `10–20` | 2,308 | +0.308 ③ | +2.496 ④ | +0.652 ③ | 7.76% |
| `>20` | 242 | +0.288 ④ | **+4.893 ②** | +0.585 ④ | 16.35% |

*(circled = rank within the column)*

| agreement | Spearman across bands | Pearson across all 6,245 trades |
|---|---:|---:|
| **R vs equity %** | **+1.000** | **+0.9944** |
| R vs position % | +0.700 | **+0.1837** |
| equity % vs position % | +0.700 | — |

> **R and % of equity are the same variable (ρ = 0.994) and rank every band identically.
> % of position is the outlier (ρ = 0.184 against R), and the band it promotes is `>20` — the
> widest-stop, largest-position cohort.**

The mechanism is not subtle: % of position divides by the position, and under risk-parity the
position is `2% ÷ stop width`. Dividing by it re-introduces stop width as a *numerator* effect, so
the lens rewards precisely the cohort that got the least capital.

---

## Conclusion, recorded

1. **For the uncapped record, R IS the money unit.** 1R = 2% of equity, exactly. Quoting an edge in
   R is quoting it in rupees, correctly scaled.
2. **% of position is the money unit only under equal-notional sizing.** It is the right lens for a
   book that sizes every name the same, and the wrong one for a book that does not.
3. **The two diverge ONLY where the notional cap binds** — i.e. in the live book, on **53.4%** of
   trades (binder §6). In the record, where the cap is at its signature default of `None`, they do
   not diverge at all.
4. **The equal-notional world is measured, and it is worse.** Finding 0130: **−10.83% of equity per
   year**, CI [−26.33, +4.74], 7 of 10 years the same sign. The lens under which the ext-band
   ordering "reverses" corresponds to a book that earns materially less.

## What this does NOT say

- It does not reverse binder §7. The **cap effect is real** and the live book genuinely collects
  less than the research measures; §7's rupee-weighted column remains the right yardstick **for the
  live capped book**.
- It does not license quoting R across cohorts with different stop widths *in the live book* — there
  the cap binds and the identity fails.
- It says nothing about which sizer should be used. 0130 measured that and it is a governance item.

## Cross-references

`DEFINITIONS_REGISTER.md` row 1 (R as a DOOR) · `oct1_binder_decisions.md` §6, §7, §8 ·
`research/findings/0130-sizing-exclusion-bound.md` · `foundation_audit_2026Q3/TRADE_POPULATION_CENSUS.md`
