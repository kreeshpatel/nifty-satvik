# Oct-1 binder — decision section (owner doors)

Companion to [system_constitution.md](system_constitution.md). Everything here is **written up, not
acted on**: each item is an owner decision, and every fix is a mid-quarter system change. Remediated
constitution rows are cited with their fix commits in the constitution itself.

Standing counts (unchanged by the audit and the remediation): **screens 12, sealed opens 1,
n_trials 138.** No trials or screens were spent; no forward-wall log was read.
(Screen count moved 11 → 12 on 2026-07-30 by finding 0123, which spent no trial.)

**Counts as of 2026-08-06: screens 15 · sealed opens 1 · n_trials 138.** The line above is the state
at the audit and is left as written; screens moved 12 → 13 → 14 on 2026-07-31 (0126 line-hugger
screen, 0127 HEG-class bound) and 14 → 15 on 2026-08-06 (0129 event-sizing bound). **`n_trials` has
not moved since 2026-06-12** — no trial has been spent by any of this work, no sealed set was
opened, and no forward-wall judge log was read. Authority for the count is
[`label_screen_ledger.md`](label_screen_ledger.md).

**Research input (2026-07-30) —** the pre-entry wall now holds **five** independent ways including
**perception**: [0123](../../research/findings/0123-vision-graded-chart-structure.md) graded 681
blind, entry-truncated charts with an instrument validated first (test-retest κ 0.867; truncation-
leakage clean) and found grades flat across false-touch / noise-stop / winner cohorts, null in **both**
the detector-agreement and detector-disagreement cohorts — so "our formulas encoded the concepts
wrong" is retired permanently. Its recorded re-open condition names **pre-extension funnels** — the
Path-B swing sleeve and the breadth-50 book already on this review's agenda — as the only territory
where chart structure remains untested (this funnel enters already-extended names: 72% graded
"extended", 98% "wait").

**Research input (2026-07-30) —** [`ml_readiness.md`](ml_readiness.md) writes the owner's
"pursue ML, judge it forward" instruction into dated lanes and re-frames two decisions already on
this agenda: the **breadth-50 amendment (§4)** is the only ML lane that can start in 2026 (EW-vs-SW
weight learning, zero in-sample fitting, first read ~2027-04-01), and the **Path-B promote/kill** is
the only door through which perception/chart-structure work can re-enter (per the 0123 re-open
condition). It also states the unflattering arithmetic: an entry-quality learner trained on
forward-wall data from the 15-slot book needs **7.5 / 11.2 / 18.6 years** for 200 / 300 / 500
observations at ~27 closed trades/yr — so declining both is coherent, but it closes the ML direction
for the foreseeable horizon.

---

## 0. Governance change already landed — gates must read SNAPSHOTS

Constitution **D2** (the record recomputes from inception every Saturday and can silently rewrite
its own past) is now **measured**: `scripts/archive_weekly_snapshot.py` runs in the Saturday cron
after the scorecard and writes a dated, **write-once** snapshot to `results/archive/<as_of>/` —
book, NAV series, closed-trade history, analytics, plus an input fingerprint (OHLCV cache sha256,
membership sha256, index-CSV sha256, engine config) — then diffs against the previous snapshot and
appends a row to `results/archive/drift_log.jsonl` recording **restated / vanished / appeared**
closed trades and the NAV delta.

**Frozen baseline artifact:** `results/archive/2026-07-24/` (flagged `is_baseline: true`) — the
state of the record at remediation time.

**The decision this forces (for the Oct-1 review):** the §10.2 promote/kill gates and the §4 halt
must be evaluated against a **named snapshot**, not the mutable working copy. Recommended wording
for the review: *"the gate reads `results/archive/<first-trading-day-of-October>/`; if that
snapshot's `drift_vs_prev.json` is not clean, the restatements must be attributed before the gate
is read."* `scripts/bhanushali_review_scorecard.py` still reads the working copy — pointing it at a
snapshot is a one-line change deliberately **not** made mid-quarter.

What this does **not** do: it does not make yfinance immutable. That was never the goal — the goal
is that drift is attributable rather than silent.

---

## 1. D1 — universe snapshot refresh policy *(couples to the re-anchor decision)*

**State.** Live trades `config.NIFTY_500`, a hard-coded snapshot dated **2025-07-20**, intersected
with `data/nifty500_membership.csv` (last written 2026-06-29, 500 rows active, sentinel
`to_date = 2030-12-31`). The certified 0094 run used the *corrected* universe (pinned + backfill +
delisted aliases). Post-snapshot index entrants can never signal live; index exits keep trading.

