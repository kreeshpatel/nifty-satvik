---
name: backtest-rigor
description: >
  Run before trusting ANY number from the long-horizon harness or a candidate overlay.
  Trigger words: "validate backtest", "is this result trustworthy", "backtest red flags",
  "harness check", "lookahead", "overfit", "data integrity", "should I trust this",
  "walk-forward gate", "corporate actions", "split bug", "demerger", "survivorship",
  "sample size too small", "multiple testing penalty", "DSR".
---

# Backtest Rigor — Pre-Trust Checklist

This skill is the integrity gate you run before anchoring on any number produced by the
long-horizon harness or a new overlay test. It is a checklist of failure modes, each
cross-referenced to the concrete safeguard (or known gap) in this repo.

It complements `skills/overlay-testing/SKILL.md` — that skill governs the promotion bar
and significance tests for a specific overlay. This skill governs whether the harness
itself is trustworthy enough to generate those numbers in the first place.

**Run this checklist every time:**
- A new overlay produces a headline metric you're about to act on.
- The harness is modified and you need to confirm it still tracks the frozen baseline.
- You are about to cite a number in a commit message, a pre-registration, or a verdict.
- A number looks too good or too bad relative to prior known results.

---

## Baseline anchor (memorise this)

The baseline of record is **baseline_v0**: gross CAGR 26.1% / Sharpe 1.02 / maxDD −41.9% /
Calmar 0.62; after-tax (STCG 20%) CAGR 23.1% / Sharpe 0.83 (supersedes the optimistic-exit
30.26%/1.15 measurement, 2026-06-27). Source: `research/baseline_v0.json`.

The `cpcv_long_horizon_final_682.json` frozen-cfg arm is the historical run that produced the
superseded 30.26% (optimistic target-fill; exit-parity unification costs ~4pp CAGR). The
re-derived 34.67% / 1.248 in `cpcv_long_horizon_tradelog_682.json` is research-only —
it uses re-derived params and does NOT match what live signals are generated from. Never
anchor on 34.67% in a promotion decision.

---

## Section A — Data Integrity (check first; kills everything downstream if wrong)

### A1. Corporate-action contamination — the VEDL lesson

**What happened:** VEDL's Hindustan Zinc demerger was processed by yfinance as a split
(price divided by the ratio). This fabricated a sma200_slope_63 of 24.94 from a true
slope of 2.16 — an 11× distortion. A name with a corrupted slope could enter or exit the
top-15 solely due to a data artefact.

**Check:**
- Do any tickers in the current panel have a slope, ATR, or price series that is visually
  discontinuous (step changes >50% in a single day that are not explained by actual price
  movement)?
- Run `data/ohlcv_integrity_check.py` on the OHLCV panel before ingesting into any backtest.
  It flags: same-day prices matching prior-day close with a large gap (potential bad split
  factor), zero-volume days mid-series, negative prices.
- Check `long_horizon/results/README.md §corp-actions` for the list of known affected tickers.
- For any ticker that was part of a demerger, merger, or name-change in the test period,
  verify the OHLCV series manually against NSE historical data before trusting its ranking.

**Our safeguard:** The incremental OHLCV builder (`data/ohlcv_incremental.py`) applies a
split-heal pass and filters zero-volume. It does NOT currently detect demerger-as-split.
This is an open gap. Treat any name with a dramatic slope ranking spike as suspicious
until verified.

### A2. Survivorship bias — universe membership

**What happened in v1:** The original universe used current NSE 500 membership (all
`to_date=2030`). Stocks deleted from the index due to poor performance were present in
the current list but should not have been eligible in 2015. This inflated absolute CAGR.

**Check:**
- Is the panel restricted to the canonical 682-name PIT-corrected universe?
  The file is `long_horizon/results/cpcv_long_horizon_final_682.json` — the names list
  baked into the panel at CI time was derived from the PIT-membership reconstruction.
- If you are using a local runner, the degenerate local cache has ~20 stocks (current
  survivors only). This is NOT the canonical universe. Local runs print ~15% CAGR.
  Never report local numbers as a result — always wait for the CI CPCV run.
- The PIT membership mask lives in `data/index_membership.py::filter_features_dict`.
  Verify that the mask's effective date range covers the full test window (2010–present),
  not just post-2017 where the reconstruction is most reliable.

