# nifty-satvik

Clean, **long-horizon-only** rebuild of the NiftyQuant long-horizon strategy:
`sma200_slope_63` top-15 cross-sectional trend-momentum on a PIT-clean, large+mid,
solvent Nifty-500 universe.

- **The plan:** [BUILD_SPEC.md](BUILD_SPEC.md) — rebuild the code clean in a fresh
  `nq/` package; transplant only the data corrections, empirical history, and golden
  master that can't be regenerated from a spec.
- **The methodology:** [`skills/`](skills/) — pre-registration, n_trials/DSR, the
  promotion bar, the baseline_v0 anchor. Binding.
- **Why a rebuild:** the monorepo wove the retired v1 model into the validation +
  import graph too tightly to subtract cleanly. No users → no live risk.

**Status:** Stage 0 (foundation). No v1 model, no ensemble, no pillar stack, no
product. Anchor (baseline_v0): 26.11% CAGR / 1.02 Sharpe / −41.9% maxDD — *not
live-validated.*

```
nq/data      OHLCV + PIT membership mask + features (sma200_slope_63, atr, ADV, D/E)
nq/engine    panel + exits (shared) + portfolio.simulate (the backtest/live engine)
nq/strategy  the long-horizon scan
nq/validation cpcv / bootstrap / dsr / metrics
nq/runner    live scanner
```
