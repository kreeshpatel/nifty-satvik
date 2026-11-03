# 2026-11-03 — Giveback: analysis, candidate solution, and the change map

**Tier:** EXPLORE (`docs/PROCESS_TIERS.md`). No screen row, no `n_trials` change, nothing changes live. Standing
counts: screens 24 · sealed opens 3 · n_trials 2. Builds on `2026-11-03_giveback_breakeven.md` (#166).
Any live change below is a CONFIRM-tier decision at the 2027-01-01 review, with its own pre-registration.

## The two problems, and their causes

| | problem | root cause in the rules |
|---|---|---|
| A | trade reaches +1R to +2R, never hits the target, finishes at a full −1R or worse | the stop never moves before +2R; it is checked on the Friday close and filled at Monday's open, so the loss is usually *beyond* −1R |
| B | trade books 40% at +2R, the other 60% falls back to a net loss | after the 2R tranche the stop on the remaining 60% stays at −1R |

A is structural (historically 92% of +1–2R peakers lose; live matches). B is rare historically (15 of 259) and
4 of 10 live, still open. Both are worse live because the falling tape (problem 1) makes fewer trades follow through.

## The candidates, measured three ways

Uncapped = per-trade book (does the rule make better trades?). Capped = the ₹10L capital book (one path,
≈0.2 Sharpe noise). Live = the rule replayed on the 50 live trades (2026-07-06..11-03, out-of-sample for every
rule here) with the live mechanics: Friday-close stop, Monday-open fill, resting 2R limit, open trades marked.
The live simulator reproduces the closed record (−40.9R simulated against −40.3R actual).

| rule | per-trade ΣR (history) | capped Sharpe / MaxDD (history) | live ΣR over 50 trades | fixes |
|---|---|---|---|---|
| live (no change) | 650 | 1.02 / −40.1% | −46.4 | — |
| **breakeven once +1R** | 632 (−3%) | **1.34 / −30.6%** | **−33.6** (+12.8) | A, and B's worst case |
| breakeven once +1.5R | 646 (−1%) | 1.26 / −34.2% | −39.8 (+6.6) | part of A |
| first 40% at +1.5R (not +2R) | 625 (−4%) | 1.24 / −38.1% | −44.1 (+2.3) | little |
| breakeven after +2R | 656 (+1%) | 1.15 / −32.3% | −42.3 (+4.1) | B only |
| entry +1R after +2R | 585 (−10%) | 1.30 / −33.3% | −36.4 (+10.0) | B, cuts runners |
| ladder: breakeven at +1R, +1R at +2R | 554 (**−15%**) | 1.49 / −36.1% | **−27.7** (+18.7) | A and B, cuts runners |

Reading:

- **Breakeven once +1R is the best-supported single rule.** It solves A directly, and because the stop is
  already at entry by the time a trade reaches +2R, it also removes B's worst case: a trade that reached the target
  can no longer finish below about breakeven (minus the Monday gap). Per trade it is a wash (−3%); it helps the
  capital book by freeing seats sooner, and it helped the live record most of the single rules.
- **The ladder helps more live but costs 15% of per-trade R in history.** Locking +1R after +2R stops runners
  that dip and then compound, which is where this strategy earns most of its money (0148). The live gain is from
  one regime with few runners. That is exactly the regime-fitting trap 0148 warned about.
- **Lowering the first target does little.** The trades that stall at +1–2R are not reliably reaching +1.5R either.
- **The common thread:** every rule that helps the capital book frees cash or seats sooner (D6, h5, throttle
  half-size, breakeven). Seat utilisation deserves its own direct measurement.

## Ensemble check (20 paired paths)

Reproduce: `python pipelines/diagnostics/explore_ensemble_breakeven_d6.py 20` →
`2026-11-03_ensemble_breakeven_d6.json`. Same draws for every config (cost ±10bp, start in the first 20 trading
days of 2019), reported 2019-03-01..2024-06-30 as continuous slices, PIT membership, prices cut at 2024-06-30.
Rule fixed before the run: robust only if the 5th-percentile paired ΔSharpe vs live is above zero.

| candidate | paired ΔSharpe median [5th, 95th] | paths better | ΔMaxDD median (pp, + = shallower) | reading |
|---|---|---|---|---|
| breakeven once +1R | +0.15 [−0.04, +0.35] | 85% | +1.6 | **inside path noise** (narrow miss) |
| breakeven once +1.5R | −0.01 [−0.21, +0.24] | 40% | +0.7 | inside path noise |
| D6 filter-before-rank | +0.04 [−0.06, +0.26] | 80% | 0.0 | inside path noise |
| h5 (caps off, scaled exit kept) | **+0.27 [+0.12, +0.71]** | 100% | −1.9 | **robust to path noise** |

Live book band: Sharpe 1.25 [1.03, 1.41], MaxDD −37.5% [−47.7%, −33.2%].

What this changes:

- **Breakeven once +1R is weaker than the single path said.** The +0.32 Sharpe and 9.5pp shallower drawdown of the
  one-path run were partly that path: the paired median is +0.15 and the drawdown gain shrinks to 1.6pp. It is
  better on 17 of 20 paths, but not on enough of them to clear the bar. It stays the best-supported fix for the
  giveback itself (live replay +12.8R, per-trade neutral), but **it is not a lead that earns a trial on these numbers**.
  The cheapest test that would change that: the forward record, logging what the rule would have done on each live
  trade from today (a shadow column, no live change).
- **D6 does not recover.** Two ensemble runs now put it inside noise (−0.06 on 2 paths, +0.04 on 20). Its
  +0.25 single-replay lead does not survive; the case for a 2027 trial is weak.
- **h5 holds at 20 paths** (+0.27, every path better) and is now the only candidate across both ensembles that
  clears the bar. It buys return, not drawdown (median MaxDD 1.9pp deeper). It is the strongest pre-registration
  candidate for the 2027-01-01 review. In-sample, with a ≈0.59 statistical half-width on top of path noise.

## The change map (if breakeven-at-+1R is adopted at a review)

After the ensemble, the recommended order is: ship row 4 (card shows the real stop) as a fix on its own, add the
breakeven rule as a **shadow column** on the forward record, and decide at the review with forward evidence.

| # | change | where | note |
|---|---|---|---|
| 1 | Pre-registration of the rule and its pass criteria, before any further run on it | `diagnostics/research/preregistry/`, screen ledger, `forward/prereg_swing.md` (owner) | CONFIRM tier; thresholds fixed in advance |
| 2 | Effective-date gate: the rule applies only to entries on or after an effective date | engine `backtest()` (new cfg key), `scripts/run_bhanushali_cron.py` (`LIVE_EXIT_EFFECTIVE`) | **required**: history is rebuilt from inception every scan, so without it the four-month live record would be silently re-priced (same failure class as the ADR-0017 retroactive entrants) |
| 3 | Live exit config | `scripts/run_bhanushali_cron.py:178` `P_EXIT['scaled_exit']` += `lockin_mfe=1.0, lockin_at=0.0` | the lever already exists (0148); no new engine logic |
| 4 | Card shows the stop the engine is actually using | `scripts/run_bhanushali_cron.py:606` and `:656` read `p["trail"]` once `half_done`, which in the scaled exit is still the original stop | **must ship first**: otherwise a raised stop never reaches the owner's screen. Use `p["stop"]` on the scaled branch |
| 5 | Card instruction: "move your stop to entry once price reaches +1R (Rs X)" and a `stop_at_breakeven` flag in `exit_stage` | `_exit_plan` / `_exit_stage` in the cron; the Signals card in the frontend | the owner executes on their own broker; the rule only works if the card says it |
| 6 | Manifest and replay parity | `nq/runner/manifest.py` `_live_scalars`, `tests/test_replay_parity.py` | so "LIVE BOOK" labels keep meaning the live config |
| 7 | Golden master | `tests/test_r94_golden.py` uses `LIVE_EXIT`, so it changes by design | governance re-pin (`/re-anchor`), an owner decision |
| 8 | ADR and the forward wall | `docs/decisions/`, signal-quality forward wall | the forward record must say which exit each trade ran under |

Already done in this branch (research only, off by default, goldens byte-identical): the `lockin_ladder` lever
(`scaled_exit.lockin_ladder`, several stop-raise steps) and its tests (`tests/test_stop_ladder.py`).

## Not covered here

The Monday-open gap-through (diagnosis problem 2) makes every stop, including a breakeven one, fill worse than its
level. A daily protective stop (`hard_stop` / `disaster_floor_pct`, already gated in the engine) is the separate
test for that.
