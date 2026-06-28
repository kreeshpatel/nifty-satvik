---
name: overlay-testing
description: >
  Use when testing any overlay, enhancement, or modification against the locked long-horizon
  baseline. Trigger words: "test an overlay", "is this edge real", "run the harness", "promote",
  "shadow", "baseline comparison", "significance test", "ΔSharpe", "does this improve", "should
  we add", "validate against baseline", "overlay registry".
---

# Overlay Testing Protocol — Long-Horizon Phase 4

This document is the end-to-end protocol for testing ANY overlay, rule modification, or
parameter change against the locked long-horizon baseline. Follow every step in order. Skipping
significance or sub-period tests has historically caused real regressions (see §11 rejections
in `long_horizon/STRATEGY_FULL.md`).

---

## 0. Prerequisites — read these first

Before testing anything:

1. **`long_horizon/STRATEGY_FULL.md` §11** — the rejection log. If your overlay is materially
   similar to one already tested, you need new evidence (new data, new sub-period, genuinely
   different formulation) before spending a trial on it. Re-running the same test is not new
   evidence.
2. **`skills/sell-replace-logic/SKILL.md`** — if your overlay is an exit rule or rotation rule
   specifically, read that skill first. It has its own candidate list and combination-test notes.
3. **`long_horizon/results/README.md`** — the baseline number ambiguity. The baseline of
   record is **baseline_v0**: gross CAGR 26.1% / Sharpe 1.02 / maxDD −41.9% / Calmar 0.62;
   after-tax (STCG 20%) CAGR 23.1% / Sharpe 0.83 (supersedes the optimistic-exit 30.26%/1.15
   measurement, 2026-06-27). Source: `research/baseline_v0.json`.
   The re-derived 34.67% / 1.248 in `cpcv_long_horizon_tradelog_682.json` is research-only and
   NOT what live signals are generated from. Never anchor on 34.67%.

**Baseline_v0 = 26.1% gross CAGR / 1.02 Sharpe / −41.9% max-DD / 0.62 Calmar (after-tax: 23.1% / 0.83).**
Source: `research/baseline_v0.json` (supersedes the optimistic-exit 30.26%/1.15, 2026-06-27).

---

## Step 1 — Write the hypothesis FIRST (before touching code)

State in writing, before any implementation:

```
Overlay name: <name>
Hypothesis: <What mechanism should this exploit? Be specific about why the data
             should look different if this overlay is real.>
Predicted direction: ΔCAGR [+/-], ΔSharpe [+/-], ΔMaxDD [better/worse/neutral]
Predicted mechanism in one sentence: <If you cannot state the mechanism in one
             sentence, you do not understand it well enough to test it.>
Failure modes: <Name at least two ways this could hurt in a regime it wasn't
             designed for.>
Prior evidence: <Is there a related §11 rejection? What is genuinely new here?>
n_trials cost: <Does this spend a trial? Measurements do not; new hypotheses do.
             Check diagnostics/research/preregistry/ and n_trials.json.>
```

Save this in `long_horizon/research/preregistry/<overlay-name>.md` BEFORE running the test.
A test run without a pre-registered hypothesis is inadmissible — post-hoc rationalization
has caused at least two false positives in this repo.

---

## Step 2 — Implement as a pluggable function

The overlay must be isolated so it can be toggled without touching baseline logic.

**Convention for entry/selection overlays:**

```python
def overlay_<name>(
    universe: pd.DataFrame,       # ranked eligible universe for today
    held_tickers: set[str],       # currently held positions
    derived: dict[str, float],    # frozen cfg from models/long_horizon/config.json
    **kwargs,                     # any overlay-specific params (keep ≤3)
) -> pd.DataFrame:
    """Return the filtered/re-ranked universe. Must be a pure function of its inputs.
    Must not modify `derived` or any shared state."""
    ...
```

**Convention for exit overlays:**

```python
def overlay_exit_<name>(
    position: Position,           # from long_horizon/backtest/portfolio.py
    today_ohlc: pd.Series,        # today's row for this ticker
    derived: dict[str, float],
    **kwargs,
) -> tuple[bool, str]:
    """Return (should_exit, reason_string). Runs AFTER the four mechanical exits
    (stop/target/trailing/time) — never overrides them, only adds an earlier exit."""
    ...
```

