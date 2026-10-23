# MEASURE 2026-10-23 -- the -389.8R trade: a degenerate stop in the uncapped book, and whether the live path is exposed

**Tier 1 (MEASURE / RE-RUN), `docs/PROCESS_TIERS.md`.** No pre-registration, no screen row, no `n_trials` change.
Standing counts, parsed by the script from the ledgers: **screens 23 · sealed opens 3 · n_trials 2**
(`diagnostics/research/n_trials.json`, `diagnostics/research/label_screen_ledger.md`).
Train only: every series cut at 2024-06-30 and asserted; `results/judge_log.jsonl` is not touched. No production path
is edited. Script: `pipelines/diagnostics/diag_degenerate_stop_restate_2026_10_23.py` (outputs
`diagnostics/research/degenerate_stop/result.json`). The restated numbers live in the dated CORRECTION sections appended to
findings 0148 and 0150; this note holds the identification, the cause and the exposure.

## 1. The trade

Live-config uncapped replay (`engine_kwargs(DEFAULT_CONFIG)` with `uncapped=True`, PIT membership, Grade-A set, 526 trades,
last bar 2024-06-28), every trade with |R| > 10 or initial risk under 0.5% of entry:

| ticker | entry week | entry | stop0 | risk0 % entry | exit | R | verdict |
|---|---|---|---|---|---|---|---|
| **VMART** | 2019-05-06 | 2019-05-06 @ 676.74 | 676.69 | **0.0074%** | 2019-05-13 @ 644.24 (`stop_part`) | **-389.75** | degenerate stop |
| SUVEN | 2019-08-27 | 2019-08-27 @ 11.87 | 10.78 | 9.2% | `sma_break` | +40.8 | genuine winner |
| ALKYLAMINE | 2020-03-23 | 2020-03-23 @ 430.95 | 400.28 | 7.1% | `sma_break` | +29.7 | genuine |
| TRIDENT | 2020-09-14 | 2020-09-14 @ 6.17 | 5.76 | 6.6% | `sma_break` | +26.0 | genuine |
| MAZDOCK, HUDCO, GMMPFAUDLR, KSB, GESHIP, NTPC | 2019-23 | | | 2.9% to 10% | `sma_break` / `eos` | +10.95 to +17.6 | genuine |

**Exactly one trade in the 526 has initial risk under 0.5% of entry: VMART.** It is the only |R| > 10 trade that is not a real
fat-tail winner. The next-smallest risks are 1.2% (IPCALAB, GSKCONS, HONAUT) with ordinary R. The nine other |R| > 10 trades
are real compounders on 3% to 10% stops; they are positive and are not an artefact.

Widening to the all-grade uncapped ledger (the 0150 Part 1 set, 1,367 trades) finds the same class on the other sign:
**TECHM 2019-01-15** entry 528.58 / stop 528.27 (risk 0.059%) closes at **+154.8R**; ICICIBANK 2022-04-18 (risk 0.099%,
R -1.9) and ZFCVINDIA 2020-08-03 (risk 0.23%, R +1.5) are also under 0.5%. So this is a population property of an
unfloored stop, not one bad bar: 3 of 1,367 all-grade trades and 1 of 526 Grade-A trades.

## 2. The cause

`prep_weekly_rank` (`scripts/run_bhanushali_weekly_rank.py`, `s["entry_win"][e0] = (days, stop, whigh, crs_dist, sma, origin)`)
stores the **signal-week low as the band floor and as the stop** and the signal-week high as the band ceiling. At fill,
`backtest` accepts any entry-week open strictly inside the band (`o_["lo"] < opn < o_["hi"]`), sets `en = opn`, `st = o_["lo"]`,
then `if max_risk_pct is not None: st = max(st, en * (1 - max_risk_pct))`. That line only **lifts a WIDE stop up to 10%**
(`max()` against `en * 0.9`). Nothing bounds risk from below: when the open lands a few paise above the signal-week low the
fill is legal and `risk0 = en - st` is a sliver. `if en > st` is the only floor, and any positive sliver passes it.

VMART shows it exactly. Signal week 2019-04-29..05-03 (no bar 04-29 in the cache): weekly low 676.69 (Tue 04-30), weekly high
704.18, close 696.4. Entry week opens Monday 2019-05-06 at **676.74**, a -2.8% gap down from the 696.4 close, which is also
that day's low: **0.05 above the signal-week low**. The fill is accepted, risk0 = 0.05 rupees, the 2R target is 676.84
(tagged the next day, so the half-exit books "+2R" on a tick), and the position then falls to a 644.24 exit
on 2019-05-13: a roughly -4.8% loss measured against a 0.0074% risk is -389.8R after the half-exit credit.

