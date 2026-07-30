# 0123 — Vision-graded chart structure: does a blind model-grader see pre-entry quality the formulas missed?

- **ID:** 0123
- **Type:** SCREEN (measurement). Screen-ledger row **#12** (running count 12 after close).
- **Registered:** 2026-07-30
- **Status:** PRE-REGISTERED
- **n_trials:** untouched at **138** (a screen makes no PROMOTE/KILL trade decision on the honest base).
- **Standing counts at registration:** screens 11 · sealed opens 1 · n_trials 138.
- **Owner sign-off:** approved-as-frozen 2026-07-30 (3-way cohort split selected).

_Everything above the RESULT section is immutable once registered. Parameters are frozen.
UNDERPOWERED and KILL are first-class outcomes. No retune toward a pass._

## Two questions (verbatim)

(A) Does a vision model, grading rendered charts blind, extract pre-entry structure
(consolidation quality, support/resistance zones, breakout stage, false-setup tells) that
separates good trades from bad — where every hand-written formula has failed?

(B) Were our formula detectors ever faithful encodings of those concepts in the first place —
i.e. is the pre-entry wall built on tested CONCEPTS or on tested (possibly wrong) FORMULAS?

## Relitigation basis

This attacks the pre-entry wall (0116 + the four walls) with a genuinely new FEATURE SOURCE —
model-graded chart structure — not a new formula from the killed zoo (0079/0013) and not the
formula chart-structure features already killed as ML inputs (prereg 0004, delta +0.10%/trade,
CIs overlap). The wall verdicts are the prior; burden of proof is maximal. The 0116 sealed-flip
(a train CI-clean, 5/6-year `path_eff` that inverted sign out-of-sample) is the governing precedent:
a clean train effect here earns a sealed check, not belief.

## Phase 0 registry confrontation (recorded)

| Idea element | Verdict | Status | Citation |
|---|---|---|---|
| Technical/indicator formulas as ranker | zoo dead, IC≠Sharpe | CLOSED | 0013/O-015 |
| Chart-structure as ML formula features | +0.10%/trade, CIs overlap → effective KILL | CLOSED (as formulas) | prereg 0004 |
| Pre-entry path-shape as selection | train-clean, sealed FLIP | CLOSED | 0116 |
| Post-entry conditional management | hindsight-only | CLOSED | 0117 |
| Regime / meta / selector | not learnable OOS; no cap transfer | CLOSED | 0103, 0112 |
| Formula setup detectors as entries | per-trade better, no sleeve beats touch under cap | entry-gen CLOSED | STAGE4_sleeves |
| **Vision model grading charts for pre-entry quality** | never tested | **OPEN** | — |

The setup-library thread built/validated formula detectors (box, S/R-pivot, VCP/flag/cup/asc-base/
dbl-bottom) and stopped at STAGE4: under the ₹10L cap the touch-only book dominates every sleeve →
ship nothing. It answered "are there better entry patterns" (yes per-trade, no under cap). It did
NOT ask whether a grader separates good touch-trades from bad ones pre-entry. That is this screen's (A).
Its committed detectors are the Phase-1.5 integrity baseline, not the Phase-2 subject.

## Method (frozen)

**Sample.** Train years only: `context_windows.parquet` rows with `entry_date <= 2024-06-30`
(train n=3,056; false_touch 401, noise_stop 470, strong-winner R≥2 942). Sealed 2024-07+ (969 trades)
is NEVER subset, rendered, or graded. Stratified matched sample **~450 charts, 3-way balanced across
false_touch / noise_stop / strong-winner (R≥2)**, matched within ext-band × CRS-tercile cells
(ext q33/q67 = 13.99 / 27.9). No loser-only or winner-only list. Final n locked only after the
power-check clears the pre-committed bar; params never move after locking.

**Charts.** New helper `scripts/render_blind_chart.py` (outside `nq/**`). Each trade truncated at the
**signal-week Friday** — no bar after the entry decision point, no future, no MFE/exit marker. Stripped:
ticker, dates, title, axis date labels, any outcome hint in image / filename / prompt. Weekly candles
+ 44-SMA + 20-SMA + volume. 44-line is the SMA (never EMA). Opaque-hash filenames.

**Rubric (frozen verbatim, no outcome language).** Structured JSON per chart:
base/consolidation quality (length, tightness, volume dry-up); level structure (S/R proximity &
cleanliness); breakout stage {pre / at / extended}; overall setup grade A–F; binary
"disciplined swing trader takes now vs waits" + one-line reason.

**Phase-1.5 annotation (same call).** S/R zones as price bands; consolidation/box region bounds if
present; setup-type classification.

**Grader protocol.** `claude-opus-5`, vision base64 image blocks, `output_config.format` structured
output, `effort` medium. Frozen: model id, prompt, effort, output schema (Opus 5 rejects `temperature`
— determinism pinned via frozen model+effort+prompt+schema). Each chart an INDEPENDENT call (no context
bleed). 10% subsample (~45) graded twice → self-consistency; an unreliable grader FAILS before any
screen runs. All raw JSON, every PNG, the prompt committed as artifacts (reproduce-before-trust).

## Pre-committed pass/kill bar (0118/0120 mold)

PASS requires ALL of:
- Grades separate false_touch from noise_stop and mark strong winners with **CI-clean conditional
  separation beyond ext-band × CRS cells**.
- **Per-year sign consistency ≥ 5/6 train years.**
- **ADV-tercile sign-robust.**
- Self-consistency reported alongside (grader reliability is a precondition, not a result).

Miss any leg → **KILL**. Underpowered (MDE > effect at locked n after honest power-check) → UNDERPOWERED.

