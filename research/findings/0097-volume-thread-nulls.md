# 0097 — Volume thread: three nulls on the swing book (HVC A+, vol ranker, vol filter)

**Date:** 2026-07-13
**Type:** MEASUREMENT (no trade decision promoted → **not a trial**; n_trials stays 114)
**Book:** Bhanushali weekly-swing, ranker of record `0094` (CRS-strength fill), corrected universe,
NET after costs, 2017-01-02 → 2026-06-29.
**Motivation:** owner hypothesis — "A/B grading is too shallow; use a daily-HVC sweep to find A+ names."
Adjacent owner question — is a volume-confirmation filter useful on the raw pool?
**Skills applied:** `backtest-rigor` (§C1b plateau-not-peak, §E1 sample floor), `quantitative-research`
(IC, t-stats), `indian-market-execution` (cost model unchanged).

## Result — REJECT all three

### (a) HVC as an A+ sub-grader — NULL, wrong-signed, underpowered
Split the **actual traded A book** (239 trades, expR +0.413) by setup-week volume ÷ trailing-L-day avg,
L ∈ {10,15,20,30,44,63,100,150}; median split, high-vol (A+) vs low-vol (A−) mean-R:

| L | IC | A+ meanR | A− meanR | A+ − A− | t |
|--:|--:|--:|--:|--:|--:|
| 20 | −0.094 | +0.298 | +0.529 | −0.231 | −1.14 |
| 44 | −0.118 | +0.235 | +0.593 | −0.358 | −1.78 |
| 100 | −0.082 | +0.265 | +0.563 | −0.298 | −1.48 |

Negative IC at **every** length, consistent sign, but **all |t| < 2** → null with a weak "quiet-pullback
beats climactic-volume" lean. The A pool (~26 trades/yr) sub-grades to ~13/yr — below the §E1 floor.

### (b) 20d momentum / volume as a RANKER — IC without spread
Pooled (2,703 entries), Spearman IC vs realized R and Q5−Q1 mean-R spread:

| Feature | IC | Q5−Q1 |
|---|--:|--:|
| crs (incumbent) | +0.080 | +0.260 |
| roc20 | +0.058 | **+0.007** |
| volsurge | +0.059 | +1.149 (driven by Q1 = −0.84, i.e. *avoid* low-vol, not *pick* high-vol) |
| roc20 × vol | +0.048 | **−0.066** |

roc20 rank-orders (real IC) but has **no tradeable top-vs-bottom spread**; the combo goes negative. CRS
stays the best-IC ranker — and still doesn't convert to a portfolio win (proved separately: top-5-CRS
Sharpe 1.003 < field 1.132). **IC ≠ Sharpe.**

### (c) Volume FILTER on the raw pool — narrow peaks, book-inconsistent (C1b overfit)
Keep entries with setup-week vol ≥ k × trailing-20d avg; k-sweep, NET, both books:

| k | all-grades Sharpe | A-only Sharpe |
|--:|--:|--:|
| 0.00 (base) | 1.132 | 1.003 |
| 0.70 | 0.974 | **1.099** |
| 0.85 | **1.125** | 0.914 |
| 1.00 | 0.858 | 0.913 |
| 1.30 | 0.673 | 0.710 |

The two "wins" are **narrow peaks** — each collapses > 0.15 Sharpe one step either side — at
**different thresholds per book** (0.85 vs 0.70), **non-monotone**. Textbook `§C1b`. The filter also
*reshuffles* which names fund (trade count rises with k) rather than cleaning the pool. REJECT.

## Root cause (the through-line)
The 6-step Bhanushali filter + CRS rank + ADV≥5cr liquidity floor **already absorbs whatever volume was
proxying for.** Volume is real in the *raw* cross-section (bottom-vol entries are genuinely bad) but adds
nothing *on top of* an already-elite, already-liquid, already-in-uptrend pool. This is the same wall the
whole technical zoo hit at 63d (0079/O-015) and the USD-tilt hit (0082): a good filter eats the signal the
next filter hoped to find.

## Process note (a real bug caught by rigor)
The first HVC sweep scored the **uncapped** ledger's A signals (626 trades, meanR −0.742) — a population we
do **not** trade. The `backtest-rigor` reflex ("number way off a known prior → halt") caught it: the real
A book is 239 trades at +0.413. Rerun on the correct population flipped the result from a spurious unstable
signal to a clean null. Recorded as a reminder that population definition precedes any IC.

## Disposition
- Grading stays **CRS-only**; the single-sleeve volume avenue is **closed** (see `forward/prereg_swing.md §7`).
- The A-only-vs-all-grades product decision is routed to the **forward wall** (`forward/prereg_swing.md`),
  not another in-sample cut.

## Next setup
None on the single sleeve. The next unbiased bit comes from the forward wall's first read (2026-10-01).
