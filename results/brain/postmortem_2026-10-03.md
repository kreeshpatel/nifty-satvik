# Saturday post-mortem — 2026-10-03 19:46

**19/40 closed, 1/4 quarters -> not yet evaluable; 90 days to the 2027-01-01 review [UNVERIFIED DATE - calendar coverage ends 2026-12-31]**

Generated from committed artifacts by `scripts/render_weekly_postmortem.py`. No number here is new: each one is reproduced from the artifact named beside it. Nothing in this page reads the sealed judge log.

## 1. Which book each headline number is about

Finding 0146: the weekly scan runs three books off one engine and the readout mixes them. A number without its book is not interpretable.

| number | value | book |
|---|---|---|
| closed trades (the readiness count) | 19 | uncapped tracker |
| expectancy | -1.49R | uncapped tracker |
| win rate | 0.0% | uncapped tracker |
| NAV | Rs.973,685.12 | capped Rs.10L book |
| Sharpe (the kill trigger) | -1.2679 | capped Rs.10L book |
| MaxDD (the halt trigger) | -7.9% | capped Rs.10L book |

**The capital book itself:** 2 closed (exact), 6 realisation event(s) — so the closure count is not the number of times money was realised. Implied realised Rs.-6,101.84 (derived, not sourced), unrealised Rs.-367.51.

The two capped books' NAV curves are IDENTICAL over 60 sessions, so §4's MaxDD/Calmar test cannot currently separate the arms.

## 2. Gates — value, convention, and whether it fired

Conventions were ratified in `forward/prereg_swing.md` §11 on 2026-09-27, **before** the first read, so no reading could be chosen after seeing the data. Between reviews every gate is **surfaced, not applied** — the only exception is §5's mechanical halt.

| gate | reading | fired? | convention | book |
|---|---|---|---|---|
| readiness | 19 closed / 1 quarters | no | closed-only count | uncapped tracker |
| promote | exp -1.49R, DD -7.9% | no | calendar years, daily grid | capped Rs.10L book |
| kill | -1.2679 | YES | raw-return, rf = 0 (below cash, not below the risk-free rate) | capped Rs.10L book |
| halt | -7.9% | no | daily grid | capped Rs.10L book |

**§4 grading (A-only vs base-swing):** INSUFFICIENT EVIDENCE -> default base-swing, carry A-only — A-only 19 vs base 4 closed against a floor of 20 per book.
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

19 of 19 closed trades carry an excursion measurement. The rest have no committed price basis: the capital book never funded them, so no archived mark exists (A3).

| trade | R | MAE | MFE | capture of MFE | basis |
|---|---|---|---|---|---|
| DELHIVERY | -1.05 | -1.17 | +0.26 | -4.018 | daily_hl |
| INDUSINDBK | -0.93 | -1.31 | +1.83 | -0.507 | daily_hl |
| NESTLEIND | -1.20 | -1.56 | +1.37 | -0.878 | daily_hl |
| LTF | -1.85 | -2.14 | +1.09 | -1.702 | daily_hl |
| CANFINHOME | -2.94 | -3.51 | +0.60 | -4.924 | daily_hl |
| GLENMARK | -0.93 | -1.67 | +0.52 | -1.799 | daily_hl |
| NATCOPHARM | -0.95 | -1.15 | +0.05 | -18.812 | daily_hl |
| NLCINDIA | -1.97 | -2.29 | +0.08 | -24.201 | daily_hl |
| BIOCON | -1.16 | -1.37 | +0.06 | -19.863 | daily_hl |
| LINDEINDIA | -2.32 | -3.14 | +0.35 | -6.563 | daily_hl |
| MRPL | -0.29 | -0.82 | +1.26 | -0.231 | daily_hl |
| 3MINDIA | -0.57 | -1.28 | +1.47 | -0.388 | daily_hl |
| GESHIP | -1.46 | -1.81 | +1.47 | -0.993 | daily_hl |
| M&MFIN | -0.78 | -0.78 | +1.50 | -0.519 | daily_hl |
| HINDALCO | -1.13 | -1.77 | +1.72 | -0.655 | daily_hl |
| CCL | -2.18 | -3.56 | +0.45 | -4.794 | daily_hl |
| HINDZINC | -1.65 | -1.61 | -0.32 | n/a | daily_hl |
| ANGELONE | -1.17 | -1.69 | +0.31 | -3.732 | daily_hl |
| CHOLAFIN | -3.76 | -4.44 | +0.00 | n/a | daily_hl |

A `weekly_marks` basis cannot see the intra-week extreme, so its MAE and MFE are UNDERSTATEMENTS — bounded by the true excursion, never beyond it. A capture near -1 means the trade gave back its whole favourable move and then the risk.

## 5. What this page does not contain

* **The AI judge stream.** `results/judge_log.jsonl` is sealed until the first review read (>= 2 quarters from 2026-08-01 AND >= 100 resolved verdicts). This renderer never opens it.
* **Owner overrides.** No source exists — the engine cannot see a discretionary deviation, and an empty column would read as 'none happened'. A declared hole, not a zero.
* **Any number computed here.** Every figure is reproduced from a committed artifact; if one looks wrong, the artifact is wrong, and the diagnostic that wrote it is named above.

*Capital book: 5 position(s), cash Rs.118,379.43, NAV Rs.973,685.12.*

