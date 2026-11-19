---
name: verify-before-report
description: The eight verification rules that bind every study and every report in this programme — method before result, artifact check, independent re-derivation, anchors, no silent scope changes, labelled claims, loud corrections, and owner decisions listed separately. Read it BEFORE writing any study, and again before writing the final message that reports one. Trigger phrases "report a result", "write this up", "is this ready to report", "artifact check", "re-derive", "anchor", "label the claims", "correction", "owner decision", "did the method make this".
---

# Verify before you report

Owner mandate, 2026-11-17. These rules are in `CLAUDE.md` under **Mission and verification** and they bind every
report, including a one-line answer in chat. They exist because the programme's expensive mistakes have not been
reasoning errors — they have been **properties of the method reported as properties of the market**, and a confident
sentence is what carries one of those out of a session and into a decision.

The worked failure that produced this skill: the 2026-11-17 IC study measured cumulative forward returns, found "IC
rises with horizon, no decay, no half-life", and drew three conclusions from it — including that weekly re-ranking is
not too slow. Cumulative returns over overlapping windows mechanically inherit the trend that the ranker is built
from, so a rising curve was the arithmetic, not the market. The study answered a different question from the one
asked and said so nowhere. Rules 1, 2 and 5 would each have caught it alone.

## The mission line

Every task opens with **one line** saying how it moves the system toward the mission (more money, less drawdown,
survives forward data; the 70/30 blend at a 15% vol target on ₹20,00,000; beat Midcap150 Momentum 50 TRI on ≥26
forward weeks). **If it does not, say so and ask before starting.** "Interesting" is not a reason, and neither is
"cheap".

## 1. Method before result

Before any number, the study states:

- the **exact formula** for each metric, with `file:line` — not the name of the metric, the formula;
- the **data window**, and that the cut was asserted where a sealed slice exists;
- the **universe**, and how membership was decided point-in-time;
- **how overlapping or dependent samples are handled** — and if they are not, that they are not.

A metric whose formula is not written down is not reportable. "Spearman IC" is a name; "cross-sectional Spearman
between the rank at Friday *t* and the return from the close of *t+h−1* to the close of *t+h*, one value per Friday,
`explore_ic_decay_halflife.py:118`" is a formula.

## 2. Artifact check — at least three, each ruled out or not

Before any conclusion, list **at least three ways the result could be an artifact of the method**, and for each say
whether it was ruled out **and how**. Not checked is an allowed answer; silence is not. The standing list to start
from, because each has bitten this programme:

| artifact | what it looks like |
|---|---|
| cumulative vs marginal returns | a quantity that grows with the horizon because the horizon is longer, not because the signal persists |
| overlapping windows | confidence bands several times too narrow; "n weeks" that are not n independent observations |
| survivorship | a universe that only contains names that were still there at the end |
| look-ahead / PIT | a feature, membership list or calendar that reached back past its own publication date |
| cap or sizing binding | a lever that appears to change size or seats when a cap is the thing actually deciding |
| single path | one start date and one cost assumption standing in for a distribution |
| open trades at cutoff | unclosed positions marked at the cut and counted as outcomes |
| fresh-capital slicing | a sub-period re-run from the window start, which resets the equity peak and manufactures a pass |

## 3. Independent re-derivation

Any number that drives a **decision** — a verdict, a pass mark, a change to live or to capital — is recomputed by a
**fresh sub-agent given the spec only, never the original code or its output**. Report **both** numbers. More than
**5% relative** difference: stop and reconcile before reporting anything.

The sub-agent's prompt carries the formula, the window, the universe rule and the data paths, and says explicitly not
to read the implementation. `blind-replica` is the agent for this; `red-team` is not a substitute, because it reviews
the reasoning rather than recomputing the number.

## 4. Anchors

Every study **reproduces one known published number first**, in the same run, and prints it. If it does not match,
**stop** — the harness has moved, and nothing downstream of it is reportable.

| anchor | value | where it lives |
|---|---|---|
| live A, uncapped total R, 2019-01-01..2024-06-28 | **650.2R** over 525 trades | `diagnostics/research/2026-11_loss_diagnosis.json` |
| 0001 momentum, run of record | **21.73% CAGR / 1.130 Sharpe / −37.17% MaxDD** | `docs/PLAN_2026Q3_STRATEGY.md`, `docs/decisions/0014-calendar-annualisation.md` |
| pinned anchor `baseline_v1` | gross Sharpe 0.667 / CAGR 15.46% / MaxDD −46.26% | the session brief, `/plausibility-check` |

