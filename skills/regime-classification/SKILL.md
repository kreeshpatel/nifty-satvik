---
name: regime-classification
description: >
  How to detect, label, and (carefully) use market regime for the long-horizon
  strategy. Use when the topic is "regime", "breadth", "bull/bear", "risk-on/off",
  "market state", "dual-momentum gate", "BULL/BEAR/CHOPPY label", or any proposal
  to gate/adjust entries based on market condition.
---

# Regime Classification — Long-Horizon Strategy

## 1. The one-line verdict (read first)

Regime is used for **dashboard display** and exists as a **candidate exposure de-gross
(0070, not yet live)**. It is **NOT an entry filter**. A full market-regime entry gate
was tested four ways and killed (§11 of STRATEGY_FULL.md). Any proposal to re-add it
as a gate must clear the promotion bar in §6 of this document — it cannot be reinstated
from design reasoning alone.

---

## 2. What "regime" actually means in the codebase

There are two regime concepts with different purposes and very different wiring status.

### 2a. Dashboard breadth label (`_regime` in `long_horizon_cron.py`)

**Location:** `src/runners/long_horizon_cron.py:456–463`

```python
def _regime(uni: pd.DataFrame, as_of) -> dict:
    """Breadth-based regime label for the dashboard header."""
    day = uni[uni["date"] == as_of]
    n = int(day[SIGNAL].notna().sum())
    pos = int((day[SIGNAL] > 0).sum())
    breadth = round(pos / n * 100, 1) if n else 0.0
    status = "BULL" if breadth >= 60 else ("BEAR" if breadth < 40 else "CHOPPY")
    return {"status": status, "strength": breadth, "breadth": breadth, "vix": None}
```

**What it computes:**

On the **as_of date only** (the current cross-section), count what fraction of the eligible
post-filter universe has a **positive `sma200_slope_63`** value:

| Label | Condition | Meaning |
|-------|-----------|---------|
| `BULL` | breadth ≥ 60% | Most tracked names have rising long-term trends |
| `CHOPPY` | 40% ≤ breadth < 60% | Mixed — roughly equal up- and down-trend names |
| `BEAR` | breadth < 40% | Most tracked names have falling long-term trends |

The result is stamped into `signals_today.json` and displayed on the dashboard's
`RegimeHeader` component. That is its **sole production function**.

**Lookahead status:** Fully trailing. `sma200_slope_63` uses only data up to and
including day `t`. The cross-section is the `as_of` slice of the already-computed
feature panel — no future data.

**Coverage:** The breadth denominator is the **eligible post-filter large+mid solvent
universe** on that date — not the full Nifty-500 and not a fixed index like Nifty-50.
This makes it strategy-coherent (it reflects the health of the names the strategy can
actually trade) but also narrower and noisier than an index-based breadth read.

### 2b. Research-grade `market_regime` function (`ohlc_panel.py`)

**Location:** `long_horizon/backtest/ohlc_panel.py:168–192`

This function is used inside the backtest harness, NOT in the live cron path. It
generates a `{date -> bool}` risk-on flag for every date in the panel, supporting two
methods:

- **`index_trend` (default):** an equal-weight daily-rebalanced index of the universe
  is above its 200-day SMA. Returns `True` (risk-on) while above.
- **`breadth`:** ≥ 50% of names have a positive `sma200_slope_63`. Threshold is 0.50
  (not the 0.40/0.60 step-labels the live `_regime` function uses).

Both are **trailing-only** (the equal-weight index uses a rolling/expanding
construction; the breadth fraction uses the `sma200_slope_63` values which are
themselves trailing). No lookahead.

This function was the instrument used to **test and kill** the regime gate. It is
research infrastructure, not a live control surface.

### 2c. 0070 market-state exposure scalars (`ohlc_panel.py`)

**Location:** `long_horizon/backtest/ohlc_panel.py:207–260`

Three continuous scalars built as part of pre-reg 0070:

| Function | Mechanism | Floor |
|----------|-----------|-------|
| `index_downside_vol_scalar` | 15-day trailing downside semideviation of the equal-weight index; de-grosses when downside vol is elevated | 0.40 |
| `index_drawdown_scalar` | Ramps from 1.0 to floor as the equal-weight index drawdown deepens from 12% to 30% below the running peak | 0.40 |
| `breadth_trend_scalar` | Min of (20-day breadth fraction vs a ramp) and (index distance from 50-day SMA); takes the min so either crash type de-grosses | 0.50 |

