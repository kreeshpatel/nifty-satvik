# Live seam repair — a scoped owner decision

**Date:** 2026-08-06 · **Class: VERIFICATION.** Counts frozen: screens 15 · sealed opens 1 ·
n_trials 138. Zero trials, zero screens. **Nothing is repaired. No option is recommended.**

Both readings are presented in full. The session was explicitly not authorised to choose, and has
not chosen.

---

## The crux question, answered first

> **Can (a) be done without re-anchoring the pin?**

**Yes — and the reason is stronger than "we could gate it".** The live path and the record path are
already *different code paths reading different artifacts that happen to share a filename*.

`data/ohlcv.pkl` is gitignored (`.gitignore:15`). It is not one file; it is two:

| | The pin | The live cache |
|---|---|---|
| What it is | release asset `dataset-pin-20260701`, sha256 `f8625a8f…`, 64 MB, 710 names, 2017→2026-06-29 | an `actions/cache` instance on the cron runner |
| Who writes it | nobody — it is immutable and released | `run_bhanushali_cron._refresh_ohlcv` → `save_ohlcv_cache`, every run |
| Lifetime | permanent | **key rolls monthly** (`ohlcv-live-${YYYY-MM}-…`), so the first run of each month rebuilds it |
| Read by | `run_bhanushali_path1.corrected_universe()` → the substrate, the run of record, the determinism guard | `_refresh_ohlcv()` → the live cards and the paper book |

They already diverge every week: the live cache carries bars past the pin's 2026-06-29 close and
has a shorter history (`INCEPTION_DEFAULT − 520 days`). **The record has never been computed from
the live cache and the live book has never been computed from the pin.**

So a repair applied inside `_refresh_ohlcv` — or in a new `nq.data` function called only from it —
is invisible to `corrected_universe()` by construction. It is not even a cfg-gate question; the two
call sites are separate functions. The engine invariant ("cfg-gated so the golden master stays
byte-identical when off") is satisfied trivially, because the record path never executes the repair.

**The pin does not move. The substrate does not move. The determinism guard does not move.**

### The real constraint is not the pin — it is the forward wall

`forward/prereg.md` §9: *"All promotion, demotion, degradation, and fork decisions happen **only** on
these dates. Between dates: monitoring and logging only — no config changes, no size changes (except
the mechanical §4 halt)."*

A data-correctness repair is literally neither a config change nor a size change. But it changes
what the live book does mid-quarter, which is what that clause exists to prevent. **This is the
genuine tension in option (a), and it is a governance question, not a technical one.** It is stated
here and not resolved.

The reading in favour of (a): the clause guards against *discretion* — moving a threshold after
seeing results. Repairing an input the exchange proves is wrong is not discretion, and the wall's
own §3 fingerprint already anticipates input drift.

The reading in favour of (b): the clause says what it says; the first quarter of a pre-registered
forward wall is exactly when a "just this once, it's obviously right" exception is most corrosive;
and the measured cost of waiting is small and now precisely known.

---

## What is actually at stake — measured, not asserted

The audit's addendum C-4 narrowed this considerably, and the narrowing cuts against urgency:

- **Exactly one name is affected live today: TRENT.** Its seam is 2026-01-01 and 17 pre-seam weeks
  remain inside the 44-week window. Every other seam has aged out of the window (CONCOR 2025-01-01,
  HBLENGINE 2024-12-24, UPL 2024-11-18, the three 2024-01-01 seams), and MAHLIFE is not in the live
  500-name universe.
- **No open position is affected.** The five held names — DELHIVERY, INDUSINDBK, NESTLEIND, CUB,
  HEG — contain no seam symbol. No entry, stop, target or NAV figure changes under either option.
- **The effect is a suppressed candidate, not a wrong position.** As served: `sma44 3248.73`,
  `close/sma 0.9456`, `close_above_sma False`. Seam-corrected: `sma44 2809.84`, `close/sma 1.0698`,
  **`True`**. TRENT is a top-decile-by-R name historically (+20.76R).
- **It self-resolves around 2026-11-06**, when the seam leaves the 44-week window — about five weeks
  *after* the 2026-10-01 review.
- **A rebuild does not fix it** (addendum C-1): the discontinuity is vendor-served and a fresh
  single-call download reproduces it exactly. Waiting for the monthly cache roll achieves nothing.

What is *not* known: whether TRENT would actually have been bought. Suppression removes it from the
candidate pool; whether it would have won a Grade-A slot in any given week, and displaced what, is
not measured here and would require a counterfactual run — which is a trial, and none was spent.
**The cost of (b) is therefore bounded above by "one top-decile name is invisible for ~3 months",
and is not equal to it.**

---

## Option (a) — repair the live cache now

**What changes in the live book.** From the next cron run, the seven seam symbols' pre-seam bars are
rescaled onto the post-seam basis before the weekly panel is computed. In practice one name moves:
TRENT's `close_above_sma` flips `False → True`, making it eligible for Grade-A ranking. Its CRS rank,
44-week SMA, extension and ATR all change. No open position changes. Candidate sets from that date
forward may differ; the paper book's NAV changes only if a different name is subsequently bought.

**What changes in the record.** **Nothing.** `corrected_universe()` does not execute the repair; the
pin is not rewritten; the substrate, the run of record, `baseline_v1`, the band census and every
published finding are untouched. The Oct-1 re-anchor question — whether the *record* should also be
repaired, alongside the 0025 survivorship correction — is unaffected and stays open.

**What the determinism guard does.** Nothing. `build_substrate.guard()` runs
`R94.backtest(prep_weekly_rank(corrected_universe()), mem, start="2017-01-01")` and continues to
reproduce **Sharpe 1.132 / 255 positions**. `tests/test_r94_golden.py` runs on a hermetic synthetic
fixture and is untouched. The full suite stays green.

**What it costs.** A live/record input divergence that must be tracked deliberately: from that date
the live book and the record are computed from series that differ for seven names. The D2 archive
already handles exactly this — `scripts/archive_weekly_snapshot.py` fingerprints the OHLCV cache
sha256 per snapshot and logs restatements to `results/archive/drift_log.jsonl`, whose docstring
already anticipates this case: *"A restatement is not automatically wrong (a split re-adjustment
legitimately re-bases prices), but it must never be silent."* A repair would appear there
automatically on the next archive run. The dated `research/config_CHANGELOG.md` entry and a
`forward/prereg.md` §10 amendment would be the human-readable half.