Place the implementation in `long_horizon/overlay/<name>.py`. Do NOT inline it in `portfolio.py`
or `long_horizon_cron.py` — the overlay must be independently testable.

---

## Step 3 — Run through the backtest harness

### Current harness

The Phase-4 harness is `long_horizon/backtest/portfolio.py::simulate`. Until
`src/research/harness.py` is built (Phase 4), call `simulate` directly:

```python
from long_horizon.backtest.portfolio import simulate
from long_horizon.backtest.ohlc_panel import load_panel, restrict_to_large_mid
from long_horizon.strategy.value_derivation import load_frozen_cfg

import json, pathlib

# Load the FROZEN cfg — this is what live signals use.
# Do NOT use the re-derived 34.67% variant (cpcv_long_horizon_tradelog_682.json).
cfg = load_frozen_cfg()  # reads models/long_horizon/config.json → cfg block only

# Load the canonical 682-name panel (cloud artifact; see long_horizon/results/README.md)
# For LOCAL development the panel is degenerate (~20 stocks). NEVER report local numbers
# as the headline — dispatch via cpcv-research.yml for real numbers.
panel = load_panel(...)  # your cloud or CI-produced panel

# Baseline (no overlay):
baseline = simulate(panel, cfg)

# With overlay — pass as a kwarg or patch the derived dict:
candidate = simulate(panel, {**cfg, "overlay_<name>_enabled": True}, ...)
```

When `src/research/harness.py` is built (it wraps `simulate` with the block bootstrap,
walk-forward, and sub-period logic), switch to that. Until then, the sub-period and
walk-forward tests are separate `simulate` calls with `start=` / `end=` / per-fold `derived`.

### Running on CI (canonical)

Dispatch via GitHub Actions to get the real 682-name universe:

```bash
gh workflow run cpcv-research.yml --ref <branch> \
  -f runner=run_long_horizon_tradelog \
  -f overlay=<name>
```

A LOCAL run on the degenerate survivor-only cache will print ~15% CAGR, NOT the headline.
Never report local numbers as the result. Always wait for the CI run.

**Phase 4 self-validation requirement:** Before trusting any overlay result from the
harness, the harness MUST first reproduce the §11 rejections from `STRATEGY_FULL.md` on the
canonical universe (market-regime gate, sector overlays, signal-level low-vol blending, etc.)
as REJECTED. If the harness promotes something §11 already killed, the harness has a bug.
Fix the harness before reporting any overlay result.

---

## Step 4 — Required outputs

Every overlay test must produce ALL of the following. Missing any one = incomplete verdict.

### 4a. Delta metrics (vs baseline_v0)

All numbers must be **post-tax** (STCG 20% on positions held < 12 months) and
**post-cost** at three friction levels:

| Metric | 1× cost | 2× cost | 3× cost |
|--------|---------|---------|---------|
| ΔCAGR | | | |
| ΔSharpe | | | |
| ΔSortino | | | |
| ΔCalmar | | | |
| ΔMaxDD | | | |
| Δturnover (trades/yr) | | | |

The **2× cost** column is the reference column for the promotion bar. The strategy survives
3× in baseline (see `STRATEGY_FULL.md` §10.3: 30.7% → 26.5% → 20.5%) — but an overlay that
introduces extra turnover may not.

### 4b. Post-tax mechanics

STCG (20%) applies to realized gains on positions held < 252 trading days (< 1 year).
The long-horizon strategy's median hold is ~22 days, so effectively all realized gains
are STCG. Apply the tax before computing portfolio returns:

```
net_trade_gain = gross_gain × (1 − 0.20)   # if gain > 0 and days_held < 252
net_trade_gain = gross_gain                 # if loss (tax credit, conservative: ignore it)
```