**Wiring status: NOT on the live entry path.** These scalars were built to bypass the
binary-gate problem (the gate kills CAGR by staying out of trending recoveries) with
a smooth, self-re-grossing alternative. Pre-reg 0070 found they plateau at approximately
**−38% maximum drawdown** — a specific crash (e.g. COVID) can be cut to −31%, but no
single signal generalises across crash characters. A dependable −30% needs the deferred
defined-risk tail hedge (the vol-carry / options program), not another sizing overlay.

The live paper book applies the **vol-target overlay** (`live_overlays` in
`models/long_horizon/config.json`) from pre-reg 0068, which is a different mechanism
(trailing book vol, not a market-state signal). The 0070 scalars are deferred research.

---

## 3. What regime is NOT used for (and why)

### 3a. Entry gate — tested and killed

A **market-regime entry gate** was tested in four distinct configurations against the
682-name corrected universe (`brain.md` — the "REGIME GATE = KILL" finding):

| Arm | Mechanism | Result vs base (30.3% / 1.10)† |
|-----|-----------|-------------------------------|
| `entry_trend` | sit out while equal-weight index < 200-day SMA | 19.9% CAGR / 0.92 Sharpe |
| `exit_trend` | exit held positions when index < 200-day SMA | 20.7% CAGR / 0.97 Sharpe |
| `breadth` | sit out when <50% of names have positive slope | 19.2% CAGR / 0.87 Sharpe |
| 4th arm (variant) | — | All hurt |

> † The `30.3% / 1.10` base here is the **old optimistic-exit measurement** the arms were tested
> against, superseded by **baseline_v0** (26.1% gross / 1.02 Sharpe; `research/baseline_v0.json`,
> 2026-06-27). The KILL is **relative** — every arm cuts CAGR ~10 pp and Sharpe — so it survives
> the common-mode exit-parity shift; the absolute base figure is provenance only.

**Mechanism of failure:** The gate whipsawed. The 2022 base year (−1.9% before the gate)
became −24% after — the gate moved the book to cash during the downturn and then kept it
sidelined as the recovery ran. V-shaped recoveries (2020 COVID, multiple 2022 sub-rallies)
are the strategy's richest periods. The cross-sectional selection already handles individual
name risk via the hard stop; a market-timing overlay on top adds systematic exit/re-entry
friction that concentrates losses at exactly the wrong moment. "**Thought around it — it
doesn't help.**" (brain.md)

This is the reason STRATEGY_FULL.md §8 says "No market-regime entry gate" under
"Deliberately absent."

### 3b. Sector overlays — also killed separately

Sector-based regime or rotation overlays (sector-residual momentum, sector filters for
selection, price-based sector overlays applied on 1159 trades) were all tested and killed
(STRATEGY_FULL.md §11; `lean_years_sector_audit` — Test A, pooled −0.04pp, CI fail).
The sector momentum IC is approximately zero. A future session should not conflate "market
regime" with "sector regime" — both were tested separately and both failed.

---

## 4. How to read the live regime output

The `_regime` function emits one dict per cron run. It appears in:

- `results/signals_today.json` under the `regime` key
- The dashboard `RegimeHeader` component (live display)
- The console log line: `regime {status} ({breadth}% breadth)`

**What the label means operationally:**

- `BULL (>60%)` — most tracked names are in established up-trends. The strategy is
  likely fully deployed (15 slots filled or close to it) and finding high-quality entries.
- `CHOPPY (40–60%)` — mixed trend quality. Position turnover may be higher; expect more
  stop exits than trailing exits.
- `BEAR (<40%)` — broad downtrend in the eligible universe. The strategy **still enters**
  the highest-ranked names (it does not sit out) and relies on its per-name hard stop for
  risk control. This is intentional and validated.

**The regime label does NOT change how the strategy trades.** It is a display signal
for the owner's situational awareness, not a parameter in the signal, sizing, or exit path.

---

## 5. Lookahead-safety checklist for any new regime signal

All regime signals must be trailing-only. Before using any regime measure, verify:

1. The signal on date `t` uses only data available at market close on `t` (or earlier).
2. The signal is computed inside the feature panel after the membership mask and liquidity
   filter — not on the full raw universe (which would include survivorship-biased names).
3. The equal-weight index construction is `pct_change → cumulative return` — no look-forward
   rebalancing. See `_equal_weight_index` in `ohlc_panel.py:195–204` for the reference
   implementation.