**Why it is loaded.** Finding 0025 measured survivorship bias scaling with holding period, and this
book has **no time cap** (item 2 below) — the maximum-exposure configuration. D1 and B-2's substance
compound.

**Freshly relevant:** the September semi-annual NSE rebalance lands **before** the Oct-1 review.
[M7](m7_universe_freshness.md) quantifies today's gap: a symmetric **48-name** difference in each
direction. The 48 currently-active names absent from the snapshot **can never produce a live
signal** (the snapshot is the scan universe; membership only masks it); the 48 stale snapshot names
are correctly blocked from entry but nothing forces an exit if a name leaves the index **while
held** — and M2 measures holds up to 201 weeks, spanning four rebalances. Sentinel handling was
verified sound (500 active rows on the `2030-12-31` marker, parsed correctly).

**Cost of deferring to the review.** Holding the refresh until Oct-1 leaves **48 of 710** cached
names (~6.8%) unable to produce a live signal for roughly **eight more weeks** — through the
September rebalance, which will widen the gap further before it is closed. The cost is bounded (a
missed-opportunity set, not a risk to open positions or to the record) and is **accepted pending the
coupled re-anchor decision**, since refreshing the universe mid-quarter would change the live
opportunity set without the re-anchor that should accompany it.

**Doors:** (a) refresh the snapshot + membership on a fixed cadence tied to NSE rebalances;
(b) switch the live universe to `build_universe("union")` so current members are included without
touching the historical file; (c) leave as-is and accept a widening gap. Couples to the pending
baseline re-anchor (CLAUDE.md data-debt note), so it is a quarterly-review-class decision either way.

## 2. B-2 substance — the missing time cap *(docstring half already fixed)*

**State.** Under config P the weekly branch decides stop / blow-off / 44w-SMA runner and returns
**before** any cap check: neither the 13-week cap nor the 52-week backstop the P2 exit carried is
reachable. Holds are unbounded above. The docstring that claimed otherwise was corrected in
`d3b4d5e`-series work; the **behaviour** is untouched, by design.

**Exposure.** Unbounded holds are the configuration where D1's stale-universe exposure bites
hardest (0025). [M2](m2_hold_age.md) now measures the realised distribution.

**⚠ Recommendation CHANGED by M2 — a cap would cut the only profitable cohort.** On the corrected
universe, live config P: median hold 18w, mean 27w, **max 201 weeks**, 13.8% of trades past a year.
Mean R rises **monotonically** with hold — 0–4w **−1.72R**, 5–13w **−0.75R**, 14–26w +0.87R,
27–52w +2.41R, 53–104w **+9.08R**, >104w **+18.71R** — and the longest decile earns **64.3% of the
book's total R**. The survivorship correction *raised* the tail's mean R rather than deflating it,
so the tail is not a survivorship artifact.

**Doors:** (a) ~~reinstate the 52-week backstop~~ — **withdrawn**: it would truncate the 18 trades
carrying the book's entire positive expectancy; (b) **adopt an explicit no-cap policy** and delete
the card's `HOLD_DAYS_DISPLAY` fiction (the docstring is already corrected). **Recommendation: (b).**
Note the caveat M2 states: the corrected universe fixes *survivorship*, not *membership staleness* —
a 201-week hold spans four semi-annual rebalances, so this decision and D1 should be taken together.

**The 0–4w negative cohort is NOT an open research target — it is a priced cost.** M2's short-hold
buckets (0–4w −1.72R, 5–13w −0.75R) are the false-touch / noise-stop population, and that population
has already been closed from every side:

* **Pre-entry** — the selection funnel and its four walls found no pre-entry discriminator
  (**0116**); the population is visible but not separable before the fact.
* **At the stop** — **0117** established that distinguishing a noise stop from a real one is
  **hindsight-only**: the information exists in the population but not at the decision moment.
* **Exit geometry** — hard stops (**0105**), stop widening (**0106**), and the surrounding geometry
  work (**0104**) each failed to convert the cohort; 0105 in particular whipsawed the shallow
  intra-week piercings that recover.

This is the standing law of the program: **population information is real; the decision margins
cannot express it; and worse-than-average is still positive-EV.** The short-hold losses are what it
costs to hold the tail that earns 64.3% of the book's R — the same trades, entered the same way, are
the entry to both distributions. Re-opening this as a research target would relitigate 0104/0105/
0106/0116/0117 without new data, a new feature, a new sub-period, or a new formulation. **The only
certifier left is the forward wall.**

## 3. D3 — the live config is not the certified config *(owner's recorded override)*

