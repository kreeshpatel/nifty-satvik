# 0140 — PBO as a standing verdict output; the external "add CPCV/PBO" doc, confronted

**Date:** 2026-08-17 · **Class:** infrastructure + measurement apparatus. **`n_trials` unchanged at 2.**
**Standing counts:** screens 19 · sealed opens 1 · n_trials 2.
**Spends:** no trial, no screen row. This changes *how a family of configs is judged*, not *what is traded* —
the golden master (`tests/test_stage2_golden.py`) stays byte-identical.

---

## 1. The prompt

An external research doc recommended tightening the harness with the López de Prado toolkit —
walk-forward that purges and embargoes, Combinatorial Purged Cross-Validation (CPCV), the Deflated
Sharpe Ratio (DSR), and the Probability of Backtest Overfitting (PBO/CSCV). Per the house rule for
external docs (CLAUDE.md: *be adversarial; cross-reference every recommendation against the
registry*), the first task is confrontation, not construction.

## 2. Confront result — the apparatus already implements the doc

Almost every recommendation is already built, tested, and (where appropriate) wired into the verdict
path:

| Doc recommendation | Status in `nq/validation/` (+ verdict path) |
|---|---|
| Deflated Sharpe Ratio (multiplicity correction) | **Live in `adjudicate`** — deflates at both cumulative *and* lifetime `n_trials` (`dsr.py`) |
| Probabilistic Sharpe / Min Track Record Length | Built (`dsr.py`), reported by `evaluate` |
| CPCV with purge + embargo (LdP Ch. 12) | Built + tested (`cpcv.py`, `test_stage4_validation.py`) — **deliberately dormant** for frozen rules |
| PBO / CSCV (Bailey/Borwein/LdP/Zhu 2015) | Built + tested (`pbo.py`, `test_pbo_montecarlo.py`) |
| Block-bootstrap ΔSharpe CI, continuous-slice sub-periods, ≥2019 fold-pass | All live in `adjudicate` / `evaluate_overlay` |

Two nuances the code makes explicit, not gaps:

- **CPCV is correctly dormant, not missing.** `nq/runner/research.py` documents why (lines 3–9): on a
  *frozen rule* every CPCV path collapses to the same stitched series — the path *distribution* comes
  from per-fold model *training* variation, which a frozen rank rule has none of. The correct
  OOS-robustness tool for a frozen rule is the overlapping block bootstrap (block = 63). CPCV earns
  its cost only on a **re-derived / trained arm**. Its activation trigger is therefore the
  **ML / learning-bot arm** the owner wants pursued (memory: *pursue-learning-bot-judge-oos*) — the
  moment that arm exists, CPCV is its OOS harness, already implemented and waiting.
- **PBO was built but not standing.** Before this note, `cscv_pbo` was called in exactly one place —
  `pipelines/research/run_0001_xsec_momentum.py` — and nowhere in the adjudication path. So no verdict
  emitted a PBO by construction.

## 3. The one gap closed — `adjudicate_family`

DSR asks: *given N attempts, is this one Sharpe still significant?* It corrects a single winner. It
cannot see the failure mode where a parameter sweep of near-identical configs manufactures a
confident-looking winner whose in-sample ranking is pure noise. PBO measures exactly that — pick the
in-sample best, ask how often it lands in the bottom half out-of-sample — so it is a statement about
the **selection procedure** and needs the whole family. DSR and PBO are complements: DSR can pass
while PBO says the choice between configs was arbitrary.

`nq.runner.research.adjudicate_family(family, ...)` makes PBO a first-class verdict output, mirroring
`adjudicate`:

- **Engine-agnostic** — takes a `{label: backtest}` mapping (the `{equity_curve, …}` contract),
  reads no panel or cfg. Aligns per-config daily returns on their common dates into the
  `(n_periods, n_configs)` matrix CSCV consumes.