The baseline numbers in `cpcv_long_horizon_final_682.json` ARE post-cost but they are
pre-tax (the portfolio.simulate costs don't apply STCG). Apply STCG consistently across
both baseline and overlay using the trade ledger, then compute the delta. The delta
direction is what matters; absolute post-tax CAGR will differ from the headline.

### 4c. Sub-period stability

Report separately for:
- **2017–2021** (trending-bull heavy, higher absolute returns)
- **2022–2026** (harder regime; recent live conditions; 21.5% / 0.84 Sharpe in baseline)

An overlay that helps 2017–2021 but hurts 2022–2026 is REJECTED, not averaged. The
2022–2026 sub-period is the deciding period because it reflects the current regime and
is the regime live users will experience.

---

## Step 5 — Significance tests

### 5a. Block bootstrap (block = 63 trading days, n = 5000)

63 days is chosen because it matches the strategy's maximum hold (one non-overlapping
trade-generation cycle). Shorter blocks understate autocorrelation in the return series.

```python
from src.validation.bootstrap import block_bootstrap_ci

# returns_overlay and returns_baseline are daily portfolio return series (same dates)
delta_series = returns_overlay - returns_baseline
ci_low, ci_high = block_bootstrap_ci(
    delta_series, stat="sharpe_annualized",
    block_size=63, n_samples=5000, confidence=0.95,
)
# Required: ci_low > 0.0 (the 95% CI excludes zero on the UPSIDE)
```

The baseline Sharpe block-bootstrap already prints `[0.58, 1.88]` (median 1.23) per
`STRATEGY_FULL.md §10.3`. The overlay's CI on ΔSharpe must exclude zero to qualify.

### 5b. Walk-forward fold-pass rate ≥ 60%

Run the overlay on each year as an independent out-of-sample fold (the same expanding-window
walk-forward structure the walk-forward backtest uses: derive on pre-year data, test on that
year). Count the fraction of folds where the overlay delivers ΔSharpe > 0. Require ≥ 60%
(i.e., positive in at least 6 of 10 years, or at least 5 of 8 for the 2019+ survivorship-clean
window that the walk-forward treats as trustworthy).

```
Folds tested: 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026
ΔSharpe>0:    [T/F] [T/F] ...
Fold-pass rate: N/10
```

A fold-pass rate below 60% is REJECT regardless of the pooled metric.

### 5c. Sample-adequacy score (C3 — before trusting the verdict)

Before accepting a bootstrap CI or fold-pass verdict as meaningful, check whether the
overlay has enough **independent observations** to be powered. An underpowered result is
not evidence of an edge, and it is not evidence of no edge — it is noise. Label it
explicitly rather than letting it pass silently.

**Effective-breadth formula:**

```
n_independent = total_overlay_trades / 63   # 63d = one non-overlapping trade-generation cycle
```

Use `src/validation/power.py::min_detectable_effect(n=n_independent)` to compute the
minimum ΔSharpe the test can reliably detect at 80% power. Report alongside the CI:

```
Sample adequacy:  n_independent = <N>   MDE(ΔSharpe, 80%) = <x>
Bootstrap CI:     [lo, hi]
Powered for stated ΔSharpe: YES / NO
```

**Hard rules:**

- `n_independent < 10` → verdict is INADMISSIBLE regardless of CI or fold-pass result.
  Register in the overlay registry as "sample too small — re-test after accumulating ≥ 10
  independent periods."
- `10 ≤ n_independent < 20` → label the verdict UNDERPOWERED. A CI that excludes zero is
  suggestive but not sufficient for PROMOTE; the result qualifies for SHADOW only.
- `n_independent ≥ 20` → sample is adequate; proceed with the normal promotion bar.

*(adapted from mphinance/alpha-skills edge-strategy-reviewer C3, MIT)*

### 5d. Cross-regime validation (C4 — required for PROMOTE)

An overlay that only works in one market regime is a regime bet, not an overlay. This is
distinct from the sub-period stability test (Step 4c): sub-period tests time-slice; this
test slices by **market regime label**.

**Minimum requirement:** the overlay must show ΔSharpe > 0 in at least two of the three
regime categories (BULL, CHOPPY, BEAR) when trades are grouped by the `regime_at_entry`
label in `results/signal_analytics.json`. A result that is positive in BULL only is
REJECT even if the pooled number passes the promotion bar.

**How to compute:**