**State, restated for the review.** The 0094 run of record (Sharpe 1.132 / 255 trades, DSR 0.89 —
UNDERPOWERED, not certified) is **all-defaults**. Live runs `LIVE_DISCIPLINE` (ext_cap 0.20,
max_risk_pct 0.10, max_notional_pct 0.20; docs/decisions/0009) **and** config-P `LIVE_EXIT`
(docs/decisions/0010), which the code itself records as failing the 2022-26 continuous slice at
**0.91** with a **−39.5%** drawdown, adopted on owner call with sole capital at risk.

No action requested — this is your override and it stands. It is restated so the review does not
read 1.132/255 as this book's pedigree. The golden master now pins both configurations separately,
so the distinction is mechanically enforced rather than remembered.

## 3b. Scheduler layer — findings that touch Sep/Oct operations

Full audit in the constitution's **Appendix S** (2026-07-30). Three items bear on the quiet
post-review window and on the Oct-1 gate mechanics:

* **The forward-wall log has no scheduled producer (S-F1).** `run_paper_cron.py` (→
  `wall_cron.update_wall`) is invoked by no workflow, so the 3-book wall CLAUDE.md calls the "only
  certifier … logged daily" runs **never** via CI. Decide before Oct-1 whether the momentum-sleeve
  wall is intentionally dormant (sleeve suspended) or must be scheduled — if the Oct-1 review is
  meant to read wall evidence, the producer has to exist first.
* **D2 archive is dormant until this branch merges (S-F5).** The Saturday snapshot step is on the
  research branch, not on `main`; `origin/main`'s scanner has no archive step and `results/archive/`
  is absent there. The Oct-1 gates are supposed to read a *named snapshot* (binder §0), so **the
  archive must be on `main` and firing well before Oct-1** — otherwise the only snapshot is the
  manual baseline `2026-07-24`. Merge to activate.
* **60-day auto-disable coupling (S-F7).** The daily monitor's commits keep every scheduled workflow
  alive; a long no-commit stretch over Aug–Sep would start the 60-day auto-disable clock for all
  crons at once. Risk is nil while the monitor commits daily, and the new dead-man (S.5) now flags a
  stopped monitor — but do not deliberately pause the monitor over the quiet period.

The one human-facing freshness alarm (`cron_health`) is miscalibrated for the weekly cadence and
reads STALE mid-week on a healthy book (S-F2); recalibrating it and surfacing the new
`scheduler_health` block (S-F3) are backend serving-path changes for the review, not mid-quarter
plumbing edits.

## 4. Low-rank divergences — one line each

| ID | What | Recommended disposition |
|----|------|------------------------|
| **D6** | Two Grade-A top-5 sets: `grade_a_entries` ranks all signals; the card pipeline filters membership/degenerate bands **first**. At the margin the book reserves a slot it cannot fill while the card promotes a name the book will never hold. | **Fix next quarter** — apply the membership/`entry>stop` filter before ranking, so one A-set exists. Small, but it is the only remaining card-vs-book set mismatch now that D5 is closed. |
| **D7** | Fractional shares: sizing is a float, the owner buys integers. Backtest and paper share the fiction. | **Accept + document.** Flooring would change every historical fill for a bounded, direction-known error (it slightly flatters the record). Revisit only if real capital is deployed. |
| **D8** | A missed/failed Saturday is healed with modeled fills the owner never saw. | **Fix cheaply** — have the archive mark a snapshot whose predecessor is >8 days old as `backfilled`, so gates can exclude weeks the owner could not have traded. Archive infrastructure now exists; wiring is one condition. |
| **D9** | Monitor flags fills on an inclusive band (`lo <= open <= hi`); the engine fills strictly (`lo < open < hi`). | **Fix next quarter** — make the monitor strict. One character; currently a boundary-tick card/book split. |
| **B-3** | The non-member-in-top-5 case inside `grade_a_entries` — the mechanism behind D6. | Resolved by the D6 fix; no separate action. |
| **B-4** | Monitor's `window_open` compares against the **data** as-of date, not today, so a stale feed shows an expired buy window as open. | **Fix next quarter** — compare against today; bounded today by the daily refresh. |

## 5. Menu items surfaced by this remediation (not run)

* **M1 — done.** R94 golden master exists (`tests/test_r94_golden.py`), pinning the frozen 0094 cell,
  the live cell, the B-1 fix diff, and the card arithmetic.
* **M2 / M6 / M7 — done**, reports committed ([M2](m2_hold_age.md), [M6](m6_demerger_scan.md),
  [M7](m7_universe_freshness.md)). M2 changed a recommendation (item 2); M6 and M7 found no live
  breakage but both surface standing exposures.
