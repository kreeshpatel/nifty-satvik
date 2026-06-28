---
name: research-log
description: >
  Use when recording any research result, experiment verdict, parameter change,
  or architectural decision in the long-horizon program. Trigger phrases:
  "record a finding", "log result", "log verdict", "pre-register", "registry",
  "ADR", "decision record", "overlay registry", "finding file", "config changelog".
---

# Research Log — How to Record a Finding

The institutional memory compounds only if every result is written down in the
right place, in a standard format, before it can be massaged post-hoc.
This skill tells you WHERE each kind of record goes and WHAT to put in it.

---

## The golden rule (from charter.md §1)

> Never just pass/fail a method. Every experiment ends in a **root-cause readout**:
> the mechanism (why it works or fails, not just the metric) and the **next setup**
> the stats frame. "Underpowered" is a first-class outcome, never massaged into a pass.

A verdict without a root-cause readout is not a complete record. Do not close a
finding file until the mechanism section is filled in.

---

## Decision tree — where does this result go?

```
Did you run an experiment (backtest / IC / walk-forward)?
├── YES → write a finding file   →  long_horizon/research/findings/NNNN-<slug>.md
│         also append a row      →  long_horizon/research/overlay_registry.md
│         (one row per tested overlay / rule, even KILLs)
│
└── NO — is this a config or live-overlay change?
    ├── YES → append to          →  long_horizon/research/config_CHANGELOG.md
    │         AND write an ADR   →  docs/decisions/NNNN-<slug>.md
    │         (follow LIVE_OVERLAY_PROTOCOL.md for promotion gates)
    │
    └── NO — is this a significant mechanism or structural observation
              (not a trial, but something you learned)?
              └── YES → add a note to brain.md "What we've learned" section,
                        or a finding file if it's substantive enough to stand alone.
```

---

## 1. Finding file — `long_horizon/research/findings/NNNN-<slug>.md`

One file per finding. `NNNN` = zero-padded sequential integer (next after the
highest existing file in that directory). The slug is a short kebab-case name.

### Required sections

```markdown
# NNNN — <Title>

**Status:** PRE-REGISTERED | RUNNING | PROMOTE-CANDIDATE | UNDERPOWERED | KILL
**Date registered:** YYYY-MM-DD
**Date closed:** YYYY-MM-DD (leave blank while RUNNING)

## Hypothesis

One sentence: what should the data look like if this rule/feature/overlay is real edge?
Include the falsification condition (what would kill it).

## Method

- Universe: membership-masked large+mid (ADV >= 5cr, 0 <= D/E < 1.5), Nifty-500 PIT
- Signal / feature / overlay being tested (exact code path or formula)
- Baseline locked at: [baseline_v0: 26.1% gross / 23.1% after-tax CAGR / Sharpe 1.02 gross / 0.83 after-tax — from research/baseline_v0.json (supersedes 30.26%/1.15, 2026-06-27)]
- Metric gate (pre-registered, copied from pre-reg doc if applicable):
  - ΔSharpe >= +0.10 post-tax post-cost
  - ΔCalmar >= +0.05
  - 2022–2026 sub-period ΔCAGR > 0
  - Walk-forward fold-pass >= 60%
  - Bootstrap 95% CI on ΔSharpe excludes 0
  - Turnover increase <= 30%
  - Mechanism explainable in one sentence
- n_trials count at time of registration (from diagnostics/research/n_trials.json):

## Result

| Metric | Baseline | With overlay | Delta |
|--------|----------|--------------|-------|
| CAGR | 26.1% gross / 23.1% after-tax | | |
| Sharpe | 1.02 gross / 0.83 after-tax | | |
| DD | -41.9% | | |
| Calmar | 0.62 | | |
| WR | 59.7% | | |
| Trades/yr | ~152 | | |
| 2022–2026 CAGR | | | |
| WF fold-pass | — | | |
| Turnover Δ | — | | |

Bootstrap 95% CI on ΔSharpe: [lo, hi]
n_trials at run: (increment n_trials.json before running)

## Verdict

**PROMOTE-CANDIDATE / UNDERPOWERED / KILL**

State which gate(s) passed and which failed.
If UNDERPOWERED: state what sample size or forward-wall accrual would be needed
to reach the minimum-detectable effect.

## Root-cause readout

WHY does this work or fail — the mechanism, not just the metric.

- If PROMOTE-CANDIDATE: what is the economic reason the overlay adds value?
  Is it orthogonal to existing signal? Does it fail any subgroup?
- If UNDERPOWERED: what would make the signal stronger? Which years/conditions
  drive the positive point estimate?
- If KILL: what is the structural reason? (whipsaw? collinear with existing?
  regime-specific? cost-dominated?) Does it reframe as a DIFFERENT test worth
  pre-registering?

## Next setup

What does this result frame for the next experiment?
Even a KILL should point somewhere.
```

