# Live stop conformance (audit) and the "why did it fall" discriminator — 2026-11-19

**Class: MEASUREMENT.** Owner queue, 2026-11-19. 0 trials, no sealed read, no rule proposed, no live change, no merge.
**Standing counts: screens 24 · sealed opens 4 · n_trials 3** (unchanged).

**Classification note, for the owner.** Part 2 is run in the exploration tier on the owner's instruction, so the counts
stay unchanged. Under `skills/verdict-machine` a feature-vs-label read on the banked 0116/0117 labels would normally be
priced as a screen, which would be screen #25. Whether it should be counted is listed as an owner decision.

**Kill-rule wording.** Per the 2026-08-08 amendment, no path is killed without a pre-registered run. "The domain stays
closed" is therefore read as **"no candidate for the January exploration lane; the path keeps its current priority"**.
It is a bound, not a KILL.

**Goal link.** Part 1 checks that live stops are the stops that were backtested, so the paper record measures the frozen
strategy. Part 2 bounds whether a stopped trade's cause of fall is knowable at stop time.

## Part 1 — live stop conformance (read-only engineering audit). Method stated before any result.

**Population.** Every swing entry in `results/attribution_ledger.csv` (69 rows: 48 reconstructed, 21 forward), joined
to `results/cards_archive.jsonl` (the card's `entry`, `entry_low` = signal-week low, `entry_high` = signal-week high,
`stop`) on ticker and signal_date. Only committed artifacts are read; no engine run touches post-cut prices.

**Live stop.** The ledger `stop`, produced at `scripts/run_bhanushali_cron.py:596`:
`stop = round(_record_stop(entry, lo), 2)`, with `_record_stop` at `:332`, i.e. max(week_low, entry × (1 − 0.10)).

**Frozen 0094 engine stop for the same signal.**
- `scripts/run_bhanushali_weekly_rank.py:1330`: `st = o_["lo"]`, the signal-week low (`_stop_arr = wlow`, `:394`;
  the live config has touch origin only).
- `:1344-1345`: lifted to entry × 0.90 by `max_risk_pct`.
- The engine's entry is the fill (the next-week open inside the band), so engine stop = max(week_low, fill × 0.90),
  and engine width = (fill − engine stop) / fill.

**Width gap per trade.** live width − engine width, in pp. The ledger carries both widths for closed rows
(`stop_width_pct_card`, `stop_width_pct_engine`); for open rows the engine width is recomputed from the card
`entry_low` and the ledger's fill price.

**Root cause of 3.76% vs 8.85% (finding 0143).** Width when the cap does not bind = (entry − week_low)/entry
= [(hi − lo)/entry] × [(entry − lo)/(hi − lo)], that is, signal-week range × entry position in the band.

The decomposition compares:
- **historical:** the unperturbed swing ledger 2019-01..2024-06 (`explore_blend_drawdown_sizing.navs()`), with each
  trade's band (lo, hi) read from the cut panel `ctx.P[t]["entry_win"]`;
- **live:** the card bands.

It reports the median of each factor and the share of trades at the 10% cap.

