---
name: plausibility-check
description: >
  Compare any strategy number — Sharpe, CAGR, drawdown, win rate, ΔSharpe — against this repo's
  reproducible anchors BEFORE reporting it, promoting it, or acting on it. A result that beats its
  anchor is a defect signal until explained. Also the guard against stating a published band from
  memory. Trigger phrases: "does this look right", "is this plausible", "sanity check this number",
  "too good", "that drawdown looks shallow", "what should this be", "typical Sharpe", "benchmark
  this", "compare to the literature", "is that realistic".
---

# Plausibility check — put the number next to its anchor before you believe it

The most expensive defects in this programme did not look like defects. They looked like good
results, and good results get written up instead of investigated. The habit that catches them is
mechanical and takes two minutes: **before reporting a number, put it beside the anchor that governs
it and say which direction it sits.**

The reference is [`docs/references/plausibility_anchors.md`](../../docs/references/plausibility_anchors.md).
Open it. Do not work from what you remember of it — the whole point of the file is that the values
are read from committed artifacts, and a recollection of a reproducible number is not reproducible.

## The check

1. **Which anchor governs this?** Long-horizon momentum → `baseline_v1`. Swing → frozen 0094. A
   sub-period → the continuous-slice base, never the fresh-capital one. A ΔSharpe → the resolution
   floor.
2. **Which direction, and by how much?**
3. **If it is better than the anchor, it is guilty.** Name the specific difference that would
   explain the gap and check that one:
   - price vintage (unpinned runs drift 1–2pp CAGR; `baseline_v0`'s 26.1% was vintage, not skill)
   - gross vs net (delivery STT is per leg, buy *and* sell — charging it once halves the cost)
   - survivorship (the pin is survivor-only; the bias scales with holding period)
   - sub-period computed by re-running rather than slicing (this manufactures a pass)
   - horizon (only ≥2019 folds and the 63-day horizon transfer)
   - leakage (a leak inflates; a result *worse* than base is not a leak)
4. **Is the difference even resolvable?** n_eff ≈ 37 independent 63-day windows ⇒ dSharpe half-width
   ~0.59. A ΔSharpe of 0.1 is a quarter of the measurement error. Most "improvements" end here, and
   saying so is the answer, not a failure to find one.
5. **State the comparison in the write-up.** "Sharpe 0.71 vs the 0.667 anchor, +0.04 — well inside
   the ±0.59 resolution band, so not distinguishable" is a finding. "Sharpe 0.71" alone is a number
   with no meaning attached.

## The specific shapes that should stop you

| you see | suspect |
|---|---|
| Max drawdown materially shallower than **−46%** on the long-horizon book | the drawdown calculation, or a re-seeded equity peak |
| Sharpe near or above **1.0** on the long-horizon book | price vintage, or gross being compared to net |
| A swing variant above **~1.13** in-sample | a perturbation that should have deflated — every tested one does |
| A sub-period kinder than the full period | fresh-capital re-run instead of a continuous slice |
| A win rate far from **~60%** with the same trade count | selection changed, not the edge |
| Any ΔSharpe under **0.6** described as an improvement | it is inside the measurement error |

## On external literature

[`docs/references/external_literature.md`](../../docs/references/external_literature.md) is a
**stub**. Until the owner populates it, this repo holds no committed external band for Indian
midcap momentum.

So: **do not state a published range as fact.** Not "the literature says 14–18% CAGR", not "typical
drawdowns are 50–70%". Say that the external file is unpopulated, give the internal anchor instead,
and — if the question genuinely needs an outside view — search the web and cite what you find, in
the moment, with the source attached. A remembered band quoted with confidence is the exact failure
this skill exists to prevent, and it is more dangerous than having no band at all, because it sounds
like knowledge.

## When the anchors and the result cannot be reconciled

Do not write it up. An unexplained gap is the finding: report what does not reconcile, what you
checked, and what you would need to resolve it. That is a smaller-sounding result and a far more
useful one than a headline number nobody can defend three months later.
