---
name: program-laws
description: >
  ALWAYS read before proposing or evaluating ANY research idea, overlay, signal, feature, entry,
  exit, sizing, universe, regime, or ML/learning idea in the long-horizon or swing program — these
  are the standing verdicts the program already paid for, with receipts. Trigger phrases: "new
  idea", "what if we", "should we test", "is this worth testing", "has this been tried", "propose
  an overlay", "new feature", "new signal", "entry quality", "predict winners", "pre-entry",
  "chart structure", "perception", "train a model", "learning bot", "regime", "relitigate",
  "re-open", "why was this killed", "standing counts", "n_trials", "screen ledger".
---

# Program Laws — the standing verdicts, with receipts

**Read this BEFORE proposing any research idea, overlay, feature, signal, exit, sizing rule, or
"what if we tried…".** These are not opinions or heuristics. Each is a law the programme paid for
with a measurement or a trial, each has a citation, and each tells you what to do when a new idea
collides with it.

**The collision rule, once, for all laws below: CITE AND NARROW, DO NOT RELITIGATE.** When an idea
touches a law, the session's job is to (a) cite the law in the pre-registration, (b) state which of
{new data, new feature source, new sub-period, new formulation} it brings, and (c) **narrow the
study to the part the law did not answer**. If you cannot name one of the four, the ledger has
already answered — do not re-run the dead test. Re-running it with a bigger sample, a different
model, or a different rubric is not new evidence; it is refused relitigation.

> ### AMENDMENT — 2026-08-08, owner decision: a citation can defer a path, never kill one
>
> **No path may be given a negative verdict without a run under the current harness.** Not KILL, not
> a screen-derived bound, not "refused relitigation". The collision rule above still governs *how* a
> study is scoped — cite the law, name what you bring, narrow to the unanswered part — but it no
> longer terminates anything on its own.
>
> **Why the owner ruled this way, and why the receipts support it.** The apparatus that produced most
> of the verdicts below is not the apparatus in the repo today. Between them sit the continuous-slice
> fix (a phantom 2022-26 base of 0.762 / −40% against the correct 0.570 / −46.3%, which produced
> false KILLs and wrongly downgraded 0071), the calendar-annualisation fix (commit `2e8a901` — every
> pinned CAGR was ~0.44pp high), the baseline_v0 → baseline_v1 re-anchor, the macro PIT truncation
> gate that split a real USD effect from a crude lookahead artifact, and the survivorship backfill
> whose bias *scales with holding period*. Independently, only 7 of 108 closed verdicts were measured
> on the book that is actually trading. A verdict is evidence about the regime that produced it, and
> most of these regimes are gone.
>
> **What this changes in practice.** A prior KILL is read as `KILL (epoch E, book B) — not re-tested
> under the current harness`. That status may be quoted, prioritised against, and used to argue a
> path is low-value. It may **not** be used to close one. Closing requires a pre-registered run whose
> outcome table was fixed in advance.
>
> **What it does not change.** The ordering still binds absolutely — pre-reg committed, counter
> incremented, then the run, thresholds never revisited. `n_trials` is still incremented for every
> re-test, and the re-tests run on the same 2017–2026 daily windows as the originals, so they raise
> the substantive multiplicity exactly as `n_trials.json` warns. Expect UNDERPOWERED to be the modal
> outcome: at n_eff ≈ 37 independent 63-day windows the dSharpe half-width is ~0.59, and no run
> resolves an effect below that. **UNDERPOWERED is the honest answer, not a failed one, and it is
> still not a KILL.** Report the deflated and the raw statistic side by side, and let the forward
> wall certify.

Standing counts as of 2026-08-07: **screens 19 · sealed opens 1 · n_trials 2.**
State them in every research readout. (The authority is
`diagnostics/research/label_screen_ledger.md` — if this line disagrees with the ledger, the ledger
is right and this line is stale. Screens moved 12 → 13 → 14 on 2026-07-31 (0126 line-hugger, 0127
HEG-class bound), 14 → 15 on 2026-08-06 (0129 event-sizing bound), 15 → 16 on 2026-08-06
(0130 sizing-exclusion bound), 16 → 17 on 2026-08-06 (0132 daily Supertrend system) and
17 → 18 on 2026-08-06 (0133 finfluencer swing survey) and 18 → 19 on 2026-08-06 (0134 PIT
market-state fronts); `n_trials` has not moved.)

