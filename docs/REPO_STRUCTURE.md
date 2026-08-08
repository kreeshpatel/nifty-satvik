# Repository Structure

*Reorganised 2026-08-07. Before this, `scripts/` held 209 flat `.py` files fusing three unrelated
layers behind `run_` / `diag_` prefixes that described how a file was born rather than what it is.*

## The three layers, now separated

| layer | where | rule |
|---|---|---|
| **library** — importable, tested, no side effects at import | `nq/` | anything another module depends on belongs here eventually |
| **entry points** — a human, a cron, or a workflow invokes it | `scripts/` | must be reachable by a stable path; workflows and tests pin these |
| **one-offs** — ran once, produced an artifact, never imported | `pipelines/<area>/` | free to move; no other code depends on them |

## `nq/` — the library

```
nq/
  data/        ohlcv · membership · eligibility · features · indicators · weekly
               integrity · fundamentals · delivery · earnings · macro · options_oi
               adjustment_guard
  signals/     pure cross-sectional signal primitives (mom_12_1, high_52w, reversal_z, ...)
  engine/      portfolio.simulate · signal_book · rebalance_book · exits · panel
  validation/  bootstrap · dsr · cpcv · metrics · factor_ic
  runner/      research (adjudicate/evaluate_overlay) · scan
  paper/       book · forward_wall · model_wall · judge · wall_cron
  strategy/    live signal emission
  research/    overlays · conviction · residual · setups · breadth50
```

**Three engines, three shapes** — they are not variants of each other:

| engine | selection | exits |
|---|---|---|
| `portfolio.simulate` | rank-gate top-N | ATR stop + fixed target + trail |
| `signal_book` | discrete entry events | per-signal stop + R-multiple target |
| `rebalance_book` | equal-weight top-N on a cadence | **fall out of the ranking buffer** — no stops, no targets |

All three return the same contract — `{equity_curve, trades, metrics}` — which is what lets
`nq.runner.research.adjudicate` hold any of them to the same bar without knowing which engine ran.

## `pipelines/` — executable work, by purpose

```
pipelines/
  build/         20  data construction: harvest, backfill, fixtures, reference builders
  research/      39  experiment runners for a specific pre-registration
  diagnostics/   77  one-off explorations; write to diagnostics/research/
  audit/          9  integrity checks; exit-code-as-verdict
  report/        11  renderers and exporters
```

Files here compute `ROOT` as `Path(__file__).resolve().parents[2]` (two levels down, not one).
They still `sys.path.insert(ROOT / "scripts")` because the library-like modules they import
deliberately stayed there — see below.

## `scripts/` — 58 files that cannot or should not move

Three kinds, and the reason each stays is mechanical rather than aesthetic:

1. **Workflow-pinned entry points** (~12) — `.github/workflows/*.yml` invokes them by path:
   `run_paper_cron` · `run_bhanushali_cron` · `run_bhanushali_monitor` · `run_intraday_scan` ·
   `run_judge_cron` · `run_blend_paper` · `run_zoo_shadow_book` · `bhanushali_review_scorecard` ·
   `archive_weekly_snapshot` · `archive_weekly_cards` · `run_forward_accumulators` ·
   `scheduler_health`.
2. **Test-pinned** (~15) — imported by `tests/`, or named as a path literal inside a test.
   `tests/test_output_contracts.py` additionally scans the workflow YAML and keys on the workflow
   *stem*, so renaming a workflow file breaks the suite.
3. **De-facto libraries wearing a script prefix** (~20) — the real reason the tree looked distorted.
   `run_bhanushali_path1` has **~90 importers**; `run_bhanushali_weekly_crs` 23;
   `run_bhanushali_sixstep` 21; `diag_sleeves` 17; `diag_swing_strategy_survey` 10;
   `diag_supertrend_system` 9.

**Promoting group 3 into `nq/` is the obvious next step and is deliberately NOT bundled here.**
It touches ~90 import sites; a rename of that size belongs in its own change with its own
verification, not folded into a directory sweep where a failure would be indistinguishable from a
move that went wrong.

## Data and output trees

| path | holds |
|---|---|
| `data/` | inputs: `ohlcv.pkl`, `weekly_panel.parquet`, PIT fundamentals / macro / delivery / OI, membership CSVs |
| `diagnostics/research/` | outputs written by `pipelines/diagnostics/` — artifacts only, no code |
| `results/` | live and paper state committed by crons; hash-chained wall logs |
| `research/` | research corpus: findings, pre-registrations, registries |
| `models/` | frozen strategy configs (`models/long_horizon/config.json`) |
| `forward/` | forward-wall pre-registration — the contract the hash chain anchors to |
| `docs/` | design docs + `decisions/` ADRs + auto-generated dependency maps |

## Invariants

- **`docs/DEPENDENCY_MAP.md` is generated** — `python scripts/gen_depgraph.py` after any `nq/**` or
  `config.py` change. Deterministic; re-running gives byte-identical output.
- **The golden masters gate everything**: `tests/test_stage2_golden.py` (exact-equality on 15
  metrics + a ledger hash) and `tests/test_r94_golden.py` (3 pinned cells). Any engine change must
  leave both byte-identical or regenerate the fixture in the same commit with the diff stated.
- **`pytest` is the only hard CI gate** (`ruff` and `mypy` are advisory). Python is pinned to 3.12
  in CI because the goldens are byte-compared.
- **`scripts/` has no `__init__.py`** yet a few modules use `from scripts.X import ...`. That works
  only via `pythonpath=["."]` plus implicit namespace packages — a latent fragility, noted here so
  it is a known condition rather than a surprise.

## Known untidiness, recorded rather than hidden

- `long_horizon/` (15 files) is vestigial — superseded by `nq/strategy/long_horizon.py` plus
  `models/long_horizon/config.json`.
- Three trees carry "research": `research/`, `diagnostics/research/`, `long_horizon/research/`.
- `frontend pictures/` has a space in its name; `nifty_satvik.egg-info/` is a build artifact.
- `skills/repo-map/SKILL.md` is stale — it describes a `src/` tree that no longer exists.
