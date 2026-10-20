# 2026-10-20 — B5 correlation-cluster activation count, and B7 live-book anchor

**Tier:** EXPLORE / MEASURE (`docs/PROCESS_TIERS.md`, tiers 0-1). No pre-registration, no screen row, no
`n_trials` change. Both items are descriptive. **B5 is an activation-bound input only**: it tests no
cluster rule and adopts nothing. **B7** re-measures the live book so the programme has an anchor on the
live book.

**Standing counts (read from the ledgers by the script, not from memory):** screens **23** · sealed
opens **3** · n_trials **2** (`diagnostics/research/label_screen_ledger.md`,
`diagnostics/research/n_trials.json`). Unchanged by this note.

**Reproduce:** `python pipelines/diagnostics/diag_cluster_and_anchor.py` (about 4 minutes) writes
`2026-10-20_cluster_and_anchor.json` beside this note, plus two untracked audit CSVs of every pair.
Code at `db35f72`; data vintage 2024-06-28.

**Train only.** Every price series is cut at 2024-06-30 by `nq.lab.runs.cut_universe` before the engine,
the correlation matrix or the Nifty benchmark sees it, and the cut is asserted (last bar seen
2024-06-28). Reported window 2019-01-01..2024-06-30. The OHLCV pickles physically contain later bars;
they are truncated in memory before any computation, and nothing past the cut is used. The sealed judge
log is not touched.

**Live configuration.** Every engine run goes through `nq.lab.runs` (`replay`, `engine_kwargs`,
`DEFAULT_CONFIG`, `pit_membership=True`). Manifest labels recorded:

| run | manifest label | differs from live on |
|---|---|---|
| B7 base (`DEFAULT_CONFIG`) | **LIVE BOOK** | nothing |
| B7 bridge (frozen-0094 switches) | NOT LIVE BOOK | ext_cap, grade_gate, max_notional_pct, max_risk_pct, scaled_exit |
| B5 uncapped ledger (`uncapped=True`) | NOT LIVE BOOK | uncapped only (`replay`) |
| B5 uncapped ledger, filter-before-rank A-set | NOT LIVE BOOK | uncapped + A-set (same call, `a_grade` swapped; `replay` has no such key) |

---

## B7 — the anchor on the live book

### Result (continuous slices of one full run, never fresh-capital re-runs)