```python
# Segment the overlay trade ledger by regime_at_entry
for regime in ["BULL", "CHOPPY", "BEAR"]:
    regime_trades = trade_log[trade_log["regime_at_entry"] == regime]
    # Compute per-trade expectancy and Sharpe for overlay vs baseline in this segment
    ...
# Require ΔSharpe > 0 in ≥ 2 of 3 regimes; report all three
```

If the historical backtest predates `regime_at_entry` tagging, use the 3-tier regime
reconstruction from `config.py` / `src/data/macro_data.py` (0=BEAR, 1=CHOPPY, 2=BULL) to
back-label the trade log. This reconstruction is reproducible and uses only PIT data.

**Report format (add to §4 outputs):**

```
Cross-regime ΔSharpe:   BULL [+/-x.xx]   CHOPPY [+/-x.xx]   BEAR [+/-x.xx]
Regimes positive: N/3   (≥2 required for PROMOTE)
```

*(adapted from mphinance/alpha-skills edge-strategy-reviewer C4, MIT)*

### 5e. Combination test (if multiple overlays are under consideration)

Individual overlays can cannibalize each other. If two overlays each individually show
PROMOTE or SHADOW, also test them together. If the combined result is materially worse
than either alone, the pair is rejected as a combination even if each passes individually.

---

## Step 6 — The promotion bar (exact, from `skills/sell-replace-logic/SKILL.md`)

**PROMOTE only if ALL of the following hold:**

1. Post-tax post-cost ΔSharpe ≥ **+0.10**
2. Post-tax post-cost ΔCalmar ≥ **+0.05**
3. **2022–2026** sub-period shows positive ΔCAGR
4. Walk-forward fold-pass rate ≥ **60%**
5. Block bootstrap 95% CI on ΔSharpe **excludes zero**
6. Turnover increase ≤ **30%** (measured as Δtrades/yr ÷ baseline trades/yr)
7. Mechanism is **explainable in one sentence** to the operator
8. **Sample-adequacy: `n_independent ≥ 20`** (§5c); UNDERPOWERED result → SHADOW only
9. **Cross-regime: ΔSharpe > 0 in ≥ 2 of 3 regime buckets** (BULL/CHOPPY/BEAR) (§5d)

**SHADOW** (log signal, observe live, do not trade) if 4–5 of the above hold.

**REJECT** otherwise.

A SHADOW result means: the overlay is wired to write a scorecard entry into
`results/signal_analytics.json` (or a dedicated `results/overlay_<name>_log.json`) but
has zero impact on position sizing, entry decisions, or exit decisions. It accumulates a
forward wall and can be re-evaluated once ≥ 50 live observations exist.

---

## Step 7 — Log the verdict in `research/overlay_registry.md`

Every tested overlay gets an entry. REJECT verdicts are as important as PROMOTE —
they prevent re-testing.

Required fields in the registry entry:

```markdown
## <overlay-name> — PROMOTE / SHADOW / REJECT

**Date tested:** YYYY-MM-DD
**Pre-reg:** long_horizon/research/preregistry/<name>.md
**Trials spent:** <N> (or "measurement, 0 trials")

**Hypothesis:** <one sentence>

**Results (1× / 2× / 3× cost, post-tax):**
| Metric | Baseline | Overlay | Δ |
|--------|----------|---------|---|
| CAGR   | 26.1% gross / 23.1% after-tax |         |   |
| Sharpe | 1.02 gross / 0.83 after-tax   |         |   |
| Calmar | 0.62     |         |   |
| MaxDD  | −41.9%   |         |   |
| Trades/yr | ~152  |         |   |

**Sub-period 2017–2021:** ΔCAGR [+/-], ΔSharpe [+/-]
**Sub-period 2022–2026:** ΔCAGR [+/-], ΔSharpe [+/-]
**Walk-forward fold-pass:** N/10 folds
**Block bootstrap ΔSharpe 95% CI:** [lo, hi] — excludes zero: YES / NO
**Sample adequacy:** n_independent = N   MDE(ΔSharpe, 80%) = x.xx   Powered: YES / NO / UNDERPOWERED
**Cross-regime ΔSharpe:** BULL [+/-x.xx]   CHOPPY [+/-x.xx]   BEAR [+/-x.xx]   Regimes positive: N/3

**Promotion bar check:**
- [ ] ΔSharpe ≥ +0.10
- [ ] ΔCalmar ≥ +0.05
- [ ] 2022–2026 ΔCAGR > 0
- [ ] Fold-pass ≥ 60%
- [ ] CI excludes zero
- [ ] Turnover increase ≤ 30%
- [ ] One-sentence mechanism
- [ ] n_independent ≥ 20 (sample adequacy)
- [ ] ΔSharpe > 0 in ≥ 2/3 regime buckets (cross-regime)

**Verdict: PROMOTE / SHADOW / REJECT**
**Reason:** <What killed it, or what makes it trustworthy enough to promote.>
**Do not re-test unless:** <What new evidence would justify re-opening this.>
```

