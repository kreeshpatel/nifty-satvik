# 0148 — The giveback ratchet under the live exit: no edge, and the sign depends on the regime

**Class:** activation bound, screen ledger row 21. **No trial.** Standing counts: **screens 21 · sealed
opens 3 · n_trials 2.** Pre-registration: `diagnostics/research/preregistry/0148-giveback-ratchet-bound.md`
(committed `3fbb020`, before the lever or the diagnostic existed). Reproduce:
`python pipelines/diagnostics/diag_giveback_ratchet_0148.py` → `diagnostics/research/giveback_ratchet/result.json`.

## Question

Seven of the live book's 19 losers rallied to between +1.09R and +1.83R before reversing to a full stop.
The forensic study had already shown blunt fixes lose and found one surgical one, the giveback ratchet
(stop to entry + 1.5R once MFE reaches 2.5–2.75R), worth +0.02R on the older half-book exit. Under the
live scaled exit the engine's ratchet lever was unreachable, so it had never been measured on the exit
the book trades. Does it help there?

## Result

Train 2019-01-01 to 2024-06-30, prices cut before the engine saw them (last bar 2024-06-28); live
configuration otherwise unchanged.

| book | arm | fired | Δ R/yr (open marked) | Δ CAGR | Δ Sharpe | Δ MaxDD |
|---|---|---|---|---|---|---|
| capped | 2.75 → 1.5 (primary) | 44 | **+0.08** | −1.09pp | −0.011 | +1.25pp |
| capped | 2.50 → 1.5 | 49 | −2.79 | −1.30pp | −0.035 | +1.25pp |
| uncapped | 2.75 → 1.5 | 319 | −6.00 | — | — | — |
| uncapped | 2.50 → 1.5 | 337 | **−14.98** | — | — | — |

**Reading, as pre-committed: BOUND RECORDED, no trial.** Every arm is inside or below the ±10 R/yr floor,
none is positive in both sub-periods, and the equity measures (CAGR, Sharpe) are negative in both arms.

## What the ratchet does

It raises the win rate (capped 47.9% → 56.8%) by locking +1.5R on trades that would have given back, and
lowers mean R (+1.86 → +1.81 primary, +1.44 robust) by stopping runners that would have gone further.
Under the scaled exit the two cancel: the exit already books 40% at +2R and 40% on a blow-off top, so
the giveback the ratchet targets is mostly already taken.

**The effect flips with the regime**, which is why it cannot be an edge:

| capped book | Sharpe 2019–21 | Sharpe 2022–24H1 | MaxDD 2022–24H1 |
|---|---|---|---|
| base | 2.10 | 1.02 | −29.9% |
| ratchet 2.75 → 1.5 | 1.60 | 1.70 | −16.9% |

It costs in the trending market and helps in the choppy one. Choosing it on the second sub-period
would be fitting the regime after seeing it. A regime-conditional ratchet would be a new rule with
its own pre-registration, and it would run into the regime findings (program-laws) first.

## Corrections folded in before writing (red-team, 2026-10-13)

- **The closed-only R sum was censored.** Trades still open at the cut carry most of the R (capped base:
  +50R of 182R; uncapped: +618R of 922R), and the ratchet closes trades the base leaves open. The first
  readout (+0.31 / −4.65 / +0.24 / +0.96 R/yr) understated the cost. The table above marks open trades at
  the cut; the closed-only figures stay in `result.json` as `delta_R_per_yr_closed_only_censored`.
- **The equity curve is the better measure** when arms differ in trade count (81 vs 85). It agrees in
  sign with the marked R sums.
- The red-team re-ran the diagnostic independently and reproduced every figure. It confirmed that the
  lever implements the frozen rule, that no data after 2024-06-30 reached the engine, and that the null
  is not a no-op: the lever fires on 44–337 trades and moves win rate and trade count.

## Limits

- The base book's absolute level (capped CAGR 39.4%, Sharpe 1.67 on a bull-heavy train window) is **not
  certified here**; only the deltas are read.
- Sub-period R deltas are summed by entry year; Sharpe and MaxDD are continuous slices of one run.
- Few independent windows: in the capped book, 2019–20 carries almost all of the base R.

## What this closes, and what it does not

- **Closes (current harness, live book):** the giveback ratchet as a standalone edge on the scaled
  exit. Cite as `BOUND (2026-10-13, live scaled exit)`.
- **Does not close:** a regime-conditional exit. That is a separate question with its own gate.
- The breakeven-at-+1R idea was deliberately **not** run: it is a blunter member of the family the
  forensic already priced, and this result gives no reason to expect a blunter version to do better.
- The engine lever stays in, off by default (`a0242a9`), so the measurement is reproducible.
