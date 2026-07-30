# 0124 — Weinstein stage analysis as a whole system: not a return engine, not a clean risk discipline — but the lowest sleeve correlation this programme has ever measured

- **Status:** **MEASUREMENT** — external-strategy shadow backtest (the 0022/0023/0024 Bhanushali
  precedent). **No `n_trials` increment, no screen-ledger row, no config change, no forward-wall read.**
  **Verdict: KILL.**
- **Standing counts, unchanged: screens 12 · sealed opens 1 · n_trials 138.**
- **Date:** 2026-07-31. Pre-reg
  [`0124-weinstein-stage-analysis.md`](../../diagnostics/research/preregistry/0124-weinstein-stage-analysis.md)
  (spec, ambiguity resolutions, bars and guards frozen before the run).
- **Scripts:** `scripts/diag_ext_band_census.py` · `scripts/diag_g1_weinstein_gate1.py` ·
  `scripts/run_weinstein_0124.py`. **Ledger:** `research/exports/weinstein_0124_trades.csv`
  (180 trades) · `research/exports/g1_weinstein_signals.csv` (294 signals).
- **Universe:** corrected (`corrected_universe()`), PIT Nifty-500 membership, ADV ≥ ₹5cr,
  2017-01-01 → 2026-06-29. Weekly panel sha256 `2b5d6592966bf7ef…`.

---

## What was tested

Stan Weinstein's stage analysis (*Secrets for Profiting in Bull and Bear Markets*, 1988) run **as a
whole system** — its own line, trigger, stop, management, exit and market rule — never as levers
strip-mined onto the incumbent 44-SMA touch funnel. 30-week SMA (his line, quarantined research-only
per the W89 precedent); stage-1 base (26 weeks, |SMA drift| ≤ 5%, range ≤ 35%); trigger = weekly
close above the base ceiling; stage-2 confirm (close > 30w SMA, SMA flattened/turning up); Mansfield
RS (52-week) ≥ 0 and rising; volume ≥ 2× the trailing 10-week mean; stop at the base low, ratcheted
to each confirmed higher swing low; half sold into the first stage-3 warning; stage-4 exit on a
weekly close below a flat/falling 30w SMA; the M-rule (no new entries with the index below its own
30-week SMA) kept **inside the grammar**. ₹10L, 2% risk per fill, RS-strongest-first.

Every ambiguity resolution is recorded in the pre-reg §1. Nothing was swept: one value per knob,
chosen from the source, published in the Gate-1 script before any outcome existed.

## Gate-1 (run first, and it already refuted the pick's premise)

| question | answer |
|---|---|
| Entry count | **211** signals on PIT members with ADV ≥ ₹5cr over 9.4 years = **22.5/yr**, 174 distinct names — **not famine-class** |
| Per-year balance | **2018-21 ≈ 12/yr vs 2022-26 ≈ 36/yr** (49 vs 162). 2017 is warmup-truncated (a 52-week RS SMA on data starting 2017-01) |
| Attrition | the breakout leg (5.2% survival) and the **volume leg (40.6%)** do the work; **Mansfield RS costs almost nothing** (86% then 97%) — at a stage-2 breakout the RS confirmation barely discriminates |
| **Ext at entry** | median **17.54%** vs the 44w SMA; **0.0% of 211 signals below 5%**; median modelled stop **24.74%** |

**G1 was picked as the census's most pre-extension grammar. The literal claim is false.** Only the
*ordinal* claim survived: 17.5% is the least-extended **breakout** funnel measured (cup 28.5, six-step
29.5, dbl 31.6, vcp 33.2, box 33.8, sr 37.9), with only the incumbent touch (8.7%) closer to the line.
Per the pre-reg, this was recorded **before** the run, and **no outcome here is evidence for or
against 0123's pre-extension re-open condition.**

## Result — view 1: per-trade, uncapped (the diagnostic-first law)

| N | win% | meanR | medR | PF | median risk% | median hold |
|---|---|---|---|---|---|---|
| 180 | 39.4 | **+0.077** | −0.135 | 1.39 | 24.9% | 9 weeks |

**Per-year meanR — negative in 8 of 10 years:**

| year | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| N | 2 | 9 | 14 | 13 | 7 | 16 | 61 | 29 | 28 | 1 |
| meanR | −0.21 | −0.18 | −0.22 | −0.23 | −0.13 | **+0.65** | **+0.25** | −0.08 | −0.02 | −0.22 |
| PF | 0.0 | 0.11 | 0.11 | 0.49 | 0.30 | 3.68 | 3.03 | 0.59 | 0.90 | 0.0 |

