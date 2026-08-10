# Forward plan, reframed — 2026-08-11

Supersedes the 2026-08-10 plan. Standing counts: read them from
`diagnostics/research/n_trials.json` and `diagnostics/research/label_screen_ledger.md`, never from
this document.

## What changed, and why the reframe is not cosmetic

The previous plan opened by asserting that the apparatus could now be trusted. That claim has not
survived. Between 2026-08-10 and 2026-08-11 three defects were found in production paths that were
green the entire time, and the most serious of them had been silently corrupting the *freshness* of
the book of record:

1. **The 1.5× cost gate had never been evaluated.** The multiplier lived only in an f-string. Now
   real, and it **passes**: 21.73% → 20.69% CAGR, still clearing passive EW at 13.20%.
2. **The Saturday scanner died on a bash syntax error** (`||` alone on a line inside a `run: |`
   block). The engine step had already succeeded, so a full week of state — including the first
   `base_swing_forward.json` — was computed and discarded.
3. **The weekly OHLCV top-up has never reached the cache.** `download_ohlcv` drops names returning
   fewer than 50 bars; the incremental window is 25 calendar days ≈ 18 sessions; so every warm name
   was discarded and `merge_ohlcv` folded an empty dict into the cache while the cron reported
   success.

Number 3 is the one that reframes the plan. **The dashboard was not stale because a job failed. It
was stale because a job succeeded without new data.** The book advanced only when the monthly
`actions/cache` key rolled and every name came back cold — which is why a successful run on
2026-08-10 published `generated_at: 2026-07-31`, nine days late, with yfinance serving through 08-10
throughout.

**The lesson to carry, because it is the third instance this week:** green is not evidence. The
adjustment guard raised, the output contract passed, the scheduler-health card read OK, and the run
committed — all while the input had not moved. Every one of those controls checks that a step *ran*,
not that it *changed anything*.

## The correction this forces to the previous plan's premises

- *"What the apparatus can now be trusted to do"* — withdrawn as written. 883 tests is a real floor,
  but none of them watched the top-up, and the defect predates all of them.
- *"The intraday store is the only route that beats the 2027-07-01 capital floor"* — **wrong.** The
  ±0.59 ceiling is `n_eff = 37` independent 63-day windows, i.e. calendar span ÷ holding period. Bar
  frequency does not enter it. Intraday certifies nothing about the swing book and does not
  accelerate its 30-closed-trade gate.
- *"Two zero-trial screens likely to close for free"* — void. Since the 2026-08-08 owner amendment
  **no screen or bound can close anything**, and both candidates died at Gate 0 for free anyway.

---

## Priority 1 — restore, then verify, the book of record

Ordered. Each step is worthless until the one above it is done.

**1.1 Merge the fix chain to `main`.** PR #68 carries the top-up fix, the scanner syntax fix, the
16:30 reschedule and the §4 scorecard. Until it lands, every weekday scan keeps writing post-close
artifacts into a partial-candle series, and the next Saturday run repeats 2026-08-08.

**1.2 Re-run the scanner and confirm the book actually moved.** The check is not "did it succeed" —
that is precisely the signal that failed. The check is `generated_at` advancing to **2026-08-07** and
`portfolio_history_weekly.csv` gaining rows past 2026-07-31.

**1.3 Audit the forward record for the staleness window.** The incremental path was introduced
2026-07-18 and inception is 2026-07-04, so between the monthly rebuilds the cache may have been
frozen for stretches of July as well. Weekly decisions land on completed weeks so the *decisions* are
probably intact, but the daily NAV series may have flat segments that are artifacts rather than
market. This must be established before any forward number is quoted, and it is the reason `§4`'s
comparator window needs re-reading rather than assuming.

**1.4 Add the control that would have caught it.** Every scheduled job that consumes data should
assert its input MOVED, not merely that it ran. Concretely: the cron fails loudly when
`generated_at` does not advance on a run that expected a new session. `scheduler_health` already
tracks `artifact_last_utc` and `artifact_corroborates` — it read `age_days 8.89` against
`overdue_after_days 9` and still said OK, hours from alarming and days after the data froze.

