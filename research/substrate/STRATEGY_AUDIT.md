# Full audit of the live strategy + the Grade-B re-test (measurement, no trial)

**Audited 2026-07-16.** Sources: `models/bhanushali_weekly/config.json`, `scripts/run_bhanushali_cron.py`,
`scripts/run_bhanushali_weekly_rank.py`. Reproduce the tests: `python scripts/diag_grade_b.py`.

## 1. What is actually live

| | |
|---|---|
| **model** | `weekly-swing-0094-rank-p2exit` · status **FORWARD_WATCH** · inception **2026-07-04** |
| **universe** | NSE Nifty-500 large+mid, PIT membership, ADV ≥ 5cr, D/E < 1.5, **corrected** (pinned + backfill + aliases) — 788 names, 2017-2026 |
| **entry (weekly, 4 ANDed)** | 44w SMA rising (slope ≥ 3% over 13wk) · low ≤ SMA×1.07 **and** close > SMA · quality-green (close>open, close in upper half of range) · RS(stock/Nifty-50) > its own 40w SMA |
| **fill** | first daily open next week printing inside [signal_wlow, signal_whigh] |
| **selection** | descending **CRS distance** = RS/SMA40(RS) − 1; **top-5/week = Grade A**; board + paper book trade **A-only** |
| **stop** | signal-week low |
| **sizing** | **2% equity risk/trade**, ₹10L book, **no** position cap, **no** vol-target |
| **exit (P2, owner-override 2026-07-15)** | half at **+2R**; then trend-following — exit on (a) **blow-off** weekly bar after 2.5R MFE, (b) 20-day-SMA −4% ratchet trail, (c) 20-week-close −4% backstop; **no time cap** (52wk backstop). Decided at weekly close, filled Monday |
| **certification** | **UNDERPOWERED** (DSR 0.894 < 0.95). Not promoted |

## 2. The numbers (in-sample, 2017-2026)

| config | trades | Sharpe | CAGR | MaxDD | Calmar | 17-21 | **22-26** |
|---|---|---|---|---|---|---|---|
| ALL grades (**as documented** in config) | 168 | 1.03 | 21.2% | −34.8% | 0.61 | 0.79 | **1.29** |
| **A-only (what the cron ACTUALLY runs)** | 171 | 1.00 | 20.9% | −36.4% | 0.57 | 0.84 | **1.17** |

**⚠ PARITY GAP (found by this audit):** `config.json → live_backtest_p2exit` documents
`Reproduce: backtest(prep_weekly_rank(ohlcv), no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)`
— **no `a_grade`** — i.e. the ALL-GRADES run (1.034/168). But `run_bhanushali_cron.py:346-349` runs the
paper book with **`a_grade=grade_a_entries(P)`** (A-only → 1.00/171). **The documented headline does not
reproduce the book that actually trades.** The −0.12 gap on the 22-26 slice is **inside the null's noise
band (σ = 0.24)**, so it is not a performance problem — but the record should state which book it describes.

## 3. What today's work adds to the audit

- **Random-selection null:** Sharpe 0.67 / 22-26 **0.74**. CRS-rank sits at the **99-100th percentile** →
  selection is worth **+0.36 Sharpe / +0.228R per trade**.
- **CRS's skill is regime-dependent:** 100th pct in 2022-26; **87.5th (inside noise) in 2017-21**.
- **Honest forward expectation: 0.67 .. 1.03** — not automatically 1.03.
- **Selection ratio 2.6%** (168 funded of 6,359 activated; 19,728 signal-days skipped for cash).
- **Cold start:** ~5-6 names by wk12, largest position **31% of book**, **−11% DD in the first 6 months**
  (`COLD_START.md`).

## 4. Grade-B re-test — the daily 14-EMA gate (owner's formulation): KILLED

A-only vs all-grades was **never decided in-sample** (routed to the wall, `prereg_swing.md` §7a), so this
was legitimately open, not a relitigation. Gate is PIT-safe (read at the signal close, index `e0-1`; the
fill is the next week's open). Windows: 8,518 total → A 2,028 / B 6,490; **5,369 B (83%) pass the gate**.

| config | trades | Sharpe | CAGR | DD | **22-26** |
|---|---|---|---|---|---|
| ALL grades | 168 | 1.03 | 21.2% | −34.8% | **1.29** |
| A-only (live) | 171 | 1.00 | 20.9% | −36.4% | 1.17 |
| **A + B above 14-EMA** | 166 | 0.86 | 17.2% | −38.8% | **0.93** |
| A + ALL B (≡ all grades) | 168 | 1.03 | 21.2% | −34.8% | 1.29 ✓ sanity |

**KILLED: 0.93 vs 1.29 (−0.36, ~1.5σ).** Per R11 a FINDING, no retune.

**Why — and it is the useful part.** The gate admits **83% of B**, so it is nearly all-grades; the damage
comes from **the 17% it excludes**. B signals *below* their 14-EMA are the **deep pullbacks** — precisely
the highest-expectancy entries measured (0-5% ext **+0.58R**; below-SMA **+2.09R**). **"Only buy if above
the short-term EMA" = "don't buy weakness" = discard the best entries.** Same lesson as the pool filter
(`POOL_vs_SELECTION.md`), reached from a new direction: **you cannot filter your way to quality here — every
filter removes the deep entries that carry the edge.**

## Verdict

The live strategy is sound and correctly specified. **Keep A-only** (it costs nothing real — inside noise —
and gives a tighter board). **Do not add the 14-EMA B gate.** Fix the config's `Reproduce:` line to state
`a_grade=grade_a_entries(P)` so the record matches the traded book. This is the **12th** attempt to improve
the book and the 12th failure.
