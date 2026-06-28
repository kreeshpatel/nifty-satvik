---
name: edge-research-pipeline
description: >
  Structured edge-discovery procedure for the long-horizon overlay research program.
  Trigger phrases: "find an edge", "new overlay idea", "research a hypothesis",
  "edge discovery", "strategy idea", "test a new rule", "is there an overlay here",
  "phase 5 candidate", "conviction feature idea".
---

# Edge-Research Pipeline — Long-Horizon Overlay Discovery

This document is the staged procedure for converting a raw overlay idea into a
pre-registered, harness-tested finding with a deterministic verdict. It wraps the
five source stages adapted from the `claude-trading-skills` edge pipeline
(MIT, Copyright 2026 TraderMonty — see `skills/_ingested/claude-trading-skills.md`)
into our specific research discipline.

The pipeline has four stages plus a gating review before any result is logged.
Every stage produces a concrete artifact. Nothing proceeds to the next stage without
that artifact existing.

---

## §0 — Read these before starting

1. **`skills/overlay-testing/SKILL.md`** — the end-to-end harness protocol for running
   any overlay against `baseline_v0` (baseline_v0: 26.1% gross / 23.1% after-tax CAGR;
   Sharpe 1.02 gross / 0.83 after-tax; supersedes the optimistic-exit 30.26%/1.15
   measurement, 2026-06-27). Baseline source: `research/baseline_v0.json`.
   Never anchor on the re-derived 34.67% in `cpcv_long_horizon_tradelog_682.json`.

2. **`skills/sell-replace-logic/SKILL.md`** — read first if the idea is an exit or
   rotation rule specifically.

3. **`long_horizon/STRATEGY_FULL.md §11`** — the rejection log.
   If your idea is materially similar to a prior rejection, stop here unless you have
   genuinely new evidence (new data, different sub-period, different mechanism formulation).

4. **Do-not-relitigate list** (§11 kills — require extraordinary new evidence to re-open):

   | Killed | Why | Re-open condition |
   |--------|-----|-------------------|
   | Market-regime entry gate | Cuts CAGR; sidetracks best bull years | Regime definition that preserves CAGR in those years |
   | Sector-selection overlays | Sector IC ≈ 0; hurt lean years | Sustained sector IC > 0.05 on 2022+ sub-period |
   | Reversal signals (RSI/MACD/ROC) | No orthogonal edge at 63d horizon | IC evidence on the 63d label specifically |
   | Signal-level low-vol blending | Diluted trend signal | Separate vol regime with documented IC |
   | Residual / beta-stripped momentum | No improvement over raw trend | New factor construction |
   | Frog-in-the-pan momentum | No edge on this universe | Different path-smoothness metric |
   | Heavy quality screens on top of debt filter | Over-filtered; reduced breadth | Metric not collinear with existing debt filter |
   | min_hold = 20 | Worst point in sweep | New hold-sweep across different universe definition |

5. **Vol-target overlay already live** (`live_overlays` in `models/long_horizon/config.json`):
   any new sizing overlay must prove it ADDS on top of this baseline — not compete on the
   same drawdown axis.

---

## Stage 1 — IDEATE: write the hypothesis (before touching any code)

Fill in this block, save as
`long_horizon/research/preregistry/<overlay-name>.md`, Status: PRE-REGISTERED.

```
Overlay name: <name>

Hypothesis:
  What mechanism should this exploit? Be specific about why the DATA should
  look different if this overlay is real. If you cannot state the mechanism
  in one sentence, you do not understand it well enough to test it yet.

Predicted direction:
  ΔCAGR [+/-], ΔSharpe [+/-], ΔMaxDD [better/worse/neutral]

Mechanism (one sentence):
  <Complete this before proceeding.>

Failure modes:
  Name at least TWO ways this overlay could hurt in a regime it was not
  designed for.

Prior evidence:
  Is there a §11 rejection close to this? What is genuinely NEW here?
  (New data = ok. Different sub-period = ok. Same test, different seed = NOT new.)

Overlay type:
  entry-filter | selection-re-rank | exit | sizing | conviction-feature

n_trials cost:
  "measurement" (no trial consumed) if this is purely an observation or
  data check.
  "trial N+1" if this is a new hypothesis. Increment
  diagnostics/research/n_trials.json BEFORE running the harness.

kill_criteria:
  # Declare the exact conditions that auto-KILL this idea — before any code.
  # At least two entries required: one per-trade, one sub-period.
  # (adapted from mphinance/alpha-skills trade-hypothesis-ideator, MIT)
  #
  # Example:
  #   - metric: ΔSharpe_ci_low      threshold: 0.0        verdict: KILL
  #   - metric: 2022-26 ΔCAGR       threshold: 0.0        verdict: KILL
  #   - metric: turnover_delta       threshold: +30%       verdict: KILL
  #
  # Fill in your actual thresholds below (copy the promotion bar defaults
  # unless the hypothesis has a specific regime/cost argument for stricter ones):
  - metric: <metric>    threshold: <value>    verdict: KILL
  - metric: <metric>    threshold: <value>    verdict: KILL

Pre-screen (complete before implementation):
  [ ] Mechanism explainable in one sentence
  [ ] Not a decimal-tuned threshold (e.g. slope > 0.0047 = red flag; slope > 0 = ok)
  [ ] Param count <= 3 for the overlay-specific params
  [ ] Not similar to any §11 kill without new evidence
  [ ] Does not require data we do not have PIT (no lookahead)
  [ ] Estimated min 30+ signal opportunities per year on the 682-name universe
```

