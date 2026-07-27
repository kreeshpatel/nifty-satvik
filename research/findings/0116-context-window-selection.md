# Finding 0116 — Context-window study: the train-years path_eff signal FLIPS SIGN on the sealed set; the pre-entry wall now holds at the PATH level too

**Verdict:** **KILL at Stage B (sealed validation). Stage C never ran — 0 trials spent** (n_trials stays
138; Stages A/B were pre-registered measurements). Pre-reg + frozen-rule amendment:
[0116](../../diagnostics/research/preregistry/0116-context-window-selection.md). Scripts:
`build_substrate.py` (determinism guard PASS 1.1319/255), `build_context_windows.py`,
`diag_context_stageA.py`, `diag_context_stageB.py`. Dataset: `research/substrate/context_windows.parquet`
(4,025 trades, ±21d windows, 100% feature coverage).

## What was studied (the new formulation vs the closed selection axis)
Pre-entry 21d PATH-SHAPE features (grind-vs-gap efficiency, drawup, compression, acceleration — absent
from 0110/0111/0112/STAGE2_ml, which used bar-level statics) as selection territory; post-exit 21d
windows as labels only (false_touch 15%, noise_stop 17%, exit_too_early 19%), behind a hard leakage
firewall; every effect conditional on ext-band x CRS-tercile cells; train 2019-01..2024-06, sealed
2024-07..2026-06 opened once after the rule freeze.

## Stage A (train only) — one CI-clean candidate
`path_eff`: conditional top-vs-bottom tercile spread **−0.23R [−0.43,−0.02]**, median −0.31R, sign 5/6
train years. Story: efficient approaches = blow-off class (bad); choppy approaches = base-building (good).
Rule frozen by amendment: skip path_eff > train-q67 (0.3344).

## Stage B (sealed) — the signal FLIPS
| slice | conditional kept-minus-skipped ΔmeanR |
|---|---|
| train | +0.085 (already sub-bar as a binary cut — the tercile spread diluted) |
| **sealed 2024-07+** | **−0.269** (skipped trades did BETTER; 2025 raw −0.698) |

The mechanism story also failed its label check: skipped (high-efficiency) trades had LOWER false_touch
rates (0.129 vs 0.161) — the blow-off narrative was not what the feature was capturing. In the 2024-25
chop the sign inverts: efficient approaches were the few real trends in a choppy tape.

## Why this matters (the lesson worth the study)
A feature with a train-set CI excluding zero and 5/6-year sign consistency STILL flipped sign
out-of-sample. This is the sharpest demonstration yet of why the sealed-set + frozen-rule protocol
exists — pooled significance with in-window consistency can still be regime luck. The pre-entry wall is
now confirmed a FOURTH independent way and extended from bar-level to path-level: **entry quality is not
visible before entry — not in the bars, not in the path.** The information that separates winners from
losers on this funnel arrives only after entry (and the post-entry levers are separately closed:
0105/0106/0109).

## Program consequence
The context-window reopening of the selection axis closes with the axis re-sealed and strengthened. The
post-exit LABEL dataset (opportunity-vs-exit quality grades) is banked as a reusable asset for future
exit-diagnostics. No config change; the engine is untouched; the capped base remains 1.1319/255.
