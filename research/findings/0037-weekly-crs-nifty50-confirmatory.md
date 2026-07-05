# 0037 — CRS on the owner's intended Nifty-50 (full 2015 data): the program's strongest, most robust book — still UNDERPOWERED, but by a hair

- **Status:** CONFIRMATORY MEASUREMENT of pre-reg [0093](../../diagnostics/research/preregistry/0093-weekly-slope-qgreen-crs.md)
  (the Nifty-50 run the 0093 pre-reg explicitly pre-committed to — NO new n_trials; same hypothesis, intended
  index + complete data). **Verdict: UNDERPOWERED** (DSR 0.745 < 0.95) — but the closest to certification and
  the most robust result of the entire program.
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_weekly_crs.py --nifty50`. New pinned data:
  `research/exports/benchmark_nifty50.csv` (^NSEI daily, **2015-01-02 → 2026-07-03**, fetched via yfinance).

## What changed vs the 0093 run of record
0093's pre-reg noted the N500 TRI was a **proxy** (only starts Sep-2017) for the owner's intended **Nifty-50**,
and pre-committed to a confirmatory Nifty-50 run. Fetched Nifty-50 back to 2015 so the CRS 40-week SMA warms
before 2017 (closing the data hole that handicapped the TRI run to a mid-2018 start). Config otherwise
identical: 0091 loose band + slope floor (≥3%/13w) + quality green + CRS (RS = stock/index > its 40-week SMA).

## Result (corrected universe, real tiered costs, full 2017–2026)

| | trades | CAGR | Sharpe | MaxDD | Calmar | CI-low | DSR | slices | biggest-yr |
|---|---|---|---|---|---|---|---|---|---|
| **0093 + Nifty-50** | 247 | **+18.7%** | **+0.900** | −42.5% | 0.44 | **+0.274** | **0.745** | +0.95/+0.83/+0.93 | 39% |
| 0091 (loose) | 275 | +18.2% | +0.869 | −41.5% | 0.44 | +0.20 | 0.466 | all + | 49% |
| 0093 + TRI (proxy) | 208 | +11.9% | +0.677 | −36.8% | 0.32 | +0.05 | 0.529 | all + | 27% |
| Nifty-500 TRI (buy-hold) | — | +12.6% | — | −38.1% | — | — | — | — | — |

**Highest of the entire arc on every axis** — Sharpe, CAGR, CI-low, DSR, slice-consistency — and it beats
buy-and-hold decisively. First trade 2017-01-30 (no hole). Only **2 losing years** (2022 −3%, 2025 −9%);
makes **+32% in 2024 where 0091 LOST −5.6%**.

## Robustness battery (the checks that killed 0085's headline — all pass)
- **Plateau, not a peak:** 3×3 sweep slope{2,3,5%} × CRS-len{30,40,50} — **all 9 cells viable** (Sharpe
  +0.71…+0.98, CAGR +14…+20%). The frozen 3%/40 cell (+0.900) isn't even the top (5%/40 = +0.976). Genuine
  ground, unlike 0085's spike-on-a-cliff.
- **Concentration BETTER than 0091:** biggest year 2023 = **39%** (vs 0091's 49%); top-10 trades **64%**
  (vs 71%); 188 names.
- **Leakage-clean:** CRS = trailing 40-week SMA of RS, index ffilled to each date — no lookahead (same PIT
  structure cleared in finding 0029; SMAs trailing).

## Root-cause readout — why the index choice swung it +0.68→+0.90
The CRS is highly sensitive to the denominator, and that is a *real structural* effect, not an artifact:
mid-caps outperform the **large-cap Nifty-50** far more readily than the **broad Nifty-500** (which contains
the same mid-caps). So RS-vs-Nifty-50 admits the strong mid-cap trends 0093-vs-TRI screened out — it catches
2023's frenzy (+68% vs the TRI version's +28%) while KEEPING the consistency (still only 2 losing years, 39%
concentration). The plateau confirms the Nifty-50 version is itself robust across params. Net: the correct
index recovers 0091's return AND retains the CRS's robustness gains. The owner's original "use Nifty-50"
instinct was right; the TRI was a genuinely poor proxy.

## Verdict & next setup
**UNDERPOWERED (DSR 0.745) — not certified — but decisively the best and most robust book the program has
produced, and the owner's actual intended spec.** It clears CI-low>0 and all slices, sits on a real plateau,
is less concentrated and higher-returning than 0091, and passed every fragility check. **It supersedes both
0091 and the TRI 0093 as the lead candidate for the live forward book and the 2026-10-01 review.**
Remaining discipline before/for go-live: (1) the Nifty-50 data is freshly yfinance-fetched — commit/pin it
(done here) and treat it as un-audited vs the pinned OHLCV pipeline; (2) two indices were tested (TRI then
Nifty-50) — mild multiple-testing, but the pre-reg named Nifty-50 as intended, so it's the primary not a
fishing expedition; (3) DSR 0.745 still means the forward wall is the only certifier. No retuning — 3%/40/7%
frozen; the plateau is the honest read (~+0.85 neighborhood, not the +0.98 peak).
