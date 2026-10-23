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


---

## CORRECTION 2026-10-13 — the run above measured the wrong book

**Nothing above this line is edited; it stands as measured, and it is superseded here.**

The pre-registration specifies "the live configuration exactly". The run above passed no index membership
to the engine, so its book could buy names outside the Nifty-500 on the date. The live cron gates every
fill on point-in-time membership. Found while building the Strategy Lab (#142): on the same window the
ungated book reads Sharpe 1.666 / CAGR 39.4%, the live, gated book **1.025 / 20.5% / MaxDD −40.1%**. The
original result is kept as `diagnostics/research/giveback_ratchet/result_membership_off.json`; the
diagnostic now passes `load_membership()` and `result.json` is the corrected run.

### Corrected result (live book, train 2019 to 2024H1)

| book | arm | Δ R/yr (open marked) | Δ Sharpe | Δ CAGR | Δ MaxDD |
|---|---|---|---|---|---|
| capped | 2.75 → 1.5 | −0.50 | +0.16 | +3.1pp | 5.7pp shallower |
| capped | 2.50 → 1.5 | +7.26 | +0.47 | +11.9pp | 5.8pp shallower |
| uncapped | 2.75 → 1.5 | −14.36 | — | — | — |
| uncapped | 2.50 → 1.5 | −15.05 | — | — | — |

**Reading, as pre-committed: still BOUND RECORDED, no trial.** Neither arm reaches +10 R/yr with a positive
sign in both sub-periods (the robust arm's 2019–21 is −0.62).

**What changed in the interpretation.** On the live capped book the ratchet now improves the equity
measures, which the ungated run did not show. The uncapped book, the clean per-signal effect, says the
ratchet **cuts runners**: open-at-mark R falls from 260 to 181. The capped gain comes from the equity path
(more trades recycling cash, 90/88 against 77, and a shallower drawdown), not from better trades, and
+0.16 / +0.47 Sharpe sits inside the ≈ 0.59 half-width. A second red-team pass confirmed the reading and
found runner truncation a better explanation than pure capital recycling.

**What it closes, restated:** the giveback ratchet as a per-trade edge on the live exit. Its effect on the
capped book's equity path is not separable from noise on this window, and is not a licence to adopt it.


---

## CORRECTION 2026-10-23 — degenerate-stop outliers in the uncapped arms

**Nothing above this line is edited; it stands as measured. Tier 1 re-run, no new screen row; standing counts
(read from the ledgers by the script): screens 23 · sealed opens 3 · n_trials 2.** Reproduce:
`python pipelines/diagnostics/diag_degenerate_stop_restate_2026_10_23.py` →
`diagnostics/research/degenerate_stop/result.json`. Cause, exposure and the proposed engine fix:
`diagnostics/research/explore/2026-10-23_degenerate_stop_outlier.md`.

**The rule, declared before any restated number** (`nq.lab.stats.exclude_degenerate_stops`, commit `e3eae32`): a trade
whose initial risk (entry − stop0) is under **0.5% of entry** is a degenerate stop, and its R-multiple measures the sliver,
not the trade; it is excluded. |R| > 20 is a review flag only and is **not** excluded (real compounders live there).

**What was wrong.** One trade in the uncapped Grade-A ledger, **VMART entered 2019-05-06**, has entry 676.74 and stop 676.69
(initial risk 0.0074% of entry) and books **−389.75R** for a roughly −4.8% loss. The engine fills any entry-week open inside
the signal-week band, sets the stop at the signal-week low, and `max_risk_pct` only lifts a *wide* stop, so a gap-down open
a few paise above the low is a legal fill with near-zero risk. It is in every uncapped arm (same fill, same −389.75R in
base, 2.75 → 1.5 and 2.50 → 1.5). It never reaches the capped book (smallest capped risk 1.8%, worst capped R −5.4; no
capped arm has a degenerate trade). It is the **only** uncapped Grade-A trade under 0.5%.

**Reproduction check.** The raw re-run reproduces the committed `result.json` `sum_R_incl_open_at_mark` for all three
uncapped arms to 1e-6.

### Restated uncapped arms (VMART excluded; 525 / 544 / 547 trades)

| arm | mean R closed, as published | mean R closed, restated | open-marked ΣR, as published | restated | win % |
|---|---|---|---|---|---|
| base | −0.262 | **+0.621** | +260.4 | **+650.2** | 42.8 → 42.9 |
| 2.75 → 1.5 | −0.359 | **+0.478** | +181.6 | **+571.3** | 45.5 → 45.6 |
| 2.50 → 1.5 | −0.365 | **+0.467** | +177.8 | **+567.5** | 45.2 → 45.3 |

Median R is unchanged (−0.65 / −0.58 / −0.60): the published **sign of the mean R was the outlier**, not the trades'
typical outcome. The 2019 R-by-year of the base arm moves from −341.1 to +48.6.

| uncapped Δ vs base | Δ R/yr (open marked), published → restated | Δ mean R, published → restated | Δ R by sub-period (2019–21 / 2022–24H1) |
|---|---|---|---|
| 2.75 → 1.5 | −14.36 → **−14.36** | −0.097 → **−0.143** | −77.94 / +26.23 (unchanged) |
| 2.50 → 1.5 | −15.05 → **−15.05** | −0.103 → **−0.154** | −80.15 / +24.65 (unchanged) |

### Does the reading change?

**No.** The pre-committed bound, **BOUND RECORDED, no trial**, is unchanged, and so is the interpretation that matters: the
ratchet **cuts runners** in the per-signal book. VMART carries the identical −389.75R in every arm, so it cancels in every
**difference** the bound is built from (Δ R/yr and the sub-period deltas are identical to the cent); it only distorted the
**levels**. Delta mean R becomes more negative once the divisor stops absorbing a −390R hole (−0.10 → −0.14 and −0.10 → −0.15),
the same sign and reading. The capped-book rows of this finding (Sharpe, CAGR, MaxDD and capped Δ R/yr) contain no degenerate trade
and are untouched. Any citation of the uncapped base book as "mean R −0.26 / closed ΣR −116" should read **+0.62 / +274**.

**Limit.** One trade, so this corrects the level of the uncapped means and leaves the ratchet verdict as it was. The
sensitivity that also drops |R| > 20 trades is in `result.json` and is not the declared rule.
