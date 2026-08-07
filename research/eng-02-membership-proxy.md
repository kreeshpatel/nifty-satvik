# ENG-02 — Validating the turnover-rank membership proxy

**Date:** 2026-08-07 · **Class:** instrument validation. **Not a trial.** `n_trials` unchanged (2).
**Status:** CRITERIA PRE-STATED — this file written and committed **before** the validation ran.

---

## Why this is not a trial

Nothing here is evaluated for adoption. No configuration competes, no verdict is available to win,
and the frozen 0001 book is not being changed in any respect. What is being measured is whether an
**instrument** — a substitute for point-in-time index membership — reads the same as the real thing
where the real thing exists.

That distinction was got wrong once already this session: ENG-01 was pre-classified "not a trial"
because nothing was swept, and the classification was wrong, because multiplicity comes from the
*option to adopt*. Here there is no such option. If the proxy fails, the conclusion is that a
pre-2017 lockbox built on it cannot be interpreted — not that some other proxy should be tried until
one passes. Trying proxies until one passes **would** be a trial, and would be pre-registered as one.

## The problem the proxy exists to solve

The pre-2017 lockbox needs a universe. Real Nifty-500 constituent history does not exist before
2018: `nq/data/membership.py` states it plainly — *"no pre-2018 Wayback snapshot exists, so 2011-2018
membership is the 2018-10 set back-extended"*.

Back-extending the 2018 membership to 2006 would make the 2008 crash **survivor-only**. Every name
that died between 2006 and 2018 would be absent from the universe by construction, so the one event
the lockbox exists to observe would be measured on the cohort that survived it. That is not a small
bias; it is the single lie the exercise is designed to prevent, and it would return a falsely gentle
crash that looks like reassurance.

NSE bhavcopy has the opposite property. Each daily file is a snapshot of everything that traded that
day, including names that later delisted, so a universe derived from it is **point-in-time clean by
construction** rather than by reconstruction. What bhavcopy does not carry is index membership. Hence
the proxy: rank the day's names by trailing rupee turnover and take the top 500 as a stand-in for the
Nifty-500, then band as usual.

The proxy is only worth building on if it reads the same as real membership where both exist.

## Pre-committed acceptance criteria

Fixed here, before running. Two gates, and the second is the one that decides.

**Gate A — set recovery.** Month by month over 2019-2026 (the period where real PIT membership is
trustworthy), the proxy's MID band must recover **≥ 85%** of the actual MID constituents. Reported as
the distribution across months, not just the mean: a 90% average that collapses to 60% in particular
months is a different instrument than a steady 90%.

**Gate B — functional agreement. This is the decisive test.** Set overlap is a proxy for the thing
that matters; the thing that matters is whether the *book* behaves the same. Run frozen 0001,
unchanged, over 2019-2026 twice — once on real membership, once on proxy membership — and compare:

| quantity | tolerance |
|---|---|
| CAGR | within **±0.75pp** |
| ΔSharpe vs the random control | the two 95% CIs must **overlap** |
| max drawdown | within **±5pp** |

**Reading, decided now:**

- **Both gates pass** → the instrument reads true where truth exists. A pre-2017 lockbox built the
  same way is interpretable, and the harvest proceeds.
- **Either gate fails** → the lockbox verdict would be uninterpretable, and a build is saved rather
  than wasted. Diagnose *where* the proxy diverges before deciding anything. The prior is the
  rank-100/101 band boundary, which churns constantly — a name a rupee either side of it changes
  band, and the proxy and the real index need not agree about which side.
- **Gate A passes, Gate B fails** → the more interesting failure, and the reason B is decisive:
  the proxy would be selecting *nearly* the right names while the book still behaves differently,
  which says the disagreements are concentrated in names that matter rather than spread evenly.

## What this cannot establish

Agreement over 2019-2026 is evidence about **2019-2026**. The pre-2017 universe is larger, less
liquid, and contains a decade of names that no longer exist; turnover rank may track index membership
differently there, and nothing measurable today settles that. The honest claim on a pass is *"the
proxy reproduces real membership on the period where both exist"*, and that is strictly weaker than
*"the proxy is correct pre-2017"*. It is also the strongest claim available, because the counterfactual
does not exist — and it is a great deal better than assuming.

One asymmetry is worth stating in advance, because it cuts the right way: pre-2017 the proxy's main
competitor is **back-extended 2018 membership**, which is known-wrong in a known direction
(survivor-only). A proxy that merely reads *approximately* right is still a large improvement on an
instrument that is certainly wrong.

