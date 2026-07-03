# 0025 — Path-1 rerun: the 4×ATR stop geometry as the ONLY change to the practitioner config

- **Status:** PRE-REGISTERED (2026-07-03, before any run).
- **Class:** MEASUREMENT / external-strategy analysis (0022–0024 series convention; not an overlay trial on
  the momentum sleeve, no cfg change, no n_trials increment). Single pre-declared mechanical change; results
  feed the v1.5 Path-B sleeve proposal for the 2026-10-01 review, nothing else.
- **Motivation (reviewer, accepted by owner).** 0024 root-cause #3: the candle-low stop (~3–4%) needs ~57%
  notional to deploy 2% risk → the 30% cap cuts realized risk to ~1% → 21 trades/yr × 1% ≈ nothing. The MAE
  diagnostic (0024 §2) showed the median RSI/dip recovery path takes −6.6% (p10 −17.4%) before working — a
  candle-low stop is structurally guaranteed to fire on the median trade, and 0023's stop-width flip
  (−0.33→+0.25 net) already demonstrated the geometry effect. A 4×ATR stop (~8–12%) simultaneously
  (a) survives the median excursion and (b) needs only ~20–25% notional for 2% risk — under the cap. One
  mechanical change tests both.

## Frozen spec
Everything byte-identical to `scripts/run_bhanushali_practitioner.py` as committed (weekly top-50 watchlist,
A+B combined signals, buy-stop entry live 3d with no-chase, quality-green + HVC, half@+2R with breakeven
floor, swing-low ratchet trail, NIFTY-TRI regime pause, 5 pos / 3 new-wk / 10d cooldown, 2% risk, 30%
notional cap, tiered real costs, PIT membership) **except one line: the initial stop = fill − 4.0×ATR(14,
signal day)** (replacing the candle-low ×0.999 / big-candle-midpoint rule, which becomes moot). The
half-target remains +2R off the new (wider) R; the swing-low trail and breakeven floor still ratchet the
stop upward. No other knob moves. **No retuning after results, whatever they show.**

## Pre-declared arms (ALL reported; 2×2 + ablation-of-record)
| | survivor-only cache (pinned f8625a8f) | corrected universe (pinned + backfill + alias map) |
|---|---|---|
| candle-low (0024 baseline) | re-report | run |
| **4×ATR initial stop** | run | run |

Gross + net for every cell. The corrected-universe cells run only after `finalize_bhavcopy_backfill.py`
lands and the CA screen is reviewed; the survivor-only cells run immediately. Corrected-universe series
sourced: pinned cache + `data/ohlcv_backfill.pkl` + `data/delisted_alias_map.json` (aliases materialized as
the old symbol pointing at the successor series, TATAMOTORS truncated at its `valid_until`). Alias pairs
have complementary membership windows, so no double-hold; any residual transition-week overlap is noted,
not patched.

## What would change the verdict (fixed now)
- **Meaningful lift:** 4×ATR net Sharpe ≥ +0.40 on the corrected universe (i.e., roughly the 0023 gross
  showing up net once deployment unblocks) → the v1.5 Path-B proposal gets this geometry and goes to the
  Oct-1 review as written.
- **No lift** (net Sharpe < +0.30 or DD blows past −30% without compensating return): the deployment
  hypothesis is wrong or costs still dominate → the sleeve proposal stands or falls on the 0024 numbers;
  no further geometry work (the next knob would be trial #2 of a search).
- Survivorship attribution: the (candle-low, corrected) cell vs 0024's headline isolates what the missing
  corpses were worth; expected direction DOWN (finding it moves UP is a red flag for the backfill's CA
  handling, per the leakage-audit house rule).

## Known limitations (carried forward)
Bhavcopy-sourced series are price-return only (no dividend adjustment) and CA-screened not CA-perfect;
gap-through stops fill at the stop; no earnings-calendar avoidance. All flagged in 0024 §"limitations".
