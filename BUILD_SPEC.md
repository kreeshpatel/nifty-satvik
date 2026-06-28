# nifty-satvik — Build Spec

A clean, **long-horizon-only** rebuild of the NiftyQuant long-horizon strategy. No v1
model, no ensemble, no pillar stack, no dashboard product. Rebuilt **code**;
**transplanted** data + empirical history that cannot be regenerated.

> **Why this repo exists.** The monorepo wove the retired v1 14-day model into the
> validation, sizing, and import graph so tightly that subtracting it cleanly proved
> harder (and riskier) than rebuilding the long-horizon path from scratch. There are
> **no users**, so there is no live-deploy risk. We rebuild the code clean and carry
> forward only what a spec + a model cannot recreate.

---

## 0. Principles

1. **Long-horizon only.** One strategy: `sma200_slope_63` top-15. If a module isn't
   on that path, it isn't here.
2. **Rebuild code, transplant proof.** Code is written fresh (Opus + `skills/`). The
   irreplaceables (§3) are copied verbatim from `C:/niftyquant-lh`.
3. **The golden master is the equivalence proof.** Stage 2 is "done" only when the
   rebuilt engine reproduces the **carried** golden fixture byte-for-byte. That proves
   the rebuilt engine ≡ the validated strategy without re-validating from zero.
4. **Stages are gated.** Each stage has a hard verification gate; we don't start the
   next until it passes.
5. **Lean by construction.** No `shap`/`statsmodels`/`lightgbm`-heavy code → the
   import-time native CI segfault that plagued the old repo cannot occur here.
6. **Governance is the `skills/`.** Pre-registration, n_trials/DSR, paired ≥2019-fold
   deltas, the promotion bar, baseline_v0 anchor — all carried, all binding.

---

## 1. The strategy (exact, from the frozen cfg)

Each scan day, over the **eligible universe**:
- **Eligible universe** = PIT index-membership-masked Nifty-500, restricted to
  **large+mid** (trailing rolling-median 20-day rupee ADV ≥ ₹5cr) **and solvent**
  (`0 ≤ D/E < 1.5`).
- **Rank** all eligible names by **`sma200_slope_63`** (slope of the 200-day SMA over
  the last 63 sessions), cross-sectionally; **higher = better**.
- **Fill** free slots (max **15** positions) with the top-ranked **non-held** names.
- **Size** by risk budget: `risk_per_trade_pct` (3.0%) of equity ÷ per-share risk,
  capped at `max_position_pct` (15%) and `max_adv_participation_pct` (5% of 20d ADV).
- **Entry** = next session open × (1 + slippage).
- **Exits** (shared live/backtest, decided on the close):
  - ATR stop at `entry × (1 − stop_atr_mult × atr_pct)`, `stop_atr_mult = 3.67`
  - target at `entry × (1 + target_pct/100)`, `target_pct = 22.52`
  - trailing: activate at +`trailing_activate_pct` (4.0%) gain, trail `trailing_pct`
    (4.27%) below the close-peak
  - `min_hold_days = 10`, hard cap `max_hold_days = 63` (TRADING-day aging)
- **Costs**: brokerage 0.03%/leg + STT 0.10% **both legs** (delivery) + tiered
  slippage (large 0.05% / mid 0.22% / small 0.40%) + impact above 0.5% ADV.
- **Live overlay** (paper-book sizing only, NOT in the frozen cfg / golden):
  0068 vol-target — `vol_target_annual 0.15 / vol_window 42 / vol_floor 0.40`.

**Anchor (baseline_v0, reproducible):** CAGR **26.11%** / Sharpe **1.02** / maxDD
**−41.87%** / Calmar **0.62** / ~152 trades-yr / WR 59.72%. After-tax (STCG 20%):
23.13% / 0.83. Frozen params derived once on the pre-2017 slice; never re-derived at
scan. *Not live-validated.*

---

## 2. Carry manifest — the 6 irreplaceables (copy verbatim from `C:/niftyquant-lh`)

These are **not** rebuildable from a spec; copy them byte-for-byte. Source → dest is
1:1 unless noted.

| # | What | Path(s) | Why it can't be regenerated |
|---|---|---|---|
| 1 | **Data corrections** | `data/nifty500_membership*.csv`, `data/corporate_actions_demergers.csv`, `data/fundamentals_pit_screener.pkl`, `data/nse_circulars/`, `data/nifty500_official_20250720.csv`, `data/macro_data.pkl`, `data/sector_intelligence.pkl`, `data/problem_sector_map.json` | PIT membership (survivorship fix), demerger catalog, deep Screener D/E scrape — empirical artifacts, re-deriving them re-introduces CAGR-inflating bugs |
| 2 | **Empirical history** | `research/baseline_v0.json`, `research/overlay_registry.md`, `research/findings/`, `diagnostics/research/n_trials.json` (=79), `diagnostics/research/HOLDOUT.md`, `diagnostics/research/preregistry/`, `long_horizon/research/preregistry/`, `long_horizon/research/findings/` | KILL log + DSR denominator + the anchor; losing them re-runs dead experiments + breaks significance math |
| 3 | **Golden fixture** | `tests/fixtures/lh_golden_panel.csv` (+ the committed golden expected output if present) | the equivalence proof for the rebuilt engine |
| 4 | **Frozen config** | `models/long_horizon/config.json` | the live source of truth |
| 5 | **Skills (methodology)** | `skills/` (all 23 docs incl `_ingested/`) | the operating discipline |
| 6 | **Spec/program docs** | `long_horizon/STRATEGY.md`, `STRATEGY_FULL.md`, `long_horizon/brain.md`, `long_horizon/charter.md`, `docs/` (ROADMAP, LIVE_OVERLAY_PROTOCOL, OPERATING_MODEL, decisions/), `long_horizon/audit/` | the §11 KILL log + decisions + the research OS |