**1.5 Pin the data dependency.** `pyproject.toml` pins `yfinance>=0.2.40`; the runner installed
**1.5.2** while local development runs **0.2.65**. A major-version float on the sole data source of a
live book is an unforced risk. Related and unfixed: `download_ohlcv`'s single-ticker branch assumes
flat columns while the multi-ticker branch expects a MultiIndex — the cron batches 25 so the live
path is safe, but the single-ticker path is untested and may already be broken under 1.5.x.

---

## Priority 2 — the 2026-10-01 review

**2.1 ADR-0013 is the only item with a mechanical consequence for not deciding.** The TRENT
acceptance expires 2026-10-01; the defect self-resolves 2026-11-06. In the 35-day gap the seam is
in-window and unaccepted, which is the escalation condition, so the weekly scan halts — five scans
(Oct 3, 10, 17, 24, 31). Memo with four costed options in `review_2026Q4/07_adr0013_seam_expiry.md`;
recommendation is to extend the acceptance to 2026-11-06 via a dated ADR, which is the only option
whose cost is one already-accepted cost.

**2.2 §4's first read is predetermined and should not surprise anyone.** It reports INSUFFICIENT
EVIDENCE → default base-swing. That default is **not** the book holding the paper capital. Two
further things need owner input: §4 as frozen has an **undefined region** (DD shallower but Calmar
between the 0.05 keep bound and the 0.10 revert bound), and the panel does not implement §4's
CI-overlap limb, so any KEEP/REVERT it emits is provisional.

**2.3 The rest of the binder**, unchanged: the corrected-universe re-anchor (September's run is the
memo of record; the smoke window cost the swing book 3.69pp of CAGR), the veto-arm retire-or-fund,
prereg 0074 run-or-withdraw, the NSE 2027 holiday list, and the scorecard spec reconciliation.

---

## Priority 3 — research, and the honest state of it

**Nothing cheap is left in the queue.** Both P0.6 candidates died at Gate 0. BREADTH_REG had already
been run to a formal KILL under prereg 0070; the three Clenow "defects" are real in principle and
immaterial in practice (the `periods` discrepancy moves 2,058 of 4,000 synthetic ranks but leaves the
**top-30 membership unchanged**, and the book takes `top_n=30`). That is the verdict machine working
— Gate 0 is free and most ideas are supposed to die there — but it also means there is no free win
waiting.

**The intraday store is built and unfetched, and that is the right state.** `nq/data/intraday.py`,
`nq/data/fo_universe.py`, `nq/data/nse_bhavcopy.py` and the two pipelines are tested and hermetic.
The universe panel is built: 359 symbols ever in the F&O segment, 208 today, 151 departed — of which
**98 are still trading**, so the genuinely-dead tail is bounded at 53 of 359 and is probably a
fraction of that.

The decision it waits on is not technical. It is **"do we want a second, faster book?"** — because
intraday pays only where the holding period shrinks, and that is a new strategy family with its own
in-sample work, pre-registration, `n_trials` charge and forward record from zero. Binder item 08
puts it as an explicit yes/no, and recommends deferring while the live book is UNCERTIFIED.

---

## What actually gates real capital, restated

Unchanged by any of the above, which is the point: **forward evidence on the live book**. The paper
gate is ≥30 closed trades and the §4 primary decision is 2027-07-01. At the observed rate the trade
count cannot be forced without changing the book, which resets the clock.

Everything in Priority 1 exists because that forward record is only as good as the data feeding it,
and for at least nine days it was being fed nothing at all.

## Verification standard, tightened

- `python -m pytest tests/ -q` — **883 passing**; nothing may regress.
- Any `nq/**` or `config.py` change: regenerate `docs/DEPENDENCY_MAP.md` and commit it.
- Live-book paths need `prod-fix:` or `prod-override:`, and `prod-fix` needs a regression test
  **verified to fail on the old code** — not assumed to.
- **New, from this week:** a control that asserts a job ran is not a control. Where a job consumes
  data, assert the data MOVED. Three defects this week were invisible to every existing green check.
