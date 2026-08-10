# forward/prereg_swing_A1.md — certifying the configuration that actually trades

**Status:** PRE-REGISTERED — written and committed **before** the run
**Date:** 2026-08-10
**Class:** **MEASUREMENT.** `n_trials` stays at **2** and is not incremented.
**Amends:** `forward/prereg_swing.md` §1. That document is not edited in place — it is a
pre-registration whose run has reported, and editing it after the fact removes the only thing that
made its result worth anything. This file stands alongside it as a dated companion, per §10's
tighten-or-clarify-only rule.
**Reproduce:** `python pipelines/diagnostics/diag_certify_live_config.py`

---

## 1. Why this exists

`forward/prereg_swing.md` §1 certifies **base-swing**: Sharpe 1.132 / CAGR 24.7% / MaxDD −42.4% /
DSR 0.894 at n_trials 114, all grades, no discipline levers, no scaled exit.

**That is not what runs.** The Saturday cron trades A-only with `LIVE_DISCIPLINE`, `LIVE_EXIT`
(config P) and `LIVE_STALENESS` (`scripts/run_bhanushali_cron.py:86,106,115`). That configuration has
**no DSR, no bootstrap CI, and no PBO row** — `pipelines/diagnostics/diag_pbo_cscv.py` sweeps 17
configs, every one a single-lever variant, and the live combination is not among them. The only
numbers ever recorded for it (`models/bhanushali_weekly/config.json → live_backtest_discipline`,
Sharpe 1.055) were produced under a **different exit** than the one running.

So the book carrying the owner's paper capital, and now designated the destination book, is certified
by nothing. This measures it. It does not change it.

## 2. Why this is a MEASUREMENT and not a trial

`diagnostics/research/n_trials.json` defines a trial as *"one independent strategy configuration
evaluated for a PROMOTE/KILL decision"*, and its ENG-01 entry records the sharper test: **multiplicity
comes from the OPTION TO ADOPT, not from how many values are tried.**

There is no option to adopt here. The configuration is **already adopted and already carrying
capital**. Measuring what is already running cannot be a selection among alternatives, because there
is no alternative in the frame. Direct precedent: finding 0025 ran the survivor-vs-corrected axis on
this book and was classified MEASUREMENT with no `n_trials` cost.

**The constraint that keeps this honest, and it is binding:** exactly **ONE** frozen configuration,
run **once**, no variants, no sweep, no neighbourhood. Measuring a *second* configuration for
comparison-with-intent-to-swap would be a trial, and would require incrementing the counter before
the run. If this document is ever used to justify running a second arm, it has been misused.

## 3. The configuration — every parameter fixed here

Taken verbatim from the live cron, not restated by hand:

| | value | source |
|---|---|---|
| grading | A-only (top-5 CRS per ISO week) | `run_bhanushali_cron.py:750,753` |
| discipline | `ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20` | `LIVE_DISCIPLINE` `:86` |
| exit | config P — 40% @ 2R · 40% blow-off pattern @ 2.5R · 20% runner to the 44w SMA | `LIVE_EXIT` `:115` |
| staleness | `stale_absent_days=10` | `LIVE_STALENESS` `:96` |
| universe | `corrected_universe()` — pinned cache + backfill + alias map | `run_bhanushali_path1.py:26` |
| capital | `EQ0` = ₹10,00,000 | `run_bhanushali_faithful.py:27` |

## 4. The two choices that must be fixed before the run, because both move the answer

**4a. End date — PRIMARY is 2025-12-31.**
Measured 2026-08-09 (`diagnostics/research/end_of_sample_stub.json`): **28.0% of the live book's
final equity at 2026-06-29 is an unrealised `eos` mark** on 9 positions force-closed at the last
bar, and the headline swings 25.02% → 27.17% CAGR and 1.201 → 1.279 Sharpe purely on where the clock
stops. Certifying against the full window would bake a 28% unrealised stub into the certification.

