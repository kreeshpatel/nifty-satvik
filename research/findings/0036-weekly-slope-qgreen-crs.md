# 0036 — Slope + quality-green + CRS on the loose weekly book: lower return, MORE robust — the first entry-side change that didn't KILL

- **Status:** TRIAL (pre-reg [0093](../../diagnostics/research/preregistry/0093-weekly-slope-qgreen-crs.md),
  n_trials 110→111, params frozen before the run). **Verdict: UNDERPOWERED** — a genuine risk/return
  trade-off vs 0091, not a kill.
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_crs.py`; ledger
  `research/exports/bhanushali_weekly_crs_0093_trades.csv` (208 trades). CRS denominator = pinned N500 TRI
  (owner asked Nifty-50; unavailable in repo — caveat, confirmatory Nifty-50 run only if warranted).

## What was tested (owner spec after the 0092 KILL)
0091 base with: (1) slope floor kept (44w-SMA up ≥3%/13w), (2) tight band REMOVED → back to 0091's loose 7%
(the 0035 winner-killer), (3) quality green, (4) NEW comparative-RS filter — weekly RS = stock/index, take
the signal only if RS > its 40-week SMA.

## Result (corrected universe, real tiered costs)

| | trades | win | CAGR | Sharpe | MaxDD | Calmar | DSR | biggest-yr % |
|---|---|---|---|---|---|---|---|---|
| 0091 (loose) | 275 | 52% | **+18.2%** | **+0.869** | −41.5% | 0.44 | 0.466 | 49% |
| **0093 (CRS combo)** | 208 | 52% | +11.9% | +0.677 | **−36.8%** | 0.32 | **0.529** | **27%** |
| 0092 (tight band) | 194 | 41% | +0.5% | +0.142 | −61.0% | 0.01 | 0.003 | KILL |

Slices +0.00 / +0.81 / +0.77 (all ≥ 0). CI **[+0.050, +1.213] — CI-low > 0** (second variant of the arc to
clear it). Gates: CI-low PASS, slices PASS, DSR FAIL (0.529 < 0.95). Head-to-head vs 0091: ΔSharpe −0.192,
ΔCAGR −6.3pp, **ΔMaxDD +4.7pp better**. Per-year: nearly every year positive (only 2020 −₹0.2L); no
one-year lottery.

## Root-cause readout (REQUIRED)
1. **Removing the tight band recovered the return** (0092's +0.5% → +11.9%), confirming finding 0035: the
   tight pullback band was the winner-killer, not the slope floor or the green rule. The owner correctly
   diagnosed this from the charts.
2. **The CRS + slope combo traded ~6pp of CAGR for real robustness, not junk.** It didn't just cut trades —
   it cut the *right* ones: the book's **2023-concentration fell 49%→27%**, the **drawdown shrank
   −41.5%→−36.8%**, and it made money in **almost every year** (0091 lost in 2024 and 2025). The RS filter
   keeps names outperforming the index on a rising RS line, which skews the book toward steadier leaders
   and away from the junk-rally names that give the deep-DD years.
3. **DSR went UP (0.466→0.529) despite lower Sharpe and a higher n_trials bar** — because the return stream
   is smoother and less skewed (less reliant on one fat tail). On the multiple-testing-corrected metric,
   0093 is the *more* trustworthy of the two, even though its headline is lower.
4. **The CRS lever behaves differently here than in 0086.** On the daily 0085 book (0086) RS-vs-index hurt
   (ΔSharpe −0.14); here, on the weekly book with the loose band + slope + qgreen, it adds consistency
   without killing return. Context-dependent — the loose band leaves the winners in, so the RS filter only
   trims the low-quality tail. Not a contradiction of 0086; a different composition.

## Verdict & next setup
**UNDERPOWERED — and the first entry-side change of the arc that improved the book instead of killing it.**
It is NOT a headline win over 0091 (lower Sharpe/CAGR), but it is a genuine, defensible **risk-vs-return
trade-off**, and on the metrics that matter for *live deployment* — drawdown, year-to-year consistency,
one-year-dependence, and the DSR robustness score — **0093 is arguably the safer book to actually hold.**
The two are now the arc's co-candidates: **0091 = highest raw return (riskier, 2023-dependent); 0093 =
steadier, shallower DD, more robust (lower return).** Both UNDERPOWERED, both CI-low>0 — the forward wall
decides. Owner call which becomes the live forward book (or run both). Optional confirmatory step: fetch +
pin real Nifty-50 and re-run (the owner's intended denominator; N500 TRI used here as a correlated proxy).
No retuning; 3%/13w slope, 7% band, CRS-40 frozen.
