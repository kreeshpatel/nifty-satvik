# Breadth Feasibility Census (2026-07-28) — desk research & arithmetic only; ZERO trials, no backtests

**Purpose:** price the capstone's structural condition ("a book shape whose decision points can express
population-level gradients") at the owner's actual scale. Counts: screens 11 · sealed opens 1 ·
n_trials 138 — all untouched. Sources are named per number; nothing is recalled from memory.

## 1. Short-side reality check — VERDICT: INFEASIBLE at current scale; threshold ≈ ₹50L margin-only / ~₹1cr for a real book

**Mechanism inventory (resident retail):**
- **Single-stock futures** — the only practical overnight short. SOURCE: NSE F&O bhavcopy 2026-07-24
  (UDiFF), near-month STF contracts: **210 shortable names**; contract values p10 ₹5.1L / median
  **₹6.6L** / p90 ₹9.6L. Margin ≈ SPAN+exposure ~25% of notional (NSE margin framework; varies by
  name/vol). Frictions: futures STT 0.02% on sell (Budget 2024 schedule, as audited in the 0114 cost
  work), monthly roll (2 legs × costs + spread), mark-to-market cash drag.
- **SLB (securities lending)** — honest statement: Indian SLB inventory is institutionally thin and
  effectively absent for mid-caps at retail size; tenors short, recall risk real. Not a breadth
  mechanism at this scale. No other overnight short mechanism exists for cash equities (intraday-only
  shorting is not position trading).

**The breadth arithmetic (median contract ₹6.6L, 25% margin, ALL capital to short margin — i.e. before
any long side):**
| capital | max 1-lot short names |
|---|---|
| ₹10L | **~6** |
| ₹25L | ~15 |
| ₹50L | **~30** (margin only, zero long book) |
| ₹1cr | ~60 (→ a real 30/30 long-short becomes possible) |
| ₹2cr | ~121 |

**Verdict:** at ₹10L-class capital the short side supports **single digits of names** — no
diversified short book exists below ~₹50L of margin capital, and a functioning 30-name-short
long-short book wants **~₹1cr+**. The classic long-short branch CLOSES at current scale, by
arithmetic. (Secondary: lot granularity means each short is an ~₹6.6L exposure step — position
sizing in lots, not rupees.)

## 2. The feasible cousin — high-breadth LONG-only: VERDICT: FEASIBLE at current scale

**Expressibility (SOURCE: the corrected-universe OHLCV cache, closes as of 2026-06-29, n=710):**
| configuration | slot | names unexpressible (1 share > slot) |
|---|---|---|
| ₹10L / 50 names | ₹20k | **8 of 710 (1%)** |
| ₹10L / 100 names | ₹10k | 20 (3%) |
| ₹20L / 100 names | ₹20k | 8 (1%) |
| ₹50L / 100 names | ₹50k | 1 (0%) |

Cash equities have no lot minimum (1 share), so **50 names at ₹10L is expressible today** (median
universe share ₹608 → median position ≈ 33 shares; weight granularity ≈ 3% of slot — fine). 100 names
prefers ₹20L+.

**Friction schedule (per the audited 0114 cost work + broker schedules):** delivery STT 0.1% each leg
(0.2% round trip); stamp 0.015% buy; exchange+SEBI ≈ 0.003%; discount-broker delivery brokerage ₹0;
**DP charge ≈ ₹16/scrip/sell-day — the small-order-specific cost**: a full 100-name quarterly
rebalance ≈ ₹1,600/quarter ≈ 0.06%/yr on ₹10L. At moderate turnover (~20%/quarter one-way), total
annual friction ≈ **0.5-0.9%** — material but not structural. Impact ≈ nil (ADV ≥ ₹5cr universe,
₹10-20k orders).

**Operational load:** 50-100 orders per quarterly rebalance (basket-order batched, ~1 session) vs the
current book's ~1-5 orders/week — comparable annual totals, chunkier cadence.

**Why this shape consumes the banked assets:** population-level signals act as WEIGHTS across 50-100
simultaneous positions, not as selection gates at a marginal slot — precisely the consumer the
campaign's decision-margin law says the current book cannot be. Candidate weight inputs, cited not
re-screened: the **delivery-quality gradient (0118**: dlv_med21 +0.363R conditional, ADV-robust**)**
and the **known-event proximity risk (0120**: −0.383R, PIT-legal**)**.

## 3. The certification path & the watched-book proposal (for the Oct-1 amendment slot — nothing starts without sign-off)

Per 0081/0115: in-sample cannot certify a new sleeve; the forward wall can, for free, as a WATCHED
paper book. **Proposal (one page):**

> **Book:** `breadth-50` — 50-name long-only cash book, ₹10L notional (paper).
> **Universe:** the corrected Nifty-500 large+mid, ADV ≥ ₹5cr, solvency-filtered (the frozen pipeline
> filters; no new universe definition).
> **Two watched variants — the comparison IS the experiment:**
> (a) **EW**: equal-weight 2%/name, the no-information baseline;
> (b) **SW**: same names, weights tilted by the banked signals — dlv_med21 percentile (up-weight) and
> known-event-within-14cd (down-weight), tilt bounded to 0.5×-2× of equal weight, definitions frozen
> from 0118/0120 verbatim.
> The EW-vs-SW forward spread isolates the signals' portfolio-expressed value with zero in-sample
> fitting — forward evidence by construction.
> **Selection into the 50:** top-50 by the frozen CRS strength that week (the existing signal engine,
> uncapped breadth) — no new selection logic.
> **Rebalance:** quarterly (Jan/Apr/Jul/Oct first trading day, matching review cadence); mid-quarter
> only delistings/corporate actions.
> **Logging:** daily NAV via the blend-logger pattern (observational sidecar, own results/ file,
> never touching the certified books); weight snapshots at each rebalance for attribution.
> **Pre-committed evaluation (12-month, first read Oct-2027):** SW-vs-EW spread (the signal test),
> both vs the 0107 blend and the capped base on Sharpe/MaxDD/worst-month (the shape test); thresholds
> may tighten, never relax; adoption/kill decided at review, never mid-stream.
> **Cost realism:** paper NAV debits the §2 friction schedule per rebalance.

**Verdict summary: long-short INFEASIBLE below ~₹50L (short margin alone) · high-breadth long
FEASIBLE at ₹10L/50-names today · certification = the watched pair above, at the Oct-1 door.**
