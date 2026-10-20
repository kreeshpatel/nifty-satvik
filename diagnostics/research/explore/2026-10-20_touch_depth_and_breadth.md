# EXPLORE 2026-10-20 -- touch-depth ranking (item 1) and the signal funnel as a breadth gauge (item 4)

**Tier 0 (EXPLORE), `docs/PROCESS_TIERS.md`.** No pre-registration, no screen-ledger row, no `n_trials` change.
Every comparison below is **EXPLORATORY**: it suggests and ranks, it adopts nothing and changes no live setting.
Standing counts, parsed by the script from the ledgers (not recalled): **screens 23 · sealed opens 3 · n_trials 2**
(`diagnostics/research/n_trials.json`, `diagnostics/research/label_screen_ledger.md`).

Script: `pipelines/diagnostics/explore_touch_depth_and_breadth.py` (deterministic; ~2.5 min; re-run reproduces every
number). Outputs: `2026-10-20_touch_depth_and_breadth.json` (everything, including the run manifest) and
`..._weekly.csv` (the per-week breadth table).

## Method and guards

- **Train only.** Every price series is cut at 2024-06-30 before the engine sees it and the cut is asserted
  (`nq.lab.runs.cut_universe` / `assert_within_cut`); reported window 2019-01-01..2024-06-30. The sealed
  2024-07-01..2026-06-30 slice is never loaded. `results/judge_log.jsonl` is not touched.
- **Live configuration with PIT membership**, driven as `nq/lab/runs.replay` drives it: `engine_kwargs(DEFAULT_CONFIG)`,
  `load_membership()`, demerger events with `LIVE_PREP` (`as_of` pinned by `complete_weeks_only` prep), no edits to the
  engine or any production path. Manifest label for the engine kwargs + membership: **`LIVE BOOK`**. Each arm swaps only
  the `a_grade` set, which the manifest does not capture, so read the label as "engine and gate are live", not "A-set is live".
  The control reproduces the lab's documented live book exactly: **Sharpe 1.025 / CAGR 20.5% / MaxDD -40.1%**.
- **Engine facts verified.** `prep_weekly_rank` stores `s["entry_win"][e0] = (days, lo/stop, hi, crs_dist, sma_sig, origin)`;
  `grade_a_entries` groups windows by the ISO week of the entry day and keeps the top 5 by `crs_dist` descending. Under the
  live prep every window is `origin == 0` (touch), where `lo` is the signal-week low and `sma_sig` the signal-week 44w SMA
  (asserted: the weekly low and SMA re-derived here match the stored tuple for all 5,862 windows).