**Our safeguard:** `data/index_membership.py` provides the PIT mask. The golden master
test (`tests/test_long_horizon_golden.py`) will catch any harness change that alters
which stocks are eligible on a given date.

### A3. Look-ahead bias — feature construction

**What happened in v1:** Three of 79 features (sector-seasonal monthly) used the full
history map to label a month, not just data available up to that month. The leak was
immaterial to the base Sharpe (ΔSharpe −0.10 on de-leak A/B) but invalidates comparisons
between de-leaked and leaky variants.

**Check every new feature:**
- Does any rolling window extend *forward* in time (e.g., a centred moving average)?
  All windows must be `min_periods=1, closed='left'` or equivalent trailing.
- Does any categorical label (sector, seasonal bucket) derive from data that wasn't
  available at the as-of date? Use the `expanding-by-year` seasonal map in
  `src/data/seasonality.py`, NOT the full-history map.
- Does any fundamental join (Screener, Compustat) use the announcement date or the
  report-available date? Use the later of the two (the date the market could observe it).
- Is `NIFTYQUANT_SEASONAL_LEAKY` set? On the Render (now GitHub Actions) environment it
  is PINNED=1 to match the frozen model's training features. The repo default is
  de-leaked. Any offline result with a local env where the pin is absent will differ by
  that −0.10 Sharpe from a result produced with the pin. Note this in your comparison table.

**Our safeguard:** `data/data_store.py::compute_all_features(persist=False)` — fresh
feature computation, no stale pkl. The `persist=False` flag is what the live cron uses.
Do NOT call with `persist=True` and then reuse the pkl across different universe
definitions — that's the AUD-018 clobber bug.

### A4. Stale feature cache

**What happened (AUD-018):** `compute_all_features(persist=True)` overwrites the shared
`features.pkl` in-place. A background job that called it with a different universe slice
(e.g., 58 unenriched stocks) silently replaced the 79-feature pkl used by the harness.
The harness loaded a stale pkl and ran on garbage features — this produced results that
appeared valid.

**Check:**
- Are you calling `compute_all_features(persist=False)` for all harness runs?
  Only the offline enrichment pipeline that builds the canonical pkl should use `persist=True`.
- If a pkl exists, check its feature count: `len(pd.read_pickle('data/features.pkl').columns)`.
  The canonical pkl has 79 features after enrichment. If it has fewer, re-enrich:
  ```bash
  python -m diagnostics.enrich_cache   # rebuilds from ohlcv.pkl + macro/sector caches
  ```
- Never commit a `features.pkl` or `ohlcv.pkl` to the repo — both are gitignored and
  must be rebuilt from source on each machine.

---

## Section B — Cost and Execution Realism

### B1. Transaction cost components (Indian NSE specifics)

Failure to include all cost components inflates CAGR by 3–6% annually at our turnover level.

**Required cost model (source of truth: `config.py`):**

| Cost | Value | Applied on |
|------|-------|-----------|
| Brokerage | 0.03% per leg | Entry + exit |
| STT | 0.1% per leg | **Both legs** (buy + sell) — equity *delivery* |
| Slippage | tiered by ADV (large 0.05% / mid 0.22% / small 0.40%) + 0.1% impact >0.5% ADV | Both legs |

- STT for **delivery** equity is 0.1% on **EVERY leg — both buy AND sell** (sell-only is the
  *intraday / F&O* rule, which does NOT apply to this ~22-day-hold delivery book). The long-horizon
  engine (`long_horizon/backtest/portfolio.py` `LEG_COST = BROKERAGE + STT`, charged on entry AND
  exit) and `config.py::delivery_leg_cost` already do this correctly; matches the algo_ai FY25-26
  table. *(Corrected 2026-06-28, Entry-Signal Arc P7 — the prior "sell side only" here was stale v1
  text contradicting the live engine.)* A harness that applies STT on 0 or only 1 leg understates
  round-trip friction by ~0.1% and inflates CAGR.
- STCG (20%) applies to gains on positions held < 252 trading days. The long-horizon
  median hold is ~22 days, so effectively ALL realized gains are STCG. Post-tax numbers
  will be materially lower than gross. See `skills/overlay-testing §4b` for the exact
  tax mechanics.