**A pre-screen failure at this stage = stop. Do not implement.**

---

## Stage 2 — DESIGN: implement as a pluggable, isolated function

Source principle: from `edge-strategy-designer` (adapted). A concept becomes
testable only when it is isolated from the baseline logic.

### Entry/selection overlay signature

```python
def overlay_<name>(
    universe: pd.DataFrame,      # ranked eligible universe for today
    held_tickers: set[str],      # currently held positions
    derived: dict[str, float],   # frozen cfg from models/long_horizon/config.json
    **kwargs,                    # overlay-specific params (keep <= 3)
) -> pd.DataFrame:
    """Return filtered/re-ranked universe. Pure function of inputs.
    Must not modify `derived` or any shared state."""
    ...
```

### Exit overlay signature

```python
def overlay_exit_<name>(
    position: Position,           # from long_horizon/backtest/portfolio.py
    today_ohlc: pd.Series,
    derived: dict[str, float],
    **kwargs,
) -> tuple[bool, str]:
    """(should_exit, reason). Runs AFTER the four mechanical exits
    (stop/target/trailing/time) — cannot override them, only adds an earlier exit."""
    ...
```

### Conviction-feature signature (Phase 5)

```python
def conviction_feature_<name>(
    ticker: str,
    ohlcv: pd.DataFrame,         # PIT OHLCV ending at signal date
    derived: dict[str, float],
    **kwargs,
) -> float:
    """Single scalar in [0, 1] or a raw value to be rank-normalized.
    Must use only data available at signal_date (no lookahead)."""
    ...
```

**File placement:** `long_horizon/overlay/<name>.py`. Do NOT inline into
`portfolio.py` or `long_horizon_cron.py`. The overlay must be independently
importable and testable.

### Pre-implementation overfitting lint (adapted from `edge-strategy-reviewer` C1–C2)

Run this mental lint before writing code. Any fail = revise the design first.

| Check | Fail condition | Action |
|-------|---------------|--------|
| Mechanism clarity | Thesis empty or generic (<10 words, no domain term) | Rewrite or stop |
| Threshold precision | Any threshold with a decimal (slope > 0.014, rank < 0.273) | Round to behavioral level or remove |
| Param count | > 3 overlay-specific params | Cut to essential |
| Condition count | > 5 combined conditions in the overlay | Simplify |
| Regime specificity | Designed for one regime only, no cross-regime validation plan | Add validation plan or flag |
| Sample adequacy | Estimated < 30 signal opportunities/yr on 682 names | Redesign; too restrictive to validate |
| Invalidation | Cannot name 2+ conditions that would falsify the thesis | The hypothesis is not testable yet |

---

## Stage 3 — TEST: run through the harness

Delegate to `skills/overlay-testing/SKILL.md` for the full protocol. Summary:

1. Pre-registration file must already exist (Stage 1).
2. Increment `diagnostics/research/n_trials.json` before dispatching to CI.
3. Dispatch via GitHub Actions for the canonical 682-name universe:
   ```bash
   gh workflow run cpcv-research.yml --ref <branch> \
     -f runner=run_long_horizon_tradelog \
     -f overlay=<name>
   ```
   **Never report local numbers** — local runner uses ~20 survivor-only names
   and prints ~15% CAGR, not the 30% headline. Local runs are for debugging only.
4. Harness self-validation gate: before trusting any overlay result, confirm the
   harness reproduces the §11 rejections as REJECTED. If a §11 kill gets promoted
   by the harness, the harness has a bug — fix it before reporting any overlay result.

### Required outputs (all must be present for a complete verdict)

**4a. Delta metrics vs baseline_v0 — at three friction levels:**