**Fills beyond the stop.** For ledger rows with `exit_reason` in {stop, stop_part}:
- slippage % = (close_price − stop) / stop;
- slippage in R = `beyond_stop_r` (the ledger's own decomposition);
- `gap_through`.

The stop order type and trigger basis are read from the code. The weekly-close trigger is at
`run_bhanushali_weekly_rank.py:1118`, `if wc <= p["stop"]`: a pending full exit filled at the next session's open
(`:868`). No broker stop order exists in the code base [to be confirmed by grep in the run].

**Output.** Fix options listed with what each changes. No rule is proposed.

## Part 2 — "why did it fall" discriminator. Method and kill rule stated before any result.

**Data.**
- `research/substrate/context_windows.parquet` (the banked 0116/0117 dataset that `diag_postentry_stage1.py` reads),
  train only: entry_date 2019-01-01..2024-06-30. Cohorts: `noise_stop` (391) and `false_touch` (314).
- **Additional sealed-safety cut:** the stop time must also be ≤ 2024-06-30. Rows whose stop falls after the cut are
  dropped and counted, so no 2024H2 bar is read.

**Stop time.** The last session strictly before `exit_date`: the weekly close that triggered the exit, which then
filled at the next open. **Firewall: every feature uses only bars ≤ the stop time.** Prices come from
`corrected_universe()` (adjusted OHLCV), cut at the stop time.

**Drawdown leg.** From the session of the highest close in [entry_date, stop time] to the stop time. If the peak is the
stop day itself, the leg is the entry → stop window.

**Features:**
- **(a) Market-adjusted leg return.** r_stock,leg − β · r_M150,leg, where M150 is the Nifty Midcap 150 TRI
  (`diagnostics/research/benchmarks/tri/nifty_midcap_150_tri.csv`). β is the OLS slope of daily stock returns on
  daily M150 returns over the 126 sessions before entry_date.
- **(b) Sector-adjusted leg return.** The same, with a sector index: the equal-weight daily return of the
  `corrected_universe()` names sharing the ticker's `config.SECTOR_MAP` label, excluding the ticker itself.
  `Others` and sectors with fewer than 5 names fall back to M150.
  **FLAG: SECTOR_MAP is a present-day map, not point-in-time**, and membership is survivorship-coloured.
- **(c) Market share of the leg.** 1 − var(ε)/var(r_stock) over the leg's daily returns, with ε = r_stock − β·r_M150
  and the pre-entry β. Clipped to [−1, 1]. Legs shorter than 5 sessions are NaN.
- **(d) Delivery on the breakdown day.** `deliv_pct` on the stop day, divided by its median over the 60 sessions
  before the stop day (`data/_delivery_raw.parquet`, release `dataset-pin-20260729`, series EQ).
- **(e) Results in the 5 sessions before the stop.** Whether a financial-results board meeting
  (`data/_earnings_raw.parquet`, purpose contains "Financial Results") has its `event_date` within the 5 sessions up to
  and including the stop time. **[assumed]** The NSE `ann_ts` timestamps the intimation, not the results release, so
  the meeting date is used as the results day. Disclosed.

**Statistics.**
- Per feature: mean(false_touch) − mean(noise_stop), with a two-sample cluster bootstrap on ticker
  (`nq.brain.portfolio.cluster_bootstrap_two_sample`, 2,000 draws), giving a 95% CI.
- Feature (e) is a share, so its difference is a difference in proportions with the same bootstrap.

**Kill rule (fixed now).** If every feature's 95% CI straddles zero, the domain gets no exploration-lane candidate (a
bound, as above). If any CI excludes zero, that feature is reported as a **candidate for the January exploration
lane**. No book backtest is run either way.

**Hindsight bound.** The rule is "keep the stop only when (a) is within ±1 SD of zero", with the SD pooled over both
cohorts. Stops with |a| > 1 SD are skipped and held. The R recoverable is the sum over the skipped trades of
`post_ret21` × exit_px / (entry − stop): the 21-session post-exit move in R, which is `diag_postentry_stage1`'s
giveback unit. It is reported for each cohort, net, and per year.
- It is hindsight in two ways: the cohort labels and `post_ret21` both look past the stop.
- It is an upper bound for this rule, not a backtest.
- The post-exit window for a stop near 2024-06-30 runs past the cut, but `post_ret21` is a banked column, not a new
  read. It is used as stored.

**Blind replica.** Re-derives feature (a) for both cohorts from a written spec.

---

## Part 1 — results [measured, `explore/2026-11-19_live_stop_conformance.json`; `pipelines/diagnostics/explore_live_stop_conformance.py`]

**Code path.** The live stop and the engine stop are **the same rule in code**:
- live: `scripts/run_bhanushali_cron.py:596`, calling `_record_stop` at `:332`;
- engine: `scripts/run_bhanushali_weekly_rank.py:1330` and `:1344-1345`.

