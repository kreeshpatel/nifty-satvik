# Result 0001 — Cross-sectional momentum, Indian midcaps

**Date:** 2026-08-07 · **Pre-registration:** `prereg.md` (written before the run)
**Trial:** `n_trials` 2 · **Verdict:** all 7 primary gates PASS → **WATCHED, not capital**

---

## 1. Outcome

*(All figures annualised by calendar time — see ADR-0014. The CAGR, Calmar and turnover columns are
~0.4pp / 0.02 / 5pp lower than the first publication of this result; nothing behavioural changed.)*

| | CAGR | Sharpe | MaxDD | Calmar | trades | turnover |
|---|---|---|---|---|---|---|
| **CANDIDATE** | **21.73%** | **1.130** | −37.17% | 0.58 | 2,951 | 311 |
| random control | 6.12% | 0.416 | −57.75% | 0.11 | 4,153 | 438 |
| **passive equal-weight** | 13.20% | 0.737 | −52.51% | — | — | — |

ΔSharpe **+0.714**, CI **[0.435, 1.027]** — excludes zero and clears the 0.30 noise floor.
`n_eff` 37 · DSR 0.991 · every primary gate passes.

**Per-regime** (continuous slices of the one curve, never re-run):

| | candidate | control |
|---|---|---|
| 2018 midcap crash | **−9.60%** | −28.75% |
| 2020 COVID | **+51.26%** | +28.33% |
| 2022 drawdown | **+3.90%** | −9.67% |
| 2024-26 correction | **+15.23%** | +10.03% |

Cost sensitivity: unchanged at the 1.5× proxy (21.73% → 21.73%).

**This is the first configuration in the programme to beat passive ownership on return, Sharpe and
drawdown simultaneously.**

## 2. Seven defects found and fixed before this number was trusted

Three of them (§2) invalidated the first two runs outright; four more (§3d) were found afterwards by
deliberately attacking the engine. Every one of the first three moved the result **toward**
plausibility — deeper drawdown, lower Sharpe — which is the direction that says they were flattering
rather than harmless.

| | run 1 | run 2 | run 3 | run 4 (this) |
|---|---|---|---|---|
| CAGR | 18.08% | 24.26% | 22.11% | 21.73% |
| Sharpe | **1.565** | 1.239 | 1.128 | **1.130** |
| MaxDD | **−19.56%** | −34.76% | −37.11% | **−37.17%** |
| PBO | 0.774 | 0.274 | 0.488 | 0.452 |
| avg positions (cap 45) | **66.89** | 34.53 | **31.22** | 31.25 |
| stale exits | — | **380** | **1** | 1 |

Run 4 adds the four further defects in §3d. It moved the headline by 6 basis points, which is the
honest summary of those four: real, correctly fixed, and economically almost irrelevant on this
configuration.

**(a) Target-queue accumulation leak (engine).** Targets were a one-shot queue consumed on the next
session; a name without a quote that morning was skipped and never revisited, so holdings grew
without bound — 67 average positions in a book capped at 45. That over-diversification is what
produced the −19.56% drawdown, implausible against a literature benchmark of −50/−70%. Targets are
now persistent until the next rebalance, with an explicit zero for every held name outside the
target. Regression-tested by punching staggered holes in the quote stream.

**(b) Mis-specified random control (runner).** The control drew a fresh random number per
(ticker, **date**), reshuffling daily, so it could never benefit from the hold buffer and churned
its whole book every rebalance — 147.7 turnover against the candidate's 78.3. That comparison
measures *persistent vs churning selection*, not *ranking vs no ranking*, and `turnover_le_30pct`
passed for the wrong reason. Now one score per (ticker, **month**).

**(c) Rows filtered by eligibility (runner).** The panel was filtered to `eligible` rows, so a name
leaving the MID band lost its prices entirely — the engine could not price a sale, held blind, and
force-closed 10 sessions later at a stale mark. **380 of 2,807 trades (13.5%)** resolved at a
fictional price. Eligibility now gates the **rank**, never the **rows**; stale exits fell to **1**.

