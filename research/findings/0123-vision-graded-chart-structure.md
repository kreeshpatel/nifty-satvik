# Finding 0123 — Vision-graded chart structure: a reliable blind grader is FLAT across outcomes; the pre-entry wall now holds against PERCEPTION (screen #12; 0 trials)

**Verdict: KILL at the Phase-2 screen — and the Phase-1.5 cross-check resolves NULL IN BOTH COHORTS,
which retires "we encoded the concepts wrong" permanently.** Screen-ledger row **#12** closed (running
count 12; sealed opens 1). **n_trials untouched at 138.** Pre-reg
[0123](../../diagnostics/research/preregistry/0123-vision-graded-chart-structure.md) (params frozen
before any chart was rendered; reliability bar + primary variable pinned before any grade was read).
Scripts: `render_blind_chart.py`, `build_0123_sample.py`, `grade_0123.py`, `screen_0123.py`,
`phase15_0123.py`. Artifacts: `research/substrate/grades_0123/*.jsonl` (681 grades + 66 double-graded
pairs + 68 truncation probes), `sample_0123.csv`, `phase15_detectors.csv`,
`phase15_disagreement_cohort.csv`. Sealed 2024H2+ set never rendered, never graded.

## What was tested (the genuinely new lever)

(A) Does a vision model, grading rendered charts **blind**, extract pre-entry structure that separates
good trades from bad — where every hand-written formula has failed? (B) Were our formula detectors
faithful encodings of those concepts in the first place?

New FEATURE SOURCE (model perception), not a new formula from the killed zoo (0079/O-015) and not the
formula chart-structure features already killed as ML inputs (prereg 0004: +0.10%/trade, CIs overlap).
Sample: 681 train-year trades (227 each false_touch / noise_stop / strong-winner R≥2), **matched within
all 9 ext-band × CRS-tercile cells**. Charts rendered by the committed weekly panel, truncated at the
signal-week decision point (no future bar), stripped of ticker/date/title/axis furniture, 44-line = SMA.
Grader `claude-opus-5`, frozen prompt/effort/schema, one independent call per chart.

## The instrument was NOT the problem (both gates passed first)

| gate | result |
|---|---|
| **Self-consistency** (66 ids × 2 independent passes) | setup_grade weighted-κ **0.867** (bar 0.45), within-1-grade **1.000** (0.80), take_now κ **1.000** (0.45), take_now agreement **1.000** (0.75), breakout_stage agreement **1.000** (0.65) — **GO** |
| **Truncation-leakage** (68 charts at two crop lengths, same decision point) | weighted-κ **0.690**, within-1-grade **1.000**, directional drift **−0.074** (bar ≤0.50), take_now agreement **0.971**, stage agreement **0.941** — **CLEAN**, no furniture leakage |

This matters: the null below is **not** a noisy-instrument artifact. The grader reproduces itself at
κ=0.87 and does not read history length. It is a reliable instrument measuring something real — that
something just carries no outcome information.

## Phase-2 screen (train only, n=681) — KILL on every leg

| test | result | bar |
|---|---|---|
| Unconditional mean grade (0=F..4=A) | strong_winner **1.339** · noise_stop **1.313** · false_touch **1.383** | — |
| take_now rate | 2.2% · 1.8% · 3.1% | — |
| **Conditional (cell-adjusted, beyond ext×CRS)** | SW−FT **−0.044** [−0.140,+0.050]; SW−NS **+0.026** [−0.062,+0.119]; NS−FT **−0.070** [−0.167,+0.024] | **all CIs straddle 0** |
| Per-year sign (SW − stop-out, cell-adj) | 2019 −0.212 · 2020 +0.099 · 2021 −0.085 · 2022 −0.012 · 2023 +0.080 · 2024 −0.124 → **2/6 positive** | ≥5/6 → FAIL |
| Liquidity-proxy terciles | −0.042 / +0.060 / −0.049 | sign-inconsistent |
| `take_now=True` subset (n=16) | cohort mix **7 false_touch / 5 winner / 4 noise_stop** | lands on losers as often as winners |
| Confound check | corr(grade, ext) **−0.087**; corr(grade, R) **+0.020** | — |

Point estimates are ≤0.07 grade-points and **mostly wrong-signed** (the false_touch losers grade
*highest* unconditionally). Not underpowered-but-promising: flat.

**The confound check is itself informative.** The pre-registered failure mode was "grade ≈ extension"
(the r=+0.48 ext↔candle-size trap). It did not happen — corr(grade, ext) = −0.087. The grade is not a
disguised ext proxy; it is genuinely reading structure, and structure genuinely does not separate.

