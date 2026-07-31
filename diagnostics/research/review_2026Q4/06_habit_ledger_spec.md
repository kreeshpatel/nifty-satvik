# §6 The habit ledger — forward memory layer (DESIGN SPEC ONLY)

**Status: SPEC — awaiting owner approval. Nothing is built. No config change, no engine change,**
**no `n_trials` increment, no screen row, no forward-wall read.**
Standing counts: **screens 12 · sealed opens 1 · n_trials 138.**
Date: 2026-07-31. Binder input for the **2026-10-01** review.

---

## 0. What this is, and the one thing that makes it worth building

Five years of research have repeatedly discovered, *after the fact*, that a question could not be
answered because the field that would have answered it was never written down. The Stage-1 substrate
(`research/substrate/trades.parquet`) had to be *reconstructed* from the engine in 2026-07 to ask
questions from 2026-06; the 0116/0117 label set had to be built from scratch; the 0123 chart sample
had to be rendered from raw bars; the ext-band census that opened this session had to re-derive
ext-at-fill from a ledger that never carried it.

**The habit ledger's entire value proposition is that it starts existing the day it ships.** It is
not a research artifact to be built when a question arrives. It is a forward substrate that the live
cron writes as a side effect of trading, so that the union of everything five years of research
proved worth recording is already on disk when the next question is asked.

**The unflattering half, stated up front (per [`ml_readiness.md`](../ml_readiness.md) §3):** this
ledger does **not** make a learner reachable on the current book. At ~27 closed trades/yr, 200/300/500
training observations are **7.5 / 11.2 / 18.6 years** away. The ledger is worth building for
*recall and adjudication*, and it becomes an ML substrate only if the book shape changes (§3.4).
Any pitch that quietly assumes "we'll collect forward data and train on it" must restate that table
or it is not an honest pitch.

---

## 1. SCHEMA — one row per trade, across ALL funnels

One append-only row per **closed** trade, plus a mutable-until-close staging row per **open** trade
(§2.3). Every column is either (a) observable at the moment it is stamped, or (b) explicitly a
post-exit label with its own stamp date. Nothing is back-filled from hindsight into a pre-entry field.

### 1.1 Identity and provenance

| field | type | notes |
|---|---|---|
| `trade_id` | str | `{grammar_id}:{ticker}:{entry_date}` — stable, the join key |
| `grammar_id` | enum | `touch44` · `box` · `sr_pivot` · `cup_handle` · `double_bottom` · `ascending_base` · `vcp` · `flag` · `trend_pullback` · `sixstep` · `weinstein` · `breadth50` · future sleeves. **Required from row 1** — this is what makes the ledger multi-funnel rather than a touch-book log |
| `book_id` | enum | `A-only` · `base-swing` · `breadth50-EW` · `breadth50-SW` · watched shadows. A trade can appear in more than one book; one row per (grammar, book) |
| `is_paper` / `is_live` | bool | the paper→real-capital boundary must be queryable forever |
| `engine_sha` | str | git sha of the engine that produced the signal |
| `input_fingerprint` | str | OHLCV cache sha256 + membership sha + index-CSV sha — the same fingerprint `scripts/archive_weekly_snapshot.py` already writes. **This is how a restated trade is later attributable** (constitution D2) |
| `as_of_snapshot` | date | the `results/archive/<as_of>/` snapshot this row was first written under |

### 1.2 Setup and entry-trigger context (stamped at signal, before the fill)

The union of what the programme proved worth recording. Every one of these has a receipt.

| field | why it is here (receipt) |
|---|---|
| `setup_class` | the router work proved origins are already one-per-name-week (ROUTER_RESULT); record it rather than re-deriving |
| `ext_vs_slow_line_pct` | **E11 / this session's ext-band census.** The single most load-bearing field in the schema — it is the axis on which every funnel comparison in the programme now rests, and it was absent from every ledger until 2026-07-31 |
| `ext_band` | pre-bucketed to E11's bands so cohorts are comparable across grammars without re-deriving cut points |
| `slow_line_value`, `slow_line_len`, `slow_line_kind` | the 44w line is an **SMA, never an EMA** (owner-mandated); a foreign grammar may carry its own line (Weinstein 30w) — record which line, so quarantined research lines never contaminate a house query |
| `zone_position` | distance to nearest pivot-high above / pivot-low below — the CONTEXT_ROUTER Layer-0 primitives, built and never persisted |
| `daily_weekly_alignment` | daily-line state at a weekly signal (and vice versa). 0084/0088 turned on exactly this and the field never existed |
| `rank_crs`, `crs_percentile` | the ranker of record; 0119 proved *screen ≠ slot*, so the rank at decision time must be stored, not recomputed |
| `mansfield_rs` | disclosed as the same construction at a different lookback (0124); store the value and the lookback |
| `atr_pct`, `vol_ratio`, `dist_52wh_pct` | the weak-but-real OOS features from the Stage-1 substrate |
| `risk_pct` (entry→stop) | **0124's Guard 1 and E6's mirage both turn on this.** A ledger without stop distance cannot distinguish an edge from a stop that never triggers |
| `regime_tags` | index vs its own slow line, breadth, vol regime — recorded as **descriptive tags only**. O-001 is killed as a gate; storing the tag is not proposing the gate |
| `known_event_within_14cd`, `dlv_med21_pct` | the two **banked** external assets (0118/0120). Screen-real, decision-margin-negative — worth *recording* forever, not worth *acting on* |
| `cash_at_signal`, `slots_free`, `was_cash_skipped` | **0112/0119/0121's decisive mechanism.** Every "pool ≠ book" finding needed to know whether capital was free, and every one of them had to reconstruct it |

