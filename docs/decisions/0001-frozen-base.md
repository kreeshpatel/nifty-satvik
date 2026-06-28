# ADR-0001 — Frozen Titman base: lock `sma200_slope_63` top-15 with pre-2017-derived parameters

**Status:** Accepted  
**Date:** 2026-06-25 (strategy cutover)  
**Author:** kreeshpatel  
**Source files:** `long_horizon/STRATEGY_FULL.md`, `long_horizon/charter.md`, `models/long_horizon/config.json`

---

## Context

### Why a new strategy was needed

The v1 14-day LightGBM ensemble reached its **information ceiling for the 14-day horizon**. Its
79 features are all ≤50-day momentum derivatives; every short-term tweak (chart structure, signal
persistence latch, meta-labelling, directional head, delivery-%, convex sizing) was killed by the
honest walk-forward gate. The model was not under-tuned — it was hitting the boundary of what
momentum signals can predict at that horizon (`charter.md`).

A 3-month hold is a structurally different strategy: different return drivers (trend persistence,
institutional-flow accumulation, momentum underreaction), a different exit and sizing regime, and a
different statistical regime (~4 non-overlapping trades per stock per year vs ~18). It required its
own build from scratch, not an extension of the short-horizon learner.

### The design choice: rules-based over ML

The 63-day horizon produces far fewer independent data points than the 14-day horizon. A machine
learning model at that sparsity is dangerous — capacity must shrink until the model is effectively
doing manual rule selection anyway, while carrying opaque calibration risk. The classical
cross-sectional ranking approach (Jegadeesh–Titman, 1993) is both theoretically grounded and
empirically the strongest signal for this horizon on this universe. A transparent rank rule that
anyone can audit is therefore preferred to a low-capacity ML layer that cannot add demonstrable
value at this sample size.

**Rules-based clarity is the edge.** There is no ML model in the long-horizon pipeline.

---

## Decision

Lock the long-horizon base strategy at the following definition, derived once on the pre-2017
training slice and frozen permanently. Research is conducted as overlays *above* this base; the
base itself is never re-optimised live.

### Universe (applied point-in-time, no survivorship)

| Step | Filter |
|---|---|
| 1 | Nifty-500 (NSE official constituents) |
| 2 | PIT index-membership mask — stock is only eligible on dates it was actually in the index |
| 3 | Large + mid: trailing rolling-median 20-day rupee ADV ≥ ₹5 crore/day (spike-robust) |
| 4 | Solvent low-debt: `0 ≤ Debt/Equity < 1.5` (point-in-time Screener fundamentals, ~90-day lag) |

This yields ~150–200 eligible names on a typical day.

### Signal

```
sma200_slope_63(t) = ( SMA200(t) / SMA200(t − 63) − 1 ) × 100
```

Percentage change in the 200-day simple moving average over the last 63 trading sessions —
i.e. how steeply the long-term trend is currently rising. Look-ahead-safe by construction
(uses only data up to day `t`). Converted to a cross-sectional percentile rank daily; selection
is purely relative.

### Selection

Hold the **top 15** names by descending `sma200_slope_63` rank. Fill free slots each day
from the top-ranked names not already held.

### Frozen configuration (`models/long_horizon/config.json → cfg`)

All values derived from 63-day favorable/adverse excursion distributions on the pre-2017 slice:

| Parameter | Frozen value | Derivation basis |
|---|---|---|
| `stop_atr_mult` | **3.67** | 5th-percentile adverse excursion of *winning* trades (ATR-63 multiple) |
| `target_pct` | **22.52%** | 63-day favorable-excursion distribution calibration |
| `trailing_activate_pct` | **4.0%** | Level where trailing adds value in excursion data |
| `trailing_pct` | **4.27%** | Give-back band beyond which winners should be cut |
| `min_hold_days` | **10** | Median favorable:adverse excursion turns favorable at day 10 |
| `max_hold_days` | **63** | Hard horizon cap (the label horizon; no extension logic) |
| `risk_per_trade_pct` | **3.0%** | 95th-pctile single-trade loss × max concurrent ≤ drawdown budget |
| `max_position_pct` | **15.0%** | Concentration limit |
| `max_adv_participation_pct` | **5.0%** | Fillability / market-impact cap |
| `max_positions` | **15** | Effective-breadth plateau |
| `gate_quantile` | **0.5** | Percentile threshold for cross-sectional rank eligibility |
| `expected_win_rate` | **0.6297** | `mean(triple-barrier hit)` on gated rows (reference, not gating) |
| `expected_rr` | **1.94** | From excursion distributions (reference, not gating) |