## Method

`pipelines/diagnostics/diag_membership_proxy.py` — measurement only, no adoption, no verdict.
Gate A from the committed PIT membership; Gate B through the unchanged 0001 pipeline with the
membership source swapped and nothing else.

---

# Result — Gate A passes, Gate B fails. **Do not build the lockbox on this proxy.**

| | | |
|---|---|---|
| **Gate A — set recovery** | mean **90.1%**, median 90.0%, p10 86.5%, min 83.3% · 4 of 89 months below floor · Jaccard 81.8% | **PASS** |
| **Gate B — functional agreement** | | **FAIL** |
| ΔCAGR | **+1.490pp** (tolerance ±0.75) | **FAIL** |
| ΔMaxDD | −1.710pp (tolerance ±5.0) | ok |
| ΔSharpe CIs | [0.155, 1.003] vs [0.327, 0.897] — overlap | ok |

| | CAGR | Sharpe | MaxDD | trades | rankable/day |
|---|---|---|---|---|---|
| real membership | 28.28% | 1.371 | −36.28% | 2,363 | 150 |
| turnover-rank proxy | **29.77%** | **1.421** | −37.99% | 2,302 | 139 |

This is the failure mode the pre-statement singled out as *"the more interesting"*: the proxy selects
nearly the right names and the book still behaves differently — so the disagreements are concentrated
in names that matter rather than spread evenly. And it fails in the **one direction a holdout
instrument must not fail in**: the proxy is *more flattering* than truth, on both CAGR and Sharpe.

## Why — and the prior was wrong in a useful way

The pre-statement predicted the rank-100/101 boundary. It is the **other edge**, and the mechanism is
worse than boundary churn.

**Where.** **100%** of the names the proxy misses sit at real rank **221-250** — the bottom edge of
the MID band — with a median rank of **243**. The top of the band (101-220) is in perfect agreement.

**Symmetric in count.** 27,678 name-days missed against 28,498 added, an imbalance of +820 on
249,285 in agreement. So this is boundary churn in volume: names swapping across the rank-250 line.

**Asymmetric in return, and that is the whole problem.**

| | n (name-days) | mean forward 63d |
|---|---|---|
| in both | 240,061 | +5.41% |
| real only — the proxy **misses** these | 27,066 | **+5.13%** |
| proxy only — the proxy **adds** these | 27,780 | **+7.57%** |

**+2.44pp per name-day** in favour of what the proxy adds. That is the mechanism behind Gate B's
+1.49pp of CAGR, and it is not noise.

**The mechanism is turnover-momentum contamination, and it is specific to this strategy.** Rupee
turnover rises with price momentum — a name that is running trades more. So ranking by turnover at
the band's bottom edge preferentially admits names that are *already moving*, which is a momentum
signal smuggled into the universe definition. For a momentum book that is not a neutral
approximation: **the instrument is correlated with the thing it is being used to measure.** A
pre-2017 lockbox built this way would flatter the strategy it exists to falsify, and the 2008 verdict
would be contaminated in the direction of reassurance — the one outcome the whole exercise is
designed to make impossible.

## Disposition

**The harvest does not proceed on this instrument.** Per the pre-statement, a build is saved rather
than wasted, and nothing is tuned: no alternative proxy width was tried, because searching widths
until Gate B passes is fitting the instrument to the desired answer, and would convert this from
instrument validation into a trial.

Three routes exist and all are owner decisions, listed with what each costs:

1. **Band on something not momentum-correlated.** Free-float market cap is the natural choice and the
   repo has none — it is already coverage gap 3 in pre-registration 0001. Acquiring it would fix this
   *and* close that gap, and would make the proxy an approximation of the real construction rather
   than a different one.
2. **Truncate the contaminated edge.** The disagreement is entirely at rank 221-250; banding 101-220
   agrees perfectly. That narrows the book by ~20% of its names and changes the strategy being
   tested, so the lockbox would no longer be testing frozen 0001.
3. **Proceed and bound the bias.** +1.49pp CAGR and +0.05 Sharpe, measured, in a known direction, on
   2019-2026. The lockbox verdict would then be read as *"the pre-2017 result minus a known
   flattering bias of at least this size"* — weaker than a clean read, but not uninterpretable, and
   the pre-2017 bias is not measurable so "at least" is doing real work.

**What has not changed:** back-extending 2018 membership remains strictly worse than any of these.
It is wrong in a known direction *and* the direction is survivorship, which for a 2008 holdout is
fatal rather than merely biased.

