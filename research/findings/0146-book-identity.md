# 0146 — The headline and the kill gate are measured on different books

**Status:** MEASUREMENT — **no trial, no screen row, no sealed open, nothing adopted, no rule proposed.**
**Standing counts:** screens **20** · sealed opens **3** · n_trials **2** — unchanged by this study.
**Date:** 2026-09-25 · **Plan:** the 2026-09-25 development plan, Phase 0 item **A1**.
**SPEC:** [`book_identity/SPEC.md`](../../diagnostics/research/book_identity/SPEC.md), committed in
`187954d` **before** the diagnostic existed.
**Record:** `diagnostics/research/book_identity/2026-09-25/summary.json`.
**Reproduce:** `python pipelines/diagnostics/diag_book_identity.py --run-date 2026-09-25`.

## The question

The 2026-10-01 review will read a page of numbers about "the book". The weekly scan runs **three** books
off one engine (`scripts/run_bhanushali_cron.py`, ~lines 1055–1100):

| book | call | what it is |
|---|---|---|
| **capped A-only** | `out_paper` — `a_grade=a_set`, ₹10L cash gate | the book that would hold real positions |
| **uncapped A-only** | `out_all` — `uncapped=True` | every A signal tracked; cash never runs out |
| **capped all-grades** | `out_base` — no `a_grade` filter | `prereg_swing.md` §4's comparator |

`build_envelopes` is fed `out_all`/`led_all` (line 1090). Nothing states this at the point of use. So:
**for every number the review reads, which book produced it?** That is the whole study. It asserts
nothing about whether the strategy works.

## Result — the readout mixes two books, and one gate mixes them inside itself

Every mapping below is verified **by value**, not inferred from the code: each scorecard field is
asserted equal to the artifact it is copied from, and the published MaxDD is recomputed from the NAV
curve (−6.66% against a published −6.7%).

| the review reads | value | artifact | **which book** |
|---|---|---|---|
| `n_closed` — the "11/40 closed" headline | **11** | `signal_analytics_weekly.total_closed` | **uncapped** |
| `expectancy_R` (gross) | **−1.56R** | `signal_analytics_weekly.avg_r` | **uncapped** |
| `win_rate_pct` | **0.0%** | `signal_analytics_weekly.win_rate` | **uncapped** |
| `maxdd_pct` — the §5 mechanical halt reads this | **−6.7%** | `portfolio_history_weekly.csv` | **capped** |
| `sharpe` — the `KILL_SHARPE < 0` trigger | **−0.1002** | `portfolio_history_weekly.csv` | **capped** |
| `nav` | **₹1,018,440.17** | `paper_portfolio_weekly.total_value` | **capped** |
| `a_only_closed` — §4's ≥20-per-book floor | **11** | `signal_analytics_weekly.total_closed` | **uncapped** |
| `base_swing_closed` — §4's ≥20-per-book floor | **1** | `base_swing_forward.n_closed` | **capped** |

**§4's floor is the one gate that mixes books inside itself.** It applies "≥20 closed **per book**" to an
uncapped count (11) and a capped count (1). Those are not the same kind of quantity.

**And `paper_portfolio_weekly.total_trades` mixes the books inside one field.** The cron's comment
(`run_bhanushali_cron.py:729-735`) correctly says "it is n_closed", then asserts
*"positions-taken-since-inception = total_trades + n_positions"* — which adds **11 uncapped closures to
6 capped opens** and gives 17. The capital book has taken **7** positions (below). The published schema
is wrong in a second way: `docs/paper_portfolio_schema.md:47` calls the field *"Counter of all trades
ever (open + closed)"*, which it is for neither book. The same comment also claims the field is "a
published field in `results/output_contracts.json`" — it does not appear in that file.

## The two capped books have produced the same equity curve on every session

All **55** common NAV points agree to within half a paisa — **maximum absolute difference 0.00**.

**Is this a plumbing bug?** The hypothesis worth killing is that `_base_swing_record` silently carries
`out_paper` — the *capped A-only* object. Noting that `out_base`'s scalars (`n_closed 1`,
`expectancy_R_gross −1.046`, `exit_reasons {'stop': 1}`) differ from the **uncapped** side's 11 / −1.56 /
0.0% does **not** discharge it: under that exact bug those are the values you would see. The first draft
of this finding made that non-sequitur and the `red-team` read caught it.