An anchor that cannot be reproduced in-run (a cloud run, a sealed read) is **quoted and labelled as quoted**, with
the reason, and a reproducible anchor is used in its place.

**Hash-seed check.** For any code that iterates a set or a dict, reproduce the anchors under at least two
`PYTHONHASHSEED` values. The #212 tax simulator's harvest step read +13,460 or +11,564 depending on the seed (PR #214,
Correction 3).

## 4b. Swing total R is quoted BOTH ways, always (owner, 2026-11-17)

Every report that quotes the swing book's historical R shows, side by side:

| | what it is |
|---|---|
| **closed-only** | sum of R over trades whose reason is not `eos` |
| **marked-at-cut** | sum of R over every trade, open ones marked at the final close |
| **share of total R from trades open at the cutoff** | (marked-at-cut − closed-only) ÷ marked-at-cut, as a percentage |

and names the **population filter** (whether trades with an initial stop inside 0.5% of entry were dropped) and the
**book** (uncapped, or the capped ₹10L book).

The published figures for dataset A, uncapped, 2019-01-01..2024-06-28
([`diagnostics/research/2026-11-17_total_r_convention_reconciliation.md`](../../diagnostics/research/2026-11-17_total_r_convention_reconciliation.md)):

| population | trades / closed / marked | closed-only | marked-at-cut | share from open-at-cutoff |
|---|---|---|---|---|
| filtered (stop ≥ 0.5%) | 525 / 441 / 84 | **+273.929R** | **+650.191R** | **57.9%** |
| unfiltered | 526 / 442 / 84 | **−115.822R** | **+260.440R** | **144.5%** |

Why this is a rule and not a preference: one trade with a ₹0.05 risk basis moves the headline by 390R while moving
the money by ₹8,041, and 58% of the published anchor is positions that were never closed. A bare "total R" hides
both. A total-R comparison between two studies that do not state these is not a comparison.

## 4c. Parameter sensitivity is reported, not assumed (owner, 2026-11-18)

Any report that recommends a candidate rule — for pre-registration, promotion or a live change — carries the
**spike table** from `skills/pre-register` Step 1b: every numeric parameter nudged −20%, −10%, +10%, +20%, one at a
time, over the 20-path ensemble, one row per parameter, PASS or SPIKE, with the comparator for "Sharpe change"
named. Pass = median Sharpe change positive at every ±10% nudge and at least half its unnudged size at every ±20%
nudge. **A spike cannot be pre-registered.** A report without the table does not recommend anything.

## 5. No silent scope changes

Horizons, settings, windows, buckets or arms added **after seeing results** are listed as **"added after first look"**
with the reason, and they **count toward multiplicity**. This applies to an exploratory study with no trial budget:
the count is still the honest record of how many looks produced the shape being reported.

## 6. Label every claim

In a final message, every factual claim carries one of:

- **[measured]** — with the artifact path that holds it;
- **[inferred]** — follows from measured things, by an argument the reader can check;
- **[assumed]** — taken on faith, including anything remembered.

No unlabelled facts. A count or a backtest number recalled from memory is **[assumed]** until a ledger or a run says
otherwise (`CLAUDE.md`: the two things no session may do from memory).

## 7. Corrections are loud

When a later finding overturns an earlier claim, the final message **opens** with `Correction:`, naming the claim, the
PR or file that carried it, and what replaces it. No burying it in paragraph four, no "to refine what I said earlier".
The withdrawn claim is also marked where it lives, not quietly edited away.

## 8. Owner decisions listed separately

Decisions for the owner go in their own section at the **end** of the message, each with **the options and the
evidence for each**. **Nothing is merged, signed, or has its capital changed without the owner's explicit word naming
that item.** A general "go ahead" earlier in a session is not that word.

## The pre-report checklist

1. Mission line written, or the task questioned.
2. Formula, window, universe and dependence handling stated **above** the results.
3. Anchor reproduced in-run and printed.
4. Three or more artifacts listed, each ruled out with its method or marked not checked.
5. Decision-driving numbers re-derived by a fresh sub-agent; both numbers reported; within 5%.
   Any candidate recommended carries its spike table (§4c).
6. Anything added after the first look labelled as such and counted.
7. Every claim in the final message labelled.
8. Corrections first; owner decisions last, with options and evidence.