**What caught (a) was not a test — it was the literature.** A −19.56% drawdown on Indian midcap
momentum contradicted every published benchmark. Had the leak produced a merely-plausible number,
it would have shipped.

## 3. What does NOT support this result

**PBO 0.452 is a coin flip, not a pass.** The gate was < 0.50 and it technically clears — but with
252 splits the standard error on a proportion near 0.5 is ~0.031, so 0.452 sits **1.5 standard
errors** from pure chance. The pre-registration's reading for this case applies in spirit: *the
family may carry edge, but the choice of top-30 / buffer-1.5 within the neighbourhood is not
supported.* **No cell from the sweep is adopted, and the baseline's specific parameters should be
treated as arbitrary within their neighbourhood.**

**DSR 0.991 is close to uninformative at `n_trials = 2`.** DSR deflates by the expected maximum
Sharpe across trials; at one trial there is essentially no deflation and it collapses to "is this
Sharpe above zero given the sample". The counter reads 2 because it was reset earlier the same day
at the owner's instruction, then incremented for this trial and for ENG-01. That gate should be re-read once the counter reflects genuine
accumulated testing.

**The planning drawdown is −59.3%, not −37.2%.** (Superseded reading — see §3c. The original text
here said the Monte Carlo was mis-calibrated and unusable; it has since been rebuilt and now
produces a usable number, which is worse than the observed path.)

**CAGR sits above the literature's honest band.** The compendium puts durable Indian midcap momentum
at ~14-18%, and "low-20s only for the best regime-managed, vol-targeted, quality-filtered
combinations". This book has **none** of those overlays and returned 21.73%. The most likely
reconciliation is the **window**: 2017-2026 excludes 2008, which is where the published −70%
drawdowns and the CAGR drag come from. That is a real limitation of our sample, not evidence of
superiority — the strategy has never met a 2008.

**Turnover is dominated by rebalancing, not selection.** Of 2,951 trades, **2,045 (69.3%) are
`rebalance_trim`** — equal-weight drift corrections — against 905 genuine exits and 1 stale close.
The cost model charges all of them and the result survives, but the book is trading far more than
its selection logic implies.

**The win rate is 73%, and that is a construction artifact, not skill.** Most "trades" are trims of
a winner back to equal weight, which by definition book a gain. Read the 905 `rebalance_exit` rows
for anything resembling a hit rate; the headline 73% mixes two different events under one label.

## 3b. Validation battery — the placebo layer

The primary gate asks "did it beat a control". This asks whether the return comes from the
**ranking** or from something with no information in it. Five tests
(`pipelines/research/run_0001_validation_battery.py`), re-run in full after every defect in §2 and
§3d — a placebo battery measured against a superseded engine certifies nothing.

**LAG TEST — pass, with the graceful-decay signature.**

| | Sharpe | ΔSharpe |
|---|---|---|
| base | 1.130 | — |
| +1 session | 1.026 | −0.104 |
| +5 sessions | 1.117 | −0.013 |
| +10 sessions | 1.001 | −0.129 |

One extra day costs **9.2%** of Sharpe. Look-ahead does not behave like this — it collapses at +1.
The strongest evidence here is the **non-monotonicity**: +5 sessions scores *better* than +1, which
means the spread across all three lags is noise. A signal genuinely indifferent to ten days of lag
cannot have been reading information unavailable at execution.

**SIGNAL PERMUTATION — pass, and this is the decisive one.**

| | CAGR | Sharpe |
|---|---|---|
| candidate | 21.73% | 1.130 |
| **ranks permuted within each date** | **4.89%** | **0.349** |
| random control | 6.12% | 0.416 |