- Circuit limits: NSE applies ±5/10/20% daily circuit filters on individual stocks.
  A position cannot be exited at a price outside the circuit band for that day. This is
  particularly relevant for stop-loss exits in volatile stocks. The harness currently
  does NOT model circuit limits. Any result in a period with heavy circuit events
  (March 2020, March 2022) is optimistic on exit execution.

### B2. Slippage — large-mid vs small-cap

The canonical 682-name universe is filtered to large+mid (ADV ≥ 5 Cr median) via
`restrict_to_large_mid`. Within that universe, the 15 bps entry slippage is calibrated
to the median ADV of ~250–500 Cr. Names in the bottom quartile of the eligible universe
(ADV 5–50 Cr) should use the 2× cost column as the reference in your cost sweep table.

**Check:**
- Does the overlay change which names get selected? If it systematically selects
  higher-ranked-by-trend names that are also less liquid, the 1× cost column is
  insufficient. Report the 2× cost column as the promotion reference.

### B3. Fill realism — close-only

The harness executes at the CLOSE price. In live trading, the scanner runs at 4:15 PM IST
and orders are placed at market-open next morning (T+1). This means:
- The effective entry price is next-day open, not close. The `slip_bps` is meant to
  model this slippage. If you are computing signals before market close and want to
  test next-day-open fills, you must adjust the entry price series.
- Stop exits in the harness fire at the CLOSE on the day the close breaches the stop.
  In live trading, a stop fired intraday may fill at a worse price. This is a known
  optimism in the harness; it is accepted as a design decision (we do not hold intraday
  granular data).

---

## Section C — Bias Taxonomy

### C1. Look-back bias / optimisation bias

The frozen params in `models/long_horizon/config.json` were derived once on the
pre-2017 train slice and confirmed by the walk-forward. They must NOT be re-derived on
the full history to explain a backtest result. Re-deriving on the full history and then
reporting the result as a "validation" is the definition of in-sample overfitting.

**Check:**
- Were the params used in this run loaded from `models/long_horizon/config.json`
  (`load_frozen_cfg`)? If any param differs from that file, the result is NOT a validation
  of the live strategy.
- Is `simulate` being called with a `cfg` dict that overrides any frozen param "just to
  see"? That is a research run, not a validation. Label it clearly.

### C1b. "Plateau, not peak" — parameter robustness red flag

A result that sits on a **smooth performance plateau** across neighbouring parameter
values is trustworthy. A result perched on a **narrow peak** — where adjacent values
drop sharply — is almost certainly overfit, even if it clears the DSR bar.

**When it applies:** any time you validate or report a threshold or multiplier value
(e.g., `stop_atr_mult`, `min_hold`, `target_pct`, `slope_lookback`).

**How to check:**
- Sweep the parameter ±20–50% around the chosen value in at least 5 steps. Plot or
  tabulate Sharpe (or per-trade EV) vs the sweep axis.
- A plateau: Sharpe varies by < 0.15 across the sweep range. Proceed.
- A narrow peak: Sharpe collapses by > 0.30 when moving one step in either direction.
  Treat the result as **invalid** until the mechanism is understood.
- Our existing robustness discipline (0026-style pre-reg: "if CI straddles 0, disable")
  complements this check — a peak result will typically fail the CI-low gate too, but
  check the sweep shape explicitly before concluding the gate failure is just noise.

**Concrete examples from this project:**
- The `min_hold=10` day guard was verified on a sweep (8 / 10 / 12 / 15 days) before
  adoption — it sat on a plateau.
- The 0026 sweep-override band was disabled when the bootstrap CI straddled zero at the
  exact boundary value — consistent with peak behaviour, not a stable plateau.

*(adapted from mphinance/alpha-skills `backtest-expert`, MIT licence)*

---

### C2. Multiple-testing / data-mining penalty (DSR)

Every time a new hypothesis is tested using the same historical data, the effective
significance bar rises. Our multiple-testing correction is the Deflated Sharpe Ratio
(DSR), implemented in `src/validation/overfitting.py`.

