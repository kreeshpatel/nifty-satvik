# Research findings

One markdown file per **significant finding**, named `NNNN-short-slug.md` (zero-padded,
append-only — never renumber, never delete; a reversed result is itself a finding worth
keeping so it isn't re-tried). This directory starts empty and accrues as the program runs.

This is distinct from the other two ledgers (see [`../../skills/research-log/SKILL.md`](../../skills/research-log/SKILL.md) for the full routing):

| Record | Goes to |
|---|---|
| A **tested overlay** (PROMOTE/SHADOW/REJECT) | [`../overlay_registry.md`](../overlay_registry.md) (append a row) |
| A **param / overlay change** | [`../config_CHANGELOG.md`](../config_CHANGELOG.md) + an ADR in [`../../docs/decisions/`](../../docs/decisions/) |
| A **significant finding / mechanism** | here — one `NNNN-*.md` file |

## Finding-file format

```
# NNNN — <title>

- Status: <SUPPORT | KILL | INCONCLUSIVE | OPEN>
- Date: <YYYY-MM-DD>   Pre-registration: <link, written BEFORE running>

## Hypothesis
What should the data look like if this is real edge?

## Method
Data window, universe, harness config, post-tax (STCG 20%) + post-cost (1x/2x/3x),
walk-forward folds, block bootstrap (block=63, n=5000), sub-periods (2017-21 / 2022-26).

## Result
The actual numbers — ΔCAGR / ΔSharpe / ΔSortino / ΔCalmar / ΔMaxDD / Δturnover,
all post-tax post-cost, with the bootstrap CI.

## Root-cause readout (REQUIRED)
WHY it works or fails — the mechanism, not just the metric. "Underpowered" is a
first-class outcome, never massaged into a pass (charter.md governing methodology).

## Next setup
What this result frames as the next experiment.
```

Promotion is decided by the strict bar in [`../../docs/LIVE_OVERLAY_PROTOCOL.md`](../../docs/LIVE_OVERLAY_PROTOCOL.md) — a finding here is evidence, not a deployment.

## Findings index

| id | date | title | status |
|----|------|-------|--------|
| [0001](0001-C4-momentum-horse-race.md) | 2026-06-28 | C4 momentum horse-race — `sma200_slope_63` is the best sole entry ranker (G2 retired) | KILL (3 replacement candidates) → entry CONFIRMED |
