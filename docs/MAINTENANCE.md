# Maintaining this codebase — the standing plan

Every rule here exists because something in this list actually happened, most of it found in the
2026-08-08/09 audit. Nothing is included on general principle. Where a rule is enforced by a test or
a hook, that is named; where it is a ritual, its cadence is named.

---

## 1. The nine failure modes this repo actually has

| # | Failure | Evidence | Enforced by |
|---|---|---|---|
| 1 | **A number lives in prose and drifts from its ledger** | `n_trials 138` survived in three files after the counter was reset to 2 — one of them the *authority* file. Registry §4 benched everything against `baseline_v0` for five weeks after ADR-0006 superseded it. | `tests/test_standing_counts.py`, `tests/test_registry_anchor.py`, `scripts/session_brief.py` |
| 2 | **A docstring asserts something about another module and nobody checks** | `nq/signals/cross_sectional_rank` claimed it "mirrors" the eligibility version. It does not (ties). `nq/data/weekly.py` claimed byte-parity with the live book — that one *was* true, and nothing was holding it there. | `tests/test_weekly_panel.py` (parity now differenced) |
| 3 | **Capability merged, never wired** | `exposure_by_date`, `clenow_score`, `kill_flags()`, `model_wall`, and the base-swing arm were all built, tested, and called by nothing. | §3.2 below — currently unenforced |
| 4 | **"No registry row" read as "untested"** | I made this error three times in one night: 0001's survivorship correction, the Clenow ranker, and turnover bucketing were all already done. Registry rows count *studies run*, not code present. | `docs/references/external_literature.md` standing caution |
| 5 | **A finding is written and never acted on** | 0001's §3 "What does NOT support this result" states every caution the overnight audit rediscovered. Pre-reg **0074** charged a trial (`n_trials` 80→81) and was never run. | §3.3 below |
| 6 | **The live book is outside the dependency map** | `scripts/gen_depgraph.py` walks `nq/` + `config.py` only. The entire Bhanushali chain — five `sys.path`-hacked scripts deep — is invisible to it. | §3.1 below |
| 7 | **A constant is unpinned and only mutation finds it** | `MAX_ADV_PARTICIPATION` 0.05→0.50 passed all 664 tests. So did the promotion bar's seven thresholds, the validation annualiser, and the market-impact term. | `tests/test_sizing_adv_cap.py`, `test_promotion_bar_thresholds.py`, `test_market_impact_repricing.py`, `test_subperiod_gate_slices.py` |
| 8 | **Two implementations of one quantity** | Three exit engines, two sizing paths, two `cross_sectional_rank`, two CAGR conventions, and ≥5 duplicated cost models in `pipelines/` — one of which drops the SMALL_CAP tier and the impact term. | §3.4 below |
| 9 | **A gate graded against the wrong document** | `bhanushali_review_scorecard.py` grades the swing book against `forward/prereg.md` §10.2 — the *momentum* wall's doc — while `prereg_swing.md` §4 is implemented nowhere. | dated to the 2026-10-01 review |

---

## 2. What is already automatic — do not re-litigate these

- **SessionStart brief** (`scripts/session_brief.py`) — counts, pin, interpreter, branch, generated from
  the ledgers every session. No session recites a number from prose.
- **Protected-path guard** (`scripts/guard_protected_paths.py`) — refuses reads/writes of the sealed
  judge log, edits to a reported pre-registration, the frozen cfg, the pinned anchor, and
  `forward/prereg.md`. Override is `NQ_GOVERNANCE_OVERRIDE=1`, deliberately one variable.
- **Production-commit guard** (`.githooks/commit-msg`) — any commit touching the live Bhanushali
  path must declare `prod-fix:` or `prod-override:`. `prod-fix` requires a regression test that
  fails on the old code.
- **Depgraph regeneration** (`.githooks/pre-commit`) — on any `nq/**` or `config.py` change.
- **Golden masters** — four, byte-identical or the change is not a refactor.
- **The 2026-08-08 amendment** — no path is killed without a run under the current harness.

