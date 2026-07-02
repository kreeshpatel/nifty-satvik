# Part 2 — FEATURES: PIT-clean fundamentals-depth conviction features

> Drill-down of Part 2 from [00_master_plan.md](00_master_plan.md). Built + tested **offline** on the 211
> cached Screener pages (no network). These are the F5 earnings-momentum family realized as PIT-safe signals
> the learner (Part 4) will consume. Nothing is wired into the live panel yet → golden master untouched.

## What was built (`nq/data/fundamentals.py::depth_feature_series`)

Per-(ticker, date) features, joined `merge_asof(direction="backward", allow_exact_matches=False)` — strictly
before the decision date — from the Part-1 depth levels. Growth is computed on the **reported annual series**
(period Y vs Y-1, both past), then joined strict-before, so a date `t` sees only the most-recent annual period
available `< t`.

| feature | definition | family |
|---|---|---|
| `rev_yoy` | Sales YoY growth | growth (F5) |
| `eps_yoy` | EPS YoY growth | growth (F5) |
| `np_yoy` | Net-profit YoY growth | growth (F5) |
| `op_to_assets` | Operating Profit / Total Assets | profitability (Novy-Marx **proxy** — true gross-profit unavailable, see 1.1) |
| `op_margin` | OPM % (level) | quality |
| `op_margin_delta` | YoY change in OPM % | quality (margin trend) |
| `asset_turnover` | Sales / Total Assets | quality |

## PIT / leakage gate (`tests/test_fundamentals_depth_features.py`) — GREEN

- **Truncation gate:** dropping the future fiscal year cannot change a past-date feature (the full store and a
  store truncated to the prior year give identical features for dates before the dropped year's availability).
  This is the growth-feature PIT guarantee the master plan promised.
- **Strict-before:** a date exactly on an availability boundary sees the *prior* period (no same-day leak).
- **Old-schema degrade:** a store carrying only the original 5 fields → all-NaN features (backward-compat).
- **Values:** hand-checked against fixtures.

## Dev validation on real cached data

Built a 36-name store from the cache; features compute sensibly (rev growth 5–86%, operating margin 7–41%,
asset turnover 0.4–1.2×) with 89% cross-sectional coverage; NaN only where a name lacks 2 fiscal years (YoY
needs a prior year — correct PIT behaviour).

## What is NOT done here (deliberately)

- **No live-panel wiring / no cfg change** — integration into `compose_ranked_panel` + the conviction model is
  Part 4/5, cfg-gated so the golden master stays byte-identical, and **gated on the paper wall** (~Sept).
- **No live-universe population** — the on-disk store still carries the old 5 fields; the depth store for
  *current* names needs the polite Screener scrape (Part 1.5, network — flag before running). Until then the
  features are developed/tested against the cached (mostly delisted) universe.
- **Sector / seasonality features** — not built (registry: sector-alpha KILLed, seasonality skeptical; both are
  elevated-burden conviction *context* at most — see the master plan design-considerations note).

## Next
The offline learning-bot spine is complete through Part 2. The remaining path (Parts 4–6: bake-off learner →
CPCV/DSR validation → forward-wall certification) is **gated on the base paper wall** (≥30 closed trades,
~Sept). Before that: the live-universe scrape (1.5/1.6) whenever we want a real backtest — an explicit,
confirm-first network step.