## Phase-1.5 — detector integrity, and the decisive cross-check

**The integrity measurement that never existed before** (model annotation vs the committed detectors at
the same decision week):

- Model sees *some* setup on **35.4%** of charts; the committed formulas fire on **18.6%** → presence
  agreement **64.8%**.
- Model marks a box/consolidation region on **46.3%** vs the box detector's **11.9%** (agreement 55.1%).
- **Setup-CLASS match: 6.5%.** The model's dominant named type is `sr_breakout` (193) while the S/R
  detector fires on 8.5%; `cup_handle` / `double_bottom` / `ascending_base` / `vcp` / `flag` fire on
  **0.0%** of this touch-funnel sample.
- Disagreement cohort **n=240 (35.2%)** — 177 "model sees setup, formulas silent" + 63 "formulas fire,
  model sees none". Committed to `phase15_disagreement_cohort.csv` for eyeballing.

So the formulas and a competent perceiver genuinely **do not see the same charts** — question (B)'s
premise is real. And the pre-committed cross-check then answers it:

| cohort | n | cell-adj grade (winner − stop-out) | verdict |
|---|---|---|---|
| **AGREEMENT** | 441 | **+0.042** [−0.045,+0.130] | NULL |
| **DISAGREEMENT** | 240 | **−0.032** [−0.166,+0.103] | NULL |

**Null in BOTH cohorts.** Per the pre-registration, this is the branch that says: the wall holds at the
**CONCEPT** level, not merely at the formula level. "We encoded the concepts wrong" is retired
permanently — the model disagrees with our detectors on a third of charts, and its *different* reading
predicts outcomes no better than theirs (which is to say, not at all).

## Root cause (mechanism, not metric)

The funnel enters names that have **already trended**: the grader called **72% "extended"** and said
**"wait" on 98%** of them. A disciplined blind trader looking at a 44-SMA touch entry sees the same
thing every time — an extended name, mid-trend, no clean base — and grades it C/D. The eventual big
winner, the recoverable whipsaw, and the unrecoverable false touch are **visually identical at the
decision point**. What separates them arrives only after entry (0117), and is unreachable there too.

This is the same law from a new angle: **population/perceptual information ≠ decision-point value**.
0079 hit it as IC≠Sharpe; 0118/0119 at the funding slot; 0120/0121 at event deferral; now 0123 at
perception itself.

## Program consequence — the fifth wall, and the last one available

The pre-entry wall now holds **five independent ways**: bar-level ML (STAGE2_ml/0111/0112), loser
forensics + Phase-1 levers, path-level (0116, with its sealed sign-flip), formula chart-structure
(prereg 0004), and now **model perception at reliability κ=0.87 with leakage ruled out**. Combined with
0117 (post-entry hindsight-only), the lifecycle map is closed against the strongest instrument we can
point at it. **Entry quality on this funnel is not visible before entry — not in the bars, not in the
path, not in the formulas, and not to a vision model that can see the chart the way a trader does.**

No PASS ⇒ per the pre-registration, **no usage paragraph is written** and the activation-bound law is
not invoked (there is nothing to bound). Engine untouched; no cfg change; no forward-wall read.

## Do not re-test unless

A materially **different funnel** is the subject — one whose entries are *not* already-extended
(e.g. the box/S-R breakout entries that fire pre-extension, or a slack-capital/longer-horizon book).
The null established here is about **this touch funnel's decision points**, where the visual variance
across outcomes is genuinely near-zero. Re-proposing model-graded charts on the same 44-SMA touch
entries — with a different rubric, a different vision model, more charts, or grade-ensembling — is
relitigation and is refused: the instrument was reliable, leakage-free, and flat, in both detector-
agreement cohorts.

## Assets banked

681 blind entry-truncated chart renders + the reusable blind renderer (`render_blind_chart.py`), the
681-row graded dataset with structure annotations, the 66-pair reliability set, the 68-pair truncation
set, and the **first detector-integrity measurement in the program's history**
(`phase15_detectors.csv` + the 240-row disagreement cohort) — reusable for any future question about
whether a formula detector marks what a perceiver sees.

## Cost

~$16 total (self-consistency $6 interactive; bulk grading switched to the Batch API at 50% for the
remaining 568; truncation probes single-shot). Screen #12 closed for the price of a measurement,
zero trials spent — the campaign's standing pattern.