* **M5** (post-tp1 giveback: the stop never moves under config P) is now the **highest-value**
  diagnostic left — M2 shows the loss is concentrated in short holds, and M5 measures the giveback
  mechanism directly. **M11** (mark-to-market compounding of the 2% risk base) is second. Both are
  column arithmetic on the existing ledger; neither spends a trial.
* **M6 follow-on:** add the demerger scan as a standing read-only cron step so a suspect entering
  the book is flagged while the quarantine decision stays open (seconds, zero risk).
* **M9 / M13 / M14** unchanged from the constitution's ranking.
* **M10** — `NSE_HOLIDAYS` ends 2026-12-25, so the 2027 Jan/Apr review dates cannot be computed
  correctly. **Add the 2027 list at the Oct-1 review** (zero-compute, but it blocks the review-date
  machinery next year).

---

## 6. R IS NOT A COMPARABLE UNIT IN THE LIVE BOOK — a D3 sharpening *(new door, 2026-08-06)*

Source: [`r_denominator_audit.md`](r_denominator_audit.md) — **verification class, free, no ledger
row, no trial, no rule proposed** (`python scripts/diag_r_denominator_audit.py`). Counts unchanged at
**15 / 1 / 138**. This does **not** claim a new divergence: constitution **H1/H3** already record the
notional cap as *"Off in run of record"*, and **D3** already records that live ≠ certified. What is
new is the **unit consequence**, and it is decision-relevant.

**The finding.** Stop width on this book spans **p10 3.59% → p90 25.25% (7.0×)**, and **41.6% of
trades carry a stop narrower than 1× weekly ATR**. That is fine in the run of record, which sizes
`eq × 2% / (entry − stop)` — there **1R = 2% of equity for every trade and R is exactly comparable**.
It is not fine live: `LIVE_DISCIPLINE`'s `max_notional_pct = 0.20` binds whenever the stop is
narrower than **10%**, which is **53.4% of trades**. Under the live cap the rupees behind 1R fall to
a median **0.918× nominal, p10 0.359×, p1 0.163×**. Re-weighting the same trades by what each R is
actually worth live turns a **1907.3R** book into **1581.9R — a 0.829 translation ratio**.

**Why it matters, and it is not academic.** Extension and stop width are coupled at **r = +0.67**
(the stop is the candle low, so a name nearer its line has a narrower stop). So the cap binds
hardest on precisely the cohort the research calls the core edge:

| | ext < 5% (the `ext_band_census` +0.717R core) | ext ≥ 5% |
|---|---|---|
| median stop width | **5.97%** | 9.90% |
| mean R **as reported** | **+0.803** | +0.469 |
| mean R at a **common denominator** | +0.549 | **+0.825** ← ordering reverses |
| **live rupee weight** | **0.621** | 0.788 |
| **live rupee-weighted mean R** | **+0.466** | +0.409 |

**The low-extension edge is real and it survives — but the live book collects only about a sixth of
it.** The as-reported gap is **+0.334R**; live-weighted it is **+0.057R**, an ~83% erosion, entirely
because the notional cap under-sizes narrow-stop trades. Three yardsticks exist and which is correct
depends purely on sizing regime: fixed-risk (run of record) → R as reported is the rupee truth;
fixed-notional → the common-denominator column is, and the ordering flips; **the live book is
`min(...)` of the two and sits between them.**

**The decision this forces.** Nothing here proposes a rule and this session proposes none. The door
is: *does the live book's anti-concentration guardrail (`max_notional_pct` 0.20, adopted 2026-07-16
against single-name concentration) knowingly cost most of the measured low-extension edge, and is
that the trade you want?* Both readings are defensible — the cap is a real risk control and
concentration is load-bearing (`FINDING_more_slots`) — but the cost was not previously quantified.
Quantified, it is large.

**Also flagged for the review, same cause, no action proposed:**
- **A −1R is not a homogeneous event.** Of stop-outs on sub-ATR stops, **37.1%** closed back above
  entry within 4 weeks, vs **10.6%** on ≥1×-ATR stops (**+26.5pp**; part definitional — a narrow stop
  needs a smaller reversal to recover). Pooling both as "−1R" mixes two different events.
- **R-denominated conventions inherit the heterogeneity**: the disaster class (`R ≤ −1.5`, 0109) is
  a −4.5% price move on a 3% stop and a −45% move on a 30% stop; and **the ±10R/yr noise floor
  itself is a blended unit**. Neither is wrong — both are load-bearing and should be read knowing it.

---

## 7. DECISION INPUT — any ext-band sizing expression must be judged in RUPEE-WEIGHTED terms