The discriminating test is a replay with and without the `a_grade` filter, and the diagnostic now runs
it on **2023-01-02 .. 2024-06-28** — strictly before the sealed slice, so it spends no sealed open:

| | final equity | closed trades |
|---|---|---|
| A-only | ₹1,683,022.23 | 13 |
| all grades | ₹2,279,012.97 | 9 |

**All 365 common sessions differ, maximum absolute delta ₹609,448.71.** (The SPEC ruled out replaying the
**live** window, because the local OHLCV cache predates inception. This is a different window answering a
different question — *can* the books differ — so it is an addition to the SPEC's method, not a departure
from its constraint.) So `a_grade` demonstrably bites,
`_base_swing_record` is not writing the wrong object, and the live identity is a fact about the *live
window* rather than a wiring defect. (`a_grade=None` simply sets `is_a = True`,
`run_bhanushali_weekly_rank.py:995`.)

**What it means.** Identical curves on every session mean the two books held identical positions
throughout, so the **funded** set is the same whether or not the grading filter is applied. The
candidate pools genuinely differ — `results/weekly_sma_panel.csv` for 2026-09-18 carries **23 signals,
14 Grade A and 9 not** — so it is the *funding* stage, not the signal stage, that erases the
distinction. The mechanism consistent with that (stated as a reading, not a measurement: this study
did not replay the books) is that under `max_notional_pct = 0.20` only about five seats are affordable,
they are filled strongest-CRS-first, and Grade A *is* the top-5-by-CRS rule — so the non-A names sit
below the funding margin. Confirming that mechanism would need a holdings replay, which the stale local
OHLCV cache cannot support (SPEC §Population).

**The consequence for §4, stated at the scope the evidence supports.** §4 decides on forward **MaxDD**
and **Calmar**, both read off these curves. Over *these 55 sessions* the two arms cannot be separated by
that test — with ~92% of the book invested (cash ₹83,005 of ₹1.02m) and exactly one closure freeing cash,
the funded sets coincided. That is **not** a structural claim that they can never differ: the replay
above shows they differ substantially given a longer window and more turnover.

What *is* currently decisive is narrower and comes earlier in the rule: the floor short-circuits
**before** the MaxDD/Calmar branches are reached (`bhanushali_review_scorecard.py:190-194` tests
`min(a_closed, b_closed) < 20`), so today it is the mismatched floor — not the curve identity — that
decides §4's verdict. The cron's own comment block states
that the comparator was added because *"with no comparator accruing, that default fires mechanically at
every review and retires the live product without evidence."* The comparator now accrues, and the default
still fires mechanically — for a different reason.

**This finding proposes no fix.** Whether §4 needs a dated amendment is an owner decision at a review.

## The capital book: 7 positions ever, 1 closed, 6 held

From the 16 dated snapshots under `results/archive/*/`:

| | |
|---|---|
| names ever held | **7** — CUB, DELHIVERY, INDUSINDBK, NESTLEIND, HEG, MCX, CHOLAFIN |
| positions that left | **1** — DELHIVERY, gone by the 2026-08-17 snapshot |
| held now | **6** |

**This count is EXACT, not a lower bound** — the SPEC conservatively assumed the latter, and the
`red-team` read showed it can be tightened. A funded name is also tracked in the uncapped book and exits
on the same weekly trigger, so capped closures are a **subset** of the 11 uncapped ones. For each of the
other ten, there is at least one snapshot **strictly inside** its `[signal_date, close_date)` window in
which the name is absent from the capped positions — so it was never funded and cannot have closed. No
closure has zero snapshots in its window, so nothing could have opened and closed unobserved, and the
pre-archive gap (inception 2026-07-04 to the first snapshot 2026-07-24) is closed by the uncapped book
reporting **0** closures at 2026-07-24.

The window must be **half-open**: a position is legitimately absent from the snapshot taken *at* its own
close date, and testing `<= close_date` mislabels DELHIVERY — the one name that really was funded.
`tests/test_book_identity.py` pins that boundary.

