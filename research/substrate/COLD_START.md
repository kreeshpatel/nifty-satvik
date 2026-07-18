# Cold start — the gap the backtest never models (measurement, no trial)

**Run 2026-07-16.** Reproduce: `python scripts/diag_cold_start.py`. Live config untouched.

## The question

The backtest's ~7-10 concurrent positions **accumulated over years** (the book grew; positions half-booked
at 2R, freeing capital). Deploying fresh capital **today** you start at 0 positions — and at 2% risk
against 2.5-6% stops a single fill is **33-79% of the book**. So the first weeks are far more concentrated
than the steady state on which the −34.8% drawdown was measured. The backtest never models this.

## The real cold-start profile (median of 12 fresh starts, 2019-2024, at the LIVE 2% risk)

| | week 4 | week 8 | week 12 | largest single position | DD in first 6 months |
|---|---|---|---|---|---|
| **2% risk (live)** | **5 names** | 5 | **6 names** | **31% of book** | **−11.1%** |

**This is the documented gap:** starting fresh you run ~5-6 names with the biggest at ~31% of equity and
should expect roughly **−11% drawdown inside the first six months** — a concentration the backtested
steady state does not show.

Worked example from the live board (2026-07-13): the 5 FRESH Grade-A cards required **₹29.3L of notional
— 293% of a ₹10L book**. The engine funds in CRS order and skips for cash: NLCINDIA (51%) → GLENMARK
skipped (needs 52%, 49% left) → BAJAJ skipped → CANFIN skipped → NATCOPHARM (33%) fits. **Result: 2 names,
~84% deployed.**

## A lower risk% is NOT the fix — it fails the gate (11th attempt, 11th failure)

A 12-start cold-start grid *suggested* 1% risk was better (more names, 18% max position, higher grid
Sharpe 0.91 vs 0.82). **On the LIVE config (2017 start) it reverses decisively:**

| risk | trades | Sharpe | CAGR | MaxDD | 17-21 | **22-26 gate** |
|---|---|---|---|---|---|---|
| **2% (LIVE)** | 168 | **1.03** | **21.2%** | **−34.8%** | 0.79 | **1.29** |
| 1.5% | 219 | 1.01 | 19.6% | −40.1% | 1.03 | 0.99 |
| 1% | 333 | 0.79 | 13.9% | −42.0% | 0.75 | **0.82** |

**Why the grid misled:** it measured 12 *late* starts over short windows, where the 2% book sits on idle
cash early. Over the full run the 2% book **compounds** — larger positions → more equity → more funding
capacity later. The grid answered a different question. **R3 (judge on the 2022-26 continuous slice)
caught it.**

**And it was a relitigation:** Phase-3 already wired and swept `risk_pct` — *"sizing is 2% risk, no caps —
every other lever fails robustly"* (`LOCKED_STRATEGY.md:51-64`). This independently reproduced that
verdict. Grep the registry first.

## The actual fix: time, not a smaller risk%

Take what cash covers **in board order (CRS rank)** and let the book **ramp**. Positions half-book at 2R
and free capital; ~5 fresh Grade-A signals fire per week. The steady state arrives in ~2-3 months. No rule
change is needed — the engine already does exactly this (fill in CRS order, skip when cash is short; the
same mechanism behind the 19,728 measured cash-skips).

**Known and accepted:** the first ~2-3 months carry concentration risk the backtest does not show. Plan for
it; do not "fix" it by shrinking risk%.
