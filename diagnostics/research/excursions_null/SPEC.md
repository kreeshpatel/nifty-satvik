# Excursions versus the random-walk null — SPEC (written before any result)

**Class:** MEASUREMENT. No trial, no screen row, nothing adopted.
Standing counts at writing, read from the ledgers: **screens 19 · sealed opens 1 · n_trials 2.**
**Plan:** Satvik Brain, Phase 1, item 1. It answers owner observation 1: "our targets are too high
somewhere and that price is never hit."
**Written:** 2026-09-16, committed before the diagnostic exists. The definitions and the interpretation
rules below are fixed now and are not revisited after the numbers come in.

## The question

For the book's own entries, with their real stop distances, how often does price reach
**+kR before the stop**, compared with what a random walk gives the same geometry?

"The target is never hit" has two different causes, and they call for different responses:

- **geometry:** a 2:1 target is reached about a third of the time by pure chance, whatever you buy.
  A low hit rate is then arithmetic, not a defect.
- **selection:** our entries reach the target *less* often than chance, or their advantage fades
  before 2R. Then the targets really are beyond what the entries deliver.

Only a comparison with the null separates the two.

## Prior art — cited, not repeated

`pipelines/diagnostics/diag_barrier_base_rate.py` (`barrier_base_rate.json`) measured *fixed-percentage*
barriers (+10% / −3% and a surface) on every stock-day, and on a candidate signal. Hit rates sat on the
theorem (23.6% against 23.1%): barrier geometry by itself carries no edge. This study differs in three
ways:

1. it uses the book's **own entries and per-trade stop distances**;
2. it sweeps the target in **R multiples** (the unit the live exit is set in);
3. it compares against a **per-trade null**.

## Populations

- **A — the research substrate** `research/substrate/trades.parquet`. Only `split ∈ {train, holdout}`
  (2019 onward; `pre2019_untrusted` is excluded by its own label).
  - Primary: `setup == touch44`, the live setup.
  - Secondary: all setups pooled.
  - Train and holdout are reported **separately**, never pooled into one headline.
- **B — the live forward book**: every entered trade since inception 2026-07-04, with entry and stop
  from the first archived card carrying `bought_date` (`results/cards_archive.jsonl`), falling back to
  `results/signals_history_weekly.json`. This is description only: data after WALL_DATE 2026-05-30
  is forward holdout and fits nothing. At n < 30 it is flagged uninformative.

## Definitions

- E = entry, S = stop, risk r = (E − S) / E. A trade with r ≤ 0 is dropped and counted.
- Target T_k = E + k·(E − S) for **k ∈ {0.5, 1, 1.5, 2, 3}** (fixed; 2 is the live `tp1_r`).
- **Path:** daily bars from the entry session (inclusive; the entry is at that session's open, so its
  whole range comes after the fill), up to **260 sessions**.
- **Target touch:** High ≥ T_k. **Stop touch:** Low ≤ S (continuous monitoring, the same convention as
  the theorem). If one bar touches both, the **stop counts first** (conservative; matches the prior
  study and pre-reg 0011).
- **Resolved** = either barrier touched within the horizon. Unresolved trades are counted, not dropped
  silently.
- The book's own exits (tranches, pattern, runner, weekly-close stop) are deliberately ignored. This
  measures the entry's geometry, not the exit policy.

## The null

- **Primary, driftless:** P₀ = b / (a + b), with a = ln(T_k / E) and b = ln(E / S). This is σ-free.
- **Sensitivity, drifted:**

      P = (1 − e^{2νb/σ²}) / (e^{−2νa/σ²} − e^{2νb/σ²})

  with ν = μ − σ²/2 and μ = +15% a year. σ is the stock's own annualised daily log-return stdev over
  the 63 sessions before entry (point-in-time); a trade with fewer than 40 prior sessions uses the
  primary null only.
- **Reported, per k:** observed hit rate among resolved trades; the mean null over the *same* trades;
  excess = observed − null.

## Uncertainty

- CIs by **cluster bootstrap on ticker**: 2,000 draws, seed 20260916. Paths overlap within a name, so
  per-trade CIs would be too tight.
- Every cell carries n, and is flagged **uninformative** below 30 resolved trades.

## Bands (fixed in advance)

Risk r in **[0, 5%)**, **[5%, 10%)**, **[10%, ∞)**. The 10% edge is the live `max_risk_pct`.

## Exclusions (data integrity, counted and reported)

A trade is excluded if its path window contains:
- a registered demerger ex-date (`data/corporate_actions_demerger_register.csv`,
  `data/corporate_actions_post_harvest.csv`), or
- any single-session close-to-close move ≤ −45% or ≥ +90%.

The swing path's raw cache carries unadjusted splits (`research/substrate/DATA_BUG_unadjusted_splits.md`),
and each would read as a false stop touch.

## Also reported (descriptive)

- median sessions to the +2R touch among hits;
- the distribution of MFE in R before the stop touch.

## Interpretation rules (fixed before the numbers)