4. When using a rolling SMA for the index (e.g. 200-day), `min_periods` must be set so warm-
   up dates default to risk-on, not risk-off (the backtest defaults to `True` for dates with
   insufficient history — conservative; never default to risk-off during warm-up).

---

## 6. The promotion bar for any new regime use

Before wiring any regime signal to the **entry, exit, or sizing path**, it must pass all
of the following (the same bar as `skills/sell-replace-logic`):

| Gate | Required threshold |
|------|--------------------|
| Post-tax post-cost ΔSharpe | ≥ +0.10 vs the locked baseline (baseline_v0: 26.1% gross / 23.1% after-tax CAGR / 1.02 Sharpe gross; supersedes 30.3%/1.15, 2026-06-27) |
| ΔCalmar | ≥ +0.05 |
| 2022–2026 sub-period ΔCAGR | Positive (not just bull-era lift) |
| Walk-forward fold-pass rate | ≥ 60% of year-folds |
| Bootstrap 95% CI on ΔSharpe | Excludes zero (block bootstrap, block = 63 days) |
| Turnover increase | ≤ 30% increase in trades per year |
| Mechanism | Explainable in one sentence — not a pure data-fit |

**SHADOW before promoting.** If a new regime signal clears 4–5 of the above, shadow it
(compute and log it in `signal_analytics.json` without acting on it) for at least one
full market cycle before promoting. See the vol-target overlay (pre-reg 0068, shipped to
paper only) as the reference example of correctly staged promotion.

**If the proposal is to reinstate a binary entry gate**, it must further show that it
does not replicate the exact failure mode documented in §3a: CAGR destruction through
V-recovery sideline. A pure drawdown reduction with CAGR-neutral or positive ΔSharpe
would be a new result; the existing evidence shows the opposite.

The burden of proof lies with the challenger. The four-way test in §3a is the null
hypothesis: "regime gates hurt this strategy." New evidence must be genuinely new
(different mechanism, different data, different universe) — not the same gate on the same
universe with a slightly different threshold.

---

## 7. If you are asked to "add a regime filter"

1. Read §3a first. Four arms were tested and all hurt. State this explicitly before
   entertaining the proposal.
2. Clarify what kind of regime signal is being proposed (entry gate? exit gate? sizing
   scalar? display only?). The evidence against entry gates is strong; sizing scalars have
   a different (and weaker) verdict (0070 plateau at ~−38%); display is already live.
3. If it is a sizing scalar, check whether the vol-target overlay (live_overlays, 0068)
   already captures the stated goal. Adding a second sizing de-gross on top compounds
   the effect non-linearly and has not been tested.
4. If the proposal is a fundamentally different mechanism (not breadth, not index-trend,
   not a binary gate), write a pre-registration entry specifying the hypothesis, the test,
   the kill criterion, and the walk-forward plan before running the backtest. Log it in
   `long_horizon/research/preregistry/`.
5. Do not run the test on the training data alone. Use the walk-forward harness
   (`cpcv-research.yml` or a local equivalent) with at least 2019+ folds as the
   trustworthy window.

---

## 8. Code locations summary

| Concept | File | Status |
|---------|------|--------|
| Live breadth label (`BULL`/`CHOPPY`/`BEAR`) | `src/runners/long_horizon_cron.py:456–463` | Live, display-only |
| Research regime flag (`{date→bool}`) | `long_horizon/backtest/ohlc_panel.py:168–192` | Research, killed as gate |
| 0070 downside-vol scalar | `long_horizon/backtest/ohlc_panel.py:207–221` | Research, deferred |
| 0070 drawdown scalar | `long_horizon/backtest/ohlc_panel.py:224–238` | Research, deferred |
| 0070 breadth-trend scalar | `long_horizon/backtest/ohlc_panel.py:241–260` | Research, deferred |
| Vol-target overlay (0068) | `long_horizon/backtest/portfolio.py::vol_target_scalar`; wired in `long_horizon_cron.py` via `live_overlays` | Live on paper book (2026-06-26) |
| Frozen cfg (no regime gate) | `models/long_horizon/config.json → cfg` | Live, frozen |

---

*This skill is grounded in the real code and audit record as of 2026-06-27. Do not update
without re-reading `long_horizon/STRATEGY_FULL.md §8 and §11`, `long_horizon/brain.md`
(REGIME GATE = KILL entry), and the Phase-1 wiring report (`long_horizon/audit/wiring_report.md`).*