Both are max(signal-week low, entry × 0.90). The live config has touch origin only, so the engine's stop array is the
signal-week low (`:394`), the same low the card uses. The only built-in difference is the reference price: the card uses
the last close or the band midpoint (`run_bhanushali_cron.py:594`), the engine the actual fill. That matters only where
the 10% cap binds.

**Width gap per trade.** 60 trades have both widths.

| | value |
|---|---|
| median live (card) width | 6.25% |
| median engine width | 6.74% |
| **median gap** | **0.00pp** |
| trades with \|gap\| > 0.5pp | 15 of 60 (max 26.2pp, SIEMENS) |

**What the 15 are.** Every one is a **two-source disagreement in the ledger**, not a rule divergence:
- the engine width is inferred as return% / R from the engine history;
- or the `stop_week_low` field disagrees with the card. GRAPHITE's card stop of 618.60 sits *below* its recorded week
  low of 654.35, which `_record_stop` cannot produce. SIEMENS's implied engine width of 32% exceeds the 10% cap, which
  the engine cannot produce.

This is the defect class 0143 found (3 of 11 then). It persists because the forward record stores the engine's stop for
only **19 of 58** rows in `results/signals_history_weekly.json`.

**Root cause of 3.76% vs 8.85% (0143). Market geometry, not code** [measured]:

| | n | median width | median signal-week range | median entry position in band | share at the 10% cap |
|---|---|---|---|---|---|
| historical 2019–24, all trades | 77 | 9.29% | 11.70% | 0.79 | 39% |
| historical, stop losses | 32 | 8.01% | 10.31% | 0.78 | 28% |
| live, with card band | 43 | 6.32% | **8.13%** | 0.80 | 16% |

A swap on the medians (width ≈ range × position) gives:
- historical range × historical position = 9.25;
- **live range × historical position = 6.43**;
- historical range × live position = 9.36.

**The narrower live signal-week range accounts for the whole gap.** The entry position is unchanged, and the cap binds
less often because the ranges are narrower. 0143's 3.76% figure was the first 11 live trades; the full live set's
median is 6.32%.

**Fills beyond the stop** (33 stop exits; per-trade list in the JSON):

| | value |
|---|---|
| exits filled beyond the stop | **30 of 33** |
| median slippage | **−2.39% / −0.20R** |
| worst | −7.80% / −3.53R |
| gap-through share | 76% |
| **stop order type** | **none.** A modelled market exit at the next session's open (pending exit, `run_bhanushali_weekly_rank.py:868`). A grep for GTT / SL-M / place_order finds only a comment on the unused disaster floor (`:977`). |
| **trigger basis** | **close basis, weekly.** `run_bhanushali_weekly_rank.py:1118` checks `if wc <= p["stop"]` on the week's last close; there is no intraday trigger. |

The overshoot is structural: a close-basis weekly trigger fills at the next open, below the level.

**Fix options. None is proposed; each is listed with what it changes.**
1. **Store the engine's own stop0 and fill on every forward row**, and have the ledger read them instead of inferring
   from return/R. *Changes:* ledger provenance only. Closes the 15 two-source mismatches. No trading change, no
   re-anchor.
2. **Print the card stop at the expected fill** (the next open) rather than the last close. *Changes:* card-to-record R
   parity where the cap binds. Same rule; display only.
3. **Rest a broker stop order (GTT/SL-M) at the stop level.** *Changes:* trigger basis from weekly close to intraday,
   which is a **rule change** (0105 hard-stop KILL, `FINDING_hard_stop`). It would need a pre-registered trial and,
   under the 2026-08-08 amendment, a re-test under the current harness.
4. **Nothing for the width itself.** The gap is narrower signal weeks, not code. Changing it means changing the stop
   rule, an axis with 0105/0106/0109 bounds on record.

## Part 2 — results [measured, `explore/2026-11-19_fall_discriminator.json`; `pipelines/diagnostics/explore_fall_discriminator.py`]