## Named failure modes checked (Phase 2)

- **0116 sealed-flip:** a clean train effect is a sealed-check earner, not truth.
- **Grader leakage / truncation trick:** same chart at two crop lengths — grades must not drift
  (evidence the model infers period/outcome from chart furniture).
- **grade ≈ extension:** the known r=+0.48 ext↔candle-size confound. If the grade merely re-measures
  ext or candle size, the conditional ext×CRS cells expose it → that is a KILL, not a discovery.

No retunes, no second pass, no added rubric dimensions after seeing results.

## Phase-1.5 decisive cross-check (pre-committed; no ledger row — same screen on a cohort split)

Per-detector **agreement rate** (S/R zone overlap, box IoU, setup-class match) vs committed
`nq/research/setups.py` for the same name-week. Commit the **disagreement-cohort** renders. Then run the
Phase-2 screen SEPARATELY on the agreement vs disagreement cohorts:
- Grades separate labels **only where model disagrees with our formulas** → the formulas were the
  limitation; the wall has a named crack with receipts.
- Grades fail in **both** cohorts → the wall holds at the CONCEPT level; "we encoded it wrong" retires
  permanently — the four walls gain their final brick (holds against perception, not just formulas).

## Cost + power

~450 charts + ~45 double-grades + ~45 truncation probes ≈ 540 calls. ~5.5k input + ~0.6k output/call
→ ~$0.045/call → ≈ $24 single-shot, ≈ $12 via Batch. Ceiling $40. MDE at n≈450 within ext×CRS cells
~0.30–0.40 R (0118 reference: +0.363R [+0.129,+0.583]). If power-check MDE > pre-committed effect at
n=450, n rises before locking.

## Phase 3 doors (pre-committed)

- **KILL** → finding + registry row + ledger row #12 closed. Valuable either way; if grades fail in
  BOTH 1.5 cohorts the four walls gain their final brick.
- **PASS** → ONE paragraph only. The activation-bound law runs (clairvoyant bound vs ±10R/yr noise
  floor) BEFORE any trial is proposed. Likeliest viable consumer stated for honesty: a conviction/quality
  input to the breadth-50 SW watched book or forward-wall machinery — NOT a new entry gate on the 15-slot
  book (decision margins proven dead: G1/G2 chaos; activation-bound law 3/3 at 0119/0121). Any trial
  stays at the owner's door with n_trials pricing. Local-model distillation is OUT OF SCOPE this session.

## RESULT

### Pre-committed BEFORE any grade exists (2026-07-30, recorded pre-data)

- **n locked at 681** (227/cohort), raised from ~450/136 per the frozen power-check contingency
  ("n rises before locking") — done before any grading, symmetric power, not a retune. All 681 render
  clean. Grading via Batch-equivalent ≈ $18.
- **PRIMARY screen variable:** `setup_grade` mapped A=4,B=3,C=2,D=1,F=0 (ordinal 0–4 quality).
  **SECONDARY:** `take_now` (binary). All other rubric fields are descriptive/annotation only.
- **Self-consistency reliability bar (test–retest on the seeded 10% double-graded, ~68 ids × 2 passes).
  ALL must hold or the grader FAILS → the screen does NOT run (instrument too noisy; no full grading):**
  1. `setup_grade`: quadratic-weighted Cohen κ ≥ **0.45** AND within-1-grade agreement ≥ **80%**.
  2. `take_now`: Cohen κ ≥ **0.45** (raw agreement ≥ **75%**).
  3. `breakout_stage` (3-cat): raw agreement ≥ **65%**.
- These thresholds and the primary-variable choice are frozen here, before the self-consistency JSONL
  is read. No adjustment after seeing the numbers.

### Outcome (2026-07-30) — KILL; null in BOTH Phase-1.5 cohorts

Run once, exactly as pre-registered. No retunes, no second pass, no added dimensions.

- **Reliability gate PASSED** (66 double-graded): setup_grade weighted-κ 0.867 / within-1 1.000;
  take_now κ 1.000 / agreement 1.000; breakout_stage agreement 1.000 → GO.
- **Truncation-leakage gate CLEAN** (68 paired crop lengths): κ 0.690, within-1 1.000,
  directional drift −0.074, take_now agreement 0.971, stage agreement 0.941 → screen authorized.
- **Phase-2 screen (n=681): KILL.** Mean grade SW 1.339 / NS 1.313 / FT 1.383; every cell-adjusted
  pairwise CI straddles zero; per-year 2/6 (bar ≥5/6); liquidity terciles sign-inconsistent;
  take_now=True (n=16) = 7 false_touch / 5 winner / 4 noise_stop. corr(grade,R) +0.020.
  The pre-registered grade≈extension confound did NOT occur (corr(grade,ext) −0.087).
- **Phase-1.5: detector integrity measured for the first time** — presence agreement 64.8%,
  setup-CLASS match 6.5%, disagreement cohort n=240 (35.2%). Decisive cross-check:
  **AGREEMENT +0.042 [−0.045,+0.130] NULL; DISAGREEMENT −0.032 [−0.166,+0.103] NULL — null in BOTH.**
  Per this pre-registration, that retires "we encoded it wrong" permanently; the wall holds at the
  CONCEPT level.
- **No PASS ⇒ no usage paragraph written; activation-bound law not invoked (nothing to bound).**
- Finding: [0123](../../research/findings/0123-vision-graded-chart-structure.md). Registry row appended.
  Ledger row #12 closed (running count 12; sealed opens 1). **n_trials stays 138.** Engine untouched.
