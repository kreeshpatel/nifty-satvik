# 0135 — Reactive exposure gates: the ceiling is too low, and the index beats the whole family

**Date:** 2026-08-06 · **Class:** measurement + activation bound. **`n_trials` unchanged at 138.**
**Standing counts:** screens 19 · sealed opens 1 · n_trials 138.
**Verdict:** **NO TRIAL.** Every implementable gate is CAGR-negative, and the clairvoyant ceiling —
perfect foresight of each year's sign — is worth only **+6.56pp**, which no real rule approaches.
The activation-bound gate is now **5/5**.

---

## 1. Why reactive rather than predictive

0134 found no PIT state variable forecasts this family's bad periods. The literature agrees at much
larger scale: Goyal-Welch (2008/2022) tested 15 macro and valuation predictors on ~a century of US
data and concluded they "would not have helped an investor with access only to available information
to profitably time the market."

The one documented out-of-sample success is a different *shape*: Faber (2007) does not forecast, it
**reacts** — exit after price closes below its own 10-month SMA. Post-publication (2006-2012) it
cut max drawdown to −9.5% against −46.0% buy-and-hold. So this study tested reaction, not
prediction.

## 2. Gates

A none · B Nifty 10-month SMA (Faber canonical) · C Nifty 200-day SMA (the 0133 §5 incumbent) ·
**D own-equity 10-month SMA (the new candidate)** · E clairvoyant annual switch (ceiling).

Gate D is the mechanically-motivated one: 0133 §6b proved the family's bad years are not the
market's bad years, so gating on the market is gating on the wrong series. D applies Faber's rule to
the book's own ungated equity curve. **PIT-legal**: the signal is the paper equity curve, which stays
observable while the traded book sits in cash — the decision series never depends on the gated
series.

Window 2017-01-01..2026-06-30 (2016 excluded per 0133 §3a-CORRECTION: ~21 eligible names).

## 3. Result

| gate | CAGR | Sharpe | MaxDD | neg yrs | worst yr | in-market | exits |
|---|---|---|---|---|---|---|---|
| **A no gate** | **5.09%** | 0.412 | −47.8% | 4/10 | −24.1% | 100% | 0 |
| B Nifty 10-mo SMA | 4.40% | 0.416 | −40.9% | **5/10** | **−28.2%** | 69.7% | 10 |
| C Nifty 200-day | 4.40% | 0.416 | −40.9% | 5/10 | −28.2% | 69.7% | 10 |
| D own-equity 10-mo | 1.71% | 0.211 | **−32.5%** | **3/10** | −26.3% | 45.8% | 10 |
| E CLAIRVOYANT (ceiling) | **11.65%** | 1.017 | −29.9% | 0/10 | 0.0% | 57.9% | 3 |

**Every implementable gate costs CAGR.** B and C *raise* the negative-year count from 4 to 5 and
make the worst year worse (−24.1% → −28.2%). D reduces negative years and drawdown but at a
two-thirds cut in return.

**Per-year — the gates broke the good years and did not fix the bad one:**

| year | A none | B Nifty SMA | D own-equity |
|---|---|---|---|
| 2017 | **+37.5%** | **+9.0%** | +9.0% |
| **2018** | **−24.1%** | **−28.2%** | −26.3% |
| 2022 | −6.4% | −4.4% | **−18.6%** |
| **2025** | **−16.7%** | **−0.2%** | −13.0% |

B fixed 2025 (−16.7% → −0.2%) and paid for it by destroying 2017 (+37.5% → +9.0%) and deepening
2018. That is the trade in one line: **the gate cannot tell the start of a bad year from a pullback
inside a good one.**

## 4. The activation bound — why no better rule exists either

**Perfect foresight of each calendar year's sign yields 11.65% CAGR against 5.09% ungated: a ceiling
of +6.56pp**, on 3 activations in 10 years. Every implementable gate landed between **−0.7pp and
−3.4pp**. The entire realisable value of annual market timing on this family sits inside a 6.6pp
band that no achievable rule has come close to, and the two nearest attempts were negative.

**The activation-bound gate is now 5/5** (0117 rotation, 0119 tiebreak, 0121 deferral, 0129 event
sizing, 0135 exposure timing). It has never passed.

## 5. The finding nobody asked for — the index beats the entire family

| | CAGR | Sharpe | MaxDD | neg yrs |
|---|---|---|---|---|
| **NIFTY-50 buy-and-hold** | **11.98%** | **0.787** | **−38.4%** | **1/10** |
| the nine-strategy family (equal weight) | 5.09% | 0.412 | −47.8% | 4/10 |
| best single strategy (Supertrend+Pivot, full window) | 7.46% | 0.518 | −35.0% | — |

Over 2017-2026 the Nifty-50 beat the equal-weight family **on every axis at once** — more than twice
the CAGR, nearly twice the Sharpe, a shallower drawdown, and one losing year against four. It also
beat the best individual strategy in the survey.

**This reframes the whole arc.** The question was never which of these strategies is best; it is
whether any of them clears buying the index. On this evidence none does — and that comparison costs
nothing to make and should be the first gate any future strategy faces.

**The Faber rule is not broken** — it does on the index exactly what the literature documents:
Nifty buy-and-hold 11.98% / MaxDD −38.4% becomes 6.35% / **−19.9%** gated. Drawdown roughly halved
for roughly half the return: Law VII, cleanly. It behaves as advertised; it simply has no
incremental value on a book whose bad years are not the market's.

## 6. Do not re-test unless

1. **More independent events.** The family has TWO negative years here. No timing rule can be fit or
   validated on two events, and every gate's 10 "exit episodes" are the real sample size. Longer
   history (Nifty is available from 1996; this repo's stock data begins 2017) or a second market is
   the only fix. Re-running gates on this window is refused relitigation.
2. **A candidate that beats the index**, not one that beats the other strategies. §5 makes this the
   binding gate.
3. **Forward evidence.**

## 7. Reproduction

`scripts/diag_reactive_gate.py` — gates, per-year attribution, clairvoyant bound, Nifty sanity
check, episode counting.