The machine-readable source of record is `models/long_horizon/config.json`. The `load_frozen_cfg`
helper returns only the `cfg` block; `live_overlays` (the pre-reg 0068 vol-target de-grosser,
shipped 2026-06-26) are applied only by the live scanner and do not touch the research baseline or
golden master.

### Sizing formula (shared, live and backtest)

```
shares = floor( 3% of equity / (entry − stop) )          # risk-budget
       capped by floor( 15% of equity / entry )           # position cap
       capped by floor( 5% of 20-day rupee ADV / entry )  # capacity cap
```

Both the live scanner and the backtest call the shared `base_risk_qty` function so they cannot drift.

### Exit logic (shared, live and backtest)

Four exits evaluated on the close daily, delegated to `src/engine/exit_logic.decide_exit` — the
same function in both backtest and live (exit-parity unification, 2026-06-26):

| Exit | Rule |
|---|---|
| Hard stop | Close below `entry − 3.67 × ATR(63)`. Close-only; never suppressed by min-hold. |
| Profit target | Intraday high reaches `entry × 1.2252`. Conservative fill *at* target. |
| Trailing stop | After +4% gain: trail 4.27% below the running close-based peak. |
| Time cap | Hard exit at 63 trading days (no extension). |

Below `min_hold_days = 10`, the profit-taking exits (target, trailing, time) are suppressed; the
stop is always active.

---

## Consequences

### What this locks in

- The base is **never relitigated** without genuinely new information. Any proposed change to
  universe definition, signal, selection count, or frozen parameters requires: a pre-registered
  experiment, a full walk-forward on the canonical 682-name corrected universe, the three-way
  verdict (PROMOTE-CANDIDATE / UNDERPOWERED / KILL), and a CPCV DSR gate.
- All future research is conducted as **overlays above the frozen base** — additional filters,
  overlays, or sleeves that are additive and independently validated.
- The re-derived-per-fold walk-forward result is the **deciding evidence**: stable derived
  parameters across folds confirm the values are not single-fit luck and can be applied OOS.

### Performance (research backtest — never traded a live rupee)

> All figures are from `long_horizon/results/cpcv_long_horizon_final_682.json` (682-name
> solvency-corrected canonical universe). They overstate what live trading will deliver.
> Outputs are model-generated, decision-support signals — not advice and not a guarantee.

**Frozen-arm headline (the canonical number anchored for comparison):**

| Metric | Value |
|---|---|
| CAGR | ~30% (30.26% per `config.json → expected_portfolio_metrics`) |
| Sharpe | ~1.15 |
| Max drawdown | ~−40% (−40.1%) |
| Calmar | ~0.76 |
| Win rate | ~63% |
| Reward:risk | ~1.9:1 |
| Trades/year | ~150 (154 per config) |

A re-derived variant that re-parameterises on the filtered universe prints ~34.7% / 1.25 / −44.9%.
**Do not anchor on the re-derived number for live comparison** — the live scanner uses the frozen
cfg, and the frozen-arm headline (30.3% / 1.15 / −40%) is the honest reference.

**Walk-forward (re-derive per fold, expanding train, one-year OOS, 2019-onward folds):**
~32% CAGR / 1.31 Sharpe / zero negative years. This is the result that demonstrates the edge
is not a single-fit artefact.

**Key risks and honest caveats:**
- ~−40% max drawdown is the price of ~30% CAGR. Regime gates that cut the drawdown also kill the
  CAGR (tested, killed — see §11 of `STRATEGY_FULL.md`). A real client must tolerate a 40%
  peak-to-trough decline.
- Bootstrap Sharpe 5th-percentile is 0.58 (below buy-and-hold in the worst ~5% of resampled paths).
  The strategy is high-variance, regime-dependent — the edge concentrates in trending bull years.