---

## 2. Overlay registry — `long_horizon/research/overlay_registry.md`

**Append-only.** One row per tested overlay or rule — including KILLs.
Never edit existing rows.

### Row format

```markdown
| NNNN | YYYY-MM-DD | <overlay name> | PROMOTE-CANDIDATE / UNDERPOWERED / KILL | ΔSharpe | ΔCalmar | WF pass | Root-cause (one line) |
```

### Header (if file does not exist yet, create it with this header first)

```markdown
# Long-Horizon Overlay Registry

Append-only. One row per tested overlay, including kills. Mechanism column is
mandatory — a bare pass/fail row is not a complete record.

| ID | Date | Overlay | Verdict | ΔSharpe | ΔCalmar | WF pass | Mechanism (one line) |
|----|------|---------|---------|---------|---------|---------|----------------------|
```

---

## 3. Config / live-overlay changelog — `long_horizon/research/config_CHANGELOG.md`

Every change to `models/long_horizon/config.json` (frozen cfg) or to the
`live_overlays` block within it gets a row here, in addition to an ADR.

```markdown
| Date | Author | Field changed | Old value | New value | Reason / ADR ref |
|------|--------|---------------|-----------|-----------|------------------|
```

**The frozen cfg fields** (stop_atr_mult 3.67, target_pct 22.52, etc.) are
derived once on the pre-2017 train slice and are never changed without a full
re-derive + cloud walk-forward gate. A finding file + ADR is mandatory before
any frozen-cfg edit.

**The live_overlays block** (vol_target_annual, vol_window, vol_floor) follows
the LIVE_OVERLAY_PROTOCOL.md promote gate. Changes go into live_overlays only
after the PROMOTE-CANDIDATE gate clears; they do NOT affect the research
backtest or the golden master.

---

## 4. Architectural decision record — `docs/decisions/NNNN-<slug>.md`

Required for: any live-overlay promotion, any frozen-cfg change, any structural
change to the universe filter or exit logic.

```markdown
# NNNN — <Title>

**Date:** YYYY-MM-DD
**Status:** PROPOSED | ACCEPTED | SUPERSEDED
**Supersedes:** (NNNN if applicable)

## Context

What forced this decision? What was the state before?

## Decision

What was decided, exactly. Quote the config key and new value if applicable.

## Consequences

- Live effect (paper book only, until paper gate clears)
- Backtest / golden master: unaffected / regenerated (state which)
- Rollback: how to undo (single field in config.json? env var?)

## Gate cleared

Paste the gate row from overlay_registry.md that authorized this promotion.
```

---

## 5. Pre-registration discipline

**Register BEFORE running.** Write the hypothesis and metric gate in the finding
file (Status: PRE-REGISTERED) before executing the backtest. This is the only
way to prevent post-hoc threshold adjustment.

Increment `diagnostics/research/n_trials.json` before each new trial
(not after). The Deflated Sharpe Ratio gate uses the cumulative trial count —
understating it makes the DSR bar lower than it should be.

The holdout wall (HOLDOUT.md) applies: development folds are for hypothesis
generation. A result that depends on the holdout to achieve statistical
significance has consumed the holdout — record that explicitly.

---

## Quick reference

| What happened | Where it goes |
|---------------|---------------|
| Ran a backtest / IC test / WF | finding file + overlay registry row |
| Changed config.json (frozen cfg or live_overlays) | config_CHANGELOG.md + ADR |
| Structural observation (no trial) | brain.md "What we've learned" (or finding file if substantive) |
| Significant architectural decision | ADR in docs/decisions/ |
| Pre-registration before running | finding file (Status: PRE-REGISTERED) |

---

## What "complete" looks like

A finding is complete when:

1. The finding file has all required sections filled, including root-cause readout
   and next setup.
2. The overlay registry has a new row (even for a KILL).
3. If the verdict is PROMOTE-CANDIDATE: a config_CHANGELOG row + ADR exist.
4. n_trials.json was incremented before the run.

A finding with a blank mechanism section is not complete. Write the root-cause
even if the answer is "we don't know why — here is what the data suggests."