Shuffling the ranking across names within each date — identical cross-sectional distribution,
identical universe, identical equal weighting, buffer and cadence, **only the ordering destroyed** —
collapses the book to the random control. The 21.73% is therefore attributable to the *ranking*,
not to portfolio construction. Had the permuted book kept outperforming, the return would have been
coming from equal weighting or the rebalance mechanics and the signal would have been incidental.

**SYNTHETIC DATA — pass.** Geometric random walks at each name's own realised volatility, zero
drift: **CAGR −0.33%, Sharpe −0.013.** The construction rules manufacture nothing on structureless
data.

**INVERTED TIME — pass.** Reversed price series: **CAGR 1.37%, Sharpe 0.174.** The effect is
time-asymmetric, as a behavioural anomaly should be.

**TRADE FORENSICS — 50/50 clean.** Fifty randomly sampled fills checked against the raw panel: no
fill on a date without a bar, none outside its bar's high/low, none above 5% of that day's ADV.
Execution leakage does not appear in any aggregate statistic, so this is checked by hand.

**What the battery does NOT clear.** It addresses leakage and construction artifacts. It says
nothing about overfitting-through-the-researcher, the coin-flip PBO, the uninformative DSR at
`n_trials = 2`, or the window limitation in §3. Those remain open.

## 3c. The drawdown distribution, rebuilt

The Monte Carlo reported in the first version of this document was invalid in **two** ways, and the
second was worse than the one originally flagged.

**(i) The block was sized in trades, not time.** Ten trades at ~320 trades/year is about ten
sessions, while the drawdown being measured spans months. A block shorter than the dependence
horizon degenerates toward iid and shreds exactly the clustering it exists to preserve.

**(ii) The "observed" drawdown was not the book's drawdown.** `resample_trades` reconstructs a path
by compounding per-trade returns at a fixed 10% notional. That reconstruction produced −29.38%,
which was then reported as the realised path and compared against resamples of itself. The book's
actual max drawdown is **−37.17%**. So the old comparison was not "realised vs resampled" at all —
it was one synthetic path against a distribution of synthetic paths, mislabelled. That mislabelling,
not the block size, is why the old figure sat at the 0th percentile: it was the wrong series.

The replacement (`resample_equity_curve`) bootstraps the **equity curve's daily returns**, which is
the series a drawdown is actually made of, and sizes the block from the data: the first lag at which
the ACF of `|r|` falls inside the white-noise band, floored at one month. Volatility clustering —
not return autocorrelation — is what produces drawdowns, so `|r|` is the right series to read.

| | old (trade blocks) | new (79-session equity blocks) |
|---|---|---|
| observed | −29.38% *(reconstructed)* | **−37.17%** *(the real curve)* |
| median | −11.71% | −37.17% |
| p95 | — | −51.76% |
| p99 | −20.57% | **−59.27%** |
| observed percentile | **0th** | **51st** |

The block came out at **79 sessions (~4 months)**, eight times the old one. The realised path now
sits at the 51st percentile — inside the distribution, and almost exactly median rather than
impossibly worse than every resample.

**The planning drawdown is −59.3%, and it is worse than anything the backtest displayed.** That is
the honest direction: a −37% observed path was a median draw, not a worst case. Note this lands
squarely on the literature's −50/−70% band for Indian midcap momentum, which the observed −37.17%
did not — an independent sign the new number is the right order of magnitude.

## 3d. Four further engine defects

Together they moved the headline by 6 basis points. They are recorded at length anyway, because the
*reasons* they were found — and the one case where a green test proved nothing — are the part worth
carrying forward.

**(d) The position cap counted names the engine could not sell.** The PBO sweep aborted at
`top_n=30, buffer_mult=1.0` holding 31 against a cap of 30. Diagnosing it rather than assuming
(`pipelines/diagnostics/diag_slot_overflow.py`) traced **all 454** over-cap sessions to one name —
TATAMTRDVR, which simply stopped quoting in Sept 2024. A name with no quote cannot be sold at any
price, so the invariant was asserting something the engine had no power to satisfy. Interior missing
bars run 0.162% of listed name-days, so this is permanent in the data. **The engine was right and
the assertion was wrong** — the cap now binds on *tradeable* positions, and every untradeable one
must sit inside the `STALE_ABSENT_DAYS` force-close window. That pair is stricter than the original
count, not weaker: it pins the escape hatch instead of leaving it unexamined.

