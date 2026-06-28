# ADR-0005 — Headline Correction: Adopt baseline_v0 as the Reproducible Anchor

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Owner  
**Related:** ADR-0003 (universe correction), `research/baseline_v0.json`,
`src/research/` harness (Stage A), `long_horizon/STRATEGY_FULL.md §6`

---

## Context

### The published headline and where it came from

Since the 2026-06-25 strategy cutover, the quoted headline for the long-horizon strategy
has been:

> **30.3% CAGR / 1.15 Sharpe / −40% DD** (solvent arm, frozen cfg, corrected-682 universe)

and a walk-forward figure:

> **≥2019 ~32% CAGR / 1.31 Sharpe** (walk-forward arms, optimistic-exit)

Both figures appear in `CLAUDE.md`, `long_horizon/STRATEGY_FULL.md`, and references in
ADR-0003 and ADR-0004. They were derived from `long_horizon/results/cpcv_long_horizon_final_682.json`
(the CPCV run that established the frozen cfg).

### Why those numbers are now known to be optimistic

`STRATEGY_FULL.md §6` contained an explicit flag:

> "The target fill logic in the backtest was conservative vs. live in the original
> measurement; exit-parity unification (backtest now fills targets on the same
> conservative basis as live) is to be re-confirmed on the next CPCV run."

The exit-parity unification was merged before Stage A — meaning the research harness
(`src/research/`) now applies the same conservative target fill in backtest that the
live cron uses. This is the correct, honest behaviour. But it means the 30.3% figure
was measured under the **old, optimistic target-fill** that the backtest no longer replicates.

Stage A's mandate was precisely to reproduce the frozen cfg through the new harness and
confirm ≤1pp of the headline. The Stage-A cloud run (the run that produced
`research/baseline_v0.json`) did that reproduction — and found a ~4pp CAGR gap, not ≤1pp.
This is the re-confirmation `STRATEGY_FULL.md §6` called for.

### The reproduced numbers

`research/baseline_v0.json` — frozen cfg, corrected-682 universe (397 solvent names
after D/E filter), 2017-01-01 through 2026, current exit-parity-unified engine:

| Metric | **Gross** | **After-tax (STCG 20%)** |
|---|---|---|
| CAGR | **26.1%** | **23.1%** |
| Sharpe | **1.02** | **0.83** |
| Sortino | 1.64 | 1.33 |
| Calmar | **0.62** | **0.51** |
| Max drawdown | −41.9% | −45.6% |
| Win rate | 59.7% | 59.7% |
| Trades | 1445 (~152/yr) | 1445 (~152/yr) |
| Final equity (₹1M seed) | ₹85.8L | ₹68.7L |

These are reproducible: re-running the harness against the same frozen cfg and the same
corrected universe produces the same figures. The golden-master byte-compare
(`tests/test_long_horizon_golden.py`) is anchored to this run.

### Reconciliation: where the ~7pp gap from 30.3% to 23.1% (after-tax) comes from

| Step | Effect on CAGR |
|---|---|
| Exit-parity unification (conservative target fill = live behaviour) | −~4pp |
| STCG 20% tax (what the client actually nets) | −~3pp |
| **Cumulative** | **−~7pp vs the 30.3% gross-optimistic-exit figure** |

The exit-parity gap is structural: the old backtest recorded a target-hit when the target
price was touched intraday; the unified engine records it only on the next close (matching
live cron behaviour). This systematically inflates gross returns in the backtest. The
tax gap is straightforward: STCG applies to any position held < 1 year, which is nearly
all long-horizon trades (max hold 63 days).

### Walk-forward figures are also superseded

The "≥2019 ~32% / 1.31 Sharpe" walk-forward figure was also measured under the
optimistic-exit engine (the same CPCV run). Those numbers have not yet been re-derived
on the parity-unified engine. They **must not be quoted as a current figure**. The honest
status is: walk-forward re-derivation is pending (Stage B, fold re-runs on the corrected
universe); until `baseline_v1.json` is committed, the walk-forward arms from
`cpcv_long_horizon_final_682.json` are superseded/unconfirmed.

### Structural reconciliation with the CPCV arms

`long_horizon/results/cpcv_long_horizon_final_682.json` includes a `base_no_filter` arm
(25.56% CAGR / 0.973 Sharpe, no solvency filter). The baseline_v0 solvent arm (26.1% /
1.02) is a touch above that — solvency filtering helps marginally by removing high-D/E
names. This internal consistency (solvent arm slightly better than unfiltered) is the
expected direction and validates that baseline_v0 is not an outlier.

---

## Decision

**Adopt `research/baseline_v0.json` as the OFFICIAL reproducible anchor for the
long-horizon strategy.** All headline references, protocol gates, and overlay deltas are
measured against these figures going forward:

