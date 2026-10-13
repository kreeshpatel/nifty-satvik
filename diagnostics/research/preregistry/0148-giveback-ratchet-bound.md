# 0148 — The giveback ratchet under the live exit: activation bound

**Class:** ACTIVATION BOUND (verdict-machine Gate 3). **No trial.** Screen ledger row **#21**, appended
**before** this runs. Standing counts at registration: **screens 20 → 21 · sealed opens 3 · n_trials 2**.
**Registered:** 2026-10-13, before the engine lever or the diagnostic exists.

## Why now

The live book's 19 closed trades are all losers, and 7 of them rallied to between +1.09R and +1.83R
before reversing to a full stop (measured 2026-10-13 against Yahoo daily highs). The owner asked what
could reduce that.

## What is already answered, and is NOT being re-asked

`research/losers_analysis/FORENSIC_FINDINGS.md` measured the giveback on the touch44 book and priced the
blunt fixes, all of which lost per trade: **trail-before-2R +0.185R vs base +0.481R** (win 59 → 42%),
**lock 2.0→1.0 +0.410R**, tp-on-high +0.322R. The mechanism: the book's R is carried by a few runners
past 4R, and an early stop raise cuts them. A **breakeven-at-+1R** stop is a blunter member of the same
family and is **not** run here. The stop axis (0105 tighten, 0106 widen, 0109 disaster floor) stays
closed and is not re-opened.

The same file found **one** improvement: the **giveback ratchet** — raise the stop to entry + 1.5R only
once intraweek MFE reaches 2.5–2.75R. It improved every metric and both sub-periods, but by **+0.02R /
+0.04 Sharpe**, below the promotion bar, and was parked as a forward-wall candidate. That verdict is
`PARKED (pre-scaled-exit epoch, base book) — not re-tested under the current harness`.

## What is new

Exactly one thing: **the exit it is measured against.** The live book now runs the scaled exit (config P:
40% at +2R, 40% on a blow-off pattern armed at +2.5R, 20% runner on the 44-week SMA). The ratchet was
measured on the older half-book exit. In the engine, the `lockin_mfe` lever sits after the scaled-exit
branch's `continue`, so **under the live exit it is inert** — the ratchet has never been measured on the
exit the book actually trades. This study adds it to the scaled branch, gated off by default, and
measures it there.

## The rule (frozen)

Inside the scaled-exit branch, after at least one week held: once the week's high puts MFE at or above
`lockin_mfe` R (on the initial risk), the stop becomes `max(stop, entry + lockin_at × initial risk)`.
It then fires on the engine's existing convention — **weekly close at or below the stop, filled at the
next session's open** — exactly as the base stop does. No other exit is touched.

| arm | lockin_mfe | lockin_at | role |
|---|---|---|---|
| base | off | — | control, the live config |
| **primary** | **2.75** | **1.5** | the prior study's best |
| robustness | 2.50 | 1.5 | the plateau's other edge |

No other value is run. The two arms are reported together; neither is chosen after the fact.

## Population and window

The live configuration exactly (`LIVE_DISCIPLINE`, `LIVE_EXIT`, `LIVE_STALENESS`, demerger events,
Grade-A set), on `run_bhanushali_path1.corrected_universe()`, **price data cut at 2024-06-30** before
the engine sees it, start 2019-01-01. The sealed 2024H2+ slice is never loaded, so it cannot be read.
Positions still open at the cut are marked at the cut and labelled. Two books, both reported:

- **capped** — the ₹10L capital book (`out_paper`'s configuration): Sharpe, MaxDD, CAGR, sum of R;
- **uncapped** — every A signal (`uncapped=True`): per-trade mean R, the population the prior study used.

## Pre-committed reading

- **Activation:** how many trades the ratchet fires on, and how many change outcome.
- **The bound:** Δ(sum of closed-trade R) per year on the capped book against the **±10 R/yr path-noise
  floor** (0109), with the per-year sign and both sub-periods (2019–21, 2022–24H1).
- **Below the floor, or wrong-signed → recorded as a bound, no trial.** That is the expected outcome given
  the prior +0.02R, and it is a complete result.
- **≥ +10 R/yr AND positive in both sub-periods → eligible to be proposed as a pre-registered trial at
  a quarterly review.** Nothing is adopted from this study, and no live config changes.
- ΔSharpe is reported with the standing caveat: n_eff ≈ 37 independent 63-day windows, half-width ≈ 0.59.

## Reproduce

`python pipelines/diagnostics/diag_giveback_ratchet_0148.py` → `diagnostics/research/giveback_ratchet/result.json`.