### 1.2b The three decision streams (joined per trade)

Every trade carries up to three independent opinions at its decision point. **The whole point is that
they are independent** — a stream that saw another stream's answer is not a comparator.

| stream | source | written when | fields on the trade row |
|---|---|---|---|
| **system** | the engine | card issued | the card itself (§1.2) — always present |
| **owner-override** | the owner's action | fill / skip / manual deviation | `owner_action` (`took` · `skipped` · `deviated`), `owner_note`, `owner_decided_at` |
| **judge** | [pre-reg 0125](../preregistry/0125-informed-judge-forward.md) | Saturday cron, after card generation | `judge_verdict` (`take`/`skip`/`wait`), `judge_conviction` (1–5), `judge_primary_reason`, `judge_risk_flag`, `judge_row_hash`, `judge_prompt_sha256`, `judge_model`, `judge_ok` |

**Join key:** `(as_of, ticker)` — the judge log's idempotency key, which is also the card's identity.
**Source of truth:** `results/judge_log.jsonl` (append-only, hash-chained, `nq/paper/judge_log.py`).
The ledger **copies** the verdict and carries `judge_row_hash` so any row can be traced back to the
chained original; the log is never rewritten by the ledger.

**Sealing propagates.** Under the default sealed regime (0125 §5) the judge columns are populated but
**not surfaced** — no dashboard, no card, no readout renders them before the first review read. Every
row records `judge_visible` so the analysis can tell sealed-regime rows from open-regime ones; if the
owner elects open-from-day-one, rows written thereafter are marked `judge_visible: true` and the
owner-override stream **is no longer an independent comparator for them**.

**A judge failure is a row, not an absence.** `judge_ok: false` with its error is recorded, so
coverage is measurable and a silent gap can't be mistaken for "the judge had no opinion".

### 1.3 Management events (append-only child rows, `trade_id` foreign key)

`event_seq · event_date · event_type · price · fraction · stop_before · stop_after · reason_code`

`event_type` ∈ `partial_book` · `stop_ratchet` · `trail_update` · `add` · `halt` · `manual_override`.

Rationale: 0117 (post-entry is hindsight-only) and 0109 (17 exits reshuffled the whole cash path)
both required event-level reconstruction that did not exist. `manual_override` is mandatory — the
owner's discretionary deviations are the single most valuable un-recorded data in the programme, and
the ledger is worthless as a *habit* ledger if it only records what the robot did.

### 1.4 Exit and outcome

`exit_date · exit_reason` (`stop` · `trail` · `target` · `time_cap` · `stage4` · `rotate` ·
`manual` · `data_end`) · `exit_px · realized_R · realized_pct · held_days · held_weeks ·
gap_through · mae_pct · mfe_pct · mae_first2wk · capture_of_mfe`.

**`exit_reason` must distinguish an initial-stop fill from a ratcheted-trail fill.** 0124 hit exactly
this: 98.9% of exits carried `stop` because the ratchet had moved it, making the field unreadable as
a stop-out rate. Two fields, not one: `exit_reason` and `stop_was_ratcheted`.

### 1.5 Post-exit labels (stamped later, with their own dates — never mixed into 1.2)

`false_touch · noise_stop · exit_too_early · opp_quality_R` — the banked 0116/0117 label set, the
programme's standing adjudication instrument — plus `label_stamped_on` and `label_version`.

**Hard rule:** a post-exit label is computed from data *after* the exit and may never be joined into
a pre-entry feature set without an explicit purge/embargo. 0116 is the receipt for what happens when
in-sample label structure is trusted: CI-clean, 5/6 years consistent, and it **sign-flipped** on the
sealed set.

---

## 2. ACCUMULATION — how rows come to exist

### 2.1 Written by the live cron, not by a research script
The ledger is a side effect of `scripts/run_bhanushali_cron.py` / `run_paper_cron.py`, written in the
same pass that produces the signal ledger and NAV. If it needs a researcher to run it, it will not
exist when it is needed — which is the whole failure this section exists to prevent.

### 2.2 Append-only and PIT-stamped
- Every row carries the timestamp it was **written**, distinct from the date it **describes**.
- No row is ever edited. A correction is a new row with `supersedes: <trade_id@write_ts>`; the
  original stays. This is the same discipline as `overlay_registry.md` and for the same reason.
