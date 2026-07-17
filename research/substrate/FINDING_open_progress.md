# Finding — `open_progress` removes the PULLBACK, which is the strategy

*Pre-registered in `research/preregistry_open_progress.md`, frozen before the run (R4). n_trials 116->118.
Guards verified byte-identical (golden 1.1319/255 · live P2 1.0342/168).*

## The rule (owner, chart review r3)

> *"the open price of current week should be higher than the previous"*

Signal week must satisfy `open[k] > open[k-1]`. **Acceptance test passed** — both owner cases blocked:
ASAHIINDIA 2024-07-22 (open 610.67 vs 651.40), COHANCE 2025-02-17 (open 1090.00 vs 1165.05).
Distinct from `require_progress` (close>close), which **passes** on both. Pool 8,518 -> 3,436 (40%).

## Result — KILL

| arm | tr | Sharpe | CAGR | DD | **22-26** | skip_cash |
|---|---|---|---|---|---|---|
| BASE | 168 | 1.03 | 21.2% | −34.8% | **1.29** | 19,728 |
| SPEC (ext20+R10+pos20) | 181 | 1.11 | 21.6% | −33.6% | **1.21** | 19,151 |
| **SPEC + open_progress** | 175 | 0.62 | 9.5% | −35.3% | **0.35** | 7,349 |
| **BASE + open_progress** | 154 | 0.73 | 12.6% | −31.0% | **0.75** | 7,760 |

SPEC+rule is **−1.6σ below the random null**. BASE+rule lands **exactly on the null (0.75 vs 0.74)** —
the rule reduces the book to coin-flipping.

## Root cause — the rule is anti-pullback, and this is a pullback strategy

The live 168 trades, split by the rule:

| signal week opens… | n | meanR | win% | **total R** | signal-wk low vs SMA (median) |
|---|---|---|---|---|---|
| **lower** than prior (rule **BLOCKS**) | 106 | **+0.80** | **58%** | **+85.0R (82% of the book)** | **+2.03%** (mean −0.16%) |
| **higher** than prior (rule **KEEPS**) | 62 | +0.30 | 48% | +18.4R (18%) | +3.19% |

**The rule keeps the weak half and blocks the strong half.** A week opens *below* the prior week's open
**because that is what pulling back means**. Those weeks are the ones that actually reach the line —
median low +2.03% over the SMA, mean −0.16% (many trade *through* it). Weeks that open higher merely
graze the SMA on the way up (+3.19%) and carry meanR +0.30 / win 48%.

Note trade count barely moved (168->154, 181->175) even though 60% of the pool was removed — exactly the
skeptical prior from the pre-reg. `FINDING_cash_starvation` showed the book takes only ~2% of signals, so
a pool cut does not bind on count; it changes **which** names reach the CRS queue. Here it swapped the
strong half for the weak half. `skipped_cash` halved (19,151 -> 7,349) and the book got **worse** —
relieving cash starvation is worthless if the pool you draw from is null-quality.

## What this vindicates

The owner's standing near-SMA instinct is **correct and is re-confirmed here from a new angle**: the deep
dip *is* the edge (blocked bucket median low +2.03% vs kept +3.19%, meanR +0.80 vs +0.30). Consistent
with `deep-near-sma-touch-edge`. This particular rule simply filters **for the opposite** of that edge.

## The honest tension

The rule **does exactly what the owner asked** — ASAHIINDIA and COHANCE are gone. But it cannot separate
them from 106 trades carrying +85R, because *being a real pullback* is the property they share. Chart
intuition indicts the pullback week's ugly open; that ugly open is the edge's signature.

## Verdict

**KILL, both arms.** R11: nothing ships. Live config FROZEN. Entry-side filters now **0-for-10** on this
book. Do not re-propose open/close-progress variants without a genuinely new formulation.

## Next setup

Unchanged: the two live threads are the **2R-on-close miss** (AEGISLOG hit +2.35R MFE and booked −2.02R —
a capture-what-we-earned leak, not a filter) and the **more-slots** experiment from
`FINDING_cash_starvation`. Both are additive, not subtractive — which, after ten subtractive kills, is
the pattern worth respecting.
