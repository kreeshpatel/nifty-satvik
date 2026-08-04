# The `|| true` audit — every guard, classified, with a named watcher

**Date:** 2026-08-05. **Class:** fail-loud hardening (zero research; counts frozen at
screens 14 · sealed opens 1 · n_trials 138).

## Why

`|| true` and `2>/dev/null` convert a failure into a green step with no annotation. That is the
mechanism behind every instance of this session's defect class:

- `results/weekly_monitor.json` dead for weeks (2026-07-18)
- the D2 archive never accumulating
- the judge cohort — **17 verdicts, $4.00, discarded** (2026-08-01)
- the PROBE instance
- `results/intraday_scan/` — the **fifth**, found by `tests/test_workflow_output_paths.py` on its
  first run, the same day the guard was written

In each case a workflow exited 0 and published nothing. **No guard survives this audit without a
named watcher** — a specific, committed check that goes red when the thing the guard hides fails.

## The classification

| # | site | verdict | disposition | named watcher |
|---|---|---|---|---|
| 1 | `ci.yml` — `ruff check \|\| true` | **legitimate** (advisory gate, deliberately non-blocking) | but no longer silent: `\|\| echo "::warning::…"` | the annotation itself, on every CI run |
| 2 | `ci.yml` — `mypy --strict \|\| true` | **legitimate** (same) | `\|\| echo "::warning::…"` | the annotation itself |
| 3 | monitor — `run_forward_accumulators.py \|\| true` | **failure-hiding** | annotated warning; the monitor still publishes (it must) | output contract: `forward_accum_health.json` in `must_update` → red when it stops appearing in the daily commit |
| 4 | monitor — `git add … 2>/dev/null \|\| true` | **failure-hiding — the core defect** | replaced by `need`/`opt` helpers: required → `::error` + red step; optional → `::warning` | `tests/test_workflow_output_paths.py` (can it be staged at all) + `results/output_contracts.json` (did it land in the commit) |
| 5 | scanner — `archive_weekly_cards.py \|\| true` | **failure-hiding** | annotated warning (paper state must still publish) | contract row `cards_archive.jsonl` |
| 6 | scanner — `run_judge_cron.py \|\| true` | **legitimate** — belt-and-braces *after* in-script handling (missing key, missing SDK, model drift, per-card failure all exit 0 inside the script); the scanner must never fail because of the judge | annotated warning; comment now names the watcher | contract row `judge_log.jsonl` + the hash-chain test |
| 7 | scanner — `run_blend_paper.py \|\| true` | **failure-hiding** | annotated warning | contract row `blend_hybrid_paper.json` |
| 8 | scanner — `git add … 2>/dev/null \|\| true` | **failure-hiding — the D5 instance** | `need`/`opt` split | as row 4 |
| 9 | intraday — `git add results/intraday_scan/ 2>/dev/null \|\| true` | **failure-hiding — the fifth instance** | `if [ -d … ]; then git add …; else ::warning; fi` | as row 4; contract row promotes to `must_update` once one scan lands |

**Cron scripts:** swept for `except …: pass`. **None found** in `scripts/run_*.py`,
`scripts/archive_*.py`. The Python side was already explicit; the shell side was not.

## What now makes regression impossible

`tests/test_workflow_output_paths.py::test_no_silent_guards_in_workflows` fails on any `|| true`
or `2>/dev/null` on a live command line in any workflow. Comments may still *discuss* the banned
pattern (this audit depends on that), so the test strips comments before matching.

Two lessons were paid for during the rewrite itself and are pinned as tests:

1. Moving paths from a literal `git add a b c` into the `need`/`opt` helpers **removed them from the
   whitelist guard's coverage** — 13 paths silently became 7. `test_workflows_declare_at_least_one_add_path`
   caught it. The parser now reads all three declaration forms, and matches `git add` anywhere on a
   line (the intraday cron guards its add behind an `if`, and an anchored match dropped it).
2. Parsing unstripped lines scraped prose out of the guard-policy comment block, so the guard went
   **vacuously green on tokens like `construct`**. A guard diluted by junk no longer means what its
   name says. Comments and helper definitions are now stripped before parsing; coverage is **18 real
   paths**, all verifiable.

## Deliverable

> Every scheduled job now has a declared output contract, an independent checker, and no silent guard.