- Hash-chained per append, the `nq/paper/forward_wall.py` §3 standard already built and tested.
- Storage: one partitioned parquet per year + a JSONL append log — the accumulator pattern already
  in use, so `scripts/diag_accumulator_health.py` extends to cover it.

### 2.3 Open trades stage, closed trades commit
Open positions live in a staging table refreshed each run (management events append as they occur).
On exit the row is **sealed** into the append-only ledger and never changes again. Post-exit labels
land later as a separate stamped write (§1.5), which is why they carry their own date.

### 2.4 Backfill policy — deliberately narrow
Historical trades **may** be loaded once, at inception, from the committed ledgers
(`bhanushali_weekly_rank_0094_trades.csv`, `weinstein_0124_trades.csv`, `trades.parquet`, …) into
rows explicitly flagged `provenance: reconstructed`. **Reconstructed rows are never admissible as
forward evidence** and are excluded by default from every governance query. They exist so the schema
can be validated against real data on day one, and for nothing else.

---

## 3. GOVERNANCE — the part that makes it safe

### 3.1 The ledger is READ for adaptation only at quarterly reviews
First trading day of Jan / Apr / Jul / Oct. Between reviews the ledger is **written and not read for
any decision**. Operational reads (a health check, a dashboard count) are permitted and are not
decisions.

### 3.2 No mid-quarter self-modification, ever
No rule, weight, threshold, grading or sizing may change because of something the ledger shows,
outside a review. The only between-review action remains the mechanical −50% halt.

**Receipts, cited because this is the clause that will be under pressure:** 0103 — regime switching
is **not learnable OOS**; every walk-forward switch loses to the static blend. 0112 — a selector with
a real **+0.215 per-trade pool lift** *loses* as the fill criterion (Sharpe 1.132 → 1.035) because
reordering changes which weeks consume capital. A system that adapts to its own recent record is
running exactly the switch 0103 killed, at exactly the margin 0112 killed it at.

### 3.3 Adaptation happens through PRE-COMMITTED rules only
Any adaptation must be written into the pre-registration **before** the review that applies it,
with its threshold and its kill condition. Thresholds are **tighten-only** — never retroactively
relaxed. An adaptation proposed *after* seeing the quarter's rows is not an adaptation; it is a
retune, and it voids the study (the amendment-before-run / never-retune-after law).

### 3.4 Any learner trains on FORWARD ROWS ONLY — with the arithmetic restated

Per [`ml_readiness.md`](../ml_readiness.md), and non-negotiable:

- **Not a lane:** any learner trained on the current funnel's in-sample labels (the five-wall
  pre-entry law; 0116 is the receipt for what in-sample fit does here).
- **Admissible training data:** rows with `provenance: forward` only, from the ledger's inception
  date forward. Reconstructed rows (§2.4) are excluded.
- **Instrument validation first** if the learner or any annotator is itself a model — test-retest
  reliability and a leakage probe *before* the study, the 0123 protocol.

**Rows per year, honestly:**

| book shape | closed trades/yr | 200 rows | 300 rows | 500 rows |
|---|---|---|---|---|
| current 15-slot swing book (0094) | ~27 | **7.5 yr** | 11.2 yr | 18.6 yr |
| + a second sleeve at a similar rate | ~50 | ~4.0 yr | ~6.0 yr | ~10.0 yr |
| + breadth-50 (50 names, weight decisions) | portfolio-level; unit is **time, not trades** | — | — | — |

**Earliest date a learner is trainable**, on an Oct-2026 ledger inception:
- **Entry-quality learner on the 15-slot book: ~2034** at 200 rows. Not a decision-relevant horizon.
- **Entry-quality learner on a two-sleeve book: ~2030** at 200 rows. Still far.
- **Breadth-50 EW-vs-SW weight learning (Lane A):** first admissible read **~2027-04-01** (≥2 quarters
  post-inception) — because its unit is time, not trades. **This remains the only ML lane that can
  start in 2026, and the ledger does not change that.**

### 3.5 What the ledger is NOT
Not a live oversight tool. Not a signal source. Not a justification for a mid-quarter change. Not an
argument that ML is now reachable. It is memory — and the honest claim is that memory is worth having
even when it is not yet a training set.

---

## 4. The owner's decision at this review

**Ask:** approve the schema and the inception date, or decline.

- **Approve** ⇒ a separate, cfg-gated build session wires §2.1 into the cron, with the ledger
  written from a dated inception and read by nobody until the following review. Build cost is
  small (the fields exist; what is missing is that nothing persists them) — the expensive part is
  the *governance*, and it is written above.
- **Decline** ⇒ coherent. It costs nothing today and forgoes the compounding recall. Note only that
  every quarter of delay is a quarter of forward rows that cannot be recovered later — the one asset
  in this programme that cannot be back-filled.

**Whichever is chosen, nothing about the ML arithmetic in §3.4 changes.** The ledger is not a
shortcut to a learner; it is the thing that makes the eventual question answerable when the book
shape finally supports one.
