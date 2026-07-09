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

## The two books

- **`baseline_v1`** — the pinned baseline of record (ADR-0006, dataset-pin-20260701).
  `sma200_slope_63` cross-sectional momentum, 63-day hold. Gross **15.46% CAGR** /
  Sharpe **0.667** / MaxDD **−46%** / ~12% after-tax. Byte-reproducible from the pinned
  OHLCV. In-sample; no real capital has traded.
- **`weekly-swing 0094`** — the weekly-swing book surfaced on the marketing site
  ("this week's scan"). NET of costs, corrected universe 2017–2026: **8.1× (₹10L → ₹81L,
  +711%)** / Sharpe **1.13** / CAGR **24.7%** / MaxDD **−42%** / 59% win over 255 trades.
  Reproduce: `python scripts/run_bhanushali_weekly_rank.py`. **`DSR 0.894` → below the
  deflated-Sharpe gate → NOT certified.** It is a registered proposal for the 2026-10-01
  review + the forward wall — paper-tracked, not proven, before 20% STCG, no real capital.

## Product

- **`frontend/`** — the marketing landing (`src/pages/LandingV2.jsx`) + the React
  dashboard. The public landing serves aggregate, non-actionable stats only (no tickers,
  no prices) via `GET /api/landing-stats`, with the "not certified · paper-tracked"
  framing intact.
- **`dashboard/backend/`** — FastAPI: signals, positions, trades, Kite (Zerodha) OAuth,
  and the public `landing_stats` router (the frozen track-record / equity / weekly-scan
  constants the landing renders).

**Numbers discipline:** every figure on the landing is reproducible from the committed
pipeline — never a chat transcript. Honesty framing (in-sample, deep drawdown, uncertified,
no real capital) is load-bearing, not decoration.

```
nq/data       OHLCV + PIT membership mask + features (sma200_slope_63, atr, ADV, D/E)
nq/engine     panel + exits (shared) + portfolio.simulate (the backtest/live engine)
nq/strategy   the long-horizon scan
nq/validation cpcv / bootstrap / dsr / metrics
nq/runner     live scanner
research/     pre-registered findings (NNNN-*.md), overlay registry, exports
dashboard/    FastAPI backend (signals, Kite, landing-stats)
frontend/     React dashboard + marketing landing (LandingV2)
```
