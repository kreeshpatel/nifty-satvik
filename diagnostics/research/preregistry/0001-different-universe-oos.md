# 0001 — Different-universe out-of-sample re-measurement of the current model

- **ID:** 0001
- **Registered:** 2026-05-30
- **Holdout:** unseen-universe (Holdout #2 in `../HOLDOUT.md`)
- **n_trials (cumulative):** 1
- **Status:** PENDING

## Hypothesis

The current live model's positive after-cost expectancy is a **real, generalizable
edge** — not memorization of the training universe (the 2025-07-20 NIFTY_500 list).

**Prediction:** when the *unchanged, already-trained* model + live gate (conf ≥ 0.92,
pred-return ≥ 8%, sweep override) is run on NSE tickers it never trained on
(Nifty Smallcap 250 / Microcap 250 constituents **not** in NIFTY_500), it produces
**positive after-cost per-trade expectancy** whose 95% bootstrap CI lower bound is
**> 0**.

This is a *generalization* test of the honest Path B baseline (~+2.5%/trade after
costs, ~60% WR, Sharpe ~1.4 on the survivor-universe backtest). If the edge is real,
it should survive — attenuated is fine — on unseen stocks. If it collapses to
zero/negative, the edge was universe-specific.

## Primary metric

**Mean after-cost per-trade return (%)**, with 95% bootstrap CI
(`bootstrap.bootstrap_metric`, trade-level). Costs: brokerage + STT + tiered
slippage + ADV-floor / liquidity tiering (Path B settings) — all ON.

## Secondary / diagnostic metrics (reported, not decisive)

- Win rate (%) + CI — sanity band ~[50%, 70%].
- Annualized Sharpe + block-bootstrap CI + **Deflated Sharpe Ratio** (n_trials=1).
- Trade count (sample-size adequacy).
- Max drawdown, profit factor.
- Per-trade return split by liquidity tier (does the edge survive *outside* the
  least-liquid names?).

## Decision rule (fixed in advance)

- **SUPPORT** (edge generalizes): per-trade mean CI lower bound **> 0**
  **AND** trade count **≥ 30** **AND** WR in [45%, 72%] (not a degenerate regime).
- **KILL** (edge was universe-specific): per-trade mean CI upper bound **≤ 0**,
  with trade count ≥ 30.
- **INCONCLUSIVE:** trade count < 30, or CI straddles 0. → need Holdout #1
  (forward) evidence; do not over-interpret.

Per the discipline, SUPPORT is *weak* support (one holdout test ≠ proof); KILL is
decisive. This cannot "bless" the model.

## Run parameters (to be fixed at run time, recorded here before execution)

- Unseen-universe ticker source: _to fill_ (index list minus NIFTY_500).
- Test period: _to fill_ (note macro-context caveat per HOLDOUT.md).
- Model: current live single-model `models/v1/` (unchanged), live gate config.
- Seed: via `src/repro/seeds.py`.

## Result

**Run:** 2026-05-30 (runner commit `0a8ac02`, `diagnostics/data/oos_unseen_universe.json`).
145 unseen tickers fetched + feature-built (from ~200 candidates; 54 dropped as
actually in NIFTY_500, ~1 delisted). Test 2021-01-01..2025-12-31, 172,925
ticker-days, **357 trades**. Frozen `models/v1` (79 features, trained 2010-2024),
live 0.92 gate. Caches isolated + restored (verified: no `.oosbak` leftover,
training `features.pkl`/`ohlcv.pkl` intact).

| Metric | Value | 95% bootstrap CI |
|---|---|---|
| **Per-trade after-cost return (primary)** | **+4.10%** | **[+2.86, +5.32]** |
| Win rate | 68.9% | [64.2, 73.7] |
| Sharpe (annualized) | 2.76 | — |
| CAGR | 52.3% | — |
| Max drawdown | −15.5% | — |
| Profit factor | 2.11 | — |

**Verdict: SUPPORT (weak — one holdout).** Decision rule met: n=357 ≥ 30, per-trade
CI lower bound (+2.86%) > 0, WR (68.9%) within the sanity band. The frozen model
produces **positive after-cost expectancy on stocks it never trained on** → the edge
is NOT pure training-universe memorization. That is a genuine, non-trivial result.

**Honest caveats — do NOT over-read the magnitude:**
- **Survivorship in the holdout universe:** the unseen list is *today's surviving*
  smallcaps (delisted losers absent) → returns biased UP. +4.1%/trade & Sharpe 2.76
  are optimistic.
- **2021 smallcap melt-up:** 2021-2025 includes the post-COVID micro/smallcap rally
  the main audit flagged as "extreme, not replicable." Sharpe 2.76 > the
  training-universe honest baseline (~1.4) almost certainly reflects survivorship +
  this window, NOT a stronger edge.
- **Liquidity / position-impact:** tiered slippage applied, but real small-cap
  position-impact not modeled → real fills worse.
- **Macro partly in-sample:** only per-stock + cross-sectional features are truly OOS.
- **DSR not computed this run** (secondary; runner reports per-trade CI + Sharpe).
  Follow-up.

**What this establishes / doesn't:** the edge *direction* generalizes (positive
expectancy, ~69% WR on unseen stocks) — argues against memorization. It does NOT
establish the *magnitude* (inflated by survivorship + 2021), and per `../HOLDOUT.md`
a holdout can only support/kill, never bless. The forward wall (Holdout #1, paper)
remains the decisive test. **n_trials now = 1.**

### Robustness (task 2, 2026-05-30): does the edge survive dropping the 2021 melt-up?

Sensitivity check of the SUPPORT verdict (not a new hypothesis) — per-year and
2022-2025-only re-bootstrap of the same 357-trade run.

| Exit year | n | per-trade after-cost | WR |
|---|---|---|---|
| 2021 | 94 | +4.21% | 70.2% |
| 2022 | 102 | +5.83% | 74.5% |
| 2023 | 40 | +2.33% | 62.5% |
| 2024 | 85 | +3.61% | 67.1% |
| 2025 | 36 | +2.07% | 61.1% |

**2022-2025 only (drops the 2021 post-COVID smallcap melt-up): n=263, per-trade
+4.07% [CI 2.62, 5.51], WR 68.4% → SUPPORT survives.**

- The "2021 inflation" caveat from the result above is **REFUTED**: 2021 (+4.21%) is
  not the standout (2022 is, +5.83%), and the post-2021 number (+4.07%) is
  essentially identical to the full-window (+4.10%). The edge is positive every
  year (WR 61-75%), including choppy 2025. NOT a one-off-rally artifact.
- **Survivorship caveat STILL stands** (not addressed by this check): the unseen
  list is today's surviving smallcaps; delisted losers absent (no yfinance data;
  paid delisted data ruled out in the main audit). Magnitude + Sharpe still biased
  up; real expectation < +4%/trade. Forward wall remains decisive.

Net: SUPPORT holds and is **strengthened** (robust to year, not a 2021 artifact);
magnitude still survivorship-caveated.

### Addendum (2026-05-30): model-mismatch caveat

The live cron runs `NIFTYQUANT_STRATEGY=ensemble` (v1 + v1_7d + v1_30d averaged),
confirmed from the cron env. This experiment used the **single-model `models/v1`**
(the BacktestEngine default), i.e. the ensemble's primary 14d component — NOT the
live ensemble. So 0001 shows the ensemble's *core component* generalizes to unseen
stocks; it is informative about, but not identical to, the live ensemble. The
forward-wall test (`0003`) reads the actual live-ensemble paper trades and is the
clean test of what's deployed. (Same caveat applies to the 0002 sector screen —
single-model v1, not the ensemble.)