Also carry the canonical result JSONs as read-only reference:
`long_horizon/results/cpcv_long_horizon_{final,wf,stress,tradelog}_682.json`,
`long_horizon/results/long_horizon_tradelog_682.csv`.

**Do NOT carry:** any `src/` code (rebuilt), `dashboard/`+`frontend/` (no product),
`diagnostics/data/` v1-experiment JSONs (the stale v1 test data), `models/v1*`,
`requirements.lock` (regenerated), the old CI.

---

## 3. Target architecture (what we write)

```
config.py                       # NIFTY_500, costs, sectors, holidays, ADV/D-E thresholds
models/long_horizon/config.json # CARRIED (frozen params)

nq/                             # the package (clean namespace, no `src/` legacy)
  data/
    ohlcv.py                    # OHLCV acquisition + cache (yfinance) + split-heal
    membership.py               # PIT index-membership mask (reads carried CSVs)
    features.py                 # sma200_slope_63, atr_pct, ADV, D/E join, demerger quarantine
    fundamentals.py             # PIT D/E from the carried Screener pickle
  engine/
    panel.py                    # build ranked eligible panel (membership + ADV + solvency)
    exits.py                    # decide_exit (stop/target/trailing/min-hold/cap) — SHARED
    portfolio.py                # simulate() — sizing + fills + exits + cost model
  strategy/
    long_horizon.py             # the scan: rank by sma200_slope_63, fill slots
  validation/
    cpcv.py  bootstrap.py  dsr.py  metrics.py   # only the LH-relevant validators
  runner/
    scan.py                     # live scanner entry point (writes results/*.json)
  research/                     # factor_screen, run_factor_lab — decoupled, no v1

tests/                          # rebuilt + the CARRIED golden fixture
research/ diagnostics/research/ skills/ docs/   # CARRIED (read-only history)
data/                           # CARRIED corrections
.github/workflows/ci.yml        # lean: ruff + mypy + pytest (OMP=1, no coverage, no shap)
pyproject.toml requirements.txt # minimal deps (pandas, numpy, scipy, yfinance, pyyaml)
```

Naming: a fresh `nq/` package (not `src/`) so there's zero chance of importing legacy
paths. Live + backtest share `nq/engine/exits.py` and `nq/engine/portfolio.py` (the
non-negotiable live≡backtest parity).

---

## 4. Validation methodology (binding — from `skills/`)

- **Anchor = baseline_v0** (§1). Never 30.26 / 34.67.
- **Pre-register every trial** (`diagnostics/research/preregistry/`) + bump
  `n_trials.json` (=79) **before** running. Canonical numbers only from the cloud
  CPCV run (local cache = degenerate survivor subset, inadmissible).
- **Promotion bar:** post-tax post-cost ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022-26
  ΔCAGR > 0, ≥2019 fold-pass ≥ 60%, block-bootstrap CI-low(ΔSharpe) > 0 (block=63),
  turnover Δ ≤ +30%, one-sentence mechanism, DSR at cumulative n_trials.
- **Golden master** = the engine-drift guard AND the rebuild-equivalence proof.

---

## 5. Staged build plan (each stage gated; STOP for review between stages)

- **Stage 0 — Foundation.** Create repo, copy the §3 manifest, scaffold `nq/` + tests
  + lean `ci.yml` + `pyproject` + `config.py`. **Gate:** repo imports an empty `nq`;
  CI scaffold lints.
- **Stage 1 — Data.** `nq/data/*` — OHLCV acquisition, the PIT membership mask (reads
  carried CSVs), features (`sma200_slope_63`, atr, ADV), the D/E join, demerger
  quarantine. **Gate:** on a small known universe, `sma200_slope_63` + the eligibility
  mask reproduce expected values; no lookahead (trailing windows only).
- **Stage 2 — Engine.** `nq/engine/{panel,exits,portfolio}.py`. **Gate (the keystone):
  the rebuilt engine reproduces the carried golden fixture byte-for-byte.** If it
  matches, the engine ≡ the validated strategy.
- **Stage 3 — Strategy + runner.** `nq/strategy/long_horizon.py` + `nq/runner/scan.py`.
  **Gate:** a frozen-cfg backtest run reproduces baseline_v0 within ≤1pp on the
  canonical universe (cloud); the live scan writes a coherent `signals_today.json`.
- **Stage 4 — Validation.** `nq/validation/*` (cpcv, bootstrap, dsr, metrics) — clean,
  decoupled, no v1 engine. **Gate:** re-derives a known §11 KILL as killed; DSR reads
  the carried n_trials.
- **Stage 5 — Tests + CI green.** Port/rewrite the LH tests; CI green on the real
  runner (no shap/lightgbm → no segfault). **Gate:** full suite green in CI.

Each stage: small commits, verify, then the next.

---

## 6. CI (lean, segfault-proof by construction)

`ruff` (advisory) + `mypy --strict` (curated list) + `pytest -v` with
`OMP_NUM_THREADS=1` (+ OPENBLAS/MKL). **No `--cov`** (instrumentation segfaults the
native libs). No Docker/product jobs. Because `nq/` has no shap/statsmodels/heavy
LightGBM, the import-time native corruption that crashed the old CI is absent.

---

## 7. Non-goals (explicitly NOT built)

v1 14-day model, ensemble, the pillar stack (fusion/calendar/news/...), the v1
backtest_engine + prediction_model, the Kelly position_sizer / trade_planner, the
admission kernel, the dashboard product (FastAPI + React), Kite integration, the
multi-deploy CI. If a future product is wanted, it consumes this repo's
`results/*.json`.
