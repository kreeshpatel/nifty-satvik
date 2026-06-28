# Pre-registration 0052 — News safety-veto (A1)

**Date:** 2026-06-19
**Track:** A (AI decision bridge) — forward-validated, NOT backtestable
**Status:** SHADOW (logging would-block; no live routing change)
**Holdout type:** forward-wall only (no PIT news corpus exists; a backtest of news would be a lie)
**n_trials:** NOT a backtest trial — does not increment `n_trials.json` (no trade decision against
the locked base until the forward gate fires; consistent with the "measurement, not trial" rule).

## Hypothesis
A narrow, asymmetric **safety veto** on the news sentiment the cron already computes (and discards) at
Step 5.5 will, over a forward sample, BLOCK signals whose names go on to **underperform** the taken
signals — without materially shrinking the book (the binding constraint is signal scarcity, not slots).

## Why veto-first (asymmetry, C4.1)
A false block costs one missed trade on a ~27%-deployed book (near-zero marginal cost). A false add risks
capital on an unvetted thesis and, in India, fights an *inverse*-signed sentiment prior. So the veto needs
far less evidence to deploy than an overlay. A1 can ONLY block; it can never add or up-size.

## The rule (FROZEN — see src/strategies/news_veto.py)
BLOCK an emitted signal iff **all** hold:
1. `headlines_used >= 1` (a real headline drove the score), AND
2. `score <= -0.70` (the model's own prompt reserves the −0.7..−1.0 band for "regulatory actions, fraud,
   SEBI investigations"), AND
3. the `risk + reason` free-text matches a frozen **hard-event** keyword set (fraud / SEBI-probe /
   regulatory / insolvency / default / auditor-resign / trading-halt / delist / ED / CBI / …).

PASS otherwise. **Both 2 AND 3 are required** — this is the India inverse-sign guard: a merely-bearish
score never blocks (only hard EVENTS do), and a stale/rumored event with a mild score never blocks.
Fail-open on any malformed/empty/no-news input.

## Primary metric (ONE) + frozen decision rule
**Primary:** forward 14-trading-day realized return of would-block names vs taken (non-blocked) names,
graded once each window closes via the `ai_sector_scorecard`-style forward machinery.

**PROMOTE (shadow → active veto) iff ALL:**
- **≥ 20 distinct would-block events** accrued (power floor; below this it can never signify), AND
- blocked names' mean forward 14d return is **below** taken names' by a margin whose bootstrap
  95% CI-low is **> 0** (i.e. blocking genuinely avoided losers, not noise), AND
- the implied book shrinkage is **≤ ~5%** of emitted signals (a veto firing on >5% of signals is
  not a rare hard-event filter — it is mis-specified), AND
- **skeptic-agent clearance** (overfit-skeptic + flaw-hunter): no leakage (post-dated headlines), the
  keyword set didn't silently widen, the events are real and India-related.

**KILL iff:** after a full forward year either the event count never reaches 20, or the CI straddles 0,
or shrinkage exceeds the cap. Honest KILL outcome = "the discarded news had no actionable safety edge;
the discard was correct," recorded as such.

## Kill risks (pre-stated)
- **Sparse Nifty-500 news coverage** (the 0006 earnings-coverage failure) → too few events to ever signify.
- **Noisy Haiku risk labels** → audit a sample of would-block events before any promotion.
- **India inverse-sign** → mitigated structurally by requiring a hard EVENT, not polarity.
- **Sample starvation** → expect months, not weeks; this is the single most likely killer.

## What ships now (shadow)
- `src/strategies/news_veto.py` (pure, fail-open) + `tests/test_news_veto.py`.
- `news_veto_enabled: false` in `models/v1/config.json` (flag-gated, default OFF).
- Cron Step 5.5 appends each emitted signal's verdict to `results/news_veto_shadow.jsonl`
  (`would_block`, score, matched_keyword, ticker, date) — **zero routing change**.
- Golden-master byte-identical (no engine path touched).

## Revisit
90-day decay re-measure pre-registered (sentiment alpha decays fast — C1.4).