- Sub-period 2022–2026 = 21.5% / 0.84 / −37% DD — alive in the harder recent regime but weaker.
- The strategy has never traded a single live rupee. Gate to real capital: ≥30 paper trades / ~2
  months reviewed before any real money.

---

## Alternatives considered

### A — Market-regime / dual-momentum entry gate

A "sit out when the Nifty-500 index is below its own 200-DMA" gate was measured. Result: cuts
drawdown but **kills CAGR** — the strategy's best years are precisely the strong-trend regimes
the gate sidelines. Net negative. **Killed** (`STRATEGY_FULL.md §11`). Not to be relitigated
without a pre-registered experiment showing the mechanism has changed.

### B — Residual / beta-stripped momentum

Using beta-adjusted or sector-residual momentum as the ranking signal rather than raw
`sma200_slope_63`. No improvement over raw trend on this universe. **Killed** (`§11`).

### C — Frog-in-the-pan (path-smoothness / information-discreteness) momentum

Rewards stocks whose trend is achieved in many small steps rather than a few large jumps. No edge
on the Nifty-500 universe. **Killed** (`§11`).

### D — Sector-residual momentum and sector overlays for selection

Using sector-relative momentum scores, or capping sector concentration in the 15-name portfolio.
Sector overlays **hurt lean years**; sector momentum IC ≈ 0 on this universe. **Killed** (`§11`).
The AI sector-regime analyst runs in shadow-only mode and has no wiring to trade selection.

### E — Reversal / RSI / MACD / ROC as alternative or supplementary signals

All tested as ranking signals or entry gates. No orthogonal edge at the 63-day horizon. **Killed**
(`§11`).

### F — Signal-level low-volatility blending

Blending `sma200_slope_63` rank with a low-volatility tilt. Diluted the trend signal, no net
improvement. **Killed** (`§11`).

### G — Heavier quality screens (earnings-quality, ROE) on top of the debt filter

Adding fundamental quality gates beyond the D/E solvency screen. Over-filtered — reduced breadth
without improving quality. The existing D/E screen (0 ≤ D/E < 1.5) already removes the
leverage-amplified momentum-crash tail; additional screens add noise. **Killed** (`§11`).

### H — `min_hold = 20` (the originally-specified floor)

The program spec originally specified a 20-day minimum hold. Data unambiguously rejects this:
`min_hold = 20` is the **worst point in the hold sweep** (~22% CAGR / 0.86 Sharpe). `min_hold = 10`
backtests at 33–36% CAGR. The strategy ships at 10 (`STRATEGY_FULL.md §11, §15`). An owner
choosing a 20-day floor for behavioural reasons should be aware it costs approximately 11pp of CAGR.

### I — ML model (low-capacity two-head LightGBM for 63d horizon)

Evaluated against the transparent rank rule. At ~4 non-overlapping observations per stock per year
the sample is insufficient to prove that a trained model adds value over a clean classical rule.
The rules-based approach is adopted as the permanent baseline; ML is allowed only if it
demonstrably adds to the rules-based rule on a pre-registered gate — it has not been shown to
do so at 63d.

---

## Operating rules derived from this decision

1. **Never hand-edit `models/long_horizon/config.json`** directly. Any parameter change requires
   offline derivation, a walk-forward, and a pre-registered verdict, then updates to both
   `config.json` and `long_horizon/config.py` in a single commit.
2. **Never re-optimise parameters live.** The `strategy_revalidator` quarterly cron (from v1) was
   removed — it has no role in the long-horizon program.
3. **The `live_overlays` block in `config.json`** is additive and deliberately separate from `cfg`.
   `load_frozen_cfg` returns only `cfg`; any new research baseline or golden master is unaffected
   by the overlays block.
4. **The exit decision (`src/engine/exit_logic.decide_exit`) is the canonical authority.** Do not
   reimplement exit logic inline in the backtest or the live scanner. Both delegate to this shared
   function so they cannot drift.
5. **Rollback** = restore v1 files from git history before commit `c0fbd1d` and re-point
   `render.yaml`. There is no env-var rollback for the long-horizon path (v1 was deleted).
