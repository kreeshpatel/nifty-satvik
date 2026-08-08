# 0136 — Narrowing the universe: midcap is the WORST bucket, and selection subtracts in all three

**Date:** 2026-08-06 · **Class:** measurement. **`n_trials` unchanged at 138.**
**Standing counts:** screens 19 · sealed opens 1 · n_trials 138.
**Verdict:** **The hypothesis is refuted.** Restricting to a midcap-type bucket produces the
**lowest** CAGR of any cut, and in every bucket the strategy underperforms simply owning that
bucket equal-weight.

---

## 1. Design

PIT size buckets assigned **per date** from **trailing** 63-day median turnover within corrected
PIT Nifty-500 membership — LARGE (rank 1-100, ~Nifty-100 analogue), MID (101-250, ~Midcap-150
analogue), SMALL (251+). Names migrate between buckets over time exactly as they would have in life;
no hindsight curation. Strategy = Supertrend + Pivot (0133's survivor). Window 2017-2026 (2016
excluded per 0133 §3a-CORRECTION).

**The bar**: each bucket is benchmarked against **its own equal-weight buy-and-hold**, because
midcaps outperformed over this window and beating the Nifty-50 by holding midcaps is size beta, not
edge.

## 2. Result

**Benchmarks (equal-weight buy-and-hold):**

| | CAGR | Sharpe | MaxDD | names/day |
|---|---|---|---|---|
| NIFTY-50 | 11.95% | 0.787 | −38.4% | 50 |
| LARGE bucket | 15.80% | 0.842 | −52.8% | ~97 |
| MID bucket | 15.40% | 0.850 | −53.0% | ~145 |
| SMALL bucket | 15.59% | 0.954 | −56.6% | ~233 |

**The size bands are nearly identical (15.4-15.8%).** The premium over the Nifty-50 is the
*equal weighting*, not the size band — a useful negative result in itself.

**Strategy restricted to each bucket:**

| | CAGR | Sharpe | MaxDD | trades | meanR |
|---|---|---|---|---|---|
| UNRESTRICTED (all N500) | 10.08% | 0.644 | −33.3% | 994 | +0.20 |
| LARGE | 5.28% | 0.432 | −29.7% | 810 | +0.16 |
| **MID (the proposal)** | **4.78%** | **0.378** | −40.0% | 906 | +0.17 |
| SMALL | 14.62% | 0.900 | −34.9% | 996 | +0.27 |

**Midcap-only is the worst cut of all four**, and worse than the unrestricted universe it was
supposed to improve on.

**The comparison that isolates skill — strategy minus its own bucket:**

| bucket | ΔCAGR | ΔSharpe | verdict |
|---|---|---|---|
| LARGE | **−10.52pp** | −0.410 | selection SUBTRACTS |
| MID | **−10.62pp** | −0.472 | selection SUBTRACTS |
| SMALL | −0.97pp | −0.054 | selection SUBTRACTS |

**In every bucket, running the strategy is worse than owning the bucket.** SMALL comes closest to
break-even and still subtracts.

## 3. What this means

**Law: on this family, universe narrowing is not a return lever.** The three size bands earn
within 0.4pp of each other, so there is no size premium to harvest; what changes between buckets is
*which names get funded*, and that is composition noise. The earlier capacity result — every ADV
band beating the unrestricted run on the train window — was that noise, not a signal, and this
larger design reverses its sign.

**Bucket choice dominates strategy choice, and we cannot make it.** Per-year spreads between buckets
are enormous: 2022 runs LARGE −4.8% / MID −28.1% / SMALL +26.7% (a 55pp spread), 2020 runs LARGE
+5.9% / MID +51.2%. Choosing the right bucket ex ante is a harder timing problem than the one 0134
and 0135 already failed to solve.

**The one genuine thing the strategy does is reduce drawdown.** EW buckets run −52.8% to −56.6%;
the strategy runs −29.7% to −40.0%. In the SMALL bucket it delivers **Sharpe 0.900 vs the bucket's
0.954 with 21.7pp less drawdown** — nearly the same risk-adjusted return for materially less pain.
That is a real, if modest, Law VII trade and the only defensible use of the machinery found so far.

## 4. This is the third independent sighting of the same conclusion

| framing | receipt |
|---|---|
| index vs family | 0135 §5: NIFTY-50 11.98% / Sharpe 0.787 beats the nine-strategy family 5.09% / 0.412 on every axis |
| EW universe vs every strategy config | 0136: every EW bucket ~15.5% beats every strategy configuration (4.78-14.62%) |
| selection alpha, bucket-neutral | 0136: ΔCAGR −0.97 to −10.62pp — negative in all three buckets |

**The binding benchmark for this whole arc is passive ownership, and nothing has cleared it.**

## 5. On "our own universe of good stocks"

Legitimate PIT constructions are narrower than they sound: **size/liquidity** (this finding —
refuted), **fundamentals** (0108 — killed a profit+sales-growth universe filter), and **index
membership** (which is what Nifty-500 already is). Any list assembled from knowledge of which names
performed is survivorship bias by construction and cannot be tested here. A specific rule computable
from information available at the time remains testable on request.

## 6. Do not re-test unless

1. A **specific PIT-computable universe rule** not already covered by size, liquidity, fundamentals
   or index membership.
2. A candidate that **beats equal-weight passive ownership of its own universe** — §4 makes this the
   binding gate, and it is cheap to apply first.
3. Forward evidence.

## 7. Reproduction

`scripts/diag_universe_buckets.py` — PIT bucket assignment, per-bucket benchmarks, restricted runs,
skill spreads, per-year attribution.
