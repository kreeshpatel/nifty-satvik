# 0029 — 0085 end-to-end validation: leakage CLEAN; parameter + cost FRAGILE; execution optimistic ~15%; CHOP is the bleed

- **Status:** MEASUREMENT (no n_trials cost, no cfg change, **no retuning** — the 0085 spec stays frozen).
- **Date:** 2026-07-04. Scripts `scripts/diag_0085_leakage.py` + `scripts/diag_0085_battery.py`;
  data `research/exports/diag_0085_battery.json`. Skills applied: leakage-audit, backtest-rigor,
  indian-market-execution. Subject: pre-reg 0085 (net Sharpe +0.587 / CAGR +11.5% / DD −37.5%, 432 trades).

## 1. Leakage audit — CLEAN (§1–§6 sweep, executable)
- Truncation test: **0/10** (ticker, signal-date) pairs change any component when the future is dropped.
- Order-of-operations: trail ratchet updates AFTER exit checks (stop used on day i is from ≤ i−1);
  orders are created after the fill loop (no same-day fills). Static-verified in source.
- Weekly bucket PIT: **0/75** strict completed-week spot-checks (the one initial mismatch was the test's
  own partial-week artifact, not the engine).
- Survivorship: **34 backfill/alias (delisted or renamed) names actually traded** — the losers exist.
- Price+volume only; no fundamentals, labels, or forward columns in the signal path.

## 2. Parameter stability — **FAIL (backtest-rigor C1b narrow peak)**
One-axis sweeps around the frozen cell (4% / EMA20 / 63d), diagnostic only:

| trail | Sharpe | | EMA span | Sharpe | | cap | Sharpe |
|---|---|---|---|---|---|---|---|
| 3% | 0.377 | | 15 | 0.557 | | 55d | 0.301 |
| **4%** | **0.587** | | **20** | **0.587** | | **63d** | **0.587** |
| 4.5% | 0.395 | | 25 | **0.031** | | 70d | 0.470 |
| 4.75% | 0.081 | | | | | | |
| 5% | **0.000** (DD −57%) | | | | | | |

Locally smooth (4.00% vs 4.01% byte-identical) — not numerical chaos — but a steep monotone ridge:
each +0.25% of trail width sheds ~0.2 Sharpe. The frozen cell is a **local peak on all three axes**.
Per C1b the +0.587 headline is not a stable property; the neighborhood expectation is ~+0.3–0.4.
Mechanism: wider trails give back more AND hold slots longer, and in a fully-invested no-rotation book
both effects compound through the fill sequence.

## 3. Cost robustness — **FAIL at 2× (the B2 promotion-reference column)**
2× slippage: Sharpe **+0.174**, CAGR **+1.2%**, DD −52.5%. The edge is ~one slippage-doubling from zero.

## 4. Execution realism — optimistic by ≈15% of profit
- **27 gap-through stops** filled AT the stop price; open-fill counterfactual costs **₹2.67L ≈ 15% of
  total net profit**.
- **21% of trades** sat through ≥1 circuit-magnitude (±9.5% close-to-close) day while open.
- Capacity: median fill = 0.07% of the name's 20d ADV (p95 0.9%) → ~**5× today's book (~₹55L)** before
  the 5%-ADV rail binds on tail names. Personal-scale fine; not a fund.

## 5. Statistical anatomy
- Trade-sequence MC (5000×): DD median −23%, 1%-worst −40% — realized −37.5% is in-distribution.
- **Concentration:** top-10 trades ≈ **100% of net profit** (rest nets ~zero); top-3 names 45%
  (IRFC, SWANENERGY, KIRLOSENG). Skip-10%-of-trades 5th pct terminal: 3.7× vs 6.0× full.
- Max losing streak **15**; longest >10%-underwater stretch **~17 months**; 34% of rolling-12m windows
  negative. Trade quality: PF 1.25, payoff 2.29, expectancy +0.23R, SQN 3.3, Kelly 13% (traded 2%).

## 6. Benchmark + regime (the owner's sideways-market question, measured)
- Vs Nifty-500 TRI: alpha **+2.8%/yr**, beta 0.79, corr 0.56, up-capture 80%, down-capture **65%**.
  But TRI buy-and-hold did **+12.6% CAGR / −38.1% DD** — more absolute return than the strategy at
  similar DD, with LTCG instead of STCG. The strategy is a diversifier, not a replacement.
- Regime slices (TRI vs 200d SMA): **BULL 51% of days → +31%/yr (Sh 1.34); CHOP 38% → −12%/yr
  (Sh −0.51); BEAR 12% → +22%/yr (Sh 0.97)**. The bleed is CHOP, not bear (bear entries are few but
  average +0.61R). Disposition per registry: entry gates are five-times-dead (0086 latest) — the
  sanctioned routes for the CHOP bleed are **portfolio-level** (O-009 vol-target mechanism on the
  sleeve's deployed equity, or O-018 ERC multi-sleeve). Owner decision at the 2026-10-01 review.

## Verdict
**0085 remains UNDERPOWERED (as pre-registered) and is now additionally flagged FRAGILE:** the headline
sits on a parameter peak, dies at 2× costs, is ~15% optimistic on gapped stops, and lives entirely in its
top-10 trades. Leakage-clean and survivorship-honest — the number is *real for its exact cell*, but it is
not deployable-grade evidence. Route unchanged: Oct-1 review packet with these caveats attached; forward
wall the only certifier. **No retune performed; the sweeps here are diagnostic and spend no trials.**
