# Ideas: an LLM-based model, the calculation model, and the data flow (2026-10-20)

**Class:** idea memo (process tier EXPLORE). No trial, no screen. Standing counts: **screens 23 · sealed
opens 3 · n_trials 2.** Built with `program-laws`, `repo-map` and `methodology-synthesis`, and against the
week's own evidence (0148 corrected, 0149, 0150, the four PIT re-runs, the engine assumption audit, the
repo scan). Owner stance applies: our findings can be wrong, so a prior verdict is a prior, and each idea
below ends in the cheapest test that would change our mind.

The end goal it serves: more money with less drawdown on the live configuration, surviving forward data.

---

## A. Should the model become LLM-based?

**Short answer: not as the decision-maker; yes as a reader of text the rules cannot see.**

What the programme has measured, and how strong each measurement is:

| question | evidence | strength |
|---|---|---|
| Can a model *see* winners at entry on this funnel? | 0123: 681 blind charts, grader reliable (κ 0.867), grades flat | strong (live funnel; re-open only on a different funnel) |
| Can a backtest of an LLM trader be trusted? | 0125 §1 and the literature it cites (memorisation; date-masking fails) | strong as a method law, not a trading verdict |
| Does an informed LLM judge add anything forward? | 0125, forward-only, sealed until ≥ 2 quarters and ≥ 100 verdicts | **open, accruing** (168 rows as of 2026-10-17) |

Why "LLM as the model" fails here specifically: an LLM's training data contains the outcomes of every
historical week, so no backtest of it is evidence; it cannot be replayed bit-for-bit, which breaks the
golden-master and parity guards; and the funnel's decision points are, per 0123, visually identical across
outcomes. A forward-only LLM book could still be run as a **shadow** with its own pre-registration, judged
only on data it could not have seen. Expected value: low, cost: a seat in the shadow wall.

Where an LLM is genuinely the right tool, in descending value:

1. **Corporate-action and announcement extractor (forward, daily).** Reads NSE announcements and flags
   demergers, splits, bonuses and schemes before their ex-date. HEG (−6.55R booked on a demerger) and the
   TATAMOTORS/PEL/LTIM renames were all text events the price-only engine discovered late. This is a data
   feed, not a signal, so Law I does not bind. *Cheapest test:* run it in shadow for a month and count
   events it catches before the price cliff. Already in the Brain plan (Layer 0).
2. **Idea intake and confrontation (Brain Layer 1).** The weekly research scout (scheduled 2026-10-20) is
   the first instance. A small fine-tuned extractor (2026-10-20 email) fits here later.
3. **Forward judge (0125).** Running. Nothing to change until the seal lifts.
4. **Narration only.** The post-mortem's numbers stay computed; an LLM may phrase them, never produce them.

---

## B. The calculation model: where the next real money is

Ranked by expected value for the live book, using this week's measurements on the live configuration.