**Data glitch check: none found.** `nq/data/adjustment_guard.KNOWN_SEAMS` has no VMART entry; the 2019-04..05 bars are
internally consistent (the entry open equals that day's low; no impossible prints or gaps) and the adjusted series reads a
steady factor against `data/raw_close_reference.parquet` (raw 2389.2 vs adjusted 596.6 on 2019-05-15, ratio 4.005). The trade
is the engine doing what it is written to do on a legitimate gap-down open.

`max_risk_pct` is therefore a **ceiling on risk**, not a floor, and the stop construction has no minimum width.

## 3. Is the live path exposed?

**Yes in principle, no in the record to date, and the capped book escaped by cash, not by a guard.** Stated plainly:

- **The live cron's uncapped tracker (`out_all` in `scripts/run_bhanushali_cron.py`) is exposed.** It calls the same
  `R94.backtest(..., uncapped=True, a_grade=a_set, **LIVE_DISCIPLINE, ...)`: same fill rule, same stop line, no floor. Uncapped
  fills EVERY signal (`if (uncapped or notion <= cash)`), so a VMART-class fill is recorded the week it occurs, and its R feeds
  the SIGNALS-page analytics and any forward readout that averages R. Its dollar size is bounded (the 20% notional cap binds,
  see below) but its **R is not**.
- **The capped paper book is exposed to the position, not to the R.** A tiny stop makes the risk-based size enormous
  (`sh = sizing_eq * 2% / (en - st)`), and what saves the book is `max_notional_pct = 0.20`: `sh = min(sh, sizing_eq * 0.20 / en)`.
  That bounds the damage to 20% of equity times the adverse move (about -1% of equity for VMART's -4.8%), not a blow-up, but
  it also means the book would have **taken a full 20% position on a stop it could not honour in practice** (a 0.05 stop on a
  weekly-bar engine is a coin flip around the open).
- **The capped book did not take VMART only because it had no cash.** On 2019-05-06 the capped replay held 7 names with
  **cash 8,873 of equity 1,102,613**; a 20% VMART position needed about 220,500. It was refused by `notion <= cash`, which is
  luck of the calendar. The capped ledger's smallest risk is 1.8% (77 trades, worst R -5.4). There is no guard that would
  have refused it with cash in hand.
- **Guards that exist, and what each does not do.** `max_risk_pct` lifts wide stops only. `max_notional_pct` bounds size.
  `grade_a_entries(filter_before_rank=True)` (D6, gated off) drops only a **degenerate BAND** (`hi <= lo`), not a degenerate
  RISK inside a normal band (VMART's band was 676.69 to 704.18, 4% wide). `ext_cap` / `ext_floor` look at the SMA, not the
  stop. The card builder's `_record_stop` mirrors the engine line, so a card would print the same sliver stop.
- **Live record to date.** The 49 closed rows of `results/signals_history_weekly.json` run from -3.76R to +3.12R and the five
  paper positions carry stops at least 6.0% below entry: no live trade has been degenerate. Frequency in the train window is
  about 1 in 500 Grade-A fills (0.2%), roughly one per 5.5 years at the Grade-A set's size, so the live record is
  uninformative either way.
- **Sibling class.** The breakout-sleeve explore (`2026-10-20_hedge_and_breakout_sleeve.md`, PR #156) saw DEEPAKNTR
  2020-03-13 with a stop 0.5% below entry and R 218. That is the same missing floor with a different stop source (the box/S-R
  breakout stops); this branch cannot see that code path and has not re-run it.

## 4. The minimal fix, for the owner (NOT applied: production path, record-changing)

Production code is untouched. The smallest fix, gated so the golden masters stay byte-identical:

1. `backtest(..., min_risk_pct: float | None = None)` in `scripts/run_bhanushali_weekly_rank.py`, placed immediately after
   the `max_risk_pct` / `stop_widen_pct` lines and before `if en > st:`:
   `if min_risk_pct is not None and (en - st) < en * min_risk_pct: skipped_degenerate += 1; continue`
   (SKIP, not clamp: clamping the stop up to `en * (1 - 0.005)` would book a position the owner cannot replicate and would
   change R on a stop the signal never had). `None` leaves every existing run byte-identical, so `tests/test_r94_golden.py`
   and `tests/test_stage2_golden.py` pass unchanged.
2. Wire `min_risk_pct=0.005` into `LIVE_DISCIPLINE` only at an owner decision: it changes which trades the book takes in the
   historical record (it removes VMART, TECHM-class fills), so it is **tier 3** (a pre-registered trial at the review), not a
   defect fix that can ride in.
3. Regression test (new file, e.g. `tests/test_degenerate_stop.py`): a two-ticker synthetic `P` whose entry-week open is 0.01%
   above the signal-week low; assert (a) `min_risk_pct=None` produces the fill with `risk0/entry < 0.001` (pins today's
   behaviour), (b) `min_risk_pct=0.005` produces **no** fill and the ledger is empty, (c) a normal 7% stop fills identically in
   both modes, and (d) the same assertions through `uncapped=True`.

Until then the research guard is `nq.lab.stats.r_sanity_flags` / `exclude_degenerate_stops` (flag, never change the engine).

## 4b. Restated headline (full tables in the CORRECTION sections of findings 0148 and 0150)

Rule declared first (initial risk under 0.5% of entry is excluded; |R| > 20 is review-only), committed as `e3eae32`.
- **0148 uncapped arms** (VMART out): mean R closed -0.262 / -0.359 / -0.365 becomes **+0.621 / +0.478 / +0.467**; open-marked
  sum R 260 / 182 / 178 becomes 650 / 571 / 568. Delta R/yr (-14.36, -15.05) and the sub-period deltas are identical (VMART is
  -389.75R in every arm and cancels); the reading, BOUND RECORDED, does not change.
- **0150 Part 1** (3 trades out, 1,364 left): rank IC -0.004 becomes -0.008; top-5 minus rest +0.08R becomes +0.37R (CI -0.38 to
  +0.76); mean R by rank 1.29 / 1.56 / 1.15 becomes 1.29 / 1.03 / 1.15; 2019-21 edge -1.41R becomes -0.49R. The reading,
  NOT DISTINGUISHABLE FROM NOISE, does not change.
- The 2026-10-20 touch-depth note's "excluding trades below -5R the arms are indistinguishable" stands; this note names the one
  trade behind it and the rule that replaces the ad hoc -5R cut.

## 5. Limits

- One degenerate Grade-A trade, three in the all-grade set: the rule is declared from the mechanism (risk under 0.5% of entry),
  not tuned; no threshold between 0.06% and 1.2% would change which Grade-A trade is excluded.
- This measures the train window's uncapped ledgers. It does not say what a degenerate fill does to the live capital curve.
- The 0.5% threshold is a research flag, not a proposal for the live floor; the live value is the owner's decision.
