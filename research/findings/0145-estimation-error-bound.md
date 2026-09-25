# 0145 — Position-level portfolio optimisation: there is no differential structure to optimise

**Status:** MEASUREMENT — **no trial, no screen row, nothing adopted.** Track P2's activation bound is
**WITHHELD**: the replay built to measure it failed its own fidelity check and may not be quoted.
**Standing counts:** screens **20** · sealed opens **3** · n_trials **2** — unchanged by this study.
**Date:** 2026-09-25 · **Plan:** Satvik Brain Phase 1, Track P2.
**SPEC:** [`estimation_bound/SPEC.md`](../../diagnostics/research/estimation_bound/SPEC.md), committed
in `665b3ce` **before** any code existed.
**Record:** `diagnostics/research/estimation_bound/2026-09-25/summary.json`.
**Reproduce:** `python pipelines/diagnostics/diag_estimation_bound.py --run-date 2026-09-25`.

## The question

> "Can portfolio theory — Markowitz mean-variance, risk parity, Kelly, correlation-aware sizing —
> improve this system?"

0142 answered the descriptive half (beta 0.702; the index explains 58–68% of drawdown variance). P2
asks the half that decides whether the optimiser is worth building: **how much of a five-to-eight name
sample covariance is estimable, and what would position-level optimisation have to deliver before this
data could see it?**

## Population

Population A, as 0142: live configuration, `entry_date` **2019-01-01..2024-06-30**, capped ₹10L paper
book, corporate-action HOLD off. 71 closed trades, 86 measured rebalances, median **8** concurrent
names. The sealed 2024-07-01..2026-06-30 slice is untouched — the truncation happens on raw OHLCV
before `prep_weekly_rank`, so no future bar reaches an indicator, and `assert_unsealed` guards the
selection. **Sealed opens stay at 3.**

## The result: the exploitable structure is flat, and identical to a liquid control

Per rebalance, on the held names' daily returns over the trailing window (point-in-time, complete
cases). The control is 8 names drawn 20 times from the 30 highest-turnover names in the same universe,
through the same filters, on the same dates.

| trailing window | δ\* book | δ\* control | noise share book | noise share control | **above upper edge, book** | **above upper edge, control** |
|---|---|---|---|---|---|---|
| 63 sessions | 0.984 | 0.632 (sd 0.228) | 0.857 | 0.644 (sd 0.073) | **0.111** | **0.125** (sd 0.000) |
| 126 sessions | 0.821 | 0.480 (sd 0.219) | 0.778 | 0.513 (sd 0.069) | **0.125** | **0.125** (sd 0.000) |
| 252 sessions | 0.659 | 0.361 (sd 0.192) | 0.667 | 0.369 (sd 0.064) | **0.125** | **0.125** (sd 0.000) |

**The column that matters is the last two.** Only eigenvalues **above** the Marchenko–Pastur upper edge
are modes of co-movement a weighting scheme could act on. That share is **flat at 0.111–0.125 across
every window, and indistinguishable from the liquid control at every window.** Lengthening the lookback
from 63 to 252 sessions buys **no additional exploitable structure**.

The noise share *does* fall (0.857 → 0.667), and that fall is not signal appearing: it is eigenvalues
being pushed **below** the lower edge (0.096 → 0.111 → 0.222), which a fixed trace forces and which
exploits nothing. Reading `1 − noise_share` as signal is the mistake that made a longer lookback look
like a fix. It is not one.

**And the window you would lengthen is already longer than the holding.** Of 564 pairs held together,
the median pair shares **48 sessions**; **62% share fewer than the 63 sessions** the correlation is read
from, and the 10th percentile is **5 sessions**. A 252-session correlation describes a year in which the
two names co-existed in the book for about two months. Estimation accuracy and relevance trade against
each other here, and the flat above-edge share says the trade buys nothing either way.
(No right-censoring treatment: positions open at 2024-06-30 are truncated at the window edge, which
biases the overlap low.)

## What δ\* does not mean — a correction to this study's own first reading

This study initially reported δ\* ≈ 0.98 as *"the optimal estimator throws away 98% of the sample
covariance, so the inputs are mostly noise."* **That inference is wrong**, and the pipeline now
computes the number that shows why:

| δ\* on **pure iid noise**, N = 8 | T = 63 | T = 252 | T = 2000 |
|---|---|---|---|
| | 0.967 | 1.000 | **0.991** |

δ\* is **0.99 at 2000 observations on pure noise**, where estimation error is negligible. δ\* =
(π − ρ)/(γT) and γ is the squared distance to the *constant-correlation* target, so δ\* → 1 whenever a
single average correlation is nearly an adequate summary — at any sample size. It is a
correlation-homogeneity statistic, not a noise statistic.

The defensible reading is different, and for this question it is stronger: **on this book one average
correlation is nearly sufficient at 63 sessions, and heterogeneity only becomes detectable by 252.**
There is little *differential* correlation structure between the held names — which is precisely the
raw material a mean-variance or risk-parity weighting needs in order to beat equal risk.
`tests/test_brain_estimation.py::test_shrinkage_intensity_is_not_a_noise_statistic` pins this so the
misreading cannot return.

Both instruments were verified rather than trusted: the Ledoit–Wolf implementation matched an
independent from-the-paper transcription to 2.8e-16 across 40 shapes, and `mp_noise_share` is
null-calibrated to 1.000 at the book's exact shape under iid noise.

## The activation bound is WITHHELD

Legs 2 and 3 — the clairvoyant ΔSharpe ceiling and the plug-in estimate over the frozen scheme set —
**ran, and are not reported as a result.**