| # | idea | evidence | cheapest next step | tier |
|---|---|---|---|---|
| 1 | **Rank only buyable names (D6).** The live Grade-A set wastes ~27% of top-5 seats on non-members and degenerate bands. | 0150 + red-team: Sharpe 1.025 → **1.275** (train) | pre-register the trial for the 2027-01-01 review | CONFIRM |
| 2 | **Book-level drawdown in falling markets.** Corrected 0142: outside COVID the book's beta in drawdowns is **1.03** and holdings bunch (corr 0.21 vs 0.15 calm). The book *is* the index when it falls. | 0142 corrected 2026-10-19 | measure a Nifty-hedge overlay (index futures or puts, sized to drawdown beta) as an activation bound; 0095's vol-target KILL is weak evidence (frozen book, old harness) and is a different mechanism | SCREEN |
| 3 | **Sizing is really 5 equal seats.** The 20% notional cap binds on every fill; risk per trade ≈ 0.75%, not the nominal 2%. | engine audit fact 1 | the running batch grids notional × max-risk | EXPLORE (running) |
| 4 | **A second funnel, not another filter.** Law I's only open territories: the pre-extension Path-B sleeve and breadth-50. Law II says population edges die inside this book; a separate sleeve with its own seats is the structural answer. | program-laws I/II, 0149 (barbell is a risk dial on one book) | coverage audit + activation bound of a pre-extension (box/S-R breakout) sleeve with its own capital | SCREEN |
| 5 | **Correlation-cluster de-duplication of the top-5.** Registry lists it OPEN. Interacts with #2: if holdings bunch in drawdowns, de-dup bites exactly then. | repo scan C1, 0142 corrected | count weeks with ≥ 2 clustered names in the top-5 (126d returns), train window | EXPLORE |
| 6 | **Cost model completeness.** No stamp duty, no DP charge, no gap slippage; STT side-convention to re-verify (methodology-synthesis §3.1). | engine audit #7 | the running batch re-costs a ledger | MEASURE (running) |
| 7 | **The certified anchor is not the live book.** The 1.132 / DSR 0.894 run of record differs from live on grades, caps, exit and handling. Every plausibility check compares against the wrong book. | engine audit fact 2 | re-derive a live-config anchor on the train window via the Strategy Lab (LIVE BOOK manifest) | MEASURE |

Deliberately low: more exit geometry (0105/0106/0109/0148 corrected), entry-quality prediction on this
funnel (Law I, five instruments), conviction re-weighting inside the book (Law II, mechanism 0131).

---

## C. Data linking and flow

The week's defects were almost all plumbing, not signal math: an ungated research path (`mem=None`), a
universe change and a vendor truncation rewriting past weeks, a stale universe snapshot, a cleaner that
never runs, and maps that point at deleted files. In order of what they prevent:

1. **One data layer with vintages.** Today research reads `corrected_universe()` (pinned pickle plus
   backfill plus aliases) and live reads a monthly-rebuilt cache plus a union download. Store each Saturday's
   input panel as a dated, hashed vintage, and let research replay any vintage exactly. Then "what did the
   live engine see on 2026-09-14" is a lookup, not a reconstruction, and parity is structural.
2. **Append-only history, rebuild as a check.** The tripwire (#146) now alarms on undeclared rewrites. The
   next step is storing each week's book state once and treating the from-inception rebuild only as a
   verification, so HEG- and ABDL-type rewrites cannot reach the record at all.
3. **Wire the data cleaner into the swing path, off by default.** `nq/data/ohlcv.py`'s cleaner (holiday
   phantoms, zero-volume, splits, bad ticks) is never called on the swing path. Measure its diff on the train
   window before anyone turns it on.
4. **Corporate-action golden source.** Register CA events from NSE circulars (with the LLM extractor of A1
   as the feed) instead of inferring them from price moves; methodology-synthesis #15/#23 is the spec.
5. **Required membership and a manifest everywhere.** The manifest (#146) labels non-live runs; make
   `mem` a required keyword in research entrypoints so `None` must be typed deliberately.
6. **Refresh the maps.** `skills/repo-map` still describes the retired long-horizon book: it cites
   `engine/exit_logic.py`, `src/runners/long_horizon_cron.py` and `FILE_MAP.md`, none of which exist, and
   never names `scripts/run_bhanushali_weekly_rank.py` or `scripts/run_bhanushali_cron.py`. A stale map is
   how the next `mem=None` happens. `methodology-synthesis` is likewise keyed to the old book's baseline.

---

## What happens next without being asked (owner directive 2026-10-20)

- Already running: the engine-assumption batch (B3, B6), the weekly research scout.
- Next EXPLORE steps, started without waiting: B5 cluster count; B7 live-config anchor in the Strategy Lab;
  C6 repo-map refresh.
- Waits for the owner: B1 pre-registration (a trial), B2 and B4 screens, C1–C3 engine/data changes.
