# 0016 — Cross-asset / macro data at 63d: per-stock USD/crude SENSITIVITY carries real orthogonal signal (the first new information source)

- **Status:** **MEASUREMENT** (rank-IC probe, no trade decision → no n_trials cost, per research-log). A positive lead: the first genuinely-new (orthogonal, non-price) signal found this arc. Frames a real pre-registrable trial.
- **Date:** 2026-07-02. Script: `scripts/screen_macro_ic.py`. Data: `data/macro_data.pkl` (VIX, crude/USD trends, regime, breadth; 2015-2026).

## Question
Does the cross-asset / macro data carry 63-day signal the price doesn't? (The technical zoo — 0079/O-015 —
was all price-derived and IC ≈ 0. Macro/commodity/FX is a *different* data source.)

## Result
**A. Time-series (regime, market-level):** macro state weakly predicts the STRATEGY's forward-63d return —
india_vix Spearman +0.136, crude_trend +0.098, global_risk_score −0.149; strategy mean forward-63d return
+8.7% in high-VIX vs +0.7% mid-VIX; regime 0 +8.2% vs regime 2 +3.2%. **Overlapping windows inflate these**,
and it is *market-timing* → an entry gate is a §11 KILL (O-001) and 0070 showed market-state overlays
plateau. Only regime-conditional *sizing* is an open door. Confirms 0070; not a new lever.

**B. Cross-sectional (per-stock macro SENSITIVITY — the genuinely-new, rankable test):**
| per-stock beta signal | mean IC | IC-IR |
|---|---|---|
| **usd_inr_trend_beta** | **−0.034** | **−0.303** |
| **crude_trend_beta** | **+0.027** | +0.263 |
| vix_trend_beta | −0.006 | −0.049 |

A stock's rolling-126d beta to USD/INR (−0.034) and crude (+0.027) has **real, non-zero, consistent-sign
cross-sectional IC** — vs the base `sma200_slope_63` |IC| 0.062. Half the base's magnitude, but **non-zero
and orthogonal** (it measures macro exposure, not the stock's own price trend — information the price does
not already contain). The entire price-derived zoo was IC ≈ 0; this is not.

## Root-cause readout
The technical indicators failed because they are all transforms of the *same price* — no new information.
Cross-asset **sensitivity** is different data: how a stock co-moves with crude / the rupee. That carries a
small but real forward signal (e.g. USD-sensitive names underperform as the rupee weakens; crude-levered
names ride crude). It is the first orthogonal source found this arc — the honest form of "train on other
data": add *information*, not re-slice price or search combinations.

## Next setup
Worth a **real pre-registered trial** — test USD/INR-sensitivity (± crude) as an **orthogonal feature**, NOT
a sole ranker (small IC loses as a ranker, like the 52-week-high): either a conviction tilt
(`nq/research/conviction.py` blend) or a multi-factor rank component alongside the slope. Skeptical prior:
small orthogonal IC + the ~34-window wall → likely UNDERPOWERED, but it may *add* (unlike the zero-IC zoo) and
it is genuinely new. This is also the direction longer history (2010+) most helps — more windows to certify a
small orthogonal edge. Do NOT gate entries on macro (killed); sizing/conviction only.