The SPEC's gate was written as an instruction: if the daily book cannot be differenced against the
engine's own curve within **median 0.5% / max 3.0%**, the diagnostic *"stops and reports the failure. It
does not proceed with an approximated book, and it does not widen the tolerance."*

- The **weight** half of that gate is now satisfied exactly, by the engine's own daily position ledger
  (added on the owner's instruction, `881a5ec`). But that check is an **identity, not a test** — the
  log's `equity` and `curve` are the same variable written twice, so it cannot fail and proves nothing
  about the replay. It is labelled as such in the record.
- The **substantive** check — does re-splitting the book by the engine's own weights give back the
  engine's book? — **fails at median 2.2% / max 7.2%.** My explanation (transaction costs charged twice)
  was tested and **falsified**: with costs off the gap gets *worse*, 3.2%. What remains is that the
  engine fills at entry and exit **prices** while a mark-to-mark replay trades at session marks. That is
  a design flaw in the replay, not a limit of the data.

So no ceiling and no plug-in ΔSharpe is established here. The numbers are kept in the record under
`bound.withheld_numbers`, flagged `NOT_A_RESULT`, for whoever writes the follow-up pre-registration.

**A pre-registered prediction failed, and it is recorded rather than dropped.** The SPEC predicted the
sign of equal-notional weighting from 0130 (notional sizing, −10.83% of equity per year). In this replay
it came out **positively signed**. Because the replay fails its own fidelity check, the disagreement
resolves nothing in either direction — but it is exactly the kind of result that must not quietly
vanish, and any follow-up must confront it.

## What it would take to finish Track P2

A new pre-registration whose replay fills at the engine's **own trade prices**, with the fidelity
tolerance fixed before the run, and with a stated reading for a **positive-but-unresolvable** plug-in
ΔSharpe — a case this SPEC's reading table does not cover (it handles ceiling < 0.59, ceiling ≥ 0.59
with plug-in ≤ 0, and plug-in ≥ +0.59). Nothing is read off that gap here.

## What the programme should take from this today

1. **Against position-level MVO / risk parity / correlation-aware sizing, the evidence is now
   mechanical rather than only historical.** C3 (0.667 → 0.610), 0130 (−10.83%/yr) and Law II's
   seats-not-weights mechanism said re-weighting has never paid here. P2 adds *why the inputs cannot
   carry it*: the exploitable correlation structure is flat in the lookback and no richer than for
   eight liquid large caps, while the pair-overlap is shorter than any window worth estimating on.
2. **Track P3 (sleeve-level allocation) is untouched by this and remains the live avenue.** Two or
   three sleeves with nine years of daily returns is a covariance you can estimate; five names that
   rotate weekly is not. 0107's swing × low-vol blend (−42.4% → −33.0% drawdown) is still the strongest
   structural lever on the board.
3. **The engine now records what it holds.** That is the durable output of this study: `position_log`
   makes every future portfolio-level question answerable from a committed artifact instead of a
   34%-wrong reconstruction.

## Defects fixed before publication (red-team read, 2026-09-25)

- **δ\* was interpreted as a noise statistic.** Corrected above, with the iid-null row computed by the
  pipeline and a test pinning it.
- **`1 − mp_noise_share` was read as signal.** The above-upper-edge share is now reported separately,
  and it is flat — which reverses the "a longer lookback helps" reading.
- **Two tests validated nothing.** The shrinkage-recovery test used a constant-correlation truth, which
  *is* the shrinkage target, so it passed for free and would have passed with δ\* hard-wired to 1.0;
  it now uses a three-factor heterogeneous truth. The δ\*-falls-with-T test compared 0.996 against
  0.973 with most draws hard-clipped at 1.0 — it tested the clip. Both rewritten.
- **The live exit was described from memory and was wrong.** I wrote "60% @ +2R, 20% @ +3R". Config P
  is `tp1_frac 0.40` at +2R, **`tp2_frac 0.0` at +3R — nothing sells at +3R**, `pattern_frac 0.40`
  armed at +2.5R, and a 20% runner. Corrected in the engine docstring, the test and the diagnostic.
- **A second, independent cause of the reconstruction failure was undisclosed.** Positions still open
  at the window end never close, so they never get a trade-ledger row: **10 names, 1,350 held
  name-days, a median 47.8% of daily notional from 2023 on.** The "91.7% of the error is upward"
  evidence does **not** discriminate between this and the tranche cause — both leave phantom shares on
  the books. Now measured and recorded.
- **"Unrecoverable without an engine change" was too strong.** Tranche *sizes* are algebra on committed
  config; it is the tranche *dates* the ledger does not pin down.
- **No matched control existed**, so "δ\* is high on this book" had no scale. Added, and it is now the
  strongest evidence in the study.
- **Turnover was normalised by the opening ₹1M** on a book that compounds 6×, which turned ordinary
  churn into five-figure nonsense. Now normalised by the running book.
- **An un-pre-registered scheme could set the ceiling.** `max_return_clairvoyant` is excluded from the
  ceiling and reported for contrast only.
- **Six SPEC deviations are recorded in the artifact** under `spec_deviations`, including the two that
  matter: the 126/252 windows are not in the SPEC (whose "do not re-test unless" clause refuses a
  different lookback), and leg 1's NaN handling was changed from zero-fill to complete-case *after* a
  first set of numbers existed. Zero-fill inflates δ\*, so the change moved toward the less flattering
  option — but the ordering is disclosed, because the ordering is what matters.

## Do not re-test unless

A different **book shape** with its own seat count and sizing (Law II's explicit carve-out), or the
follow-up pre-registration described above. A different lookback, shrinkage target or optimiser on this
same window is relitigation and is refused.