---

## I. The pre-entry wall — entry quality is not visible before entry

Five independent instruments have now been pointed at the same question — *can we tell, at the
moment of decision, which touch-entry becomes a winner?* — and all five returned nothing.

| # | Wall | Receipt | What it rules out |
|---|---|---|---|
| 1 | **Bar-level ML** | STAGE2_ml, 0111, 0112 | Trained selectors on bar-level statics; the per-trade lift does not survive the cash gate |
| 2 | **Loser forensics + Phase-1 entry levers** | `trade-forensic-lessons`, OWNER_CHART_REVIEW | Hand-built entry guards; 8 levers exhausted; G1/G2 showed filters cascade chaotically |
| 3 | **Path shape** (0116) | Train-clean `path_eff` −0.23R [−0.43,−0.02], 5/6 years → **sealed-set sign FLIP** to −0.269 | Pre-entry 21d path/grind/gap/compression features |
| 4 | **Formula chart structure** (prereg 0004) | 84f retrain; unseen-universe OOS delta **+0.10%/trade**, CIs overlap | S/R distance, breakout-of-structure, consolidation-range as ML features |
| 5 | **Perception** (0123) | 681 blind entry-truncated charts, grader validated FIRST (test-retest κ **0.867**, truncation-leakage clean); grades **flat**: winner 1.339 / noise-stop 1.313 / **false-touch 1.383**; per-year 2/6; all conditional CIs straddle zero | A vision model reading the chart the way a trader does |

**Law:** *On this 44-SMA touch funnel, entry quality is not visible before entry — not in the bars,
not in the path, not in the formulas, and not to perception.* The mechanism is that the funnel
enters names that have **already trended**: 0123's grader called 72% "extended" and said "wait" on
98%, because the eventual winner, the recoverable whipsaw and the unrecoverable false touch are
**visually identical at the decision point**.

**Corollary — "we encoded the concepts wrong" is RETIRED.** 0123's Phase-1.5 measured detector
integrity for the first time: the model and our committed formula detectors agree on setup presence
only 64.8% of the time and on setup *class* just **6.5%**, disagreeing outright on 240 of 681
charts. The pre-committed cross-check then ran the screen separately inside each cohort:
**agreement +0.042 [−0.045,+0.130] NULL; disagreement −0.032 [−0.166,+0.103] NULL — null in both.**
The formulas were not the limitation.

**On collision:** an idea that proposes to predict entry quality on this funnel is closed. Cite the
wall, and either narrow to a different question or take the one re-open condition below.

### The 0123 re-open condition (verbatim, the only opening in wall #5)

> A materially **different funnel** is the subject — one whose entries are *not* already-extended
> (e.g. the box/S-R breakout entries that fire pre-extension, or a slack-capital/longer-horizon
> book). The null established here is about **this touch funnel's decision points**, where the
> visual variance across outcomes is genuinely near-zero. Re-proposing model-graded charts on the
> same 44-SMA touch entries — with a different rubric, a different vision model, more charts, or
> grade-ensembling — is relitigation and is refused: the instrument was reliable, leakage-free, and
> flat, in both detector-agreement cohorts.

**In practice this names exactly two live territories** (both already on the Oct-1 agenda): the
**Path-B pre-extension swing sleeve** and the **breadth-50 book**. Nothing else.

---

## II. Population information is real; this book's decision margins cannot express it

The single most-repeated finding in the programme, hit from **9 different angles** — the 8th is the first to carry an **arithmetic mechanism** rather than a description, and the 9th is the first where the ranker that was supposed to rescue the population is **wrong-signed** rather than merely absent.

*(Count corrected 2026-08-06: this line read "five" against seven receipt rows — it had gone stale as rows were appended. It is now 9, matching the table below.)*