**Residual risk.** The repair is our arithmetic applied on top of the vendor's, using factors from
the NSE corporate-action record. It is correct for the five events with a known exact factor
(4, 5, 4, 1.25, 1.5) and requires a judgement call for the two rights issues (1.0884, 1.0425), whose
factors were measured against the exchange rather than derived from a ratio. It also does not cover
the two `OPEN-undiagnosed` seams (HBLENGINE, TRENT-2019), which have no known factor at all.

---

## Option (b) — leave it until 2026-10-01

**What changes in the live book.** Nothing. TRENT stays suppressed for approximately three more
months. If the review chooses repair on 2026-10-01, the seam clears the window on its own about five
weeks later, so the repair would buy roughly one month of corrected signal on one name.

**What changes in the record.** Nothing.

**What the determinism guard does.** Nothing.

**What it costs.** Up to ~3 months of a known-wrong input suppressing one top-decile-by-R name, with
the caveat above that suppression ≠ a forgone trade. It also means the live book knowingly runs on
an input the repo has proven wrong, which is a precedent question as much as a P&L one.

**What it buys.** The forward wall's mid-quarter discipline is not breached, and the repair is
decided in the same session as the 0025 survivorship re-anchor and the demerger convention — three
questions about the same data layer, decided together with one consistent convention rather than
piecemeal. It also allows the two `OPEN-undiagnosed` seams to be localised first, so a repair covers
the whole class rather than the part currently understood.

---

## What ships regardless of the decision

The **guard** (`nq/data/adjustment_guard.py`) is in either way. It is detection, not repair: it
asserts the monotonicity invariant on every refresh, warns on the 13 registered seams, and **raises**
on any seam not on the register. That is the standing protection against a *new* seam entering
silently, which neither option addresses and which the existing `_detect_readjusted` threshold
cannot see.

## Cross-references

- `FOUNDATION_AUDIT.md` §F-1 and the 2026-08-06 addendum (C-1 … C-5)
- `nq/data/adjustment_guard.py` · `scripts/check_adjustment_seams.py` ·
  `diagnostics/research/foundation_audit_2026Q3/adjustment_guard_pin.json`
- `forward/prereg.md` §9 (between-review discipline), §10 (amendment protocol)
- `scripts/archive_weekly_snapshot.py` — the D2 drift log that would capture the delta
- `research/findings/0025-*` — the survivorship re-anchor this pairs with

---

# DECISION — 2026-08-06: option (b). Recorded, not recommended.

**The owner chose (b): no live repair before the 2026-10-01 review.** Formal record:
[`docs/decisions/0013-defer-live-seam-repair.md`](../../../docs/decisions/0013-defer-live-seam-repair.md).
Config-event entry: `research/config_CHANGELOG.md`, 2026-08-06.

The reasoning as given:

1. **Scope is one suppressed candidate** — TRENT alone sits inside the 44-week window.
2. **No open position is affected** — the five held names contain no seam symbol, so nothing the
   book owns is mispriced.
3. **It self-resolves on 2026-11-06**, about five weeks after the review; acting now buys roughly
   one month of corrected signal on one name.
4. **The fix is a vendor override, not a restoration.** The discontinuity is upstream, so a repair
   is our arithmetic layered permanently on the vendor's — and it would cover only the part of the
   class with known factors, leaving the two `OPEN-undiagnosed` seams uncovered.
5. **`forward/prereg.md` §9 protects three newly-started forward streams.** The first quarter is
   when a "just this once" exception is most corrosive, and the cost of declining is now measured.

Note that (a) was **feasible** — the pin never had to move. It was declined on governance grounds,
not blocked on technical ones. That distinction is the point of having asked the crux question first.

## The pre-committed escalation trigger

The acceptance is scoped, dated and machine-evaluated — not a note anyone has to remember.
`nq.data.adjustment_guard.assert_no_live_escalation` runs on **every** cron refresh and **raises**,
halting the weekly scan, when either condition fires:

- **any ADDITIONAL live-affecting seam** — inside the 44-week window and not owner-accepted; or
- **any seam on a name the book HOLDS**, accepted or not, because the acceptance was granted for a
  *suppressed candidate* and an open position is a different question.

Halting is the intended consequence: the pre-commitment is that this returns to the owner **before
the book acts again**. The TRENT acceptance carries
`owner_status = "ACCEPTED_UNTIL_2026-10-01 (ADR-0013)"` and **expires by date** — on 2026-10-02 the
same seam escalates with no edit to any file. A malformed status fails closed.

Current state, evaluated on the pinned cache: 1 seam in-window (TRENT), owner-accepted; 0 on open
positions; **escalate = False**.