**This is a standing rule for how a future proposal is evaluated, not a proposal.** It is recorded
now so that the next ext-band idea is not scored on the wrong yardstick by default.

0126 closed with the `<5%` extension band carried forward intact as *"one undifferentiated cohort
for the unshipped sizing question."* §6 measures what that cohort's R actually is, and the answer
changes how any such expression must be read.

**The measurement.** Extension and stop width correlate at **r = +0.67** — mechanically, since the
stop is the candle low, a name nearer its line has a narrower stop. So the `<5%` band **is** the
narrow-stop band (median stop **5.97%** vs **9.90%**), and its R is computed on a systematically
smaller denominator:

| yardstick | ext < 5% | ext ≥ 5% | gap |
|---|---|---|---|
| **R as reported** (fixed-RISK sizing = the run of record) | +0.803 | +0.469 | **+0.334** |
| at a **common denominator** (fixed-NOTIONAL sizing) | +0.549 | +0.825 | **−0.276 — reverses** |
| **live rupee-weighted** (`min(risk, 20% notional)` = what actually trades) | +0.466 | +0.409 | **+0.057** |

**Two distinct effects, and they must not be merged into one number.**
1. **A denominator effect.** Under a fixed-*notional* yardstick the ordering **reverses** — high-ext
   trades produce the larger price outcomes; low-ext trades produce the larger *ratios*. The
   R-measured edge is a ratio effect, not a bigger-move effect.
2. **A cap effect.** The live notional cap under-sizes narrow stops, so the live book puts **0.621×**
   nominal capital behind the `<5%` cohort vs **0.788×** behind the rest — and the gap erodes from
   **+0.334R to +0.057R, an ~83% erosion.**

**The edge is real and it survives in live-rupee terms** (+0.466 vs +0.409 still favours `<5%`). What
it does not survive is being *quoted in R* as though R were rupees. The one-line reading: **the
research measures the edge at roughly six times the size the live book can actually collect.**

**The rule this fixes for the review.** Any future proposal to size, tilt, or concentrate on the
extension band — the unshipped 0126 sizing question included — is judged on the **live
rupee-weighted** column, because that is the capital that moves. An ext-band proposal scored in R
will look ~6× better than it can be. Corollary: **the largest available ext-band lever is not a new
overlay at all — it is `max_notional_pct`**, which is already binding on this cohort today (see §8
and the door in §6). That is a config decision, not a research question, and it costs no trial.

**No rule is proposed here and none should be inferred.** The `<5%` band remains exactly what 0126
left it: one undifferentiated cohort, unshipped.

### 7.1 The cap curve — concentration vs collection *(added 2026-08-06)*

Source: [`notional_cap_curve.md`](notional_cap_curve.md) —
`python scripts/diag_notional_cap_curve.py`. **Verification class: population arithmetic on the
existing substrate, no book re-run, counts frozen at 15 · 1 · 138. No arm is recommended.**

**Limitation, first, because it binds: this cannot show which trades a different cap would fund.**
Position size feeds the cash path and the cash path decides which later signals are affordable; that
is inseparable from a book re-run. Every row holds the funded set fixed at the substrate's. The
curve prices the cap's effect on **capital deployment across the trades we took**, never on **trade
selection**. Second approximation: R is held at the uncapped book's realized R, and `max_risk_pct`
is modelled on the sizing side only.

**There is deliberately no Sharpe / MaxDD / worst-year column.** That half is trial-class (5 arms on
the honest base) and was declined. Independently, **0113 measured what such a column would be
worth: PBO 46.2%**, with the in-sample-best config on this exact cfg-lever family landing at the
**OOS median** (1.239 → 0.843 vs 0.835). Within this family a per-cap return ranking carries ~zero
OOS decision weight while permanently deflating every future DSR bar.

| cap | risk-sizing under-sizes | **weight ext<5%** | weight ext≥5% | book weight | **realized-R recovery** | positions sized *by* the cap | max exposure |
|---|---|---|---|---|---|---|---|
| **0.15** | 100.0% of trades | **0.466** | 0.591 | 0.580 | **0.622** | 100.0% | 15% |
| **0.20** *(live)* | 53.4% | **0.621** | 0.788 | 0.773 | **0.829** | 100.0% | 20% |
| **0.25** | 43.3% | **0.713** | 0.851 | 0.838 | **0.884** | 43.3% | 25% |
| **0.30** | 34.0% | **0.780** | 0.894 | 0.884 | **0.922** | 34.0% | 30% |
| **unbounded** | 0.0% | **1.000** | 1.000 | 1.000 | **1.000** | 0.0% | **2299%** |

