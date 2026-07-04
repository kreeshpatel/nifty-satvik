# 0090 — Market-regime entry filter on the 0089 fully-weekly book: no new buys when the index is below its 44-week EMA

- **ID:** 0090. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning under any outcome).
- **Registered:** 2026-07-04, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 107 → 108.
- **Anchor / data:** identical cell to 0089 (corrected universe, PIT membership, tiered costs, 2017–2026,
  EQ0 ₹10L) + the pinned Nifty-500 TRI (`research/exports/benchmark_nifty500_tri.csv`). Script
  `scripts/run_bhanushali_weekly_regime.py`.

## Why this trial exists
0089 (fully-weekly six-step) has the family's best Sharpe (+0.626) and CAGR (+11.8%) but a **−54% drawdown**
driven by 2018 (−₹6.3L) and 2024 (−₹12L) — years the broad market reversed while the book kept buying
pullbacks into a falling tape. Owner hypothesis: stop taking NEW trades when the market itself is in a
downtrend (index below its own 44-week EMA). Directly targets the DD, and uses the same weekly-44 logic the
strategy is built on.

**Registry honesty (relitigation guard).** This is the FIFTH market-regime / entry-gate test in the
program — O-001 (dual-momentum/breadth gate), A5 (index < 200-SMA to-cash, ΔSharpe −0.05), 0056
(regime-conditional entry), and 0086 (comparative-RS gate on this funnel: fixed 2025, hurt the book) all
landed KILL/UNDERPOWERED. What is NEW: all four were on the base momentum book or a rank tilt; this is a
**market-index trend filter on the weekly Bhanushali funnel**, targeting a real −54% DD that book has no
market filter against. New book + new mechanism = a legitimate arm, held to the same bar.

## The FROZEN spec (one delta from 0089)

| Param | Frozen value |
|---|---|
| Everything | **exactly 0089** — weekly 44-EMA green-bounce signal, in-range open entry, signal-week-low stop, 0085 exit levels decided at the weekly close / filled Monday, 2% risk, no rotation, tiered costs |
| Market filter | before creating ANY new entry order, require: the Nifty-500 TRI's **latest completed weekly close > its 44-week EMA** (`tri_wclose.ewm(span=44)`); if the TRI is below its 44-week EMA, take **no new entries** that day. Open positions are managed and exited normally. |
| Filter timing | per calendar day, use the most recent completed weekly TRI bar (ffill) — PIT-safe (that week closed on/before the day) |
| Warmup / missing TRI | TRI series starts 2017-09-14 → filter active from its 44-week warmup (~2018-07); before that (and on any missing date) the filter passes through (trade as 0089), frozen |

Pre-declared sensitivity: erratum-dropped INDIAMART bars.

## Primary metric + diagnostics
**Corrected-universe NET Sharpe** (one number); **MaxDD is the co-headline** (the change's whole purpose).
References (not gates): 0089 +0.626 / +11.8% / −54.3%, 0085 +0.587 / +11.5% / −37.5%, TRI +12.6% / −38%.
Diagnostics: % of trading days the filter blocks entries, trades retained vs 0089, per-year P&L (does it
kill the 2018/2024 losses?), DD, Calmar.

## Decision rule (pre-committed)
Family rule: **PROMOTE→forward-wall watch** iff DSR@108 > 0.95 AND bootstrap CI-low > 0 AND all three
continuous slices > 0. Sharpe > 0 otherwise → **UNDERPOWERED**. Sharpe ≤ 0 or a negative slice → **KILL**.
Additional informational reads (no gate): ΔSharpe, ΔCAGR, ΔMaxDD, ΔCalmar vs 0089 — a DD cut at flat
CAGR/Sharpe is a *risk* win worth noting even if uncertifiable. No retuning; the 44-week EMA and the TRI
choice are frozen.

## Skeptical prior (honest)
Four prior regime gates failed because blocking entries in downtrends also blocks the sharp recovery
entries that follow — you miss the V-bottom trades that carry the next up-leg, so CAGR falls roughly as
much as the DD improves (A5's exact finding). For it: 0089 uniquely has NO market filter and a −54% DD, so
there's real DD to cut, and the weekly-matched 44-EMA is a cleaner filter than A5's 200-SMA. Most likely:
DD improves (maybe −54%→−40s), CAGR slips a few points, Sharpe roughly flat → UNDERPOWERED but possibly a
genuine *risk* improvement (the honest reason to keep it as a candidate). If it lifts BOTH Sharpe and cuts
DD it would be the first regime-gate win in the program — a high bar, treated skeptically.