**Our n_trials tracking:** The current trial count is in
`diagnostics/research/preregistry/n_trials.json`. Check it before every test:
- Does this test spend a trial? (New hypothesis = yes. Measurement / diagnostic = no.)
- Is the DSR at the current n_trials applied to the candidate Sharpe? A result that would
  be PROMOTE at n_trials=20 may only reach SHADOW at n_trials=50.
- The DSR penalty formula requires the estimated trial-to-trial Sharpe correlation ρ
  (configured in `n_trials.json`). Do not change ρ without a documented justification.

**Never run the same hypothesis twice** and report the better of the two outcomes. The
second run does not lower n_trials; it raises the DSR penalty. Decide the hypothesis
from the pre-registration, run once, report regardless.

### C3. Regime-selection bias

A result that is strong in 2017–2021 and weak in 2022–2026 is NOT a positive result.
The 2022–2026 period (particularly 2022–2023 and the 2025 range-bound market) represents
live trading conditions. A strategy that only works in the strong bull years of 2017–2021
has regime-selection bias — it is not a general edge.

**Check:**
- Does the overlay show positive ΔCAGR in the 2022–2026 sub-period specifically?
  This is one of the hard gates in the promotion bar (see `skills/overlay-testing §4c`).
- An overlay that is CAGR-neutral in 2022–2026 but dramatically positive in 2017–2021
  is a SHADOW candidate at best — it should not be promoted unless the mechanism
  predicts why 2017–2021 conditions will recur.

### C4. Granularity / stability bias

Is the result driven by 1–2 exceptional years or exceptional names?

**Check:**
- What is the walk-forward fold-pass rate (positive ΔSharpe across individual years)?
  Require ≥ 60%. See `skills/overlay-testing §5b`.
- What fraction of the total P&L comes from the top 3 names? If >30%, the result is
  name-concentration-driven and may not generalise.
- Removed a name from the test universe (jackknife one stock at a time on the top
  performers). Does the headline metric change by >10%? If yes, the result depends on
  those names being in the universe — that's fragile.

---

## Section D — Harness Self-Validation

### D1. Golden master gate — the engine drift guard

**The non-negotiable gate:** `tests/test_long_horizon_golden.py` byte-compares the full
harness (signal generation + sizing + cost accounting + exit logic) against a committed
fixture (`tests/fixtures/lh_golden.json`). ANY change to any of the following modules
must regenerate the fixture in the same PR:

- `long_horizon/backtest/portfolio.py`
- `src/engine/exit_logic.py`
- `long_horizon/strategy/value_derivation.py`
- `data/index_membership.py`
- `config.py` (any cost param)

If the golden master test is RED and you are proceeding with a harness run anyway, you
are running against an untrusted harness. Stop. Fix the engine drift first.

To regenerate the fixture intentionally (after a deliberate harness change):
```bash
python diagnostics/build_lh_golden.py
```
Commit the new `tests/fixtures/lh_golden.json` in the same PR as the engine change,
with a description of what changed and why the new fixture is correct.

### D2. Harness must reproduce §11 rejections

Before trusting any new overlay result from a modified harness, verify the harness
correctly rejects overlays that are already known to be dead:

```
From long_horizon/STRATEGY_FULL.md §11 (must all show REJECT):
- Market-regime gate (dual-momentum, breadth threshold)
- Sector-residual momentum / sector selection overlays
- Reversal signals (RSI / MACD / ROC blending)
- Signal-level low-vol blending
```

If the harness promotes one of these, the harness has a bug. Fix it before reporting
any new overlay result.

### D3. Local vs canonical universe

A LOCAL run (without the CI-produced 682-name panel) uses only the yfinance-cached OHLCV
for the ~20 names that happen to be in `data/` locally. This produces ~15% CAGR on the
baseline (vs 26.1% gross on the canonical universe — baseline_v0; the superseded 30.26%
was the old optimistic-exit figure). Every local run should print a warning:

```
WARNING: running on local cache (~N tickers). This is NOT the canonical result.
Dispatch via `gh workflow run cpcv-research.yml` for the 682-name canonical run.
```

Never report a local run number as a result. Use it only for smoke-testing that the
harness doesn't crash.

---

## Section E — Sample Size and Statistical Power

### E1. Minimum trade counts

