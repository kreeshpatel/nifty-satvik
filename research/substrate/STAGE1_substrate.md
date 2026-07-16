# Stage 1 — the wide, uncapped trade substrate (measurement, no trial spent)

**Built 2026-07-16. Status: MEASUREMENT** (like findings 0097/0098 — no `n_trials` increment, no
config change). Reproducible from the committed pipeline; the live book is untouched.

## What was built

- `nq/data/weekly.py` — canonical cached weekly panel (ISO-week, reconciles byte-for-byte with
  `prep_weekly_rank`). 336,382 rows / 788 tickers, determinism-hashed.
- `nq/research/setups.py` — the TraderLion pattern zoo as pure, trailing-only detectors:
  VCP, bull/high-tight flag, cup-with-handle, ascending base, double bottom (origins 4-8).
- `scripts/run_bhanushali_weekly_rank.py` — zoo wired in as cfg-gated **additive** levers
  (`zoo_origins=()` default off ⇒ byte-identical 0094). Weekly volume added (read-only).
- `scripts/build_substrate.py` → `research/substrate/trades.parquet` — **4,391 uncapped trades**
  (18× the 255 the ₹10L cap funds) via the engine-of-record's `backtest(uncapped=True)` under the
  LIVE Phase-2 exit, origin-tagged, with PIT-safe features (ext-vs-SMA, risk%, MAE/MFE, rank-CRS,
  ATR%, vol-ratio, 52w-high distance, fundamentals ep/bp/roe/low_debt) and a train(2019-22) /
  holdout(2023-26) / pre-2019-untrusted split.

**Determinism guard: capped-default reproduces Sharpe 1.1319 / 255 — the engine is unchanged.**

## Per-setup expectancy (uncapped, live P2 exit)

| setup | N | win% | meanR | medR | PF | risk%_med | stopout% |
|---|---|---|---|---|---|---|---|
| touch44 (base) | 1754 | 44.2 | 0.329 | **−0.94** | 1.42 | 7.1 | 53 |
| trend_pullback | 1178 | 44.8 | 0.338 | −0.95 | 1.38 | 6.1 | 54 |
| sr_pivot | 57 | 50.9 | 0.557 | +0.25 | 1.88 | 8.5 | 51 |
| box | 557 | 54.2 | 0.566 | +0.31 | 2.12 | 17.7 | 37 |
| cup_handle | 198 | 56.6 | 0.678 | +0.66 | 2.42 | 17.3 | 35 |
| ascending_base | 107 | 59.8 | 0.622 | +0.83 | 2.37 | 22.6 | 35 |
| double_bottom | 509 | 59.3 | 0.593 | +0.48 | 2.70 | 25.0 | 25 |
| flag | 16 | 62.5 | 1.288 | +1.85 | 4.48 | 14.8 | 31 | *(N too small)* |
| vcp | 15 | 66.7 | 0.864 | +1.30 | 6.14 | 33.2 | 7 | *(N too small)* |

## Findings

1. **The base touch is the weakest entry per-trade** — its *median* trade loses ~1R (50% near-full
   stop-outs), carried by a 27% R≥2 tail. This is the "why bad trades fail" structure the 255-trade
   sample was too small to expose.
2. **The pattern-zoo entries are genuinely higher quality per-trade** — cup_handle / ascending_base /
   double_bottom all have **positive median R** and 55-60% win, and **hold in the 2023-26 holdout**
   (double_bottom strongest: N=231/237, 63%→58% win, +0.67→+0.59R).
3. **The edge is NOT a tight-stop mirage** (the E6 trap). The zoo patterns carry **wider** stops
   (17-33%) than the touch (7%) and *still* win on an R-normalized basis — the opposite of the crude
   S/R mirage. Risk-normalized meanR: vcp 0.86 / flag 1.29 / double_bottom 0.59 vs touch 0.33.
4. **Chart-validated** — rendered detections (TATAMTRDVR cup, NBCC double-bottom, JBMA ascending
   base, DELTACORP failed-cup) show real, recognizable patterns with the entry at the breakout, SMA
   rising. Detectors are not labeling random breakouts.
5. **VCP / flag are too rare (N=15/16) to certify** — the detectors are strict; treat as unproven.

## Caveats (carried into Stage 2/4)

- **Serialization**: the uncapped substrate is the engine's one-position-per-ticker walk, so adding
  the zoo *reduced* touch/trend counts (they compete for the ticker slot over time). It is NOT a
  clean signal-level census; per-setup N shifts with which detectors are on. A true signal-level
  (overlap-independent) substrate is a candidate v2 if Stage 2 needs it.
- **Per-trade ≠ portfolio** still governs: these win per-trade but must be re-tested under the real
  capital cap in Stage 4 (the registry's iron law). Nothing here is a config change.
- Numbers differ from the ad-hoc E10 table by construction (live P2 exit not frozen 13wk-cap;
  serialized not overlapping; proper sr_pivot not crude S/R).

## Reproduce

    python scripts/build_substrate.py      # -> research/substrate/trades.parquet + guard