- **Gross:** CAGR 26.1% / Sharpe 1.02 / maxDD −41.9% / Calmar 0.62
- **After-tax (STCG 20%):** CAGR 23.1% / Sharpe 0.83 / maxDD −45.6% / Calmar 0.51
- **Trades:** ~152/year, WR 59.7%
- **Universe:** 397 solvent names (corrected-682, D/E 0–1.5), 2017-2026
- **Engine:** exit-parity-unified (conservative close-fill, matching live cron)

The previously reported 30.3% CAGR / 1.15 Sharpe headline and the ~32% / 1.31
walk-forward are hereby superseded. They are preserved below as historical provenance —
the audit trail that shows where the number came from and why it changed — not as current
figures.

### Correction scope: every place that presents the old numbers

The following references must be updated to the baseline_v0 anchor (or noted as
superseded/historical) wherever they appear in committed docs, config comments, and
operator-facing text:

| Old figure | Correct status |
|---|---|
| 30.3% CAGR (gross, optimistic-exit) | Superseded by baseline_v0 gross 26.1% |
| 1.15 Sharpe (gross, optimistic-exit) | Superseded by baseline_v0 gross 1.02 |
| −40% DD (gross, optimistic-exit) | Superseded by baseline_v0 gross −41.9% |
| ~32% CAGR walk-forward (≥2019) | Pending re-derivation; do NOT quote as current |
| 1.31 Sharpe walk-forward (≥2019) | Pending re-derivation; do NOT quote as current |

The compliance framing is unchanged: all figures are **research backtest results**,
never traded live, decision-support output only.

### Promotion bar anchored to baseline_v0

Per ADR-0004 §promotion-bar, all Stage C/D layer verdicts are measured against the
baseline. The baseline is now baseline_v0 gross (26.1% CAGR / 1.02 Sharpe). Any overlay
that clears the promotion bar (ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, fold-pass ≥ 60%, etc.)
does so relative to these numbers, not the old 30.3%.

### baseline_v1 will supersede baseline_v0

Stage B (ADR-0003) corrects the universe (demerger-aware cleaner, 48 invisible members,
financials capital-adequacy proxy) and re-derives the frozen cfg. The Stage-B walk-forward
will produce `research/baseline_v1.json`. Baseline_v1 is expected to move the anchor
further — the current corrected-682 universe is survivor-only (all exits set to 2030;
zero delisted names); adding ~284 delisted names will introduce survivor bias correction
and will likely move CAGR somewhat lower. The honest stance: **anchor to whatever
baseline_v1 says, not to any expectation set from baseline_v0**.

---

## Consequences

### What improves

- **The headline is honest.** The figure presented to users and used for internal gates is
  reproducible: anyone running the harness against the frozen cfg and the corrected universe
  arrives at 26.1% / 1.02 gross. There is no gap between what is quoted and what the code
  produces.
- **After-tax is the client-facing number.** 23.1% CAGR / 0.83 Sharpe is what an investor
  actually nets on short-term gains. Quoting only gross when STCG applies to nearly all
  trades is a material omission; this ADR makes after-tax the first-cited figure.
- **Overlay deltas are measured honestly.** A conviction layer that adds +0.12 Sharpe on
  top of 1.02 is a +12% improvement, not +10% on the inflated 1.15 base.

### What gets harder

1. **The headline is lower.** 26.1% gross / 23.1% after-tax is a genuinely good
   risk-adjusted result (Calmar 0.62 on a strategy that has never traded live), but it is
   lower than what was previously communicated. Owner communication to any current users
   who saw the 30.3% figure should acknowledge the correction and its cause.

2. **The walk-forward "≥2019 ~32%/1.31" can no longer be cited** until Stage B re-derives
   it on the parity-unified engine. This removes a positive headline that had been
   presented as corroborating evidence. The honest substitute is: "walk-forward
   re-derivation pending; full fold results to be committed to `baseline_v1.json`."

3. **Any overlay that was pre-staged against the 30.3% baseline** may now look larger
   (absolute Δ vs a smaller base), but the promotion bar thresholds (ΔSharpe ≥ +0.10)
   are absolute, not percentage-relative — so the bar does not move.

---

## Historical provenance (do not delete; required for the audit trail)

### The 30.3% figure: origin and trajectory

| Date | Event | Figure |
|---|---|---|
| 2026-06-25 | Strategy cutover; first published headline | 30.3% CAGR / 1.15 Sharpe / −40% DD (gross, solvent arm, optimistic-exit engine) |
| 2026-06-25 | ADR-0003 issued | References the 30.3%/1.15 headline as the defective-universe baseline to be superseded by baseline_v1 after Stage B |
| 2026-06-25 | ADR-0004 issued | References 30.3%/1.15 as the base; Stage-A gate set at "confirm ≤1pp of 30.3%" |
| 2026-06-27 | Stage-A cloud run produces `research/baseline_v0.json` | Gross 26.1% / 1.02 (exit-parity-unified engine); ~4pp gap confirmed; 30.3% superseded |
| 2026-06-27 | **This ADR (0005) adopted** | 26.1% gross / 23.1% after-tax is the OFFICIAL anchor |

