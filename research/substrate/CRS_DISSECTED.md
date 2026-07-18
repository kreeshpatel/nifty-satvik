# CRS-rank dissected — is its skill real, and how does it work? (measurement, no trial)

**Run 2026-07-16.** Reproduce: `python scripts/diag_crs_dissect.py 40`. Attacks the
0.67-vs-1.03 forward question **in-sample** (the forward wall is not the only instrument).

## 1. CRS's skill is REGIME-DEPENDENT, not universal

| period | CRS | null mean | null max | CRS percentile |
|---|---|---|---|---|
| **2017-21** | 0.79 | 0.56 ±0.23 | **1.30** | **87.5th — inside the noise** |
| **2022-26** | **1.29** | 0.74 ±0.23 | 1.24 | **100th — beats every draw** |

The headline "99-100th percentile" (full period) was driven **entirely by 2022-26**. In 2017-21 CRS is at
the 87.5th percentile and **12.5% of random draws beat it**.

**Reading:** this is NOT the signature of a pure in-sample artifact — a selector overfit on the full
period would look good in *both* halves, and it doesn't. But it is also **not reliably 1.03**. CRS's skill
is **real in the recent regime (2022-26) and unproven in the older one.** Since the near future more
plausibly resembles 2022-26 than the 2017-21 bull, this is moderately encouraging — but it caps how much
confidence the 1.29 deserves.

## 2. What CRS picks — relative strength IS extension

| bucket | CRS % of picks | random % | tilt |
|---|---|---|---|
| <0% | 0.6% | 1.4% | −0.8pp |
| 0-5% | 2.4% | 7.6% | −5.2pp |
| 5-10% | 9.5% | 18.2% | −8.7pp |
| 10-15% | 23.2% | 27.4% | −4.2pp |
| **>15%** | **64.3%** | 45.4% | **+18.9pp** |

**Two-thirds of CRS's trades are >15% above the SMA.** It systematically avoids the near-SMA buckets.

## 3. Where the skill lives — concentrated, not uniform

| bucket | CRS meanR | random meanR | edge | CRS N |
|---|---|---|---|---|
| 0-5% | 0.644 | 0.378 | +0.266 | 4 ⚠ thin |
| **5-10%** | **1.632** | 0.554 | **+1.078** | 16 ⚠ thin |
| 10-15% | 0.198 | 0.376 | **−0.179** | 39 |
| >15% | 0.607 | 0.310 | **+0.297** | 108 |
| **ALL** | **0.616** | **0.388** | **+0.228** | 168 |

- **CRS's per-trade selection edge is +0.228R** — real, and the source of its portfolio edge.
- It is **strong in the >15% bulk** (+0.297, N=108 — the trustworthy number) and **NEGATIVE in 10-15%**
  (−0.179).
- The **+1.078 in the dead 5-10% band rests on only 16 trades** — suggestive, not established. It is
  independently corroborated: removing that band collapsed CRS 1.29 → 0.47 (`POOL_vs_SELECTION.md`),
  which is only explicable if those few trades are load-bearing.

## 4. The paradox

CRS allocates **64% of picks to the >15% bucket (pool mean +0.31R)** while nearly ignoring the **0-5%
bucket (pool mean +0.58R)**. **It systematically allocates to the WORSE pool and wins anyway through
within-bucket skill.** That is the tension the pool test exposed, now quantified from both sides:
pool quality and CRS's tilt point in opposite directions.

## 5. The paradox RESOLVED — the tilt is a feature, not a bug

Two declared variants (R9: K=2), `scripts/diag_crs_stratified.py`, judged on the 22-26 gate:

| config | Sharpe | CAGR | DD | 22-26 |
|---|---|---|---|---|
| **A CRS as-is (LIVE)** | 1.03 | 21.2% | −34.8% | **1.29** |
| H1 stratified-CRS (tilt stripped; CRS %ile *within* bucket) | 0.82 | 16.0% | −39.7% | 1.10 |
| H2 bucket-prior (train-2019-21 meanR) + CRS tiebreak | 0.63 | 11.3% | **−61.7%** | 0.84 |

**Both LOSE to CRS-as-is.** Stripping the extension tilt costs 0.19; re-allocating toward the
"better" buckets costs 0.45 **and** blows the drawdown out to −61.7%.

**Why the paradox dissolves:** relative strength and extension are **the same phenomenon**. High-RS names
*are* extended — their extension is a *consequence* of the strength that makes them win. Bucketing by
extension decomposes the signal and destroys it. The 0-5% bucket's superior *pool average* is
**unreachable by selection**, because the property that makes a name selectable (strength) is the property
that pushes it out of that bucket. (Both variants still beat the random null 0.74 — within-bucket CRS
retains genuine skill — but raw CRS beats both.)

**Conclusion: CRS-rank as-is is the selector. Its tilt is load-bearing. Do not stratify, cap, filter, or
re-weight it** — every version tested (near_sma, ext_cap, pool filter, conviction ML, H1, H2) loses.