**Population.**
- Labelled train cohorts: noise_stop 391, false_touch 314.
- **39 rows dropped by the sealed-safety cut** (stop after 2024-06-30). Used: **noise_stop 367, false_touch 299**.
- The latest stop time read is 2024-06-28.
- 13.7% of trades use the M150 fallback for the sector index. The median drawdown leg is 17 sessions.

Differences are false_touch − noise_stop, two-sample cluster bootstrap on ticker, 2,000 draws:

| feature (at stop time) | noise_stop mean | false_touch mean | diff [95% CI] | excludes 0 | 99% CI (5-feature Bonferroni; added after first look) |
|---|---|---|---|---|---|
| a) leg return − β·M150 leg | −12.86% | −12.06% | +0.80pp [−0.87, +2.59] | no | [−1.34, +3.17] |
| b) leg return − β·sector leg (**SECTOR_MAP not PIT**) | −12.73% | −11.51% | +1.22pp [−0.50, +3.14] | no | [−1.02, +3.73] |
| c) market share of the leg's variance | 0.236 | 0.174 | −0.062 [−0.117, −0.005] | **yes (95%)** | **[−0.132, +0.011], straddles** |
| d) delivery % on the stop day / 60-day median | 1.065 | 1.060 | −0.005 [−0.047, +0.037] | no | [−0.056, +0.050] |
| e) results meeting within 5 sessions up to the stop | 6.8% | 16.4% | **+9.6pp [+4.7, +14.4]** | **yes** | **[+3.2, +15.8], survives** |

**Kill rule as pre-stated.** Two CIs exclude zero, (c) and (e), so the domain is **not** closed.

**Candidates for the January exploration lane:**
- **(e)**: a false touch is 2.4× as likely as a noise stop to have had a results meeting in the 5 sessions before the
  stop. It survives the 5-feature multiplicity check.
- **(c)**: marginal. It does not survive the 99% check, so it is flagged as weak.

No book backtest was run.

**Registry confrontation (cite and narrow).** `program-laws` Law V (0117) says the two cohorts are indistinguishable at
stop time **on price-path features**.
- Features (a), (b) and (d) **agree with Law V**: market-adjusted, sector-adjusted and delivery readings are null.
- (e) is an **event** feature, not a price-path one. It narrows Law V rather than overturning it.
- (e) is adjacent to 0120 (earnings proximity costs −0.383R, screen pass). That cost proved decision-margin-negative as
  a deferral rule (0121, −15.72 R/yr) and as sizing (0129). Per the 2026-08-08 amendment, those are evidence about their
  rules and set priority; they do not close (e).

**Hindsight bound for feature (a)**, per the pre-stated rule. Pooled SD of (a) = 11.6%. Keeping the stop only when
|a| ≤ 1 SD skips 274 stops (noise 146, false 128).

| | R |
|---|---|
| noise_stop, recovered | +145.4R |
| false_touch, further loss | −105.2R |
| **net, over 5.5 years** | **+40.2R (about +7.3R a year)** |

By stop year: 2019 −1.8, 2020 −19.3, 2021 +15.6, 2022 +7.8, 2023 +13.2, 2024H1 +24.7. The sign flips across years.
**This is hindsight twice over** (the labels and `post_ret21` both look past the stop), and it is an upper bound for
this rule. Even so, it sits **under the ±10 R/yr floor** [inferred]. Feature (a) itself does not separate the cohorts.

### Artifact check

1. **Multiplicity:** 5 features. Handled by the 99% check, which was added after first look. Only (e) survives.
2. **Sector map not PIT** (b). Present-day `config.SECTOR_MAP`, survivorship-coloured. **Not ruled out**; (b) is null
   anyway.
3. **Results date proxy** (e). The board-meeting `event_date` is used as the results day [assumed]. A meeting held
   after the stop day by up to 0 sessions is excluded by construction; the window ends at the stop time. Results
   released after market hours on the meeting day are counted on that day. **Not ruled out.**
