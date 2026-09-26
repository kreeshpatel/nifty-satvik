# Estimation-error bound for position-level optimisation — SPEC (written before any result)

**Class:** MEASUREMENT, with an activation-style clairvoyant ceiling. **No trial. No screen row.**
Nothing is adopted. Standing counts at writing, read from the ledgers:
**screens 20 · sealed opens 3 · n_trials 2.**
**Plan:** Satvik Brain, Phase 1 / **Track P2**.
**Written:** 2026-09-25, committed before the diagnostic exists. Every definition, constraint and
reading rule below is fixed now and is **not** revisited once the numbers come in.

## Why this is not a trial and takes no screen row

Nothing here is a trade-bearing configuration evaluated for adoption, which is `n_trials.json`'s own
definition of a trial. No cohort label is screened for a relationship with outcomes, which is what the
`label_screen_ledger` counts. This study asks a question *about the measuring instrument*: for a book
of about five names that rotate weekly, **is the position-weighting axis resolvable at all?** A
clairvoyant ceiling that fails is the cheapest possible answer, and it is the same template 0127 and
0144 used without spending multiplicity.

## The owner's question

> "Can portfolio theory — Markowitz mean-variance, risk parity, Kelly, correlation-aware sizing —
> improve this system?"

Track P1 (0142) answered the descriptive half: the book is beta **0.702** to the Nifty and the index
explains 58–68% of daily variance in drawdowns. P2 answers the half that decides whether anyone should
ever build the optimiser: **how much of a five-name sample covariance is noise, and what ΔSharpe would
position-level optimisation have to deliver before this data could see it?**

## Prior art — cited, narrowed from, not relitigated

| receipt | what it already says |
|---|---|
| **C3 conviction sizing** | re-weighting by conviction: Sharpe **0.667 → 0.610**. KILL. |
| **0130** | sizing by notional instead of risk: **−10.83% of equity per year**. |
| **`FINDING_more_slots`** | 4–5 seats **1.21**, 7 seats 0.97, 10 seats 0.81, random null 0.74. Concentration is load-bearing; "diversify inside the book" *lowers* Sharpe here. |
| **Law II, mechanism 0131** | the dilution axis is **seats**, not queue depth and not weights: stop width → notional → seat count → dilution. |
| **0095 / TRANSFERABILITY_REGISTER** | book-level vol targeting was promoted on momentum and **killed here at ΔSharpe −0.398**. Any exposure change is a different question and is not this one. |
| **0107 / 0115** | sleeve-level allocation is where portfolio theory has worked here. That is Track **P3**, deliberately separate. |

**Prior expectation, stated before the run so a null reads as a null:** the opening status is expected
to be **NARROWED** — the ceiling is expected to sit inside the noise floor. Two of the schemes below
have already-measured cousins (equal-notional is 0130's direction; conviction weights are C3), and
their sign is predicted. Recording that here means a confirmation cannot later be presented as a
discovery.

## Population

**A — historical, live configuration.** `run_bhanushali_weekly_rank.backtest` with the live dicts
(`LIVE_DISCIPLINE`, `LIVE_EXIT`, `LIVE_STALENESS`, `LIVE_PREP`, registered demerger events) on
`corrected_universe()`, **2019-01-01 .. 2024-06-30**, capped ₹10L paper book — the same population A
as 0142, for comparability. The corporate-action HOLD is **off**, as in 0142 §A1 and for the same
stated reason.

**The window stops at 2024-06-30 so the sealed 2024-07-01..2026-06-30 validation slice stays shut.**
`nq.brain.io.assert_unsealed` guards the trade selection. Sealed opens stay at 3.

**The live forward book is not used.** It has 11 closed trades and about 46 rows; a covariance question
cannot be asked of it, and pretending otherwise is how a small-sample number gets quoted later.

## The weight reconstruction, and the gate it must pass first

The engine records entries, exits and R, but **not** a daily position ledger, and this study will not
edit a production path to add one six days before a review. Daily notional per held name is therefore
**reconstructed**: shares from the engine's own sizing rule (risk budget ÷ (entry − stop0), the
`max_notional_pct` cap applied as the engine applies it), halved on a recorded half-exit, marked at
each session's close, with the engine's cost stack on every reconstructed leg.

**A reconstruction is not trusted because it is plausible.** Before any result below is computed, the
reconstructed book NAV (cash + Σ notional) is differenced against the engine's own equity curve:

