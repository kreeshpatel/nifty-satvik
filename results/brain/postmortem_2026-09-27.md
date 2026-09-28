# Saturday post-mortem — 2026-09-28 06:10

**13/40 closed, 0/4 quarters -> not yet evaluable; 4 days to the 2026-10-01 review**

Generated from committed artifacts by `scripts/render_weekly_postmortem.py`. No number here is new: each one is reproduced from the artifact named beside it. Nothing in this page reads the sealed judge log.

## 1. Which book each headline number is about

Finding 0146: the weekly scan runs three books off one engine and the readout mixes them. A number without its book is not interpretable.

| number | value | book |
|---|---|---|
| closed trades (the readiness count) | 13 | uncapped tracker |
| expectancy | -1.43R | uncapped tracker |
| win rate | 0.0% | uncapped tracker |
| NAV | Rs.993,530.65 | capped Rs.10L book |
| Sharpe (the kill trigger) | -0.7310 | capped Rs.10L book |
| MaxDD (the halt trigger) | -7.3% | capped Rs.10L book |

**The capital book itself:** 2 closed (exact), 6 realisation event(s) — so the closure count is not the number of times money was realised. Implied realised Rs.-6,101.84 (derived, not sourced), unrealised Rs.-367.51.

The two capped books' NAV curves are IDENTICAL over 60 sessions, so §4's MaxDD/Calmar test cannot currently separate the arms.

## 2. Gates — value, convention, and whether it fired

Conventions were ratified in `forward/prereg_swing.md` §11 on 2026-09-27, **before** the first read, so no reading could be chosen after seeing the data. Between reviews every gate is **surfaced, not applied** — the only exception is §5's mechanical halt.

| gate | reading | fired? | convention | book |
|---|---|---|---|---|
| readiness | 13 closed / 0 quarters | no | closed-only count | uncapped tracker |
| promote | exp -1.43R, DD -7.3% | no | calendar years, daily grid | capped Rs.10L book |
| kill | -0.7310 | YES | raw-return, rf = 0 (below cash, not below the risk-free rate) | capped Rs.10L book |
| halt | -7.3% | no | daily grid | capped Rs.10L book |

**§4 grading (A-only vs base-swing):** INSUFFICIENT EVIDENCE -> default base-swing, carry A-only — A-only 13 vs base 2 closed against a floor of 20 per book.
  **Those two counts are not the same quantity** — the first is the uncapped tracker's, the second a capped book's — and this floor short-circuits before the MaxDD/Calmar branches, so it is what currently decides §4. Recorded, not repaired: repairing it is a live-rule change (0146).

## 3. Where the loss came from

Across 13 closed trades in the 2026-09-25 snapshot: realised -18.67R = designed -13.00R + beyond-stop -5.67R (9 of 13 filled past the stop).

| cohort | n | realised | beyond-stop |
|---|---|---|---|
| **funded — the book that holds money** | 2 | -2.25R | -0.25R |
| never funded — tracker only | 11 | -16.42R | -5.42R |

0147: beyond-stop slippage on the funded book is the first row. The second belongs to a book no rupee was exposed to, and must not be quoted as the book's.

Two committed conventions disagree by +1.26R: netting favourable fills gives -5.67R, counting adverse overshoot only gives -6.93R. Neither is wrong; a quoted figure should say which.

## 4. How the trades travelled

2 of 13 closed trades carry an excursion measurement. The rest have no committed price basis: the capital book never funded them, so no archived mark exists (A3).

| trade | R | MAE | MFE | capture of MFE | basis |
|---|---|---|---|---|---|
| DELHIVERY | -1.05 | -1.05 | +0.00 | n/a | weekly_marks |
| NESTLEIND | -1.20 | -1.20 | +1.19 | -1.005 | weekly_marks |

A `weekly_marks` basis cannot see the intra-week extreme, so its MAE and MFE are UNDERSTATEMENTS — bounded by the true excursion, never beyond it. A capture near -1 means the trade gave back its whole favourable move and then the risk.

## 5. What this page does not contain

* **The AI judge stream.** `results/judge_log.jsonl` is sealed until the first review read (>= 2 quarters from 2026-08-01 AND >= 100 resolved verdicts). This renderer never opens it.
* **Owner overrides.** No source exists — the engine cannot see a discretionary deviation, and an empty column would read as 'none happened'. A declared hole, not a zero.
* **Any number computed here.** Every figure is reproduced from a committed artifact; if one looks wrong, the artifact is wrong, and the diagnostic that wrote it is named above.

*Capital book: 6 position(s), cash Rs.66,182.62, NAV Rs.993,530.65.*