**(e) `min_trade_pct` was suppressing full exits.** A small position implies a small trade, so the
guard that skips dust *rebalancing* was also skipping the *exit*. A zero-target position below the
floor was skipped every session for ever, holding a slot the book could never reclaim. The
diagnostic above could not see this one — it modelled slots, not trade sizes — so it was found by
reading the branch rather than by measurement, and it required care to reproduce: a naive test is
worthless because the next rebalance simply tops the position back up to weight. The leak needs the
top-up to be **blocked**, which is what the ADV participation cap does to a collapsed illiquid name.
**(f) "Sells first" was a comment, not the code.** The execution block carried the line *"sells
first, so their proceeds fund the buys (never borrow)"* above a **single loop over
`sorted(set(book) | set(targets))`** — one alphabetical pass with the sell and buy branches inside
it. So a buy for `AAA` was attempted before the sell of `ZZZ` that funds it. On a synthetic full
rotation into alphabetically-earlier names the book ended the fill session holding **1 position out
of 3**, the rest in cash. Execution is now three ordered passes: absent, all sells, all buys.

**(g) Cash was rationed first-come.** Even with sells running first, the buy pass drew from a shared
cash balance in ticker order, so a short balance gave a full fill to whoever sorted first and the
remainder to whoever sorted last. Cash is now scaled **pro rata** across all buys by one common
factor, priced against a deliberately conservative impact budget so the outlays fit without a
sequential clamp — which would have smuggled the ordering straight back in.

**How (f) and (g) were found, and why it generalises.** Not by suspecting them. By asserting a
property that must hold for *any* correct implementation: **renaming the tickers must not change the
curve.** Ticker strings carry no economic information, so any dependence on iteration order shows up
under relabelling without needing to be anticipated first. (f) surfaced from reading the block
against its own comment; (g) surfaced only from the property, and would not have been guessed —
it moved the curve 0.02%, small enough to hide indefinitely and large enough to be wrong.

**All four fixes are pinned by regression tests verified to FAIL without them.** This mattered
concretely: the first version of the dust test **passed against the broken engine**, because the
next rebalance topped the position back up before it was ranked out. A regression test that passes
on the unfixed code documents nothing while looking exactly like coverage — so each test here was
run against a deliberately re-broken engine before being kept.

## 3e. Two accounting corrections, found by reading the pre-registration against the code

**The tax model did not do what §5.4 of the pre-registration says.** The pre-reg specifies *"STCG is
applied at 20% inside the compounding"*. `_after_tax_cagr` instead netted the whole bill off the
final value — its own docstring admitted *"no path compounding of the tax drag"* — and computed that
final value as `capital + realised PnL`, silently discarding **₹614,149 of unrealised gains**. Two
errors pointing opposite ways: no compounding flatters, dropping unrealised penalises.

`after_tax_curve` now pays each calendar year's bill out of the book at the year boundary, so the
tax stops compounding, and scales the actual equity curve rather than reconstructing one.

| | |
|---|---|
| gross CAGR | 21.73% |
| after-tax, as previously reported | 17.96% |
| **after-tax, compounded (as specified)** | **18.16%** |
| total STCG over the window | ₹1,053,712 |

The tax model previously had exactly one test — that the field exists. It now has eight, including
the one that matters: two books with identical gains but different *timing* of realisation must not
produce the same after-tax result. The old model could not tell them apart.