**Not independent corroboration.** The first draft called `base_swing_forward.n_closed = 1` an
independent confirmation. It is not: it comes from the same weekly run, and its relevance presupposes the
very book-equality being inferred. `results/attribution_ledger.csv` is likewise rebuilt from the same
archives. There is one source here, read two ways.

There are **12 distinct as-of snapshots**, not 16 — four of the sixteen directories are `__rerun-*`
repeats of a parent as-of and are not additional observations. Three of the twelve (08-12, 08-14, 09-15)
are mid-week ad-hoc runs rather than Saturday scans.

The capital book's own closed-trade record is therefore **one stop at −1.046R** — a number published
nowhere. DELHIVERY was funded at the notional cap: 391.43 shares × ₹510.95 = **₹200,000** exactly 20% of
opening capital, closed at ₹458.70 for **−₹21,135** (−10.23%).

## NAV reconciliation, and what cannot be decomposed

Within the latest snapshot the identity holds: cash **₹83,005.41** + Σ current_value **₹935,434.75** =
**₹1,018,440.16** against a published **₹1,018,440.17** — residual **−₹0.01**.

Σ unrealised on the 6 open positions is **+₹11,407.25**, so

> `implied_realised = NAV − 1,000,000 − unrealised` = **+₹7,032.92**

**This is DERIVED, not sourced, and it is not the profit of closed trades.** The decisive fact is that
the capital book realised money **five times** while closing **once**. From the share path in the
snapshots:

| event | ticker | shares | approx proceeds |
|---|---|---|---|
| partial booking, 2026-07-31 | CUB | 943.40 → 571.34 | ≈ ₹76,830 |
| **closed**, 2026-08-17 | DELHIVERY | 391.43 → 0 | realised **−₹21,135** |
| partial booking, 2026-08-21 | MCX | 70.03 → 69.97 | ≈ ₹191 |
| partial booking, 2026-09-15 | CUB | 571.34 → 190.45 | ≈ ₹85,997 |
| partial booking, 2026-09-18 | CHOLAFIN | 112.01 → 111.34 | ≈ ₹1,206 |

Proceeds are **approximate**: the share delta is priced at the snapshot's mark, not the fill the engine
took, and entry prices are restated between snapshots (CUB 212.00 → 210.03). The two sub-rupee-scale rows
(MCX 0.06 shares, CHOLAFIN 0.67) are consistent with fractional restatement rather than a deliberate
tranche; the two CUB rows are material and unambiguous.

**So the positive sign comes from partial bookings on a position that never closed, plus a corporate
action — while the only closed trade lost money.** The first draft's arithmetic was wrong in a way that
mattered: it said "−₹21,135 plus the full credit would be +₹118,386, so the gap is a declared hole",
treating HEG's ₹139,521 credit as if it were all P&L, in a paragraph that had already described the
offsetting basis change. The credit comes with a simultaneous basis release of roughly
305.93 × (652.99 − 244.07) ≈ **₹125,111**, so HEG's realised contribution is on the order of **+₹14k**,
not +₹139.5k — and the partial bookings, omitted entirely from that arithmetic, are the rest.

**The fourth book-identity hole.** `closed = 1` is not the number of realisation events, and **no
published field expresses a partial realisation at all**. That sits alongside the three holes already
named in `DECLARED_HOLES` (`scripts/collect_attribution_ledger.py`), and it is the concrete case for the
development plan's item **B3** (per-event management child rows).

**The two artifacts disagree about the one corporate action in the live book.** `paper_portfolio_weekly`
records HEG's credit as **₹139,521.35** on **305.9344** shares with `r_credited 0.7216`;
`attribution_ledger.csv` records **₹140,323.02** on **307.6923** shares with `r_credited 0.7539` — an
**₹801.67** gap from a price restatement. The ledger also carries **no `shares` for HEG at all**, because
its join key is `(ticker, signal_date = 2026-07-24)` against a position entered 2026-07-28, so it names
6 of the 7 funded names. A1 is precisely the study that should surface this, and the first draft quoted
one figure as "the credit" without noticing the other.