- **Reports, never gates.** PBO is a standing cross-check recorded *alongside* the verdict, not an
  eighth promotion gate. Headline field `selection_informative` (PBO < 0.5). The in-sample winner's
  Sharpe is additionally deflated at the **family size** (`winner_dsr_in_family`) — the multiplicity
  the sweep itself spent; program-wide multiplicity stays `adjudicate`'s DSR concern.
- **Degrades honestly** — < 2 configs, or too few aligned periods for one CSCV split, returns
  `UNDERPOWERED`, never a crash and never a fabricated number.

## 4. What changed (code)

| file | change |
|---|---|
| `nq/runner/research.py` | new `adjudicate_family` + `cscv_pbo` import |
| `tests/test_stage4_research.py` | 3 hermetic tests — noise → PBO≈0.5 (calibration regime), dominant config → informative + winner picked, underpowered paths |
| `pipelines/research/run_0001_xsec_momentum.py` | the existing one-off `cscv_pbo` call now routes through `adjudicate_family`, so 0001 emits the structured output (PBO + winner + DSR-in-family) instead of a bare print |

Golden master byte-identical (additive pure function; no engine path touched). Depgraph regenerated.
Full validation suite green.

## 5. Retro-audit — what could be scored now, and what owes a cloud pass

The honest scope: PBO needs a family of per-period **return curves**, admissibly produced. Two
constraints bound the retro-audit:

- **No local sweeps.** A local run uses the degenerate survivor universe (backtest-rigor §D3) → its
  PBO is not a real robustness statement. No fabricated local numbers are recorded here.
- **No sealed/forward books.** The breadth-50 arms (EW / SW / SW-accum) are forward-only with zero
  in-sample fitting; computing an in-sample PBO spread across them would break the forward seal.
  Excluded by design.

**Scored now (the one admissible existing family):** pre-reg 0001's parameter neighbourhood
(top-N ∈ {20,30,50} × buffer ∈ {1.0,1.5,2.0}, 9 configs) — committed PBO **0.452**, selection
**informative** (< 0.5), consistent with 0001's PROMOTE-CANDIDATE. It is now emitted by the standing
wrapper; the next cloud re-run of 0001 will restate it marginally (the wrapper aligns on real returns
rather than the prior fillna(0) row) and add the `winner` / `winner_dsr_in_family` fields.

**Owes a standing PBO at the next cloud sweep (registered, not fabricated):** the adopted swing-book
parameters whose robustness rests on a sweep (backtest-rigor §C1b "plateau not peak") — `stop_atr_mult`,
`min_hold`, `target_pct` and the like. Each was validated on a neighbourhood sweep; none has a PBO
persisted. These are the Oct-1 cloud-PBO to-do, run through `adjudicate_family` when the sweep is
next dispatched on the corrected universe.

## 6. The doc's other suggestion — RL

The doc also floated reinforcement learning (for execution / sizing). Parked, not adopted: a ~5-seat
weekly delivery book with ~150 trades/year is far below the sample an RL policy needs to generalise,
and it collides with the standing preference for mechanism-explainable rules (program-laws). If an ML
arm is pursued, it is the *selection* model (judged OOS-only, memory *pursue-learning-bot-judge-oos*)
that consumes CPCV — not an RL execution layer.

## 7. Oct-1 handoff

- PBO now travels with any family-level verdict — the review reads it, it is not re-derived per session.
- CPCV is armed for the ML arm's OOS evaluation the moment that arm exists.
- The adopted-parameter families above are the concrete cloud-PBO work-list for the review.

## Root-cause readout

The gap was never missing machinery — it was an *unwired* one. PBO existed as a validated primitive
called in a single pipeline, so the apparatus could compute selection-overfit but no verdict ever
did. Promoting it to `adjudicate_family` costs nothing at trade time and closes the one place the
external doc was genuinely additive; everything else it recommended, the harness already did.

## Next setup

When the swing-book parameter sweeps are next dispatched on the corrected universe, route each family
through `adjudicate_family` and persist the PBO beside the ΔSharpe/DSR verdict — turning §5's register
into recorded numbers for the Oct-1 review.