| Angle | Receipt |
|---|---|
| **IC ≠ portfolio Sharpe** | 0079/O-015: `prox_52wh` has *higher* IC than the base signal (0.068 vs 0.062) and still collapses Sharpe 0.67 → 0.48 as a ranker. 0082 repeated it for USD-beta as a rank tilt. |
| **Pool ≠ book** | 0112: a GBM with a real +0.215 per-trade pool lift **loses** as the fill-priority criterion (Sharpe 1.132 → 1.035) — reordering changes *which weeks consume capital*. |
| **Screen ≠ slot** | 0118 → 0119: delivery's +0.363R population gradient becomes **−1.29 R/yr** at the funding margin. |
| **Screen ≠ entry decision** | 0120 → 0121: a real −0.383R event cost becomes **−15.72 R/yr** as a deferral rule. |
| **Perception ≠ outcome** | 0123: a κ=0.867-reliable structural grade separates nothing. |
| **Cohort ≠ playbook** | 0127: a 0.43R-worse cohort's clairvoyant conditional-management gain is **0.0 R/yr in all 8 years** — the optimum does not move. |
| **Population ≠ funding margin** | 0129: the −0.383R event gap replicates exactly on the population and is **wrong-signed (+0.076) on the capped book**, where the rule fires 2.2×/yr instead of 50×/yr. |
| **Pool ≠ book — WITH THE MECHANISM** | **0131**: cup/box/dbl beat touch44 on the population with CIs excluding zero in **both** units, and pooled into the capped book they cost **−1.941pp of equity per trade** (CI [−3.598, −0.264]) while trade count runs 255→491. |
| **Ranker ≠ rescue — WRONG-SIGNED** | **0132**: on a new daily funnel with 39,102 signals chasing ~10 seats, the proposed RS fill ranker has **rank-IC −0.0227**; Q5-strong is the *worst* quintile (−0.009) and the top 5% worse still (−0.017). The capped book would underperform the null population it draws from. |

**Law:** *A real effect measured on a population does not survive to this book's decision points.*
The margins are narrow by construction (CRS-adjacent contenders), the book is cash-constrained, and
composition noise is ±10R/yr.

### The mechanism, named at last (0131, 2026-08-06)

For six sightings this law was a **description** — population effects vanish at the margin, cause
unstated. 0131 supplies an arithmetic cause for the pool-into-book case, and every link is measured:

> **stop width → notional → seat count → dilution**

| link | measurement |
|---|---|
| the candidate cohort has **wider stops** | median stop width: touch44 **7.00%** vs cup **17.29%**, box **19.33%**, double_bottom **24.87%** |
| so under `shares = equity × 2% ÷ stop` its positions are **cheaper** | median position: touch44 **28.58%** of equity vs **8–12%** for the three |
| so the same cash buys **more seats** | mean concurrent positions **5.64 → 12.15** (max 10 → 20) |
| and seat count is an already-measured **dilution** axis | `FINDING_more_slots` (**trial-priced**): 4–5 seats **1.21** → 7 **0.97** → 10 **0.81**, random null **0.74**. 12.15 seats is past its worst measured point. |

**Why this makes the case terminal rather than open:** both ways around link 2 were already closed.
Leaving the freed cash idle is Law III's bookend (0104/0108, and 0117's negative queue alternative);
sizing by notional instead of risk is **0130, at −10.83% of equity per year**.

**Not part of the mechanism, and recorded because it was the natural guess:** the funded cohort does
*not* show a walked-down CRS queue — `crs_dist` **rises** (+0.140 → +0.422), because `crs_dist` is
not comparable across detectors (breakouts sit further above their own RS line: touch44 median
+0.046 vs box +0.202). The dilution axis is **seats**, not queue depth.

**On collision with this mechanism specifically:** a proposal that widens the candidate pool inside
the concentrated book is answered by arithmetic, not by re-measurement — it does not depend on which
detectors are chosen. A different **book shape**, with its own sizing and its own seat count, is a
different question and is not closed by this.

**On collision:** any proposal of the form "X predicts Y, therefore rank/filter/size by X" must run
the **activation bound** (see [`skills/verdict-machine`](../verdict-machine/SKILL.md) Gate 3) before
a trial is even proposed. That gate is 3/3 and costs nothing.

---

## III. Worse-than-average is still positive-EV — subtractive rules pay for what they remove

0121's decisive arithmetic: trades entered into a known imminent event are **worse than their peers
by −0.38R and still make money (+0.51R mean)**. Removing them cost **−20.96 R/yr**.

**Law:** *Identifying a below-average cohort does not license removing it.* On a cash-constrained
book the removed trade's slot is not free — the counterfactual is the next-best fill, and the
substrate's same-week queue alternative was net negative (0117).