## What this does NOT say

**It does not say the book is doing well.** One closed position is not evidence about a strategy in
either direction, and the `≥30 closed` precondition means **expectancy and win rate are not informative
quantities here at all** — on either book. Nothing above restates performance as better or worse than the
published record. What it establishes is narrower and, for a review, more useful: **which book each
number is about.**

It also does not re-specify a gate, propose a config change, or restate the published record. The
artifacts stay exactly as they are.

## What the 2026-10-01 review should take from this

1. `0-of-11, −17.18R, expectancy −1.56R` describes the **uncapped** tracker. The **capped** book that
   would hold real money has one closed trade.
2. The `KILL_SHARPE < 0` trigger is computed on the capped NAV curve over **55 daily points** (54
   returns) of a 12-week book. It is surfaced-not-applied between reviews, which is correct — and its
   **sign is noise**: SE(annualised Sharpe) ≈ √(252/54) ≈ **2.16**, so −0.1002 is indistinguishable from
   zero, against a programme resolution floor of ~0.6 Sharpe
   ([`plausibility_anchors.md`](../../docs/references/plausibility_anchors.md) §3). The gate has fired on
   a quantity this data cannot resolve. The diagnostic confirms the gate's live state reads
   `triggered: true`.
3. The readiness gate (`≥40 closed OR 4 quarters`) counts **uncapped** closures while the Sharpe and
   MaxDD printed beside it are the capped book's.
4. §4's per-book floor compares quantities from two different books, and its MaxDD/Calmar test is
   currently unable to separate the arms at all.

None of that is a reason to kill, retune, or move a threshold. It is a reason to state, next to every
number, which book it belongs to.

## Defects fixed before publication (red-team read, 2026-09-25)

- **The curve-identity proof was a non-sequitur.** It differenced `out_base` against the *uncapped* book,
  when the hypothesis was that `out_base` silently carries the *capped* one. Replaced with the
  with/without-`a_grade` replay, which the committed diagnostic now runs.
- **The claim was over-generalised.** "Grading does not change what gets funded" and "MaxDD shallower can
  never be true" are structural claims the replay contradicts. Scoped to these 55 sessions, and the
  floor's short-circuit is now named as what actually decides §4 today.
- **The closure count was reported as a lower bound; it is exact.** Proven by the subset argument, with
  the half-open-window boundary that would otherwise mislabel the one funded closure.
- **"Corroborated independently" was false.** `base_swing_forward.n_closed` and
  `results/attribution_ledger.csv` both derive from the same weekly run.
- **The reconciliation was wrong and its label insufficient.** Partial bookings were omitted entirely and
  HEG's credit was treated as pure P&L. There are five realisation events against one closure, and the
  positive sign is bookings plus a corporate action while the only closed trade lost money.
- **A code defect published a wrong value:** `_kill_triggered` scanned each gate's serialised *value* for
  "kill" when the scorecard names the gate in the *key*, so the record read `kill_triggered: null` while
  the live gate was triggered. Fixed, with a regression test.
- **One test was vacuous.** The §4 mismatch test asserted on the diagnostic's own hardcoded strings and
  would have passed unchanged after the defect was fixed. It now compares the artifacts the gate reads.
- **The Sharpe row was the only provenance mapping not verified by value** — and it is the one the kill
  decision rests on. Now recomputed from the NAV curve and asserted.
- **The cross-artifact HEG disagreement and the ledger's missing `shares` join were unnoticed.** Both are
  now measured and recorded.
- **Citations corrected:** the cron comment does not call `total_trades` the capped count; the wrong
  arithmetic is `total_trades + n_positions`. `docs/paper_portfolio_schema.md:47` mis-describes the field,
  and it is not in `results/output_contracts.json` as that comment claims.

## Do not re-test unless

The scan's book plumbing changes, or a gate's inputs change. Re-running this diagnostic is cheap and it
is the right check after any edit to `build_envelopes`, `_base_swing_record` or the scorecard's
`_forward_metrics`. `tests/test_book_identity.py` pins the §4 two-book mismatch deliberately: when it is
addressed, that assertion flips and someone has to acknowledge it in a diff.
