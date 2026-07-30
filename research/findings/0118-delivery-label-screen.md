# Finding 0118 — Delivery-quality screen: dlv_med21 PASSES its kill-shot (screen #7; 0 trials; usage NOT designed)

**Status: SCREEN PASS at the pre-registered bar — STOPPED at the PASS door awaiting owner sign-off.**
Pre-reg [0118](../../diagnostics/research/preregistry/0118-delivery-label-screen.md); screen-ledger row
#7 (running count 7). n_trials untouched at 138. Data: 1,949 days / 3.49M rows of NSE delivery archives
(2019->2026-07), PIT layer truncation-proven, audit gate PASSED on all four checks (coverage 94-100%/yr
incl. 813 delisted-in-window symbols; MTO<->sec_bhavdata seam byte-identical 0.00pp on 1,500+ common
symbols x 3 overlap days; spot-checks exact; uncovered trades outcome-neutral +0.487 vs +0.484).

## The result (train 2019-01..2024-06, n=2,648; sealed set never read)
| question | answer |
|---|---|
| **Q3 R-gradient** | **dlv_med21: conditional +0.363R [+0.129,+0.583] top-vs-bottom tercile, sign 5/6 years, ADV-tercile signs [+,+,+]** — clears every leg of the bar incl. the liquidity-proxy check. dlv_dwn21 close behind (+0.316 [+0.085,+0.550], 5/6) but ADV-mixed [-,+,+]. dlv_trend / z sub-bar. |
| Q1 false_touch vs noise_stop | Weak and direction-odd: only the z-form is CI-clean (+0.215 [+0.05,+0.40]) and it says false_touches carry HIGHER delivery-z than recoverable stops — the naive accumulation story does not explain the stop cohorts. |
| Q2 exit_too_early | Null (all CIs straddle). |

## Mechanism (honest version)
High pre-entry delivery share marks approaches carried by position-taking rather than intraday churn,
and those signals resolve better ON AVERAGE (the Q3 gradient) — but delivery does NOT know which stop
victim recovers (Q1), so it is quality information about the POPULATION, not a stop discriminator. The
effect is orthogonal to price by construction (0117), survives ext x CRS x ADV conditioning, and comes
from a dataset the price path cannot contain.

## The mandatory caveats (stated before any enthusiasm)
1. **The 0116 flip precedent:** path_eff passed an equally clean Stage-A bar (CI excluding zero, 5/6
   years) and INVERTED on the sealed set. This pass earns a sealed check, not belief.
2. **Screen multiplicity:** this is screen #7 (~30 feature-target comparisons cumulative) — the ledger
   prices the reuse.
3. **The 0010-redux clause binds:** a pass does NOT authorize a ranking overlay; and the graveyard
   (0104/0108 subtractive filters, 0110 floors, 0112 cash-gate) constrains any usage shape.

## Usage sketch (one paragraph, per the pre-reg; NOT designed further, awaiting sign-off)
The mechanism-matched shape is a **within-week funding-queue SWAP** — when two same-week signals compete
for the last funded slot, prefer the higher-dlv_med21 one (CRS remains the primary key) — i.e. a
tiebreak, not a filter and not a ranker: the book stays full (no idle-cash/redeployment killer, the
0104/0108 mechanism), no absolute threshold (no 0110 drift), and only intra-week substitution (the
0112 lesson contained). If signed off, the test is a REAL TRIAL: full pre-reg with the swap rule frozen,
train-design -> sealed 2024H2+ check -> Stage-C capped continuous-slice endpoint, n_trials 138->139.

---

## ADDENDUM (2026-07-27) — Step-1 activation bound: the swap-tiebreak is underpowered BY CONSTRUCTION; no trial run

Owner-gated Step 1 (`scripts/diag_tiebreak_bound_0119.py`; screen-ledger row #8, running count 8;
n_trials untouched at 138):

- **Activation is rare:** 53 of 279 train weeks had any marginal competition (funded > 0 AND
  unfunded > 0); the delivery ordering disagreed with the incumbent CRS pick in only **15 weeks over
  5.5 years** (~3 swaps/year).
- **The clairvoyant bound is NEGATIVE: −1.29 R/yr** (swap deltas mean −0.47R, median −0.30R, sum
  −7.1R). Even with perfect hindsight execution, the delivery-preferred contender did WORSE than the
  incumbent pick at the margin.
- **Gate verdict (pre-committed):** far below the ±10 R/yr path-noise floor — and wrong-signed.
  **NO TRIAL.** n_trials stays 138.

**Mechanism reading:** the +0.363R population gradient does not survive at the decision margin. The
marginal pairs are CRS-adjacent by construction, and within that narrow band delivery quality adds
nothing (and historically subtracted) — the same law the program has hit repeatedly: population-level
information ≠ decision-point value (0079's IC≠Sharpe, 0112's cash-gate, now at the slot level).

**The two remaining doors (per the sign-off):** (a) **bank-and-hold** — the delivery dataset + PIT
layer + screen result stay as recorded assets; the population gradient is real and may matter to a
future, structurally different consumer; (b) **a wider usage shape** (ranking/filtering/sizing) —
requires a fresh owner sign-off because every such shape re-enters closed territory
(0104/0108 subtractive filters, 0110 absolute thresholds, 0112 cash-gate). Nothing proceeds without
that sign-off.