*(`max exposure` is the cap itself by construction for any bounded cap ≤ 0.30 — the informative
concentration column is the one beside it. The curve reproduces §7's 0.621 and §8's 0.829 at the
live cap, which is the arithmetic self-check.)*

**The structural finding, which was not previously stated anywhere.** The notional cap is **not a
rare guardrail on this book — it is the position sizer.** With the live `max_risk_pct = 0.10` in
force every stop is at most 10% wide, so risk-sizing always wants at least `2% / 10% = 20%` of
equity per name. **Any cap at or below 0.20 therefore sets the size of 100% of positions, and the
2%-risk rule never binds at all.** Two true statements are easy to conflate at the live setting: the
cap sets **notional** for 100% of trades, while equity **risked** falls below the nominal 2% for the
53.4% whose stop is narrower than 10%.

**The tradeoff, stated without a recommendation.** Collection and concentration move together and
there is no interior optimum in these columns by construction — the curve is monotone in both. So
the Oct-1 call is a pure risk-preference placement:

- **Loosening 0.20 → 0.30** raises the `<5%` cohort's capital from **0.621 → 0.780** of nominal and
  the book's R-to-rupee recovery from **0.829 → 0.922**, and buys that by allowing a **30%**
  single-name position instead of 20%.
- **Tightening 0.20 → 0.15** cuts the `<5%` cohort to **0.466** and recovery to **0.622** — i.e. the
  book would collect under two-thirds of its own realized R — for a 15% single-name ceiling.
- **Unbounded is not a real option and is shown only to price the guardrail's purpose:** implied
  single-name notional reaches **2299% of equity**, with 34% of trades implying >30% and 12.9%
  implying >50%. Cash would bind first (constitution H5), but that is an accident of affordability,
  not a risk control — which is exactly the runaway the 2026-07-16 decision was adopted against.

**What is NOT established here:** whether any of these caps produces a better book. That question is
the trial-class half, it is declined, and 0113 says the answer would not be readable anyway.

## 8. DECISION INPUT — the 0.829 research→live translation factor, and what the ±10R floor is made of

**Two caveats on units. Neither moves any verdict on the record; both change how the next number
should be read.**

### 8.1 The translation factor

Re-weighting the substrate by the rupees the live cap actually puts behind each R turns a **1907.3R**
book into **1581.9R** — a **0.829** research→live translation factor. It is a **property of the trade
mix, not a constant**: it is the average of a per-trade weight that runs from **1.000** (stops ≥10%,
uncapped) down to **0.163** at p1, so a cohort of narrow-stop trades translates far worse than 0.829
and a cohort of wide-stop trades not at all. **Do not apply 0.829 as a blanket multiplier** — it is
the book-level average of a quantity that must be recomputed per cohort. §7 is the worked case: the
`<5%` band's own factor is 0.621, not 0.829.

### 8.2 The ±10R/yr floor is a blended unit

The floor (0109 / 0117) is denominated in the same heterogeneous R as everything else, so "10 R/yr"
is 10 units of a quantity whose rupee value varies ~6× across the book. This is a **statement about
precision, not a reason to move the floor** — the floor was derived empirically from composition
noise on this book, in these units, so it is internally consistent with every bound measured against
it. It is recorded so the number is not later mistaken for a rupee quantity.

**A trap to avoid, stated explicitly.** Deflating a *bound* by 0.829 while leaving the *floor* at 10
is not a valid comparison — both are in the same R units, so a uniform rescaling cancels and the
bound/floor ratio is unchanged. The heterogeneity only bites where the rescaling is **non-uniform**,
i.e. where a proposal's activated cohort has a materially different stop-width mix from the book
average. That is the only situation in which any of this can change a verdict.

### 8.3 No prior bound verdict moves — and here is the actual reason

The clean argument is not "every bound failed by ≥10×" — **that is not true of the record**: 0117's
rotation bound was ≈**11 R/yr** (*above* the floor, closed as sitting at/under it) and 0127's
exclusion bound was **1.92 R/yr** (5.2× short, not 10×). The correct argument is directional:

- **The factor is < 1 everywhere**, so it can only ever **shrink** a bound. Every bound on the record
  **failed**, and all but one failed for being **too small or wrong-signed** — shrinking a bound that
  is already too small cannot rescue it. Direction of travel is safe for: 0119 (−1.29, wrong-signed),
  0121 (−15.72, wrong-signed), 0127(a) (1.92), 0127(b) (0.0 by identity), 0129 (all arms, max +0.78
  clairvoyant).