---

## Quick reference — what NOT to test without new evidence

From `STRATEGY_FULL.md §11` (killed, do not relitigate):

| Killed overlay | Why killed | New evidence needed to re-open |
|---|---|---|
| Market-regime / dual-momentum gate | Cuts CAGR, sidelines the best bull years | A regime definition that preserves CAGR in those years |
| Residual / beta-stripped momentum | No improvement over raw trend | New factor construction |
| Frog-in-the-pan momentum | No edge on this universe | Different path-smoothness metric |
| Sector-residual momentum / sector selection overlays | Hurt lean years; sector IC ≈ 0 | Sector IC > 0.05 sustained on a 2022+ sub-period |
| Reversal signals (RSI / MACD / ROC) | No orthogonal edge at 63d horizon | IC evidence on the 63d label specifically |
| Signal-level low-vol blending | Diluted the trend signal | Separate volatility regime with documented IC |
| Heavy quality screens (earnings, ROE) on top of debt filter | Over-filtered, reduced breadth | Metric that doesn't collinear with the existing debt filter |
| `min_hold = 20` | Worst point in the sweep (22% / 0.86 Sharpe) | New hold-sweep across a different universe definition |

A result that contradicts a §11 finding is extraordinary and requires the block bootstrap CI
at block=63 plus the walk-forward fold-pass BOTH to hold before it overrides the prior verdict.

---

## Notes on the vol-target overlay (live_overlays, pre-shipped)

The vol-target overlay (pre-reg 0068, arm V2: `vol_target_annual=0.15, vol_window=42, vol_floor=0.40`)
has already cleared the harness and been PROMOTED to the paper path (shipped 2026-06-26). It is
recorded in `models/long_horizon/config.json → live_overlays` and applied by
`long_horizon/backtest/portfolio.py::vol_target_scalar`.

Its metrics: CAGR-neutral, drawdown reduced from ~−45% to ~−39% in-backtest. It applies only
to the live paper-book sizing equity (results/portfolio_history.csv); the research backtest and
golden master are explicitly unaffected (`load_frozen_cfg` returns the `cfg` block only, not
`live_overlays`).

Any NEW sizing overlay must prove it adds on top of this baseline, NOT compete with it on
the same axis. The drawdown axis budget is approximately accounted for.

---

## Cross-references

- **Frozen cfg source of truth:** `models/long_horizon/config.json`
- **Backtest engine:** `long_horizon/backtest/portfolio.py::simulate`
- **Exit logic (shared live/backtest):** `src/engine/exit_logic.py::decide_exit`
- **Baseline result files:** `long_horizon/results/cpcv_long_horizon_final_682.json` (frozen-cfg arm = baseline_v0)
- **Rejection log:** `long_horizon/STRATEGY_FULL.md §11`
- **Exit / rotate overlays specifically:** `skills/sell-replace-logic/SKILL.md`
- **Pre-registration discipline:** `long_horizon/research/preregistry/` + `diagnostics/research/preregistry/`
- **Overlay registry:** `research/overlay_registry.md` (create if absent)
- **Golden master (engine drift guard):** `tests/test_long_horizon_golden.py` — must stay byte-identical unless the engine change is intentional and the fixture is regenerated in the same PR via `python diagnostics/build_lh_golden.py`
