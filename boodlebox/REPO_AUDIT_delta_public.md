# Repository audit — delta supplement (public version, 2026-10-23)

A read-only, code-only audit that supplements three existing maps rather than repeating them:
[`skills/repo-map/SKILL.md`](../skills/repo-map/SKILL.md), [`docs/DEPENDENCY_MAP.md`](../docs/DEPENDENCY_MAP.md)
and the engine assumption batch
[`diagnostics/research/engine_assumptions/2026-10-20_batch.md`](../diagnostics/research/engine_assumptions/2026-10-20_batch.md).

**What is summarised here on purpose.** This repository is public. The full audit names individual
authentication endpoints and admin flows that lack HTTP-level tests, and deployed routes that nothing calls.
Published in detail that is a map of weak spots, so those parts appear below only as themes and counts. The
full version is kept privately by the owner.

## 1. Backend routes vs frontend calls (summary)

- **94 routes** are registered in the FastAPI backend (`dashboard/backend/main.py`, routers under `/api`).
- **About 12 routes have no caller** in either frontend (the live one in `frontend/` or the newer `frontend2/`).
- **One abandoned integration is still deployed:** the HDFC market-data swap was abandoned on 2026-07-10, but
  its routes are still registered and uncalled.
- **Latent broken calls:** the live frontend's API client still wraps two endpoints that were removed from the
  server on 2026-08-27. Nothing on any page uses those wrappers, so nothing breaks today. `frontend2/` has none.
- **14 API-client exports** in the live frontend are never imported.

## 2. Dead and orphaned code (proven: zero inbound imports, last-touch commit checked)

- **The "retired" long-horizon / momentum book is not retired in code.** A daily workflow
  (`cron-forward-wall.yml`) still runs it, `config.py` still loads its frozen config, and about 45 files use
  that loader, including a live script and a golden-master test. The repo-map rewrite of 2026-10-20 labels it
  retired, which is wrong: a cleanup that deleted it would break the wall and a golden test.
- **Proven dead:** `scripts/reorg_tree.py` (zero references; a one-shot tree move) and the Render-era
  `dashboard/backend/Procfile` (the backend is on Fly.io).
- **Probably dead:** `nq/strategy/long_horizon.py` and `nq/runner/scan.py`, kept alive only by their own test.
- **Stale references:** a backend comment cites a module path that no longer exists; `nq/signals` cites a test
  file that does not exist; `build_universe` is defined twice (`nq/universe/__init__.py`, `scripts/run_cpcv.py`).
- **Not dead, by design:** about 130 `pipelines/**` scripts have no importer because they reproduce the evidence
  behind past findings ("reproduce-before-trust"). Their last-touch dates reflect a 2026-08-07 tree move, not use.
- The dependency map omits the `nq/signals` and `nq/universe` packages.
- No commented-out code blocks of 10 lines or more.

## 3. Test coverage gaps

- **Coverage is never measured** in CI (instrumentation crashed an old runner), and the frontend's `*.test.js`
  files are not run in CI.
- **The live trading path is densely tested:** about 25 test files exercise the weekly cron, about 20 the
  engine, plus golden masters, a lab-to-cron replay-parity test and guard tests.
- **Untested functions on that path:** the monitor's tranche-status and missed-exit helpers; the review
  scorecard's forward-metrics helper; the cron's regime and Nifty-refresh helpers; `history_guard.check_history`;
  `weekly.load_weekly_panel`; macro and options-OI series builders.
- **Backend:** most routers have no HTTP-level tests. Notably, the authentication lifecycle is tested only at
  the guard level, not end to end, and the test fixtures mint tokens directly. *(Detail withheld; see note above.)*

## 4. Code-only health verdict

1. A hidden live dependency on the book the docs call retired.
2. The backend: authentication and several routers lack end-to-end tests, and coverage is unmeasured.
3. A possible product bug: the live frontend's per-user NAV chart reads a history table whose rows are written
   only as a side effect of an endpoint that only `frontend2/` calls. Unverified at runtime.
4. Dead surface still deployed (the abandoned HDFC routes, unused routes, stale client wrappers).
5. Some workflow steps end in `|| echo`. Most are non-fatal on purpose and are caught by post-commit checks;
   one health-report step in the wall workflow is genuinely masked.

**Verdict:** the live swing engine and its cron are in good shape — golden masters, replay parity and data
guards are dense. The weak side is the product layer: backend and frontend tests, a hidden dependency on the
"retired" book, and deployed endpoints nothing uses.