**2025-12-31 is the primary because it is the most recent full calendar year end and excludes the
thinnest, least-audited stretch.** The full window is reported as a secondary line, never as the
headline. A certification carries its end date the way a DSR carries its trial count.

**4b. Trial count — the gate reads the CERTIFIED 114.**
`CERTIFIED_N_TRIALS = 114` (`run_bhanushali_weekly_rank.py`, pinned in commit 66d1475). DSR is also
reported at the live count (2) and the lifetime count (140), because each answers a different
question. **The gate reads 114**, so the live config is judged against the same bar base-swing was.

## 5. What will be measured

Net of costs, on one continuous run, with sub-periods as **continuous slices** of that run and never
a fresh-capital re-run:

- Sharpe, CAGR, MaxDD, Calmar, trades, win rate
- Block-bootstrap 95% Sharpe CI (block 63, 5,000 samples, seed 12345)
- DSR at n_trials 114 / 2 / 140
- The three registered sub-period slices, and the 2022-26 gate
- Per-calendar-year returns, gross and after tax
- After-tax CAGR (STCG 20%, paid annually out of the book)
- A PBO/CSCV row for the live combination, added as an 18th config to `diag_pbo_cscv.py`

## 6. Pre-committed outcome table

There is no PROMOTE/KILL here — nothing is being adopted. These are descriptive states, and which one
obtains is decided by the numbers, not re-read afterwards.

| outcome | condition, fixed now | what follows |
|---|---|---|
| **CERTIFIED-EQUIVALENT** | DSR > 0.95 at n_trials 114 **AND** bootstrap CI low > 0 **AND** all three slices > 0 | the live config may be quoted as certified, with its end date and trial count attached |
| **UNCERTIFIED, BOUNDED** | any gate above fails | record which, with numbers. **Disposition unchanged** — the book keeps trading on the owner's recorded override, but the override is now quantified rather than assumed |
| **DEFECT SIGNAL** | any headline differs from the recorded `live_backtest_discipline` numbers by more than **0.15 Sharpe** or **3pp CAGR**, unexplained by the exit difference | stop. Route to `red-team` before the number is used anywhere |

**The 2022-26 slice is pre-declared as not resolvable.** Config P scores 0.91 against a 1.04 bar
(`docs/decisions/0010-swing-config-P.md:41`). That −0.13 miss is roughly **one fifth** of the ±0.59
dSharpe half-width on this data. The correct output is *"misses its pre-registered slice gate by an
amount the instrument cannot resolve, and is uncertified"* — **recorded, not litigated.** No argument
about whether −0.13 is "close" is admissible; the instrument cannot tell −0.13 from zero.

## 7. What would make this wrong

- **The reconstruction is not the live book.** Guard: parity assertion against the numbers already
  committed in `pipelines/research/mc_year_on_year_P.py` — 130 trades / 27.2% CAGR / −39.5% DD on the
  full window. If parity fails, the run is void and nothing is reported.
- **The eos stub reappears at the new end date.** Report the unrealised share at 2025-12-31 too; if
  it is comparably large, the end-date choice has not solved the problem and must be said so.
- **`scaled_exit` dead-codes 16 levers** via the `continue` at `run_bhanushali_weekly_rank.py:674`,
  including the whole context-router. Any PBO row for this config is measuring a configuration where
  those levers are inert. Footnote it; do not silently compare against rows where they are live.

## 8. What this cannot do

It cannot promote, demote, or re-grade anything. `forward/prereg.md` §8 confines every promotion,
demotion, degradation and fork decision to a quarterly review date. **The next is 2026-10-01.** This
document produces the input that review has never had; the decision remains the owner's, on the date.

## 9. Refusal clause

If the result is unfavourable it is recorded as-is. The configuration is not re-tuned, no neighbouring
cell is run "to check", and no threshold in §6 is revisited. UNCERTIFIED is a first-class outcome and
is the expected one.
