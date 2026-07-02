# 0022 — The COMPLETE Bhanushali strategy, backtested faithfully: NO GROSS EDGE (break-even), cost-killed on turnover

> **CORRECTION (2026-07-03, bug-hunt `scripts/diag_faithful_debug.py`).** The original verdict below ("loses
> catastrophically / destroys capital / Sharpe −1.6") was **overstated — a cost-model × turnover artifact, not
> the strategy's true behaviour.** A cost sweep shows the strategy is **break-even GROSS** (cost=0: Sharpe
> +0.085, −0.4% CAGR). The entire −90%+ loss is transaction cost compounded over **~5,100%/yr turnover** (260
> trades/yr), and its magnitude was inflated by two modelling problems: (1) a **punitive uniform 0.22% slippage**
> applied to every name incl. liquid large-caps (it alone moved Sharpe −0.57→−1.61), and (2) a **notional-cap
> under-sizing bug** — 94% of trades hit the 20% cap, so realized risk was **0.75%/trade, not the intended 2%**,
> making cost ~18% of the risk budget. Trades are clean (R∈[−1,+2], zero |R|>5 glitches; no data corruption).
> **Corrected verdict: his mechanical strategy has NO gross alpha (break-even) and is cost-unfriendly due to
> high turnover — NOT a catastrophic capital-destroyer.** It is still not tradeable (no gross edge), but the
> alarming framing was wrong. The sections below are the original (uncorrected) writeup, kept for the record.

- **Status:** **MEASUREMENT / definitive strategy analysis** (standalone, no n_trials cost, no cfg change) —
  **verdict corrected (see box above): no gross edge, cost-killed on turnover; original "catastrophic" framing retracted.**
- **Date:** 2026-07-03. Script `scripts/run_bhanushali_faithful.py`. Window **2017–2026** (~684 PIT names;
  pre-2019 mildly survivor-biased). Two faithfulness fixes prior diag scripts lacked: **PIT Nifty-500
  membership** (his watchlist + survivorship fix) and **real NSE round-trip cost 0.70%** (config
  brokerage+STT+slippage, not the flat 0.25% earlier scripts used).

## What was tested (his EXACT rules, both systems, no deviations)
- **Engine A — RSI-35 system:** WEEKLY 44-SMA rising (trend/watchlist) + DAILY RSI(14) <35 then cross back ≥35
  on a green candle → buy above the candle high, stop below its low, target 1:2, hold 3–10d.
- **Engine B — 44-SMA pullback:** DAILY 44-SMA rising + price pulls back to the MA + green candle → same
  entry/stop/target/hold.
Faithfulness spot-checked by hand (e.g. RELIANCE 2021-07-22: pullback to the 44-SMA, green candle, buy above
962, stop below 950 — exactly as he draws it).

## Result — both faithful baselines are catastrophic
| engine (his exact rules) | trades | win | expR | CAGR | Sharpe | MaxDD | final |
|---|---|---|---|---|---|---|---|
| **A — RSI-35 system** | 1,397 | 36.5% | −0.05 | **−23.9%** | **−1.62** | **−92.6%** | 0.08× |
| **B — 44-SMA pullback** | 2,424 | 37.5% | −0.00 | **−30.6%** | **−1.61** | **−97.3%** | 0.03× |

**Negative in every continuous-slice sub-period** (A: 2017-18 −1.78 / 2019-21 −1.64 / 2022-26 −1.56; B:
−2.09 / −1.49 / −1.50). Not a regime fluke — a structural loss across the whole window. Exit mix confirms the
mechanism: stops dominate (A 763 stops vs 290 targets; B 1364 vs 611) — **his tight candle-low stop is shredded
by noise** at a 36–37% win-rate, and **0.70% round-trip × 1,400–2,400 trades** is a drag the tiny entry edge
(finding 0020: +0.15pp) cannot cover.

## Sensitivity grid — only multi-rule DEVIATION turns it positive (and it's then not his strategy)
Changing ONE knob from the faithful baseline stays deeply negative (stop→4%-floor, hold→20/40d, target→1:3,
trend→sustained, RSI→30 all Sharpe −0.8 to −1.5). The **only** positive cells combine **several** deviations at
once — wide 2.5×ATR stop **+** 40-day hold **+** 1:3 target: **A +0.23, B +0.59 Sharpe.** At that point it is no
longer Bhanushali's system (he teaches candle-low stops and 3–10d holds) — it is a generic wide-stop momentum
book, and even that sits **below baseline_v1 (0.667)** once real costs apply. (The earlier ~+1.0 Sharpe hybrid
was inflated by the missing PIT membership + the flat 0.25% cost; the honest fixes cut it to ~+0.6.)

## Root-cause readout (REQUIRED)
His *exact mechanical* strategy does not work on this market: (1) the **tight candle-low stop** exits on normal
2–4% noise before any edge plays out (36–37% win); (2) **real transaction costs** (0.70% round-trip) on a
high-frequency swing book overwhelm a ~0.15pp entry edge; (3) proper **PIT membership** removes the survivorship
inflation that flattered the approximate runs. The "wins" in his videos are **cherry-picked, survivorship-
selected examples**, not the systematic reality across all names net of costs. What *does* carry value is his
**principles** — trade a clear/strong uptrend, let winners run on wide stops, respect risk, volume confirmation
(findings 0020/0021) — but those are the *opposite* of his tight-stop/short-hold mechanics, and even assembled
optimally they are ρ 0.57 momentum, uncertifiable in-sample (0021, DSR 0.60). The faithful mechanical system is
a **KILL**.

## Verdict
**KILL — Bhanushali's exact swing systems (both the RSI-35 and the 44-SMA pullback) are net losers on
2017-2026 NSE data after real costs and PIT membership** (Sharpe ≈ −1.6, −90%+ drawdown). This is the
definitive, faithful, no-approximations test the owner asked for. His *educational* value (mindset, risk
discipline, the momentum/volume *principles*) stands; his *mechanical rules* do not. Do not re-test the exact
mechanical spec again — it is settled. Any future work uses the *principles* (momentum-continuation + wide
stops + volume), judged only on the forward wall, never in-sample.