- **The one leg whose magnitude cleared the floor was rejected on other grounds and still is.**
  0127's clairvoyant refuse-only-losers leg was 26.22 R/yr (→ ≈21.7 live-weighted, still clearing);
  it failed because its sign test is a **tautology** and it is **unreachable** (perfect loser
  foresight is the five-wall pre-entry problem). Unit heterogeneity touches neither objection.
- **0117 is the only bound close enough to the floor for units to matter** (≈11 vs 10). Its cohort is
  the capped book's *losers*, and nothing in the audit suggests that cohort's stop-width mix departs
  from the book average in the direction that would rescue it — and it was closed as a clairvoyant
  ceiling on an unreachable rule regardless. **No re-adjudication is requested and none is implied.**

**Net: no verdict on the record changes. The caveats apply prospectively**, to the next bound whose
activated cohort is stop-width-atypical — which is exactly the case §7 governs.

---

## 9. DECISION INPUTS — where a metric's DEFINITION changes what a gate means *(new, 2026-08-06)*

Source: [`DEFINITIONS_REGISTER.md`](DEFINITIONS_REGISTER.md) — **verification class, zero trials,
zero screens, counts frozen at 15 · 1 · 138.** Nothing was re-run and **no verdict was
re-adjudicated.** The register carries 18 rows; most are clean or were label problems fixed at
source. **Four reach this door**, each stated with **both readings**, unweighed.

**None of these is an error.** In every case the code does exactly what it says; the question is
which reading the Oct-1 gate should be evaluated under.

### 9.1 `KILL_SHARPE = 0.0` — kill below *cash*, or below the *risk-free rate*?

Every Sharpe in this programme is a **raw-return** Sharpe: `mean/std × √252`, **no risk-free
subtraction** (`nq/validation/metrics.py:19`). That cancels in ΔSharpe comparisons — which is how
essentially every verdict on the record was decided — so **nothing on the record moves.** It does
**not** cancel in the one *absolute* gate:

| reading | what §10.2's kill leg means | threshold |
|---|---|---|
| **as coded (rf = 0)** | kill if the book underperforms **cash at 0%** | Sharpe < 0.00 |
| **excess-return** | kill if the book underperforms the **risk-free rate** (~6–7%) | Sharpe ≈ < 0.25–0.30 |

**The decision:** which one §10.2 intends. The as-coded reading is the more forgiving of the two.

### 9.2 CAGR — two committed year-denominators

The same curve (Sharpe 1.132 / MaxDD −42.4) is published as **24.7%** and **25.21%**, because
`run_bhanushali_sixstep.py:220` divides by **calendar** years and `run_corrected_anchor.py:52` by
**trading-bar** years. Neither is wrong; bar-years are the shorter denominator and print higher.

**The decision:** nominate **one** convention as the publication standard for the review, so a
number quoted in the binder is unambiguous. **The live exposure is cross-document comparison** —
specifically any **book-vs-benchmark CAGR gap**, which is only valid if both sides use the same
denominator. (Finding 0114 is *not* an instance: it compares monthly book returns to monthly ETF
NAVs on one convention and says so.)

### 9.3 MaxDD — the grid is load-bearing for a *risk control*

The formula is uniform; the **grid** is not. The same book family is published at **−42.4% (daily)**
and **−33% (monthly granularity, finding 0114, which labels it)**. A coarser grid can only
**understate** a drawdown — it cannot see troughs between samples.

The **§4 mechanical −50% halt** reads this quantity. It currently evaluates on a **daily** grid,
which is the conservative and correct choice — but nothing in the pre-registration *states* that the
grid is part of the rule.

**The decision:** write the grid into the halt rule explicitly, so a future series change cannot
silently loosen a live risk control. **Also note:** a Calmar quoted from a monthly DD and a bar-year
CAGR is not comparable to one from a daily DD and calendar-year CAGR — it compounds 9.2 and 9.3.

### 9.4 The promote gate currently rests on 4 closed trades

`PROMOTE_EXPECTANCY_R = 0.10` and `win_rate` are computed over **closed trades only**
(`run_bhanushali_cron.py:468-474`); open positions are excluded. On a trend book **losers stop out
fast while winners stay open for months**, so both read **biased low by construction** in a young
book and rise as winners mature.

Current state: **4 closed, 5 open** (the `total_trades: 4` / `n_positions: 5` pair is consistent —
9 positions taken since inception; the key is merely misnamed, and the gate reads the correctly
named `total_closed`).

| reading | what the gate measures today |
|---|---|
| **as coded (closed-only)** | expectancy over 4 observations |
| **mark-to-market (incl. opens)** | unmeasured — computing it is out of this audit's scope |