- **pass:** median |Δ| ≤ **0.5%** of NAV and max |Δ| ≤ **3.0%**;
- **fail:** the diagnostic **stops and reports the failure**. It does not proceed with an approximated
  book, and it does not widen the tolerance. A failed reconstruction is a complete, publishable result
  — it says the weights this question needs are not recoverable without an engine change.

## What is measured

### Leg 1 — how much of the covariance is estimable

At each weekly rebalance date, over the names held, on the **trailing 63 sessions strictly up to and
including the decision day** (point-in-time):

1. `q = N / T` (N names, T = 63) and the **Marchenko–Pastur** upper edge `λ₊ = (1 + √q)²` on the
   correlation matrix; the **share of sample eigenvalues inside the MP bulk** — eigenvalues a pure-noise
   matrix of the same shape would produce anyway.
2. **Ledoit–Wolf shrinkage intensity δ\*** toward the constant-correlation target: the fraction of the
   sample covariance the optimal estimator throws away. δ\* near 1 means the sample matrix carries
   almost nothing.
3. **Joint-holding overlap**: for each pair held together, the number of sessions both were actually
   held. A correlation estimated on 63 sessions that governs a 15-session shared holding is mostly
   describing a period neither position existed in, and that is reported, not assumed away.

### Leg 2 — the clairvoyant ceiling

For each rebalance, using the **realised forward returns and realised forward covariance of the week
about to happen** — information no one can have — choose long-only weights that maximise the book's
realised Sharpe. Rebuild the NAV. **ΔSharpe against the engine's actual risk-based weights is the
absolute ceiling for any position-weighting scheme whatsoever**, and it is unreachable by construction.

### Leg 3 — the plug-in (honest) estimate

The same optimiser with **point-in-time** inputs: μ from the trailing 63-session mean, Σ from the
Ledoit–Wolf shrunk sample covariance. Plus the frozen comparison set, **fixed now, no sweep**:

`{ actual risk-based weights (control) · equal-notional · inverse-vol · minimum-variance ·
max-Sharpe plug-in · max-Sharpe clairvoyant }`

### Constraints, frozen

- **Long only.** No shorting, no leverage.
- **Total invested notional each day is held exactly equal to the engine's**, so exposure and cash drag
  are unchanged. This is a pure *weighting* question. Changing exposure is 0095 and is a different,
  already-killed question.
- **Per-name cap** = the engine's own `max_notional_pct` where one is set.
- **Rebalance weekly**, on the engine's own decision day; weights are held between rebalances; there is
  no intra-week trading.
- **Turnover is charged** with the engine's cost stack (`_cost_leg`, plus STT on the sell leg). An
  unpriced re-weighting is not a result.
- Seats, entries and exits are **untouched** — the same names on the same days. Only the split of the
  same money between them changes.

## The gate, fixed now

The resolution floor is the programme's, not this study's:
`diagnostics/research/n_trials.json` — **n_eff = 37 independent 63-day windows ⇒ ΔSharpe half-width
0.59**. Readings, fixed before the run:

| outcome | reading |
|---|---|
| **clairvoyant ceiling < 0.59** | the axis is **unresolvable on this data at any trial count**. Recorded as a bound; status **NARROWED**; no trial is earned now or later from this window. |
| ceiling ≥ 0.59 but plug-in ≤ 0 | the information exists and **cannot be estimated** — the classic error-maximisation result. Same practical outcome, different cause. A re-test needs a different estimator and its own pre-registration. |
| plug-in ≥ +0.59 | earns a **screen row** at the next monthly batch. Not adoption, not a trial, not a live weight. |

Per-year sign consistency is reported for every ΔSharpe. Every cell carries n. Any scheme whose result
rests on a single year is labelled as such.

## What this may never become

Nothing here authorises a live weight change. Position sizing stays **2% risk per trade**. A change to
it is a live sizing rule: pre-registration, trial, quarterly review — and it would be arguing with C3,
0130 and Law II, which is a case that has to be made on its own evidence, not on a measurement.

## Do not re-test unless

A different **book shape** with its own seat count and its own sizing (Law II's explicit carve-out), or
forward data long enough to estimate a covariance the sealed slice has not already seen. A different
lookback, a different shrinkage target or a different optimiser on this same window is relitigation and
is refused.
