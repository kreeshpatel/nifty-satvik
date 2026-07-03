# 0023 — Bhanushali's REAL method (trailing/let-winners-run + volume), corrected-faithful: a modest but genuine edge — his "catch the rocket" is real

- **Status:** **MEASUREMENT / corrected strategy analysis** (standalone, no n_trials cost, no cfg change).
  **Supersedes the conclusion of 0022:** his method is NOT edgeless / catastrophic. Implemented *as he
  actually teaches it*, Engine B has a real positive **gross** edge; net it is modest and uncertifiable.
- **Date:** 2026-07-03. Script `scripts/run_bhanushali_corrected.py`. Window 2017–2026, PIT membership, tiered
  real costs. Prompted by the owner correctly flagging that the "faithful" test (0022) was letter-faithful but
  violated the *spirit* — it omitted the trailing stop, volume confirmation, curated liquid watchlist, and 2%
  sizing that are central to his teaching.

## What changed vs the letter-faithful test (0022)
The five fixes: (1) **trailing stop / let winners run** — a chandelier ATR trail ratcheting up from the
candle-low initial stop, **no fixed target, no hard time-cut** (the core fix — stops cutting the rockets);
(2) **curated liquid watchlist** (min ADV filter + cap-tiered slippage: large-caps 0.05% not 0.22%);
(3) **real 2% risk sizing** (fewer/larger positions, not the 20%-cap pathology); (4) **volume/HVC
confirmation**; (5) **visibly-sustained** trend.

## Result
| config | GROSS Sharpe / CAGR | NET Sharpe / CAGR | maxR | win |
|---|---|---|---|---|
| **B: pullback + volume + 3×ATR trail** | **+0.39 / +5.9%** | +0.15 / +1.0% | 18R | 36% |
| B: same, **4×ATR trail** (wider) | — | **+0.34 / +5.0%** (DD −45%) | 28R | 33% |
| B: **no volume filter** | — | **−0.90 / −20.5%** | 12R | 27% |
| A: RSI-35 system | −0.05 / −2.5% | −0.33 / −7.2% | 18R | 33% |
| A: 4×ATR trail | — | +0.25 / +3.1% | 13R | 34% |

## Root-cause readout (REQUIRED)
The strategy's edge **lives in the two things the letter-faithful test omitted:**
1. **Letting winners run.** With a fixed +2R target the system is break-even (0022); with a trailing stop it
   captures **18–28R** rockets, flipping Engine B's *gross* expectancy positive (+0.10R, Sharpe +0.39). A
   ~35%-win system is only profitable if the winners are allowed to be large — his "catch the rocket" pitch
   (Adani/Bajaj examples) is mechanically real, and cutting winners at 2R destroyed it. Wider trail = more
   rocket = better (4× > 3× > 2.5×).
2. **Volume confirmation.** Removing the HVC filter collapses Engine B to −0.90 Sharpe (expR −0.16) — his
   "volume is the voice of god" is empirically load-bearing, filtering out the false-breakout losers.
Engine B (momentum pullback) beats Engine A (RSI-oversold entry) — consistent with the whole program:
momentum-continuation carries edge, mean-reversion does not.

## Verdict — real but modest and uncertifiable
His **actual** method (Engine B: sustained-uptrend pullback + volume + trailing/let-run) has a **genuine
positive gross edge** (Sharpe +0.39, CAGR +5.9%). But **net of real costs it is marginal** (Sharpe +0.15 at
3×, +0.34 at 4× trail), **below baseline_v1 (0.667)**, in-sample with several chosen knobs (trail width,
volume, ADV) → it would face the same Deflated-Sharpe wall as every overlay (cf. 0021 DSR 0.60), and it is
ρ~0.57 **momentum** (partial diversifier of the base, not new alpha). So: **a real method, not a new tradeable
alpha; forward-wall-only if pursued.**

## Corrections to the record (both owner-caught)
1. **0022's "−90% catastrophic loser" was a cost×turnover artifact** (break-even gross, corrected in that file).
2. **0022's "no edge" was letter-faithful only** — his *real* method (this finding) has a modest real edge,
   which lives in the trailing/let-winners-run + volume he teaches and we had omitted.
The durable, honest summary: **Bhanushali's momentum method — pullback in a strong uptrend, confirmed by
volume, with a trailing stop to ride the move — is a real but modest, cost-sensitive, in-sample-uncertifiable
momentum strategy. His mindset/risk/volume principles hold; his letter-exact tight-stop/fixed-target mechanics
do not; the edge is in letting winners run.** Not for the cfg; the forward wall is the only certifier.
