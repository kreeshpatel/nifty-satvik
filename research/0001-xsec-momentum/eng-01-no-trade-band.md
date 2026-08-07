# ENG-01 — No-trade band on rebalance drift trims

**Date:** 2026-08-07 · **Class:** ~~engineering change, not a trial~~ → **TRIAL** · `n_trials` 1 → **2**
**Status:** **RESULT — expectation MISSED, band NOT adopted** (see §Outcome). Expectation pre-stated
below, written before the run and left unedited.

---

## Correction: this WAS a trial

The section below argued this was not a trial because nothing was swept. **That reasoning was
wrong**, and it is left standing rather than deleted so the error is visible.

Multiplicity comes from the **option to adopt**, not from how many values were tried. A single
pre-derived configuration evaluated for adoption is precisely this programme's definition of a trial
(`n_trials.json`: *"one independent strategy configuration evaluated for a PROMOTE/KILL decision"*),
and had it passed it would have been adopted. The counter was incremented **after** the run, which
breaks the before-the-run rule; the breach is logged in `n_trials.json` rather than papered over.
One value was tried and nothing was retuned after the miss, so the ordering did not change the
decision — but the counter still has to carry it.

## ~~Why this is not a trial~~ (superseded — the original reasoning, preserved)

A trial searches. This does not: the band is derived from the cost structure below, one value is
implemented, and it is run once. Nothing is swept, so no multiplicity is spent and the DSR counter
does not move. If the derived value disappoints, the honest response is to record that the
derivation was wrong — **not** to try a second value. A second value would make this a sweep
retroactively, and the result would have to be judged as one.

## The problem

Of 2,951 trades in run 4, **2,045 (69.3%) are `rebalance_trim`** — equal-weight drift corrections
carrying **zero selection information**. Every one pays friction and realises a taxable gain. The
book is paying to correct noise.

## Deriving the band from cost, not from a sweep

**Cost of a trim, per rupee moved:**

| component | rate | source |
|---|---|---|
| brokerage + STT, one leg | 0.13% | `config.BROKERAGE_PCT + STT_PCT` |
| slippage, one leg (MID tier) | 0.22% | `config.SLIPPAGE["MID_CAP"]` |
| **round trip** | **0.70%** | both legs — a trim is followed by a later re-buy |
| STCG on the realised gain | 20% × 18.64% ≈ **3.73%** | `avg_return_per_trade_pct`, `_after_tax_cagr` |
| **total** | **≈ 4.4% of the notional moved** | |

**Tax dominates friction by more than 5×.** A trim is not a 0.7% decision, it is a ~4.4% decision,
and that is the number the band has to clear.

**Benefit of a trim:** restoring equal weight, whose value is the rebalancing premium. That premium
is **quadratic in the drift** — correcting a small deviation buys almost nothing, while paying the
full linear cost. So there exists a drift below which trimming is strictly value-destroying, and the
current engine trims all the way down to `min_trade_pct` (0.25% of equity).

**Choosing the band.** MID-cap monthly volatility is ~10%, so a position drifts ~10% of its own
value between monthly rebalances as a matter of routine. Correcting that is re-trading noise. A band
of **±20% of target — roughly 2σ of ordinary monthly drift —** trades only when a position has moved
much more than a normal month explains. It is also the standard practitioner value, which here is a
virtue rather than a red flag: it was not chosen by looking at our results.

**Entries and exits are exempt.** The band governs drift correction only. A name entering the book
and a name leaving it are selection decisions, and suppressing those would change the strategy
rather than its execution.

## Pre-stated expectation

Written before running. Recorded so the outcome can contradict it.

| quantity | now | expected |
|---|---|---|
| `rebalance_trim` count | 2,045 | falls by **≥50%** |
| turnover / yr | 316.7% | falls materially |
| CAGR | 22.17% | **+0.3 to +0.7pp** |
| Sharpe | 1.130 | ~flat |
| MaxDD | −37.17% | ~unchanged |

**Reasoning for the CAGR band:** 316.7% annual turnover at 0.35%/leg is ≈1.11%/yr of friction.
Removing ~60% of trims — which are 69.3% of trades but smaller than average in notional — saves on
the order of 0.4-0.5%/yr, plus deferred (not avoided) STCG.

**The falsifying outcome:** if CAGR **falls**, the rebalancing premium was real and larger than the
costs saved. That is a genuine finding about the construction, and it gets recorded as such — the
band is then reverted, not re-tuned.

## Engine invariant

`RebalanceConfig.rebalance_band` defaults to **0.0 (off)**, so every existing result and the golden
master stay byte-identical. **The band is not set anywhere** — see the outcome.

---

# Outcome — the derivation was wrong, and that is the finding

| | frozen 0001 | band 20% | |
|---|---|---|---|
| `rebalance_trim` | 2,045 | **504** | −75.4% |
| turnover / yr | 316.7% | **151.4%** | halved |
| trades | 2,951 | 1,411 | |
| CAGR | 22.17% | **21.83%** | **−0.34pp** |
| after-tax CAGR | 17.96% | **17.52%** | **−0.43pp** |
| Sharpe | 1.130 | 1.126 | −0.004 |
| MaxDD | −37.17% | −36.58% | +0.59pp |
| planning DD (p99) | −59.27% | −59.34% | ~same |

Four of five pre-stated expectations were met. **The one that mattered was missed, with the sign
reversed:** CAGR was predicted to rise 0.3-0.7pp and it fell 0.34pp.

## What this means

**The trims were not waste. They were earning more than they cost.** Cutting turnover in half —
removing three quarters of the drift corrections, saving ~0.5%/yr of friction and deferring tax —
still left the book *worse* on return. The only thing that can pay for that is the **rebalancing
premium**: systematically selling what has risen and buying what has lagged, within a book of
30 high-volatility midcaps.

The derivation's error is now identifiable. It assumed the premium is "quadratic in the drift and
therefore small". Quadratic it is; small it is not, at these volatilities. Individual midcaps run
35-50% annualised, so monthly dispersion inside the book is large and equal-weight restoration
harvests a real amount of it. That effect is worth **more than 4.4% of the notional moved**, which
is the bar the band was built to clear.

There is an irony worth stating: this is a **momentum** book, where the folk rule is *let winners
run*. Mechanically trimming winners back to equal weight should hurt. It helps — because the
volatility harvest inside the book outweighs the momentum forgone at a one-month horizon.

## Disposition — reverted, not retuned

Per the pre-statement: **the band is not adopted, and no second width will be tried.** Trying 10% or
30% now would convert one honest miss into a two-cell sweep, and the adopted cell would be selected
on the same data that just falsified the reasoning behind it. `rebalance_band` stays in the engine,
defaulted off and tested, because the mechanism is now measured rather than assumed.

## The one thing worth keeping

**Half the turnover for 0.004 of Sharpe and 0.6pp less drawdown.** On the return axis the band
loses; on the risk-adjusted axis it is a wash, and it is materially cheaper to run. That is not
enough to adopt on this evidence — but if capacity, execution risk or tax timing ever become
binding constraints, this is the measured price of halving the trading, and it does not need to be
re-derived.