The grammar's entire lifetime edge is **2022–23**. Five consecutive negative years precede it and
three follow it.

## Result — view 2: the capped ₹10L book (continuous slice, never a fresh-capital re-run)

| | Sharpe | CAGR | MaxDD | Calmar | ann vol | trades | cash skips |
|---|---|---|---|---|---|---|---|
| Weinstein standalone | **0.259** | 1.66% | −21.13% | 0.08 | 7.6% | 135 | 45 |

Bootstrap 95% Sharpe CI **[−0.58, +1.03]** — straddles zero.
Continuous slices: **2017-21 −0.74** (CAGR −3.73%) · **2022-26 +0.861** (CAGR 8.0%).
Calendar years (%): 2017 −0.0 · 2018 −4.0 · 2019 −5.7 · 2020 −11.0 · 2021 +2.7 · 2022 +3.0 ·
**2023 +37.5** · 2024 +0.4 · 2025 +0.8 · 2026 −1.5.
**Top decile of trades = 264% of total R** (the other 90% is net negative).

## Result — correlation and the 0115 blend test

| | ρ(swing) | ρ(lowvol) |
|---|---|---|
| **Weinstein** | **0.381** | **0.344** |
| 0115 quality candidate | 0.58 | 0.64 |
| 0115 low-USD-beta candidate | 0.59 | 0.57 |
| incumbent pair with each other | 0.54 | — |

**This is the lowest sleeve correlation the programme has measured, by a wide margin** — and it is
the one genuinely new, bankable fact in the study.

Quarterly inverse-vol ERC blend (weekly, both sides recomputed identically):

| blend | Sharpe | MaxDD | worst year | losing years |
|---|---|---|---|---|
| swing + lowvol (incumbent pair) | **1.182** | −29.7% | **+3.8%** | **0** |
| + Weinstein (3 sleeves) | 1.005 | −21.0% | −2.5% | 2 |

## Verdict against the pre-committed bars

- **Bar A (return engine) — FAIL.** 2022-26 continuous slice **0.861 < 1.29**; full-period Sharpe
  0.259 with a CI straddling zero.
- **Bar B (a seat under 0115's blend logic) — FAIL.** The correlation limb **PASSES** (0.381 / 0.344,
  both < 0.55) and the standalone-positive limb passes trivially — but the blend limb fails outright:
  the 3-sleeve ERC **loses** Sharpe (1.182 → 1.005) and **breaks the zero-losing-year property** the
  pre-reg named explicitly.
- **Risk discipline (Law VII) — partial, and not clean enough to claim.** The blend's MaxDD improves
  −29.7% → −21.0% (−8.7pp), but at −0.177 Sharpe **and** a worse worst year (+3.8% → −2.5%). Robustness
  bought with return, plus a broken year-consistency property. Logged for the review; **never promoted
  in-sample.**
- **Guard 1 (wide-stop mirage) — did NOT fire.** Win rate 39.4% is *low*, not inflated, and meanR is
  +0.077. The ratchet converts the 24.9% base-low stop into a genuine trailing stop, so the E6
  signature is absent. *(Labeling note: 98.9% of exits carry the `stop` reason because the ratcheted
  trailing stop, not the initial stop, is what fills — the field conflates the two and should not be
  read as a stop-out rate.)*
- **Guard 2 (power) — fired, and then was overtaken by signal.** 2017-21 is underpowered by
  construction (N=45), but it is **5/5 negative years**, and 2024/2025/2026 are negative too. This is
  not a power story; "2022-26 was the good slice" is really "2022-23 was the good slice."
- **Guard 3 (leakage) — clear.** The result is far worse than the incumbent, and leaks inflate.

**The honest trichotomy: NOTHING.** Not a return engine, not a clean risk discipline.

## Root-cause readout (REQUIRED — the mechanism, not the metric)

**1. 0115's law, re-proved from the opposite side.** 0115 killed two third-sleeve candidates because
they were *neither* orthogonal *nor* strong (ρ 0.57–0.64, Sharpe 0.18–0.39) and concluded that "the
diversification free-lunch requires BOTH low correlation and a positive edge." This study finally
supplies the missing half of that experiment: a sleeve that **is** genuinely orthogonal (ρ 0.34–0.38)
— and it still fails, because it has no edge. The free lunch needs both; having one is worth nothing.
That is a stronger statement of the law than 0115 could make.

