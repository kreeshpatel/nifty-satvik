# Momentum-crash states: one episode, so no study (2026-10-13)

**Class:** MEASUREMENT on market data only. No trade outcome read, **no screen spent**, no trial.
Standing counts unchanged: screens 22 · sealed opens 3 · n_trials 2.

Daniel & Moskowitz (2016) locate momentum crashes in "panic states": a falling market (trailing 24-month
return below zero) with high volatility, followed by a rebound led by past losers. The swing book ranks
by relative strength, so the question "how does our book do after panic states?" is natural, and was
proposed on 2026-10-13. Before spending a screen on it, the states were counted
(`python pipelines/diagnostics/count_panic_states.py`):

- **Panic months since the data allows (≈2010 on):** 2020-03 to 2020-08. **One episode, COVID.**
- **Train window 2019–2024H1:** 6 of 66 months, all that one episode.
- **Now (Oct 2026):** trailing 24-month return −7.6%, so the bear half is on; 126-day volatility 11.8%,
  so the high-volatility half is off. **Not a panic state.**

**Reading:** a study of the book across one episode cannot separate a pattern from that episode. It is
underpowered by construction, so it is recorded here and not run. It becomes runnable only with more
episodes: an earlier data source (2008), or future ones.

**What this does tell the owner:** the classic crash risk for a relative-strength book is the *rebound*
after a high-volatility decline. Today's market is falling but not panicking. If volatility spikes and
the market then turns sharply, that is the regime where relative-strength picks have historically lagged
the index. That is a reason to watch, not a rule: the book's book-level vol-targeting response (0095)
was killed on this book.
