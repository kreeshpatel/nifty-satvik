# 0017 — Macro cross-asset IC re-confirmed on a PIT-CLEAN rebuild: USD/INR-sensitivity survives (GO), crude was a lookahead artifact (dropped)

- **Status:** **MEASUREMENT** (re-confirmation of the 0016 IC on a from-scratch clean series; no trade decision → no n_trials cost). **Decision: GO on USD/INR-sensitivity only → Step 2 pre-registered trial.**
- **Date:** 2026-07-02. This is Step 1 (THE GATE) of the cross-asset plan.
- **Trigger:** the 0016 IC was **provisional** — its source `data/macro_data.pkl` has NO builder in version control and could not be truncation-tested, so the −0.034 USD / +0.027 crude IC could have been a lookahead artifact of an un-audited derivation.

## What was rebuilt (the fix for the un-auditable pickle)
- **New `nq/data/macro.py`** (`build_macro_series`): fetches the raw underlyings from yfinance — WTI crude
  `CL=F`, USD/INR `INR=X`, India VIX `^INDIAVIX`, Nifty `^NSEI` — and derives **trailing-only** factors
  (`*_ret` = daily pct_change; `*_trend` = 63d trailing ROC; `vix_level`). Persisted to
  `data/macro_pit.parquet` (2015-01→2026-07, 2999 rows). Every value at `t` uses only data `≤ t`.
- **`tests/test_macro_pit.py`** — the truncation/leakage test the pickle never had: deriving on a series
  truncated at date `d` gives byte-identical values (∀ dates ≤ d) as deriving on the full series. **GREEN.**
  Any forward-looking op (centered window, full-sample z-score, bfill, `shift(-k)`) would fail it.
- Re-ran `scripts/screen_macro_ic.py --clean` — same per-stock rolling-126d beta → cross-sectional
  rank-IC vs forward-63d stock return, now on the clean factors.

## Result — clean PIT rebuild vs the provisional 0016 (like-for-like = the `*_trend` betas)
| per-stock beta signal | 0016 (un-audited pkl) | **clean PIT** | read |
|---|---|---|---|
| **usd_trend_beta** | −0.034 / IC-IR −0.303 | **−0.0295 / −0.275** | **REPRODUCES** — real, PIT-robust |
| crude_trend_beta | +0.027 / +0.263 | +0.0017 / +0.014 | **COLLAPSED** → lookahead artifact of the pkl |
| vix_trend_beta | −0.006 / −0.049 | −0.0086 / −0.076 | dead (matches 0016) |

Daily-return betas (informational): usd_ret −0.0092, crude_ret −0.0047 — weak; the **trend** transform is
the informative one. (An incidental `vix_chg_beta` +0.032/+0.19 appeared, but it was NOT pre-specified in
0016, is weak in IC-IR, and rides the high-NaN VIX calendar + relaxed `min_periods` — noted, **not pursued**;
chasing it would be the multiple-testing trap the gate exists to avoid.)

## Verdict — GO, narrowed to USD/INR-sensitivity
The gate did exactly its job: it **separated the real signal from the artifact.** An independently-rebuilt,
truncation-tested USD/INR series reproduces the 0016 USD-beta IC almost exactly (−0.034 → −0.0295, IC-IR
−0.30 → −0.28) — so USD/INR-sensitivity is **not** a lookahead mirage; it clears the pre-set bar (|mean IC|
≳ 0.025, consistent-sign IC-IR). **Crude collapsed** (+0.027 → +0.002) — it *was* an artifact of the
un-audited pickle, and is **dropped**. VIX stays dead.

## Root-cause readout (REQUIRED)
Why crude was fake and USD real: the un-audited `macro_data.pkl` `crude_trend` almost certainly carried a
non-PIT transform (a smoothed/normalized level) whose structure the transparently-trailing 63d ROC does not
reproduce — so its IC evaporated under a clean rebuild. The USD signal, by contrast, is economically grounded
(rupee-depreciation-sensitive names — importers, USD-cost businesses — underperform over the forward quarter;
negative IC = high USD-beta rank → lower forward return) and survives an honest derivation. This is precisely
what a leakage gate is supposed to catch: a too-good number (crude) is guilty until cleared, and it did not
clear; a modest, mechanism-backed number (USD) that reproduces from clean data is trustworthy.

## Next setup (Step 2)
Proceed to the **pre-registered trial**: USD/INR-sensitivity (`usd_trend_beta`) as a **rank component**
(`trend_rank ← pctile(trend_rank + λ·usd_beta_rank)`, λ∈{0.15,0.25}), 2019-2026 primary, via
`evaluate_overlay` (paired 63d block-bootstrap ΔSharpe/ΔSortino, DSR, continuous-slice 2022-26, after-tax).
**Crude is excluded** (artifact). Skeptical prior unchanged: |IC| ≈ 0.03 (half the base 0.062) + the ~34-window
wall → most likely **UNDERPOWERED**, but it is the first orthogonal, PIT-clean, mechanism-backed feature of the
program, so it earns one honest trial and — if it adds — a forward-wall watch slot (never a frozen-cfg edit).
