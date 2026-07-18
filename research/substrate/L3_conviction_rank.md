# L3 — conviction fill-ranking: KILLED (measurement, no trial)

**Run 2026-07-16.** Reproduce: `python scripts/diag_conviction_rank.py`. Live config untouched.

## The premise (owner's insight — and it was well-founded)

The live book **activates 6,359 entry windows and funds only 168 — a 2.6% selection ratio** — skipping
**19,728 signal-days** for lack of cash while holding ~7 names ~100% of the time. So WHO gets the scarce
capital is the dominant decision, and the only change that ever improved this book (finding 0094) was
exactly a fill-ordering change (CRS-rank). This tests replacing CRS-rank with a **trained multi-feature
conviction score** — the registry's last cleared in-sample lever (L3). Non-diluting by construction: the
trade SET is unchanged, only the ORDER.

## Design (clean OOS)

Ranker trained on **2019-2021 only** (N=610 labelled touch windows, from the uncapped run so every signal
has an outcome), judged on the **2022-26 continuous slice** it never saw. Features (all from the completed
signal week, PIT-safe): `crs_dist, ext_sig, risk_frac, slope44, atr_pct, vol_ratio, dist_52wh`.

## Result — the ranker is anti-predictive out-of-sample

| | AUC |
|---|---|
| train (2019-21, N=610) | 0.889 — pure overfit, ignore |
| **OOS (2022-26, N=1708)** | **0.472** — **worse than random** |

| config | trades | Sharpe | CAGR | MaxDD | **22-26** |
|---|---|---|---|---|---|
| A CRS-rank (live baseline) | 168 | 1.03 | 21.2% | −34.8% | **1.29** |
| C CONVICTION-rank (L3) | 165 | 0.78 | 14.6% | −44.4% | **0.44** |

**0.44 vs 1.29 → KILLED.** Per R11 this is a FINDING; no retune.

## Root cause + what it teaches

- The trained score has **OOS AUC 0.472** — it is *anti*-predictive, so ranking by it systematically funds
  WORSE candidates than CRS. That's why the book collapsed rather than merely flatlining.
- This **retro-invalidates Stage-2's AUC 0.536** as noise: on a cleaner, smaller (touch-only, 2019-21)
  split the same feature family falls **below 0.50**. Entry-time features do not generalize —
  **4th independent confirmation.**
- **CRS-rank is a genuinely good selector.** It is not an arbitrary default; it is doing real work, which
  is precisely why 0094 was the largest single improvement in the arc. Beating it needs a signal that
  demonstrably generalizes — and none of the measured entry features do.

## Status of the lever

**L3 is now SPENT.** With entry-filtering (dead), zoo entries (portfolio-negative), sleeves (nothing),
per-branch exits / routing (worse), and now conviction fill-ranking (anti-predictive), **every
registry-cleared in-sample avenue on the swing book is closed.** The live touch-only book
(Sharpe 1.03 / CAGR 21.2% / DD −34.8% / 22-26 slice 1.29) stands as the best configuration tested.

## One principled alternative, NOT yet run (declare before spending — R9 makes this K=2)

The book's economics are **fat-tailed** (27% of touch trades are R>=2 runners carrying it), so ranking by
**P(win)** is arguably a *mis-specified objective* — it optimises win-rate, not runner-capture. Ranking by
**E[R]** or **P(R>=2)** is an a-priori-defensible re-specification (economic argument, not result-fitting).
Expectations should stay low: the features fail to predict even *win* OOS. Recorded here so that, if run,
it is a **declared 2nd test**, not a search.