| Metric | 1× cost | 2× cost (reference) | 3× cost |
|--------|---------|---------------------|---------|
| ΔCAGR | | | |
| ΔSharpe | | | |
| ΔSortino | | | |
| ΔCalmar | | | |
| ΔMaxDD | | | |
| Δtrades/yr | | | |

2× cost is the reference column for the promotion bar. The baseline survives 3×
(30.7% → 26.5% → 20.5% per `STRATEGY_FULL.md §10.3`) — but extra-turnover
overlays may not.

**4b. Post-tax mechanics:**
STCG 20% on positions held < 252 trading days. Median hold ~22 days = effectively
all gains are STCG. Apply consistently across baseline and overlay trade ledger.
The delta direction is what matters; absolute post-tax CAGR will shift from headline.

**4c. Sub-period split (non-negotiable):**

| Sub-period | Baseline CAGR | Overlay CAGR | ΔSharpe |
|------------|--------------|--------------|---------|
| 2017–2021 | | | |
| 2022–2026 | 21.5% / 0.84 | | |

An overlay that helps 2017–2021 but hurts 2022–2026 = REJECT, not averaged.
2022–2026 is the deciding sub-period: it reflects live conditions.

**4d. Block bootstrap (block = 63 days, n = 5000):**
```python
from src.validation.bootstrap import block_bootstrap_ci
delta_series = returns_overlay - returns_baseline
ci_low, ci_high = block_bootstrap_ci(
    delta_series, stat="sharpe_annualized",
    block_size=63, n_samples=5000, confidence=0.95,
)
# Required: ci_low > 0.0
```

**4e. Walk-forward fold-pass rate:**
Run overlay on each year as an independent fold. Require ΔSharpe > 0 in ≥ 60%
of folds (≥ 6/10 years, or ≥ 5/8 for the 2019+ survivorship-clean window).

```
Folds: 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026
ΔSharpe>0: [T/F] ...
Pass rate: N/10
```

---

## Stage 4 — REVIEW: adversarial pre-promotion gate

Source principle: adapted from `edge-strategy-reviewer` criteria C1–C8 (MIT,
TraderMonty 2026) — the eight-criterion weighted verdict gate, re-mapped to our
promotion bar. This is a structured skeptic review BEFORE writing the registry entry.

Work through each criterion in order. A hard-fail on any of the first three =
immediate REJECT; stop there.

**Hard-fail criteria (any one = REJECT immediately):**

| # | Criterion | Hard-fail condition |
|---|-----------|---------------------|
| R1 | Mechanism clarity | Thesis is empty, generic, or not falsifiable in one sentence |
| R2 | Overfit complexity | Overlay has >5 conditions, any decimal threshold, or >3 params |
| R3 | 2022–2026 sub-period | ΔSharpe < 0 in the recent sub-period (even if pooled is positive) |

**Scored criteria (all must clear for PROMOTE; see promotion bar):**

| # | Criterion | Our bar |
|---|-----------|---------|
| R4 | ΔSharpe (post-tax, 2× cost) | ≥ +0.10 |
| R5 | ΔCalmar (post-tax, 2× cost) | ≥ +0.05 |
| R6 | Walk-forward fold-pass | ≥ 60% |
| R7 | Block bootstrap CI on ΔSharpe | ci_low > 0 (excludes zero) |
| R8 | Turnover delta | ≤ +30% (Δtrades/yr ÷ baseline trades/yr) |

**Bounded revision loop (adapted from `revision_loop_rules.md`):**

- A first-draft design that fails R1–R3 gets ONE revision pass: fix the design
  flaw, re-run the harness. If it still fails R1–R3, verdict is REJECT — no
  further cycles. This prevents an open-ended "keep tweaking until it passes" loop.
- A result that fails only R4–R8 (but passes R1–R3) may be designated SHADOW —
  log signal, observe live, do not trade — if 4 of the 5 scored criteria hold.
- Anything not reaching SHADOW bar = REJECT. Log the reason; it prevents re-testing.

**Combination test (if multiple overlays are under review simultaneously):**
Overlays that individually PROMOTE or SHADOW may cannibalize each other.
Always test the combined result before promoting more than one overlay at once.

---

## Stage 5 — LOG: write the verdict to the registry

Use `skills/research-log/SKILL.md` for exact file formats and paths.
Summary of mandatory artifacts:

1. **Finding file:** `long_horizon/research/findings/NNNN-<slug>.md` — complete all
   sections including root-cause readout and next setup. A finding without a
   root-cause is not a complete record.

2. **Overlay registry row:** append to `long_horizon/research/overlay_registry.md`.
   Append-only, never edit prior rows.

   ```
   | NNNN | YYYY-MM-DD | <overlay-name> | PROMOTE-CANDIDATE / SHADOW / UNDERPOWERED / KILL | ΔSharpe | ΔCalmar | WF pass | Root-cause (one line) |
   ```