**Separately: every CAGR in the programme was annualised by a convention that overstated it — now
fixed (ADR-0014).** `compute_metrics` computed `years = sessions / 252`. This panel supplies
**247.5 sessions per calendar year**, so 2,348 sessions were counted as 9.32 years where **9.49**
elapsed, and a shorter denominator inflates the rate.

| | |
|---|---|
| gross CAGR at the 252-session convention | 22.17% ← as first published |
| **gross CAGR by calendar time** | **21.73%** ← the figure in §1 |
| overstatement | **0.44pp** |

Owner-approved and applied. The headline in §1 is the corrected number; the run-history table in §2
keeps its original figures because those rows record what was measured at the time.

**Two things worth carrying from the fix.** First, it was provably free of behavioural effect: the
Stage-2 golden master's trade-ledger hash is byte-identical and not one trade moved — only the four
figures derived from `years`. That is what separates a MEASUREMENT change from an ENGINE one, and
it was checked rather than assumed.

Second, the fix exposed a live instance of a hazard this repo had already written down.
`DEFINITIONS_REGISTER` §6 warns that a book-vs-benchmark CAGR gap is only valid if both sides share
a denominator — and `passive_equal_weight` in this very pipeline computed `len(eq)/252.0`
independently of the engine. When the engine moved, the benchmark silently did not, which would
have left the pre-registration's *"must clear equal-weight passive ownership"* gate comparing two
conventions with the benchmark flattered by ~0.4pp. Caught and fixed in the same change; passive is
13.20%, not 13.48%.

**`baseline_v1` is NOT re-anchored, and that is a governed decision rather than an open defect.**
Its producer prints 0.647 against the pinned 0.667 — but the pin file itself records why, under
`producer.calendar_correction_2026_08_06`, status *"RECORDED, NOT APPLIED"*. The cause is commit
`78f6f26` (M10), which corrected the NSE holiday calendar: three 2026 dates were listed as holidays
that the exchange's own bhavcopy shows as trading days, so the cleaner had been deleting 2,130 real
sessions. M10 measured the move with a control (Sharpe −0.020, CAGR −0.59pp) and deferred the
re-anchor to the 2026-10-01 review as a record-accuracy matter, the move being far inside the
±0.302 resolution band. Archaeology confirms it: the producer at `3ae38db` reproduces 0.667/15.47
exactly, and at `78f6f26` onward gives 0.647/14.88.

ADR-0014 is irrelevant to that figure either way — the anchor harness carries a private `metrics()`
and never calls `compute_metrics`. So `baseline_v1` is stale by design, on the old calendar *and*
the old annualisation, and both corrections land together in October.

## 4. Coverage gaps, carried from the pre-registration

1. Size bands reconstructed from trailing turnover rank — **not** NSE constituent lists.
2. Circuit screen is a returns-based proxy; no ASM/GSM or circuit-band feed. It removed **zero**
   rows, which is itself a sign the proxy is weak rather than that the universe is clean.
3. Equal weights, not NSE's free-float-mcap × NMS tilt (no market-cap data in the repo).
4. STCG at 20%, now genuinely inside the compounding (§3e). Calendar year still approximates the
   Apr-Mar fiscal year, and business-income treatment is not modelled.
5. **CAGR annualisation overstates by 0.44pp** on this window (§3e) — unfixed by design.

## 5. Disposition

Per the pre-registration: gates pass, PBO nominally clears, and it beats passive → **route to the
forward wall as a WATCHED book. Not capital.** The specific parameter cell is explicitly not
endorsed (§3).

The honest next steps are the ones that would make the result *harder* to believe, not easier.
**The Monte Carlo block is now sized in time (§3c) and the answer was unflattering — the planning
drawdown roughly doubled and the observed path turned out to be mid-range luck, not a worst case.**
Remaining: re-read DSR against a counter that reflects real testing; build an independent second
implementation of `rebalance_book`, which has now produced six defects and is the only engine
without one; and test whether the edge survives a window containing a 2008-class event, which this
data cannot provide.