**Receipts for the general shape:** 0104/0108 subtractive filters, 0110 absolute floors, 0112 cash
gate, and the owner-guard cascade (G1 alone 0.47, G2 alone 0.42, **G1+G2 0.97** — filters that
partially *cancel*, the signature of chaotic reshuffling rather than signal).

**On collision:** a skip/veto/filter proposal must show its bookend cost — what the removed trades
actually earned — before its benefit. "These are bad trades" is not an argument; "removing these
nets positive after redeployment" is, and has never yet been true here.

---

## IV. Setups do not survive events — deferral is a de-facto skip

0121: after a results event, the engine re-signals the deferred name within 28 calendar days in
only 16 of 275 cases — a **94% lapse rate**.

**Law:** *On this funnel a "wait and re-enter" rule is not a delay, it is a deletion*, and it
therefore inherits Law III's bookend cost. The 16 genuine re-entries were excellent (+2.82R each)
but 3/year cannot carry a rule.

**On collision:** any timing/deferral/postponement proposal must measure the lapse rate first. If
the setup does not survive the wait, the proposal is a skip and must be argued as one.

---

## V. Post-entry is hindsight-only

0117, across three independent questions: noise_stop vs false_touch are **indistinguishable at stop
time** (every CI straddles zero; weekly-structure-intact 48% vs 47%); day-10 strength carries
**IC = −0.029** against the *subsequent* leg (the seductive +0.356 is pure mechanical head start);
and the clairvoyant rotation bound (~11R/yr) sits under the noise floor.

**Law:** *The price path carries no exploitable conditional information anywhere on this funnel
beyond the original signal and week-relative selection.* The book's R is earned by **holding
through noise the information cannot resolve** — which is why every "manage it smarter" lever dies.

**On collision:** proposals to cut/rotate/add/pyramid/tighten based on in-flight state are closed.
Exit *geometry* is separately closed unconditionally (0105 tighten, 0106 widen, 0109 disaster-floor
— all KILL, the 0094 stop is a robust optimum unmovable in either direction).

---

## VI. Micro-edges are uncertifiable here — the ±10R/yr noise floor

0109 proved it at machine precision: a change that is **strictly positive per-trade** (a floor no
winner ever pierced in 9 years) still *lost* at book level, because 17 exits reshuffled the cash
path (Mar-2020 freed cash re-entered the crash).

**Law:** *On a 4–5-name cash-constrained book, any edge below roughly ±10R/yr is swamped by
composition noise and cannot be certified in-sample.* Only structural changes (a second sleeve,
a different book shape) clear it.

**On collision:** state the expected effect size in R/yr *before* running. If it is under the floor,
the study is a measurement, not a trial — and should be designed as one.

---

## VII. Robustness is bought with return — nothing in-sample clears both

Six independent instances (0093, 0099, 0107, 0112, A-only variant, sleeves): every lever that
improves drawdown or year-consistency pays in CAGR. 0112 is the cleanest — the model book has
**zero losing years** and −8.8pp better MaxDD, at −3.8pp CAGR and −0.097 Sharpe.

**Law:** *This is owner risk-preference territory, not a bar-passing promotion.* Log such profiles
for the review; never promote them in-sample, never relitigate them toward a pass.

---

## VIII. Method laws (how any number must be produced)