4. **Label leakage.** The cohorts are defined by post-exit paths, but every feature uses bars ≤ the stop time
   (firewall). The 39 rows with a stop after the cut are dropped. **Ruled out for the features. Not ruled out for the
   hindsight bound**, which is labelled as such.
5. **Clustering.** The cluster bootstrap on ticker handles repeated names. Time clustering (several stops in one
   market drawdown) is not handled. **Not ruled out**: (c) in particular could reflect a few market-wide selloffs.

### Owner decisions (queued task)

1. **Screen accounting.** Does Part 2 count as screen #25 under `verdict-machine`? It was run in the exploration tier on
   your instruction, so the counts are unchanged.
2. **January exploration lane.** Should (e), the results-proximity false-touch feature, go into the lane, given that
   0121 and 0129 found the event cost decision-margin-negative as a deferral and as sizing? (c) is flagged as weak.
3. **Stop-record fix, option 1** (store the engine's stop0 and fill on every forward row). It is engineering only and
   needs your word. Options 2 to 4 are listed for information.

### Independent re-derivation of feature (a) [measured]

A fresh `blind-replica` worked from the spec and the exported closes, the M150 TRI and the trade list, with no code.
Spec, code and result are in `explore/2026-11-19_fall_discriminator_replica/`.

| quantity | replica | pipeline | gap |
|---|---|---|---|
| n noise / false | 367 / 299 | 367 / 299 | 0 |
| mean a, noise_stop | −0.12859 | −0.1286 | 0 |
| mean a, false_touch | −0.12059 | −0.1206 | 0 |
| diff | +0.00801 | +0.0080 | 0 |
| cluster 95% CI | [−0.00870, +0.02587] | [−0.0087, +0.0259] | 0 |
| pooled SD of a | 0.11625 | 0.1163 | 0 |

The replica flagged one reading: on a ticker's missing sessions, its multi-day return is paired with a one-day index
return. The pipeline makes the same choice, so the match confirms the arithmetic under that reading.

---

## Owner decisions, 2026-11-19

1. **Part 2 counts as screen #25**, because it read the banked 0117 cohort labels. Ledger row 25 was appended *after* the
   run, which is disclosed in the row. **Standing counts are now screens 25 · sealed opens 4 · n_trials 3.**
   `diagnostics/research/n_trials.json` notes that n_trials is unchanged. Every reciting file and its `.claude` mirror
   was updated, and `tests/test_standing_counts.py` passes (61).
2. **Feature (e) gets a hindsight bound before any lane decision.** It is part of screen #25, not a new screen.
3. **Stop-record fix, option 1, approved as engineering** (branch `eng/forward-stop-record`).

**(e) confirms; it does not independently replicate.** Feature (e) is the **stop-side form of finding 0120 Q1** (+9.8pp
false-touch enrichment near known events), measured on **overlapping trades** of the same banked substrate. It
**confirms** 0120 Q1; it is not an independent replication.

## (e) hindsight bound — definition and kill rule, stated before computing

**Population.** The screen #25 cohorts: 367 noise stops and 299 false touches, train only, stop time ≤ 2024-06-30,
firewall at the stop time. Of these, the **(e)-flagged stops** are those with a results meeting in the 5 sessions up to
the stop. Counted by cohort and by stop year.

**Counterfactual.** Each (e)-flagged stop is **not** taken, and the position is held to the trade's eventual exit.

**Eventual exit — primary.** The book's remaining exit rule after the stop: the **runner's 44-week SMA break**, i.e.
the first weekly close below the 44-week SMA at or after the stop week, filled at the next session's open
(`run_bhanushali_weekly_rank.py:1125`, the scaled-exit branch). Close basis, weekly. The price path comes from the
adjusted OHLCV, cut at 2024-06-30. A path with no exit by the cut is **marked to the 2024-06-28 close**.
- If the stop week's own close is already below the 44-week SMA, the SMA break fires at the same moment as the stop
  would have, and the recoverable R is 0. That is the rule-faithful result, not an artifact.
- The +2R tranche and the pattern tranche are ignored, because a stopped position has not reached +2R by the stop.
  Disclosed.

**Eventual exit — secondary, descriptive.** The banked 21-session post-stop path, `post_ret21` × exit_px / risk, marked
to the cut where the 21 sessions run past it.

**R per trade.** (hold exit price − stop fill price) / (entry − stop), on the full position. Units are the banked
substrate's R; it is an uncapped signal population, so this is not a capped-book R/yr. Disclosed.

**Reported:** total R, R per year over the 5.5 train years, per-year signs, and the worst single trade, by cohort and
net.

**Kill rule (owner, fixed now).** If **R per year is under 10**, or the **per-year sign flips in 2 or more of the 6 years**
(a year whose net sign is opposite to the total), the **stop domain closes for this book**, written into this report.
**No book backtest.**

## (e) hindsight bound — result [measured, `explore/2026-11-19_results_stop_bound.json`; `pipelines/diagnostics/explore_results_stop_bound.py`]

**Stops with a results meeting in the 5 sessions up to the stop:**

| cohort | flagged / total | 2019 | 2020 | 2021 | 2022 | 2023 | 2024H1 |
|---|---|---|---|---|---|---|---|
| false_touch | **49 / 299** | 8 | 4 | 7 | 24 | 3 | 3 |
| noise_stop | **25 / 367** | 5 | 1 | 6 | 3 | 4 | 6 |

**Each flagged stop held to the eventual exit** (74 trades). The primary hold uses the runner's 44-week SMA break,
marked to the cut. How the 74 holds ended:
- 39 **exit the same week**: the stop week already closes below the 44-week SMA, so 0R is recoverable;
- 28 exit at a later SMA break;
- 7 are marked to the cut.

| | primary: eventual exit | secondary: banked 21-session path |
|---|---|---|
| total R | **+116.3** | −2.1 |
| R per year (5.5 years) | **+21.1** | −0.4 |
| noise_stop / false_touch | +143.6 / −27.3 | +54.9 / −56.9 |
| by year 2019 · 20 · 21 · 22 · 23 · 24H1 | −4.8 · −3.0 · **+109.2** · −14.8 · +15.9 · +13.8 | +0.3 · −9.3 · +9.7 · −24.9 · +7.5 · +14.7 |
| years with sign opposite to the total | **3 of 6** | 4 of 6 |
| worst single trade | SUPRAJIT, false_touch, 2022-02-11: **−6.88R** | the same trade, −5.71R |

**Concentration** (primary):
- **One trade carries 74% of the total.** CUMMINSIND, a 2021 noise stop held to the cut, contributes +85.8R.
- The top 3 trades carry 99%.
- Without CUMMINSIND the primary bound is about +5.5R a year [inferred: (116.3 − 85.8) / 5.5].

### Verdict under the owner's kill rule

**KILL RULE MET: the stop domain closes for this book.**
- Primary: R per year is +21.1, which clears the 10 floor, but the per-year sign flips in **3 of 6 years** (the rule
  closes at 2 or more).
- The secondary reading fails both legs: −0.4R a year and 4 flips.
- The primary's floor clearance rests on a single trade.

This is a closure by the owner's pre-stated rule, applied to a hindsight bound. Per the 2026-08-08 amendment, the
closure is recorded as **"stop domain closed for this book by owner rule (screen #25 bound)"**. Re-opening it would take
a pre-registered run under the current harness.

**Artifacts:**
1. **Hindsight.** The cohort labels and the hold path both look past the stop. This is an upper bound.
2. **Eventual-exit approximation.** ISO-week closes and the 44-week SMA are recomputed from adjusted closes, and the
   +2R / pattern tranches are ignored. Disclosed.
3. **Mark-to-cut.** 7 holds have no exit by 2024-06-28 and are marked there. CUMMINSIND is one of them.
4. **Units.** R is the uncapped substrate's, not the capped book's R per year.