**2. The grammar's own R lands where every other breakout funnel's does — not where its premise
said.** Matched-cell anatomy (ext band × risk-width tercile):

| cell | N | meanR | win% |
|---|---|---|---|
| >20% ext × **wide** stop | 42 | **+0.278** | 47.6 |
| 15-20% ext × **wide** stop | 17 | **+0.310** | 41.2 |
| 10-15% ext × tight stop | 35 | +0.017 | 37.1 |
| 15-20% ext × mid stop | 33 | −0.017 | 33.3 |
| 10-15% ext × mid stop | 10 | −0.290 | 20.0 |

The money is in the **most-extended, widest-stop** cohort — the box/sr anatomy — not in the
base-resolution, near-the-line entries that motivated the pick. A stage-1 base on this universe does
not resolve into a low-extension entry; by the time the ceiling breaks on 2× volume, the name is
17-25% above its slow line with a 25% stop beneath it.

**3. The 2022-23 concentration is the regime, not the rule.** 61 of 180 trades and essentially all of
the profit sit in 2023 — the year Gate-1 independently flagged as a 64-signal outlier against a ~20
baseline. A grammar whose signal *count* and signal *quality* peak in the same single year is
measuring the Indian 2023 broad-base breakout, not a durable stage-2 edge.

**4. Weinstein's RS confirmation is nearly free — and is already ours anyway.** Gate-1's attrition
shows RS ≥ 0 and rising removes only ~14% then ~3% of surviving candidates. Separately, our incumbent
ranker of record `crs_dist` is the **same Mansfield construction at 40 weeks**
(`run_bhanushali_weekly_rank.CRS_LEN = 40`). The one leg of this grammar that looked like an
independent quality filter is both non-binding here and already installed at home.

## Do NOT re-test unless

A future proposal may not re-run Weinstein stage analysis on this universe unless it brings **at
least one** of:

1. **New data** — a universe with materially more stage-1 bases per year outside 2022-23 (e.g. a
   longer history than the 2017 pin, or a broader/smaller-cap universe), such that the per-year
   sample is not 5-negative-years-then-2023;
2. **A new formulation of the ENTRY geometry** that demonstrably shifts the ext-at-entry distribution
   — Gate-1's 0.0%-below-5% is the falsification target; a variant that puts a material share of
   entries near the slow line is a different object and may be proposed;
3. **A new sub-period** — genuine forward data from 2026-07 onward, judged forward, never re-cut
   in-sample.

**Explicitly refused as relitigation:** a different base length, flatness tolerance, range cap,
volume multiple or RS lookback; a tighter stop grafted on (that is not Weinstein's stop and would be
retuning toward a pass); or re-running with the M-rule off. The parameters were frozen before the run
and the failure is not a knob failure — it is 8 negative years out of 10 with the R sitting in the
wide-stop tail.

## Next setup

- **Bank the correlation asset.** ρ 0.34–0.38 to both incumbent sleeves is the first genuinely
  orthogonal long-only equity return stream this programme has produced. It failed only on edge. Any
  future third-leg question should start from *this* structural shape — a base-breakout book with its
  own line and its own exit — and ask what would give it an edge, rather than re-testing candidates
  that were never orthogonal to begin with. Recorded for the Oct-1 binder.
- **The census's G2 (Minervini VCP/SEPA) is next-in-line per the owner's standing order**, not run
  now — one grammar at a time. This finding sharpens its prior in two ways: (a) its 5-8% hard stop is
  the one mechanism in the census that would move the R away from the wide-stop tail this study
  landed in, which is now a *measured* reason to prefer it rather than a stylistic one; (b) its trade
  count must be Gate-1 censused first, because the 8-leg trend template will cut harder than
  Weinstein's stage filter did, and Weinstein's own 22.5/yr already produced a CI straddling zero.
- **G6 (Darvas) stays the control; nothing is spent on it.**
- **No component of this grammar is extracted onto the base.** O-001 and 0030/0087 remain killed for
  our book; they were tested here only in their letter-faithful foreign home.

## Reproduce

    python scripts/diag_ext_band_census.py       # the companion ext census
    python scripts/diag_g1_weinstein_gate1.py    # Gate-1: entry counts + ext at entry
    python scripts/run_weinstein_0124.py         # Phase 2: per-trade uncapped + capped book