| Law | Receipt / rule |
|---|---|
| **Continuous-slice sub-periods** | Never a fresh-capital re-run from the sub-window start — it resets the equity peak and manufactures a phantom gate (base 2022-26 Sharpe 0.762 phantom vs **0.570** correct), which produced a false KILL. Use `nq.runner.research.evaluate_overlay`. |
| **Matched controls, never one-sided lists** | Extension IS the engine (69% of book R; ext ≈ candle size r=+0.48). A loser-only list re-discovers ext every time. Condition on ext × CRS cells; sample matched within them. |
| **Reproduce-before-trust** | Every decision-informing number comes from a committed script, never a chat transcript. Artifacts (raw responses, rendered inputs, intermediate datasets) are committed. |
| **Validate the instrument before believing it** | If the measuring device is itself a model/grader/annotator: test-retest reliability and a leakage probe come first, and gate the study (0123: κ 0.867 + clean truncation probe, *then* the screen). An unvalidated null is unreadable. |
| **Specification uncertainty is a multiplicity axis** | 0133: an external rule stated ambiguously across sources ("cross above a pivot") admitted **four faithful readings**; holdout came out **+12.80 / −13.34 / −8.42 (the *sourced* one) / −8.65**, family mean −4.40%, and the readings disagreed in **sign** window by window. Testing ONE reading is a hidden multiple comparison. **The unit of evidence is the FAMILY of reasonable readings, not the reading you implemented.** A result that survives only one reading is a specification lottery ticket. Corollary (0132): research the published spec BEFORE testing — RS55-vs-RS14 and RSI-50-vs-60 were each worth more than any parameter in the study. |
| **Price the null in the same window** | 0133: a random-entry control returned **+9.12% CAGR / Sharpe 0.558** on 2019-23 and **−11.07%** on 2024-26. Three of nine surveyed strategies never beat it in-sample, and holdout results are only readable as a spread over it. Any strategy survey without a matched random control cannot distinguish skill from the window. |
| **Leaks inflate** | A result WORSE than base is not a leak. A too-good result is guilty until cleared (`skills/leakage-audit`). |
| **Trust 63d/≥2019 only** | Old v1 7–14d kills do not transfer to the long-horizon horizon. |
| **The 44-week line is a SMA, never an EMA** | Owner-mandated; live R94 conformant. |
| **Engine invariant** | Any overlay is cfg-gated so the golden master stays byte-identical when off; full suite green before push. |

---

## IX. What is CLOSED, at a glance

Do not re-propose as-is. Each has a finding; each requires the collision rule to reopen.

- **Entry gates / regime**: O-001, 0056, 0086, 0090, 0103 (switch not learnable OOS; static blend dominates), cash-gate 0112.
- **The technical/indicator zoo at 63d**: O-015/0079 — RSI/MACD/Stoch/Williams/CCI/Bollinger/MFI/OBV have IC≈0; 52-week-high/SMA-dist/ROC have IC and lose as rankers.
- **Reversal / RSI-oversold**: triple-killed (0020/0022/0024).
- **Daily Supertrend(10,3) + RS + RSI>60 system**: 0132 — entry flat at the cross (21d −0.00 ± 0.11),
  exit is an RSI rule in disguise (`RSI<60` on 99.9% of exit-days) that truncates at 8d against a
  10.6% stop, net meanR +0.006 ± 0.013, 3/8 years. Four explicit re-open conditions in §8 of the
  finding; re-tuning the 2-of-3 thresholds against that census is refused relitigation.
- **Selection axis**: 0110 (absolute floors), 0111/0112 (trained selector), 0116 (path shape), 0123 (perception).
- **Exit geometry**: 0105 / 0106 / 0109 — both stop directions and the zero-whipsaw floor.
- **Post-entry conditional**: 0117.
- **Macro**: crude was a lookahead artifact; USD-sensitivity is real but KILLED as a rank tilt (0082). Only a portfolio-level sleeve via ERC remains, and 0115 killed the low-USD-beta sleeve on correlation.
- **External data usage**: delivery (0119) and earnings (0121) banked, screen-real, decision-margin-negative. Campaign **paused**.
- **Sleeves under the cap**: STAGE4 — no sleeve config beats the touch-only book; DSR 0.000, WF 4/10.

---

## X. What is OPEN

- **The forward wall** — the only certifier. Decisions at quarterly reviews only; between them, log and leave it alone.
- **The breadth-50 watched pair (EW vs SW)** — the comparison IS the experiment; forward evidence by construction, zero in-sample fitting. Awaiting the Oct-1 amendment slot.
- **Path-B pre-extension swing sleeve** — registered proposal for the 2026-10-01 review; also the only funnel where the 0123 re-open condition permits chart-structure work.
- **The corrected-universe re-anchor** — owner/governance decision (survivor-only pin bias scales with holding period).
- **Operational value** — memo/risk-gate/barbell, scheduler hardening. Not backtest levers.

---

## Cross-references

- [`skills/verdict-machine`](../verdict-machine/SKILL.md) — how to run what survives these laws
- [`skills/research-log`](../research-log/SKILL.md) — where the record goes
- `research/overlay_registry.md` · `research/findings/` · `diagnostics/research/n_trials.json`
- `diagnostics/research/external_data_campaign_capstone.md` — the campaign synthesis
- `diagnostics/research/oct1_binder_decisions.md` — the live owner-door list