**The decision:** this is an argument for the **≥30 closed** precondition being load-bearing rather
than advisory — i.e. do not read expectancy or win rate as informative before it is met. **No
re-computation was attempted and none is proposed.**

---

## VRP / option-selling — REJECTED without a screen (memo line, 2026-07-31)

Recorded so the idea does not recur as a fresh proposal. Short-volatility premium harvesting is **not
pursued and gets no screen**, on **risk-shape grounds, not on expected return**: selling vol
concentrates exactly the tail the equity book already carries — both are short the same crash. A
sleeve whose worst quarter coincides with the base book's worst quarter fails 0115's diversification
requirement **by construction**, before any Sharpe is computed. Consistent with 0100/0101/0102, which
found every timed-protection construction negative-EV and concluded this book's drawdown needs a
**sleeve-level** lever rather than an index-options one.

**Re-proposing requires:** a defined-risk structure (spreads, not naked) **and** an explicit
demonstration that its tail is not the book's tail. Absent both, this is a standing rejection.

---

## Demerger adjustment convention — either is defensible, both is not (2026-08-06)

**Source:** `diagnostics/research/foundation_audit_2026Q3/FOUNDATION_AUDIT.md` layer 2.
**Verification class; counts unchanged (15 / 1 / 138). Nothing measured here is a proposal.**

### The finding

Of the 37 demergers in the pinned universe 2019-01-01 → 2026-07-01, the vendor **back-adjusted 22**
and **left 15 as cliffs**. Both are legitimate conventions:

- **Back-adjust** (total-return): the spun-off shares were value the holder received, so the
  history is rebased to keep the series continuous. RELIANCE ×1.083 (Jio Financial), SIEMENS ×1.704,
  EDELWEISS ×1.850, NMDC ×1.301, ITC ×1.039, and 17 others.
- **Leave the cliff** (listed-entity): the listed company genuinely shrank, and smoothing invents
  trend it never had. VEDL −64.9%, ABFRL −66.6%, RAYMOND −64.8%, SKFINDIA −54.8%, and 11 others.

**This repo has already chosen — in writing.** `data/corporate_actions_demergers.csv` states the
listed-entity convention and gives the reason: back-adjusting a demerger *"FABRICATES a soaring
trend slope (e.g. VEDL: raw sma200_slope_63 2.16 → 24.94)"*. That file names **4** of the 37 events.

The problem is not which convention is right. It is that **the data applies both**, so any statistic
pooling across the two groups is comparing series built on different definitions of price.

**The single clearest demonstration: `AARTIIND` appears in BOTH groups.** It has two demergers in the
window; one is back-adjusted and one is left as a cliff. One name, one series, two conventions.

### The cross-group statistics this currently contaminates — named

Convention-mixed names are **243 of 4,321 substrate trades (5.6%), carrying 7.5% of total R**. Their
distribution is not uniform across the cells that carry published claims:

| Published cell | As published | Convention-mixed trades inside it | Their mean R |
|---|---|---|---|
| **`<5%` extension deep core** | **+0.717 R, N=418** | **30 (7.2%)** | **+1.292** |
| **sub-line `<0%`** | **+2.088 R, N=39** | **4 (10.3%)** | **+3.012** |
| whole substrate | +1,907.32 R, N=4,321 | 243 (5.6%) | — |

In both cells the mixed names sit **well above the cell mean** — +1.292 against +0.717, and +3.012
against +2.088 — so they are over-represented in exactly the cells the research calls the core edge.
This is a statement about *composition*, not a claim that the cells are wrong: no re-computation was
attempted, and none is proposed.

Also pooled without distinction: back-adjusted names average **+0.667 R** across 132 trades against
cliff names' **+0.749 R** across 89. Every aggregate that sums or ranks across both — the band
census, CRS cross-sectional ranking, the 44-week SMA and slope features on those names, per-origin
expectancy, and the alpha decomposition's sleeve panels — treats those two populations as one.

### What reaches the door

1. **Nominate one convention** for the data layer, and state it. Either is defensible on its own
   terms; the committed reference already asserts the listed-entity one, so the cheapest coherent
   answer is to make that real rather than to switch.
2. **The committed reference covers 4 of 37 events.** Whichever convention is chosen, the reference
   must enumerate the events it governs, or the choice is unenforceable.
3. **This pairs with the two other data-layer questions** now open: the vintage-seam repair
   (`LIVE_REPAIR_DECISION.md`) and the 0025 survivorship re-anchor. All three change historical bars
   and therefore share one re-anchor; deciding them separately would mean re-anchoring the pin more
   than once.

**Neither reading is weighed here, and no verdict on the record moves.** The 22/15 split is reported
so October decides a convention, not so a number changes today.