---

## 3. What to add, in priority order

### 3.1 Extend the dependency map to the live book *(highest value, mode 6)*
`gen_depgraph.py` walks `nq/` + `config.py`. The book that trades real capital is a five-deep
`sys.path` chain in `scripts/` and appears nowhere. Extend the walker to `scripts/` and `pipelines/`,
emitting a second graph. **Until this exists, nobody can answer "what breaks if I change
`run_bhanushali_weekly_rank.backtest()`" except by reading five files.**

### 3.2 An unwired-capability test *(mode 3)*
A test that walks `nq/**` public functions and asserts each is either called outside its own module
and tests, **or** listed in a committed `docs/UNWIRED.md` with a date and a reason. Five capabilities
were sitting built-and-dark; each was invisible until someone happened to grep. The register makes
"built but not wired" a deliberate, dated state rather than an accident.

### 3.3 Findings must name an owner and a next action *(mode 5)*
`skills/research-log` already requires a root cause and a next setup. Add: every finding's next
setup carries **a date or a review it is bound to**. A quarterly sweep lists findings whose next
action has passed its date with nothing recorded. 0001's §3 and pre-reg 0074 would both have
surfaced.

### 3.4 A single-source-of-truth register *(mode 8)*
`docs/DEFINITIONS_REGISTER.md` exists; extend it into an enforced list: for each quantity that has
more than one implementation (exit logic, sizing, cross-sectional rank, CAGR convention, cost model),
name the canonical one and test the others against it — or record that they are *deliberately*
different and why. The two `cross_sectional_rank` functions differ legitimately; the false docstring
was the defect, not the divergence.

### 3.5 Scheduled mutation testing *(mode 7)*
Every constant found unpinned this week was found by mutating it and re-running. Add a monthly job
that perturbs the constants in `config.py`, `nq/engine/portfolio.py`, `nq/data/features.py` and
`nq/runner/research.py` one at a time and reports which leave the suite green. Each survivor is
either a missing test or a genuinely free parameter — and both are worth knowing.

### 3.6 Compute the live book's after-tax return
0001's after-tax CAGR is committed (18.16%). **The Bhanushali book's has never been computed**, and
it is the one holding capital. `nq/runner/research.py` already has `after_tax_curve`; the swing
harness does not call it. Until it does, the live book's headline is not comparable to anything.

---

## 4. Cadence

**Every session** — the SessionStart brief runs; route with `/session-router` before non-trivial work.

**Every change** — declare the class (MEASUREMENT / RESEARCH / ENGINE / REFACTOR / PRODUCT). A bug
fix ships a test that fails on the old code. A move commit contains no edits. `nq/**` or `config.py`
⇒ regenerate the depgraph and run the full suite.

**Monthly** — the mutation sweep (§3.5); the unwired-capability register review (§3.2); check that
every finding's next action is still in date (§3.3).

**Quarterly (first trading day Jan/Apr/Jul/Oct)** — the only dates on which forward-wall promotion,
demotion, degradation and fork decisions may be taken. Between them: log and leave it alone. The
next is **2026-10-01**, carrying the veto arm, the scorecard reconciliation, and the swing §4 grading
decision.

**Annually** — re-read the closed-verdict corpus against the current harness. Under the 2026-08-08
amendment a verdict is evidence about the regime that produced it; the apparatus has changed five
times in three months and will change again.

---

## 5. The two rules that would have prevented most of this

1. **A number that informs a decision must be reproducible from the committed pipeline.** Not from a
   transcript, not from a docstring, not from a finding's prose. If it is quoted, its authority is
   named next to it, and a test holds the quote to the authority.
2. **Before claiming something is untested, grep the source tree.** The registry records studies, not
   capabilities. This one cost three false conclusions in a single night, two of which were published
   into a reference file before being caught.