Live book, `DEFAULT_CONFIG`, PIT membership, 2019-01-01..2024-06-28, ₹10L. CAGR is calendar-annualised
(matches the engine's own 20.47%). Sharpe uses the lab's convention (daily, ddof 1, rf 0); Sortino is
`nq.validation.metrics.sortino`.

| window | Sharpe | Sortino | CAGR | MaxDD | trades entered | win rate | mean R |
|---|---|---|---|---|---|---|---|
| **2019-01..2024-06 (full)** | **1.025** | 1.314 | 20.5% | −40.1% | 77 | 48.1% | +1.29 |
| 2019-21 | 1.029 | 1.383 | 22.2% | −40.1% | 51 | 43.1% | +1.20 |
| 2022-24H1 | 1.026 | 1.231 | 18.5% | −25.2% | 26 | 57.7% | +1.46 |

Drawdown inside each slice is measured against the slice's own running peak; against the full run's peak
it is identical here (the −40.1% trough is in 2020). This reproduces the 20.5% / 1.025 / −40.1% that
`nq.lab.runs.replay` documents for the same window.

**Resolution warning.** 77 trades over 5.5 years is roughly 22 independent 63-day windows. The standing
resolution floor (`plausibility_anchors.md` §3, ΔSharpe half-width about 0.59 at n_eff 37) is wider still
here. 1.025 is a point estimate, not a distinguishable-from-0.6 claim.

### Beside the run of record

Quoted from `docs/references/plausibility_anchors.md` §6 and the sources it names
(`docs/BHANUSHALI_REPRODUCE.md`, `research/config_CHANGELOG.md`, `tests/test_swing_adapter.py`).

| | book / config | window | Sharpe | CAGR | MaxDD | trades | win | mean R | slices (Sharpe) |
|---|---|---|---|---|---|---|---|---|---|
| **Run of record**, frozen 0094 (`weekly-swing-0094-rank`) | all grades, engine default exit, no ext/risk/notional caps, PIT membership, corrected universe | 2017-2026 | 1.132 | 24.7% | −42.4% | 255 | 59.2% | +0.481 | 2017-18 +1.17 · 2019-21 +1.05 · 2022-26 +1.19 |
| **B7 live book** (this note) | `DEFAULT_CONFIG`: Grade-A only, ext_cap 0.20, risk cap 0.10, notional cap 0.20, config-P scaled exit, PIT | 2019-01..2024-06 | 1.025 | 20.5% | −40.1% | 77 | 48.1% | +1.29 | 2019-21 1.03 · 2022-24H1 1.03 |
| Bridge: live plumbing, frozen-0094 switches | all grades, no caps, engine default exit, PIT | 2019-01..2024-06 | 1.503 | 35.9% | −42.4% | 157 | 62.4% | +0.60 | 2019-21 1.06 · 2022-24H1 2.12 |
| Replica: exact record call on cut data, sliced | `backtest(prep(cut), PIT, start=2017-01-01)` | 2019-01..2024-06 | 1.487 | 36.1% | −42.4% | 156 | 62.8% | +0.60 | 2017-18 **1.17** · 2019-21 **1.05** · 2022-24H1 2.12 |

(The long-horizon anchors in the same file, `baseline_v1` 0.667 / 15.46% / −46.26% and its 0.570
sub-period base, are a different book and are not comparable to any row above.)

### Which switches differ, and what the bridge shows

1. **The replica validates the comparison.** Run on cut data, the record's own call reproduces the
   published 2017-18 slice (1.165, published +1.17) and 2019-21 slice (1.053, published +1.05), and the
   −42.4% trough. The engine is causal, so slices that end before the cut must match; they do. So the
   cut and the harness are not what separates the live book from the record.
2. **Window.** The record spans 2017-2026. The live anchor here ends 2024-06-28 by the train rule. The
   record's 2022-26 slice (+1.19) includes 2024-07 onward, which is sealed and was not read, so it cannot
   be compared to the 2022-24H1 slice (2.12 for the frozen switches). Whatever pulled +1.19 below 2.12
   lies in the sealed span and is not decomposable on train data.
3. **Five live-only switches** (manifest `differs_on`: ext_cap, grade_gate, max_notional_pct,
   max_risk_pct, scaled_exit; the A-grade gate is the `grade_gate` item, the exit is the config-P scaled exit). Turning them back to the frozen
   defaults on the same window and plumbing lifts the book from 1.025 to 1.503 Sharpe (CAGR 20.5% to
   35.9%, trades 77 to 157, MaxDD about the same) in-sample. This is the combined effect of the switches,
   not an ablation of each, and it is consistent with the recorded owner-override history: ADR 0010 adopted
   config P against the research recommendation, and the registry describes A-only as a defensive variant,
   not a return edge. It is an observation about this window, not a recommendation: the bridge book is
   not the live book, and 2019-24H1 favours it.
4. **Live plumbing the record lacks** (staleness guard, B′ demerger events, completed-weeks prep) is not
   switchable from `replay`. Its effect is bounded by the bridge-versus-replica gap on matched slices:
   2019-21 1.063 vs 1.053 and 2022-24H1 2.123 vs 2.120. Immaterial at this resolution (the bridge also
   restarts capital at 2019-01-01, so some of that gap is path, not plumbing).
5. **Plausibility.** The live book reads below the record (1.025 vs 1.132), not above it, so the
   "better than anchor is a defect" rule is not triggered. The 1.50 bridge figure is above the record and
   is explained: the record's 2017-26 window includes the sealed span and 2017-18, the sliced pieces
   reproduce, and it is not a live number.

### Proposed anchor row (for the owner to add; `plausibility_anchors.md` is not edited here)

Suggested for §6, "Swing book", beside the frozen-0094 row:

> **Live book, train window (measured 2026-10-20, `DEFAULT_CONFIG`, manifest LIVE BOOK, PIT membership,
> data vintage 2024-06-28, 2019-01-01..2024-06-28, ₹10L):** Sharpe **1.025**, Sortino 1.314, CAGR
> **20.5%** (calendar), MaxDD **−40.1%**, 77 trades, win 48.1%, mean R +1.29. Continuous slices: 2019-21
> **1.03**, 2022-24H1 **1.03** (MaxDD −25.2%). Source:
> `diagnostics/research/engine_assumptions/2026-10-20_cluster_and_anchor.json`. Not comparable to the
> frozen-0094 row (different switches and window); a live-book variant that beats 1.03 on this window by
> less than the resolution floor is not distinguishable from it.

---

## B5 — correlation-cluster activation count (ACTIVATION-BOUND INPUT ONLY)

Label: descriptive, zero-trial. Nothing here tests, tunes or recommends a cluster rule.

**Method.** For each setup week in the train window (273 weeks with a signal pool; entry week starting
2019-01-01..2024-06-30) the live Grade-A top-5 is `R94.grade_a_entries(P)`; the variant is
`grade_a_entries(P, mem=mem, filter_before_rank=True)`. Pairwise Pearson correlation of trailing
126-session daily close-to-close returns, pairwise-complete with at least 100 overlapping returns, sliced
at the last session of the signal week and asserted strictly before the entry week (PIT). Market
drawdown week: Nifty-50 close at least 10% below its trailing 252-session high at that same close (35 of
the weeks). Weeks with fewer than two names or no computable pair are dropped (14 live, 27 variant).
Random-5 control: five names drawn at random from the same week's full signal pool, 20 draws, seed fixed.

### Finding 1 (a data defect that dominates the raw reading): alias duplicates in the live top-5

In the live Grade-A set, 29 of the 34 pairs above 0.7 (in 28 of the 33 weeks that have one) sit at correlation 0.98-1.00: the **same company
under two symbols** (PVR/PVRINOX, EPL/ESSELPACK, 360ONE/IIFLWAM, SWANCORP/SWANENERGY,
AKZOINDIA/JSWDULUX, GET&D/GVT&D, NAVA/NBVENTURES, COHANCE/SUVENPHAR, GSKCONS/HINDUNILVR after the merger, and others) — renamed or merged
tickers that coexist in the corrected universe. In the unfiltered live rank they occupy two of the five
Grade-A slots (28 of 259 weeks, 29 pairs), and in every one of those 28 weeks one leg is not an index member, so it
is refused at fill. This is the seat-waste mechanism D6 / `filter_before_rank` describes, seen from the
correlation side. The filter-before-rank variant has no pair above 0.98. Both readings are reported.

### Results

| | live Grade-A, as measured | live Grade-A, alias-de-duplicated | filter-before-rank | random-5 from pool (de-dup) |
|---|---|---|---|---|
| weeks with at least one computable pair | 259 | 259 | 246 | about 205 per draw |
| share of weeks with a pair above 0.5 | **27.0%** (70) | **17.0%** (44) | **21.1%** (52) | 17.4% (as measured 20.5%) |
| share of weeks with a pair above 0.7 | **12.7%** (33) | **1.9%** (5) | **2.8%** (7) | 2.0% (as measured 5.6%) |
| mean pairwise correlation, all weeks | 0.214 | 0.205 | 0.212 | 0.210 |
| mean pairwise correlation, drawdown weeks (35) | 0.319 | 0.314 | 0.330 | 0.328 |
| mean pairwise correlation, calm weeks | 0.198 | 0.188 | 0.192 | 0.187 |
| drawdown minus calm, week-bootstrap 95% CI | +0.121 [+0.086, +0.157] | +0.127 [+0.093, +0.159] | +0.137 [+0.103, +0.172] | n/a |
| share of weeks with a pair above 0.5, drawdown / calm | 48.6% / 23.7% | 42.9% / 12.9% | 51.4% / 16.1% | n/a |

Reading: (a) once alias duplicates are removed, the live top-5 holds a pair above 0.5 in about one week
in six and above 0.7 in about one week in fifty; (b) correlation within the top-5 rises by about 0.12-0.14
in drawdown weeks, but a random draw from the same signal pool rises by the same amount (0.33 vs 0.19), so
this is the market-wide common factor, not something the top-5 selection adds; (c) the top-5 is not
measurably more clustered than a random five from its own pool. The control compares different week sets
for some cells (205-208 weeks versus 246-259) and is context, not a test.

### Do high-correlation pairs' trade outcomes co-move?

Pairs are matched to an **uncapped live-config replay ledger** on ticker plus entry ISO week (R is the
trade's own R multiple). Co-movement is the Pearson correlation of the symmetrised pair list. The
control is non-clustered pairs (correlation at or below the threshold) from the same weeks, and from all
weeks.

| variant, threshold | high-corr pairs matched (weeks) | co-move (Pearson / Spearman) | same-week non-clustered control | all-week control | diff, week-bootstrap CI |
|---|---|---|---|---|---|
| live, >0.5 | 9 (8) | 0.59 / 0.67 | 0.47 / 0.76 (22 pairs) | 0.21 / 0.21 (444) | +0.12 [−0.56, +0.57] |
| live, >0.7 | **0** | n/a | n/a | 0.22 / 0.22 (453) | n/a |
| filter-before-rank, >0.5 | 22 (18) | 0.22 / 0.48 | 0.31 / 0.41 (57 pairs) | 0.15 / 0.20 (708) | −0.08 [−0.46, +0.47] |
| filter-before-rank, >0.7 | 3 (3) | 0.66 / 0.83 | 0.01 / −0.01 (9 pairs) | 0.16 / 0.21 (727) | n/a (too few) |

The alias-de-duplicated rows for the live variant are identical at >0.5 (none of the nine matched pairs
involves a duplicate) and there is nothing at >0.7.

**Reading: UNDERPOWERED.** Matched high-correlation pairs are 0-22 in 5.5 years and every confidence
interval spans zero by a wide margin. Against the all-week control (about 0.15-0.22) the high-correlation
point estimates are larger at >0.5 in the live variant, but the same-week control is similarly large
(common weekly shocks), and the difference is indistinguishable from zero. No co-movement claim is
supported either way.

**Why so few matched pairs (itself an activation fact).** Only about 19% of live pairs (33% for the
variant) have both legs funded in the uncapped replay, because an uncapped fill still needs index
membership, an entry inside the band under ext_cap 0.20, and the name not already held. Pairs above 0.7 in
the live variant had a leg fill rate of 19% (no pair had both legs) versus 43% for pairs at or below 0.5,
since most are the non-member alias duplicates above. Under the variant the leg fill rate is 55-58%
across buckets.

### What this gives the activation bound (input only)

Counting weeks (not R): on the train window the live top-5 had a pair above 0.5 in 44 weeks (17.0%, about
8 a year) and above 0.7 in 5 weeks (1.9%) once duplicates are removed; the variant 52 weeks (21.1%) and 7
weeks (2.8%). The weeks where both legs of a high-correlation pair were actually funded and have an R are
9 (live) or 22 (variant) at >0.5 and 0 or 3 at >0.7 over 5.5 years, that is roughly 2-4 a year at the
looser threshold. Any rule keyed on these clusters therefore activates on a small number of funded trades;
that is a statement about frequency only, with no outcome sign attached.

## Caveats

- Correlations use the corrected-universe close series (`s["c"]`), including alias-stitched names; the
  duplicate finding is a property of that universe, not of the market.
- The 126-session window means the earliest 2019 weeks use 2018 history (fine, PIT), and new listings with
  under 100 overlapping returns drop out of the pair set.
- The uncapped ledger matches only trades the engine would have filled; unmatched pairs are not treated
  as zero outcomes.
- Lab-meter side effect: three distinct configs were added to the untracked `lab_runs.jsonl` (the meter
  counts ideas, not clicks); this is the multiplicity meter, not the programme's `n_trials`.