| Use case | Minimum trades | Preferred |
|----------|---------------|-----------|
| Any metric at all | 30 | — |
| ΔSharpe verdict | 100 | 200+ |
| Walk-forward fold | 15 per fold | 30+ per fold |
| Sub-period sub-split | 20 per sub-period | 50+ |

The long-horizon strategy generates ~154 trades/year on the 682-name universe.
An overlay that substantially reduces trade count (e.g., a heavy filter that cuts trades
by 60%) will often fail the walk-forward fold minimum even if the per-trade edge improves.
Report trade counts alongside all metrics.

### E2. Block bootstrap block size

Use `block_size=63` (one full strategy cycle). Shorter blocks (e.g., 21 days) will
understate autocorrelation in the daily return series and produce falsely narrow CIs.
The baseline block-bootstrap 95% CI on Sharpe is [0.58, 1.88] (median 1.23) — any
overlay CI that is substantially narrower than this on the SAME data should be checked
for block-size mismatch.

---

## Section F — Checklist Summary (run in order, stop on first fail)

Copy this table into your pre-registration or verdict doc and fill it in:

```
[ ] A1. OHLCV integrity check run — no demerger-as-split distortions in top-15 names
[ ] A2. Universe = canonical 682-name PIT panel (not local cache)
[ ] A3. All features trailing-only (no look-ahead); seasonal env-pin noted if applicable
[ ] A4. features.pkl freshly computed (persist=False) or verified 79-feature count
[ ] B1. Cost model includes brokerage (0.03%/leg) + STT (0.1% sell-only) + slippage
[ ] B1. Post-STCG (20%) applied to gains; absolute post-tax CAGR reported
[ ] B2. 2× cost column used as promotion reference for any overlay with extra turnover
[ ] C1. Params loaded from frozen cfg — no re-derivation on full history
[ ] C1b. Any param value being validated: swept ±20–50% to confirm plateau (not narrow peak)
[ ] C2. n_trials checked; DSR applied; new hypothesis pre-registered before running
[ ] C3. 2022–2026 sub-period ΔCAGR > 0 (not just pooled 2017–2026)
[ ] C4. Walk-forward fold-pass ≥ 60%; no single-name concentration check failed
[ ] D1. Golden master test GREEN before trusting harness numbers
[ ] D2. Harness reproduces §11 rejections as rejected
[ ] D3. Run is CI-produced (or explicitly labelled as a local smoke test)
[ ] E1. Minimum 100 trades in the overlay arm; 15+ per walk-forward fold
[ ] E2. Block bootstrap block_size=63; n=5000; 95% CI lower bound reported
```

All boxes must be checked for a PROMOTE verdict. A result with unchecked boxes is at best
SHADOW pending a clean run.

---

## Attribution

Core "punish-the-strategy" philosophy and stress-testing structure adapted from
`claude-trading-skills/skills/backtest-expert/SKILL.md` (MIT licence,
https://github.com/claude-trading-skills), authored by the claude-trading-skills
contributors. Substantial portions rewritten for the NiftyQuant long-horizon context:
corporate-action contamination protocol, Indian cost model (STT/STCG/circuit), PIT
universe handling, golden master gate, DSR/n_trials integration, and the §11 harness
self-validation requirement are original to this project.

---

## Cross-references

- **Overlay promotion bar and significance tests:** `skills/overlay-testing/SKILL.md`
- **Exit / rotation overlays specifically:** `skills/sell-replace-logic/SKILL.md`
- **Frozen cfg (live params):** `models/long_horizon/config.json`
- **Baseline result (frozen-cfg arm):** `long_horizon/results/cpcv_long_horizon_final_682.json`
- **Rejection log:** `long_horizon/STRATEGY_FULL.md §11`
- **DSR implementation:** `src/validation/overfitting.py`
- **OHLCV integrity checker:** `data/ohlcv_integrity_check.py`
- **Trial counter:** `diagnostics/research/preregistry/n_trials.json`
- **Golden master fixture:** `tests/fixtures/lh_golden.json`
- **Golden master builder:** `diagnostics/build_lh_golden.py`
- **Feature enrichment single source of truth:** `data/feature_enrichment.py`
- **Seasonal env pin note:** `CLAUDE.md §Consolidation 2026-06-12`