- **Touch depth, PIT.** (c) uses `depth_8w` = the minimum over the 8 weeks ending at the signal week of
  (weekly low / that week's own 44w SMA - 1), the "pullback low" extension of `forward/prereg_signal_quality.md` Q2.
  Q2 is written on `dist_to_sma_pct`, which the cron computes from closes; the engine does not keep weekly closes per entry,
  so this is the **low-based** form, the one faithful to the "pullback low, not signal-week ext" wording. A supplementary
  arm (c0) uses the simpler signal-week-low extension straight from the tuple. Both use only data known at the signal-week close.
- **Buyable** (as D6): band exists (`hi > lo`) and the name is a PIT Nifty-500 member on the entry date.
- **Deflation.** `nq.lab.runs.deflated_sharpe` with `n_trials = lab n_configs_tried() + 5 arms = 5` (the lab ledger
  `lab_runs.jsonl` is gitignored, so it reads 0 on a clean clone; the five arms here are each counted as a distinct config;
  the lab ledger is not written). `sr0` (expected max Sharpe) = 0.52. Sub-periods are **continuous slices** of the one
  full-run NAV, never fresh-capital re-runs.

## Item 1 -- rank the weekly top 5 by touch depth instead of CRS

Evidence being tested (registry `deep-near-sma-touch-edge`): touches < 5% above the 44w SMA are +0.717R (n=418) vs +0.094R
for 5-10%; extension is rank-orthogonal to CRS. Law II (population edges die in the 5-seat book, 0131 mechanism) is the
prior against it carrying over to the capped book.

Arms: **(a)** live A-set (control); **(b)** D6 `filter_before_rank=True`; **(c)** top 5 by smallest 8-week touch depth among
buyable names; **(d)** deep bucket (8w depth < 5%) first, CRS descending within bucket (touch depth with CRS as tiebreak;
a continuous depth has no ties, so the tiebreak is applied inside the registry's own deep/shallow bucket); **(c0)** as (c)
on signal-week-low depth. Set overlap with (a) by Jaccard: b 0.62, c 0.23, d 0.52, c0 0.19.

### Capped live book (5 seats), EXPLORATORY

| arm | Sharpe raw | Sharpe deflated (n=5) | CAGR % | MaxDD % | trades | Sharpe 2019-21 | Sharpe 2022-24H1 | CAGR 2019-21 | CAGR 2022-24H1 | DD 2019-21 | DD 2022-24H1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a live CRS (control) | 1.025 | 0.504 | 20.5 | -40.1 | 77 | 1.03 | 1.01 | 22.1 | 18.1 | -40.1 | -25.2 |
| b D6 filter-before-rank | 1.275 | 0.755 | 27.3 | -40.1 | 85 | 1.01 | 1.61 | 21.8 | 33.6 | -40.1 | -28.7 |
| c 8w depth, buyable | 0.837 | 0.316 | 15.1 | -32.8 | 99 | 0.94 | 0.71 | 17.3 | 12.4 | -32.8 | -22.0 |
| d deep bucket, then CRS | 1.262 | 0.742 | 25.3 | -33.2 | 74 | 1.49 | 0.93 | 32.5 | 16.5 | -33.2 | -26.1 |
| c0 signal-week depth | 0.739 | 0.219 | 12.2 | -31.7 | 99 | 0.81 | 0.63 | 13.8 | 10.1 | -27.4 | -24.1 |

DSR probabilities (n=5): a 0.80, b 0.87, c 0.71, d 0.86, c0 0.66.

**Does (c) beat (b) in both sub-periods? No.** Sharpe delta vs (b): 2019-21 -0.07, 2022-24H1 -0.90 (CAGR -4.4 pp and
-21.2 pp). Pure touch-depth ranking is worse than the CRS ranking in the capped book, and clearly worse in the later
sub-period. (d) beats (b) in 2019-21 (+0.48 Sharpe, +10.7 pp CAGR) and loses in 2022-24H1 (-0.68, -17.2 pp): a split, not a
pass. (d) does carry a shallower drawdown than (a)/(b) (-33.2 vs -40.1) with similar full-window Sharpe, but one drawdown
number from a 74-trade book is not a finding.

### Per-trade mean R of each A-set (uncapped book, so no seat rationing)

| arm | trades | mean R (closed) | median R | win % | worst trade | mean R excl. R < -5 | mean R 2019-21 | mean R 2022-24H1 |
|---|---|---|---|---|---|---|---|---|
| a live CRS | 526 | -0.262 | -0.653 | 42.8 | **-389.8R** (2019-05-06) | 0.637 | -0.474 | 0.077 |
| b D6 | 668 | -0.165 | -0.773 | 41.8 | **-389.8R** (same) | 0.554 | -0.297 | 0.017 |
| c 8w depth | 694 | 0.510 | -0.552 | 38.8 | -10.2R | 0.555 | 0.970 | -0.037 |
| d deep then CRS | 666 | -0.210 | -0.821 | 41.0 | **-389.8R** (same) | 0.500 | -0.310 | -0.084 |
| c0 signal-week | 752 | 0.602 | -0.512 | 37.7 | -17.3R | 0.659 | 1.226 | -0.119 |

**Read this table with the outlier in mind.** The headline uncapped means (a -0.26 vs c +0.51) look like a large
touch-depth edge in per-trade terms, but a single stop-part exit on 2019-05-06 at **-389.8R** (a near-zero band, so R
explodes) sits in sets a, b and d and in neither c nor c0. Excluding trades below -5R the arms are indistinguishable:
**0.50 to 0.66 R**. Medians are all negative (-0.5 to -0.8) and the depth-ranked sets have a *lower* win rate (38-39% vs
42-43%). So in this run the per-trade case that depth-ranked sets are better is **not** supported once the tail is
handled; the registry's +0.717R vs +0.094R is a statement about the touch population by depth bucket, not about a
5-per-week top slice, and this slice ranks differently (it ignores strength entirely). The 2022-24H1 mean R of the depth
sets is negative while their 2019-21 mean R is large, so even the unadjusted edge sits in one sub-period. The capped-book mean R
(a 0.877, b 0.741, c 0.542, d 1.194, c0 1.812 on closed trades) is a different and censored population (seats rationed,
10/13/9/7/9 positions still open at the cut) and should not be compared across arms.

### Item 1 reading (EXPLORATORY)

- Law II holds again: where the depth ranking looks good per trade it is not reaching the book, and the capped Sharpe falls
  (c 0.84, c0 0.74 vs a 1.03, b 1.28).
- The only candidate that is not worse than the control on full-window Sharpe is (d), the CRS-led ranking with a deep
  bucket in front, and its edge over (b) is one sub-period. Worth a note, not a trial.
- The big mover in this table is (b) over (a) (+0.25 Sharpe, +6.8 pp CAGR), which is the already-known D6 effect on the old A-set; it is
  the thing to beat, and it is a governance-class change that goes to the review, not something this note adopts.
- **Cheapest test that would change the answer** (not a refusal): a per-trade comparison of *the same names* at the touch-depth
  bucket boundary on the uncapped substrate with the -389.8R trade handled (R floor or exclusion declared first), judged
  on the 63d horizon, ≥2019 folds. If deep-bucket membership still adds R at equal CRS rank, a tier-2 bound is justified.

## Item 4 -- the signal funnel as a breadth gauge (zero-trial count, descriptive only)

Per week (keyed on the entry week's Monday; anchor = the prior Friday close): the number of entry windows ("signals")
across the universe, and as a percent of names with a bar that week. 286 weeks in 2019-01..2024-06, universe about
676 names with bars (about 497 PIT members). Signals per week: mean 16.6, median 11, p10 2, p90 38.5, max 133, 13 weeks
with none; about 2.4% of names on average (p90 5.5%).

Spearman rank correlation of weekly signal count with forward outcomes (n_eff is the overlap-adjusted n, n/horizon):

| outcome | n | rho (count) | rho (% of names) | n_eff | 2019-21 rho | 2022-24H1 rho |
|---|---|---|---|---|---|---|
| Nifty next 4w return | 283 | +0.02 | +0.02 | 71 | -0.01 | +0.13 |
| Nifty next 13w return | 274 | -0.03 | -0.02 | 21 | -0.08 | +0.16 |
| live book next 4w return | 283 | -0.02 | -0.02 | 71 | -0.01 | -0.00 |
| live book next 13w return | 274 | -0.05 | -0.05 | 21 | -0.18 | +0.13 |
| mean R of trades entered that week (live capped book) | 58 | -0.04 | -0.04 | 58 | -0.11 | +0.09 |
| mean R of trades entered that week (uncapped live A-set) | 217 | +0.13 | +0.14 | 217 | +0.09 | +0.27 |

Member-only counts (PIT members only) give the same picture (rho -0.02 to +0.03 against the Nifty and the book).

Quintile table, weekly signal count Q1 (0-4 signals) to Q5 (26-133 signals), next-13-week Nifty return mean / median:
Q1 5.6% / 5.5%, Q2 5.2% / 3.5%, Q3 1.8% / 2.6%, Q4 4.1% / 6.8%, Q5 3.3% / 5.8%; live-book next-13w return mean:
7.2%, 5.9%, 3.1%, 5.6%, 4.7%. No monotone pattern; the middle quintile is lowest, the flood quintile is not distinguishable
from the dry one. Next-4w Nifty: 1.2%, 1.8%, 0.8%, 1.2%, 1.2%.

Mean R of trades entered that week, median by count quintile (means are dominated by single trades, e.g. the Q1 mean of the
uncapped set is -8.6R from the 2019-05-06 outlier): uncapped A-set Q1..Q5 median R -0.23, -0.39, -0.61, -0.48, **+0.22**;
live capped book (about 12 weeks per quintile, noise) -0.54, +0.38, -1.01, -0.90, +0.75. Pooled over trades, the top decile of
signal weeks (>= 38.5 signals) versus the rest: uncapped A-set mean R +0.73 (n=39) vs -0.36 (n=403), difference +1.09, trade-level
bootstrap 95% CI [-0.55, +3.47]; live book -0.00 (n=7) vs +0.98 (n=60), CI [-3.2, +0.9].

**Reading (EXPLORATORY, descriptive).** A flood of touches (a broad sell-off in the leaders' pullbacks) is **not** followed by
a measurably better or worse market or book outcome: correlations are within about 0.05 of zero for the Nifty and the
book, and the sign flips between 2019-21 and 2022-24H1 (the book's 13w rho goes -0.18 to +0.13). The only faint tilt is a
slightly better median trade R in the highest-count quintile for the uncapped set (+0.22 vs -0.2 to -0.6), but the pooled
difference has a CI spanning zero and is carried by the tail trades; with 7 live-book trades in the flood decile nothing
can be said there. This matches the weak prior from 0103 (regime switches were not learnable out of sample on other books):
a signal count is not a usable regime switch on this evidence. It is a free, PIT, already-computed series, so it can keep
being logged as a descriptive gauge; it is not a candidate rule.

## Caveats

- Item 1 arms are n=5 configs in one exploratory pass on one window (about 5.5 years, n_eff about 22 independent 63-day windows);
  deflation at n=5 is lenient and the 0.59 Sharpe half-width noted in `n_trials.json` applies: differences of 0.1 to 0.3 Sharpe
  between arms are not resolvable.
- The -389.8R trade is an engine artefact of an uncapped book (tiny band); it does not occur in the capped live book (worst
  -5.4R). It is flagged, not fixed, and not hidden.
- Open positions at the cut are closed at the mark as `eos` and excluded from closed-trade R; counts are in the JSON.
- Item 4 uses the engine's entry windows (touch signals); the denominator of "% of names" is names with a bar in the signal week.
