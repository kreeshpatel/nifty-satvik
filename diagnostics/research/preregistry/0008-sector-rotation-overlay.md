# 0008 — Sector-rotation overlay (allocation, not feature)

- **ID:** 0008
- **Registered:** 2026-06-03
- **Holdout:** unseen-universe → forward-wall. No retrain (post-model allocation rule).
- **n_trials (cumulative):** ~54.
- **Status:** PENDING

## Motivation

0002 proved sector momentum is a REAL signal (rank-IC 0.09; top-bottom +1.05%/mo,
t=2.75) but KILLED it as a per-stock *feature* (redundant with per-stock momentum +
rs_rank). The unresolved question: is it harvestable as an *allocation overlay* —
i.e. among the stock-picker's signals, do those in top-momentum sectors realize
better outcomes, so tilting toward / filtering for strong sectors lifts the
picker's risk-adjusted return?

## Hypothesis

Among the model's BUY signals, those whose sector is in the top-momentum half on
the signal date realize materially higher after-cost expectancy / Sharpe than
those in the bottom-momentum half; a sector tilt (drop or down-size bottom-sector
signals) improves the picker's Sharpe without collapsing trade count.

## Primary metric

**Delta in Sharpe** of the sector-tilted signal set vs the untilted set, on the
unseen universe (the thesis is risk-adjusted/allocation, so Sharpe is primary).
Secondary: per-trade after-cost of top-momentum-sector vs bottom-momentum-sector
signal buckets (with CIs); trade-count retention.

## Decision rule (fixed in advance)

- **SUPPORT:** top-sector signals' per-trade CI lower bound ≥ bottom-sector point
  AND a tilt lifts Sharpe with ≥80% trade-count retained AND DSR>0.95.
- **KILL:** no top-vs-bottom difference (sector momentum redundant even as an
  overlay — long-only picks already cluster in strong sectors).
- **INCONCLUSIVE:** overlapping CIs.

## Priors

Skeptical: 0002 showed the signal is redundant for *selection*; a long-only
momentum picker likely already concentrates in strong-momentum sectors, so the
overlay may add nothing. But the mechanism (allocation vs feature) is genuinely
different — worth the cheap, no-retrain test before the expensive delivery% build.

## Result (2026-06-03) — INCONCLUSIVE (coverage-limited); no benefit observed

Ran the tilt on the unseen universe (`run_0008_sector_overlay.py`):
- Untilted: 355 trades, +4.22%/trade, Sharpe 2.858.
- Tilted (drop bottom-half-momentum-sector signals): 350 trades, +4.16%, Sharpe 2.791.

**Methodological limitation (flagged, not papered over):** the unseen smallcaps are
NOT in `SECTOR_MAP` (it maps only the Nifty 500), so `get_sector` returns "Others"
for most of them — only **28 of 355 trades** could be tagged with a sector, and the
tilt therefore dropped just 5 trades. The top-vs-bottom buckets (top n=20 +4.9%/70%WR
vs bottom n=8 +7.1%/100%WR) are tiny, unreliable, and show no top-over-bottom effect
(if anything the reverse, on noise).

**Verdict: INCONCLUSIVE on the unseen universe (coverage-limited); the tilt showed
no Sharpe benefit (2.86→2.79).** A clean test would need the unseen tickers
sector-mapped (or an in-sample training-universe run, contaminated). Given 0002's
clean KILL of sector momentum as a feature + the skeptical prior (long-only momentum
picks already cluster in strong sectors), the overlay-on-the-picker is low-value to
pursue further. Net for the whole sector thread: the +1.05%/mo sector momentum is
real but harvestable only as a STANDALONE sector-rotation product (long-short across
sectors), not as an enhancement to the per-stock picker (neither feature nor tilt).
Status: **CLOSED — overlay no-benefit/coverage-limited; sector edge = separate product.**
