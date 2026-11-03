# Problem 1 — is the live loss regime, or is something broken? (2026-11-02)

**Class:** MEASURE (process tier 1, `docs/PROCESS_TIERS.md`). No pre-registration, no screen row, no
`n_trials` change. Standing counts: screens 23 · sealed opens 3 · n_trials 2. Train window only (prices cut
at 2024-06-30, asserted by `nq.lab.runs`); the sealed 2024-07-01..2026-06-30 slice is not read.

## Question

The live book lost 9.0% over 2026-07-06..2026-10-30 (MaxDD -13.9%) while the tracker closed 32 trades with
1 win and 31 losses (mean -1.26R). The Nifty fell 5.0% in the window and is about 15% off its January
high. Is that the signature of a trend-pullback book inside a correction, or is something broken?

## Verdict rule, committed BEFORE any number was computed

Fixed here; not revisited after the run.

**Episodes.** Nifty-50 drawdown from its trailing 252-session high >= 8% (primary) and >= 10%
(sensitivity), consecutive days merged into one episode (runs separated by fewer than 21 sessions are
merged). Episode start = first session at or beyond the threshold (the live book also began "inside" a
correction), end = last session at or beyond it.

**Comparison shape.** Primary = the equal-length window (116 calendar days, the live window) starting at
each episode's start, taken as a continuous slice of ONE live-config replay. Full-episode slices are
reported too, not used for the rule.

**Measures and the "inside the range" test**
- Book return: live (-8.96% on the 1,000,000 start) vs the capped book's window return in each historical
  episode. Inside = live is no lower than the worst historical episode.
- Win rate: live 1/32 closed (win = R > 0) vs the per-episode win rate of Grade-A signals (uncapped
  replay) entered in the window and CLOSED by the window end (the censoring-matched analogue of the
  tracker's closed-only record). Episodes with fewer than 10 such trades are shown but not used for the
  range. Inside = live is no lower than the lowest qualifying episode.
- Binomial: p = pooled closed-within-window win rate of uncapped Grade-A signals entered in primary
  episode windows; P(X <= 1 | n = 32, p). Pass if P >= 0.05.

**Verdicts**
- **REGIME** — live is inside the range on book return AND on win rate AND binomial P >= 0.05.
- **WORSE THAN REGIME** — live is outside the range on book return or win rate, or binomial P < 0.05.
  Then the next step is a defect hunt (universe/data drift, fills, stops), listed in the readout.
- **INCONCLUSIVE** — fewer than 3 episodes at the primary threshold, or fewer than 3 qualifying episodes
  for the win-rate range.

**Caveats fixed in advance.** Few episodes (each is one path). The live book trades the post-2026-10-16
universe union while research uses `corrected_universe`. 19 live winners are still open (mark-to-market
-0.27R), so the live closed record is biased toward losses; the censoring-matched win rate removes that
bias from the historical side. Signals in one window are cross-correlated, so the binomial (independent
trials) is optimistic about how surprising 1-in-32 is. Eventual-outcome win rates are reported as a
secondary column and are not used in the rule.