1. **Excess CI straddles 0 at k = 2:** the 2R hit rate is what geometry gives. The target is not
   "too high" relative to chance; a higher rate needs better selection or drift, not a closer target.
2. **Excess clearly positive at small k but falling to ~0 by k = 2:** the entries have an edge that
   decays before 2R. That is a **hypothesis** that a closer first target may suit the edge. It can only
   be tested by a pre-registered trial on train windows, and changed live only at a quarterly review.
3. **Excess clearly negative at k = 2:** selection reaches the target less often than chance. This is
   a selection finding, not a target finding.
4. **Excess positive through k = 3:** the target is inside the edge's reach, and "never hit" is sample
   noise or path timing.

**Whatever the result, nothing is adopted.** A change to `tp1_r` changes the live book and needs a
pre-registration, a trial, and the quarterly review. These numbers describe outcomes; program-laws I
says they are not features for choosing entries.

---

## Amendment A1 — 2026-09-16, after the first run: the sealed slice

**What went wrong.** Population A read `split ∈ {train, holdout}`. The substrate's `holdout` split
(2023-01-02 onward) **contains the sealed validation slice**: entries from 2024-07-01 to 2026-06-30
(`verdict-machine`; `label_screen_ledger.md`). The first run therefore opened the seal with no rule
frozen and no ledger row written first. `/skills-first`, run after the results existed, caught it.

**Owner decision, the same day:** count it, disclose it, guard it.
- It is recorded as **sealed open S2 (unplanned)**.
- Its numbers are reported, but never as evidence.
- `nq.brain.io.assert_unsealed` now refuses any substrate selection that reaches into the slice
  without a ledger S-row.

**Populations after A1:**
- **Evidence** (all interpretation rules apply here, and only here):
  - `train` = split `train`, entries 2019-01-14 .. 2022-12-26;
  - `holdout_unsealed` = split `holdout` with entry_date ≤ 2024-06-30.

  Both are reported separately, as before.
- **`sealed_S2`**, disclosure only: entries 2024-07-01 .. 2026-06-30. It is read only through
  `assert_unsealed(..., declared_open="S2")`, so every rerun reproduces the record rather than
  opening the slice again. **No interpretation rule reads it.** It also can no longer validate any
  future rule about target distance, R-multiple targets, or stop-width bands.
- **Live book:** unchanged. It is forward-wall description.

Nothing else in the SPEC changes: definitions, null, bands, bootstrap, and the interpretation rules.

## Amendment A2 — 2026-09-16, after the red-team read: a matched-control null and three fixes

**Why.** The `red-team` read of the first run found the arithmetic reproducible (0 of 3,781 outcomes
mismatched), but the reading wrong:
- The first-passage nulls omit the drift the universe actually had: equal-weight average ≈ 20%/yr in
  both 2019–22 and 2023–26, against the SPEC's μ = 15%.
- Against **stocks bought the same day with similar volatility and the same stop distance**, the
  entries' "excess over chance" mostly disappears.

That control is the right null for "is the selection better than the market", so it is added here.
**It is post-hoc,** added after results were seen, and it is labelled as such everywhere it appears.

**A2.1 — matched-control null (post-hoc), evidence populations only.** For each trade:
- Draw up to **20 other tickers**, seed 20260916, that print a bar on the entry date with ≥ 64 prior
  bars, a pre-entry σ within **±25%** of the trade's, and no split-size move or registered demerger in
  their own window.
- Put each at that session's **open**, with the trade's **risk fraction** r and the same +kR targets.
- Take the control rate as the mean over the resolved controls.
- **Excess = trade outcome − control rate**, cluster-bootstrapped on ticker.

Caveat: controls come from the corrected universe, not point-in-time index membership.

**A2.2 — the live stop rule (post-hoc, descriptive).** Alongside the SPEC's continuous stop, the same
table with the book's actual stop: a **weekly close ≤ S** (the last bar of each ISO week in the data),
target unchanged, same-week ties counted as the target touched first only when the target bar is
earlier. Both the trade and its controls are measured this way.

**A2.3 — fixes.**
1. **Live prices:** they were dividend-adjusted (`download_ohlcv` uses `auto_adjust=True`) while the
   archived entry and stop are raw, which pushes toward earlier stops. The live leg now downloads
   unadjusted prices.
2. **Band edge:** risk is rounded to 6 dp before banding, so a stop capped at exactly 10% lands in
   `r>=10%` as the SPEC's `[10%, ∞)` says, not by float noise.
3. **Live source:** the live entries and stops were read from the archived weekly snapshots
   (`results/archive/*/signals_today_weekly.json`), not `cards_archive.jsonl`. Entry equals
   `fill_price` in every snapshot, so this is harmless; the SPEC text is corrected by this note.

**Reading after A2.**
- The SPEC's rules are still reported against the first-passage null, as specified.
- **Claims about selection ("better or worse than chance") are made only against the matched control.**
  The first-passage null cannot separate selection from market drift.
- Band-level results are descriptive. No band claim is made unless it holds against the matched
  control in both evidence populations (about 160 cells were looked at; some land outside zero by
  chance).
