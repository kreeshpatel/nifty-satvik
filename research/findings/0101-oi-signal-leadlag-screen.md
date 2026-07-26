# Finding 0101 — OI signal lead-lag screen + knowledge import: timed hedge-triggers are exhausted (MEASUREMENT, 0 trials)

**Type:** MEASUREMENT / diagnostic — makes no PROMOTE/KILL decision on the honest base, so **no trial
spent** (n_trials stays 130). Harness `scripts/diag_oi_signal_screen.py`; data `data/options_oi_pit.parquet`
(now incl. put-skew, IV term-structure, VRP — `nq.data.options_oi`, PIT-tested). Knowledge digest
`.claude/skills/_ingested/options_oi_tailhedge.md` (sourced: Gao-Pan CIX, AQR, Universa, NSE WP-9, etc.).

## Question
After the 0100 coincident-IV hedge KILL, does **any** options-OI signal *LEAD* the swing book's drawdowns
(so a hedge could arm ahead), or is the whole timed-trigger avenue exhausted? Screened the full
evidence-backed zoo — PCR (level/z/Δ), ATM-IV (level/z/rise), **put-skew** (level/z/steepening, built from
the bhavcopy wings = the best-evidenced academic lead), **IV term-structure** slope, **VRP**, OI-buildup,
max-pain gap — against forward Nifty AND forward BOOK returns & drawdowns at 5/10/21/42/63d.

## Result — three hard reads
1. **No signal leads the BOOK's drawdowns.** The only non-trivial forward-drawdown IC is against **Nifty**
   (put_skew −0.14, IV −0.22 at 10-21d) — and it **washes out on the book (~0 to −0.08)**. Structural:
   the book's drawdowns are concentrated/idiosyncratic (4-5 momentum names); index-OI signals can't see
   single-name risk. An index hedge is the wrong shape for this book's actual DD (0100 failure-mode #2,
   now generalized across every signal).
2. **Every "stress" signal precedes RECOVERIES in returns.** put_skew AND IV both have **positive**
   forward-return IC (+0.11..+0.15) — high skew/IV → *higher* forward returns (vol-risk-premium /
   mean-reversion). This is *why* timed protection-buying is negative-EV (AQR: index puts "most expensive
   when most needed"). Confirmed now across skew, not just IV.
3. **Term-slope & VRP behave exactly as the literature predicts — as VETOS, not arms.** iv_term_slope has
   *positive* forward-DD IC (+0.16 Nifty: backwardation → *milder* forward DD, because it inverts during
   the stress); vrp_z top-decile → forward DD **+0.73pp better** than average. So high-VRP / backwardation
   = "the worst is already priced, do NOT buy protection here" — the filter that would have blocked 0100.
4. **Max-pain gap** is 78% price-trend and rated control/null by the literature — its residual +0.14 is not
   a robust lead.

## Conclusion
The **timed OI-hedge-trigger avenue is exhausted** for the swing book, triangulated three ways: our
measurement (no signal arms ahead of the book's DD; stress signals precede rebounds), the imported
knowledge (AQR negative-EV, put-spread truncates the tail, PCR/max-pain folklore), and our own priors
(0100 KILL; PCR dead-as-alpha; IC≠portfolio-Sharpe). **Do not pre-register another timed OI trigger**
(leading-PCR, skew-arm, IV-rise-arm) — the measurement pre-refutes them without spending trials.

## What survives (the ONE un-refuted construction)
The measurement kills TIMING, not continuous convexity. The knowledge's construction verdict — an
**always-on, small, deep-OTM put ladder with monetization on spikes** (Universa-style; keep convexity,
never a put-spread; use term-slope/VRP only to time *monetization*, never to arm) — is the single
un-refuted shape and finding-0100's option #3. Skeptical prior for THIS book (index hedge vs idiosyncratic
DD; AQR's negative-carry warning), but only a pre-registered backtest answers "does convexity beat its
drag here." That is the next owner decision: test the continuous ladder as one real trial, or bank the
data+knowledge as reusable assets and stop the hedge program on this book.

## Assets banked (reusable regardless of the decision)
- PIT NIFTY-option OI/PCR/IV/**skew/term-structure/VRP** series, 2359 days 2017-2026.
- Sourced tail-hedge/OI knowledge digest in `_ingested/`.
- The lead-lag screen harness (re-runnable on any future signal).