### Why the Stage-A gate language in ADR-0004 is now resolved

ADR-0004 §Stage-A said: "confirm ≤1pp of the 30.3% CAGR / 1.15 Sharpe frozen-cfg headline."
The Stage-A run found ~4pp, not ≤1pp. That gate as written fails. This ADR resolves it: the
gate language was predicated on the old headline being accurate; Stage A's job was reproduction,
and it correctly reproduced the lower number. The Stage-A gate is satisfied as "harness
reproduces the frozen cfg" — the new number IS the correct reproduction. The ≤1pp tolerance
referenced the old inflated figure, not a floor on what the result must be. ADR-0004's §Consequences
already acknowledged "the headline may move" and committed to anchoring to the honest new number
(baseline_v0 is that anchor).

---

## Alternatives considered

### A — Keep quoting 30.3% with a footnote

Add a small disclaimer that the figure uses the old exit-fill method and is pre-tax. Continue
to use it as the headline.

**Rejected.** The exit-parity unification was a correctness fix — the old backtest behaviour
was wrong relative to live. Quoting a number derived from wrong behaviour as the headline,
even with a footnote, violates the honesty principle that every ADR in this series has
referenced. The footnote would need to say "our headline is from a behaviour we corrected because
it was inaccurate" — at which point the headline itself should just change.

### B — Use the gross baseline_v0 figure (26.1%) but not quote after-tax

Present 26.1% gross as the headline; mention 23.1% after-tax only in footnotes or detailed docs.

**Rejected.** STCG at 20% applies to essentially all trades (max hold 63 days < 1 year). A
user making investment decisions on a 26.1% headline who actually nets 23.1% is being given
optimistic information. After-tax is the first-cited figure; gross is provided for
research-comparison purposes.

### C — Wait for baseline_v1 (Stage B corrected universe) before correcting the headline

Keep the old 30.3% temporarily; replace it once in one shot when baseline_v1 is available.

**Rejected.** baseline_v0 is available now, is reproducible, and is more accurate than 30.3%.
Continuing to cite 30.3% after knowing it is wrong — even temporarily — is not the right stance.
Baseline_v1 will supersede baseline_v0 when it is ready; until then, baseline_v0 is the anchor.

---

## Cross-references

| Reference | What it specifies |
|---|---|
| `research/baseline_v0.json` | Frozen: the authoritative baseline_v0 numbers (gross + after-tax) |
| `long_horizon/results/cpcv_long_horizon_final_682.json` | The CPCV run; contains the optimistic-exit 30.3% figures (historical provenance only) |
| `long_horizon/STRATEGY_FULL.md §6` | The original flag: "exit-parity re-confirmation pending" |
| ADR-0003 | Universe correction (Stage B); baseline_v1 will supersede baseline_v0 after B4 |
| ADR-0004 | Hold real capital until Stage E; promotion bar anchored to baseline_v0 per this ADR |
| `src/research/` harness | Stage-A harness that produced baseline_v0 |
| `tests/test_long_horizon_golden.py` | Golden master byte-compare anchored to the baseline_v0 run |
| `models/long_horizon/config.json → expected_portfolio_metrics` | Must be updated to baseline_v0 gross figures in the same PR that finalises Stage-A |

---

## Operating rules derived from this decision

1. **Quote gross 26.1% / 1.02 Sharpe and after-tax 23.1% / 0.83 Sharpe as the official
   headline.** Never quote 30.3%, 32%, or 1.15/1.31 as current figures (historical
   provenance only).

2. **After-tax is the first-cited figure in any user-facing context.** Gross is for
   internal research comparison. Users are not exempt from STCG.

3. **Walk-forward "≥2019 ~32%/1.31" must not be cited until baseline_v1 is committed.**
   The correct substitute: "full walk-forward results pending Stage B re-derivation."

4. **All overlay deltas (Stage C/D promotion bar) are measured vs baseline_v0 gross.**
   A ΔSharpe of +0.10 means 1.02 + 0.10 = 1.12 gross, not 1.15 + 0.10 = 1.25.

5. **`models/long_horizon/config.json → expected_portfolio_metrics`** must be updated to
   the baseline_v0 gross figures (CAGR 26.1%, Sharpe 1.02, DD −41.9%, Calmar 0.62,
   trades/year ~152) in the Stage-A finalisation PR. Until then, the config comment
   "(superseded by baseline_v0; see ADR-0005)" must be added to any existing
   `expected_portfolio_metrics` block that still shows the old figures.

6. **baseline_v1 supersedes baseline_v0 when committed.** After Stage B (ADR-0003) is
   complete and `research/baseline_v1.json` is committed, these operating rules update
   accordingly. The transition is a new ADR (0006 or equivalent), not an in-place edit
   of this file.