3. **If PROMOTE-CANDIDATE:**
   - Config changelog entry in `long_horizon/research/config_CHANGELOG.md`
   - ADR in `docs/decisions/NNNN-<slug>.md`
   - Follow `LIVE_OVERLAY_PROTOCOL.md` for the paper-book promote gate

4. **If SHADOW:**
   - Wire the overlay to write a scorecard entry into
     `results/overlay_<name>_log.json` — zero impact on sizing/entry/exit
   - Record target forward-wall size (minimum 50 live observations before
     the next evaluation is admissible)

5. **If KILL:**
   - Fill in "Do not re-test unless" in the finding file — what evidence would
     reopen it? If you cannot name a specific falsification condition, the
     hypothesis is not scientifically framed.

---

## Promotion bar (exact; non-negotiable)

PROMOTE only if **all seven** hold:

1. Post-tax post-cost ΔSharpe ≥ **+0.10** (at 2× cost)
2. Post-tax post-cost ΔCalmar ≥ **+0.05** (at 2× cost)
3. **2022–2026** sub-period shows **positive ΔCAGR**
4. Walk-forward fold-pass rate ≥ **60%**
5. Block bootstrap 95% CI on ΔSharpe **excludes zero** (ci_low > 0)
6. Turnover increase ≤ **30%**
7. Mechanism **explainable in one sentence** to the operator

SHADOW if 4–5 of the above hold.
REJECT otherwise. Reasons must be logged.

---

## Summary — artifact checklist

| Stage | Artifact | Location |
|-------|---------|----------|
| 1 — Ideate | Pre-reg file (Status: PRE-REGISTERED) | `long_horizon/research/preregistry/<name>.md` |
| 1 — Ideate | n_trials.json incremented | `diagnostics/research/n_trials.json` |
| 2 — Design | Overlay implementation | `long_horizon/overlay/<name>.py` |
| 3 — Test | CI run result (canonical 682 names) | GitHub Actions → cpcv-research.yml |
| 3 — Test | Delta table (1×/2×/3× cost, post-tax) | In finding file |
| 3 — Test | Sub-period split 2017–21 / 2022–26 | In finding file |
| 3 — Test | Block bootstrap CI | In finding file |
| 3 — Test | Walk-forward fold table | In finding file |
| 4 — Review | Adversarial gate (R1–R8) passed | In finding file |
| 5 — Log | Finding file (all sections complete) | `long_horizon/research/findings/NNNN-<slug>.md` |
| 5 — Log | Registry row | `long_horizon/research/overlay_registry.md` |
| 5 — Log (Promote) | Config changelog + ADR | `long_horizon/research/config_CHANGELOG.md` + `docs/decisions/` |

---

## What a KILL means (root-cause discipline)

From `skills/research-log/SKILL.md` (the golden rule): never just pass/fail.
Every experiment ends in a **root-cause readout**: the mechanism (why it works
or fails, not just the metric) and the **next setup** the stats frame.

A KILL finding is only complete when:
- The structural reason is named (whipsaw? collinear with sma200_slope_63?
  regime-specific? cost-dominated? sample inadequate?)
- The reframe is offered: does this KILL point toward a different hypothesis
  worth pre-registering, or does it close the family entirely?
- "Underpowered" is a first-class status — not a failed test that can be
  silently ignored, but an explicit record of what sample size would be needed.

---

## Cross-references

- **Harness protocol:** `skills/overlay-testing/SKILL.md`
- **Exit/rotate overlays:** `skills/sell-replace-logic/SKILL.md`
- **Research logging:** `skills/research-log/SKILL.md`
- **Registry:** `long_horizon/research/overlay_registry.md`
- **Pre-reg directory:** `long_horizon/research/preregistry/`
- **Finding files:** `long_horizon/research/findings/`
- **Rejection log:** `long_horizon/STRATEGY_FULL.md §11`
- **Baseline result:** `long_horizon/results/cpcv_long_horizon_final_682.json` (frozen-cfg arm)
- **Frozen cfg:** `models/long_horizon/config.json`
- **n_trials:** `diagnostics/research/n_trials.json`
- **Source adapted from:** `claude-trading-skills` edge pipeline
  (`edge-pipeline-orchestrator`, `edge-candidate-agent`, `edge-concept-synthesizer`,
  `edge-strategy-designer`, `edge-strategy-reviewer`) — MIT, Copyright 2026 TraderMonty.
  Methodology adapted; no verbatim code copied. Full ingest notes in
  `skills/_ingested/claude-trading-skills.md`.
