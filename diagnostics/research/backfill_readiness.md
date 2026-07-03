# Delisted-price backfill — READINESS NOTE (2026-07-03)

**The survivor-only-cache data debt (CLAUDE.md / prereg v1.5 §3) is CLOSED for research use.**

- **103/103 missing PIT members resolved**; coverage-weighted recovery **~100%** of the 141,793 lost
  member-days (2017–2026). Worst residuals: TIFIN (560/1031d), HEXAWARE (delisted-period gap), both small.
- Sources: 33 index-dropped-but-still-trading (yfinance, dividend-adjusted); 6 old-symbol yfinance
  retentions; 17 identity-validated rename aliases (`data/delisted_alias_map.json` — bhavcopy raw-close
  identity check; 2 impostor aliases rejected); 47 NSE bhavcopy archives (old format to 2024-06, UDiFF
  tail to 2026-03), CA-screened (`scripts/finalize_bhavcopy_backfill.py`): clean-factor splits adjusted,
  demergers/crashes left raw per W-01 (HSIL 2019 demerger and INFIBEAM 2021 bonus hand-audited overrides).
- Artifacts: `data/ohlcv_backfill.pkl` (gitignored, regenerable via the committed harvest/finalize scripts)
  + `data/ohlcv_backfill_manifest.json` + the classified scope CSV. **The pinned `data/ohlcv.pkl`
  (sha f8625a8f) was never touched** — baseline_v1 remains byte-reproducible.
- Known limitations: bhavcopy series are price-return only (no dividend adjustment; conservative for the
  corpses, slightly anti-conservative for the PSU banks); gap-through stop fills unchanged.

**First measurement on the corrected universe (finding 0025):** survivorship was worth −0.04 Sharpe on the
candle-stop swing config and **−0.18 on the 4×ATR (let-winners-run) config** — wide-stop/long-hold books
ride the corpses down, so survivorship bias scales with holding period. **Implication: baseline_v1 (63-day
holds, 0.667 on survivor-only data) is now measurably suspect in the same direction. The
survivorship-corrected re-run of the BASE is unblocked and is the next data-honesty job** — it re-anchors
the pinned baseline, so it is an owner/governance action (quarterly-review class), not a session decision.
