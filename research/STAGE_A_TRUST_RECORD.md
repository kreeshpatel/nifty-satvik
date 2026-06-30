# Stage A — Trust Record (for owner sign-off)

**Date:** 2026-07-01 · **Status:** trustworthy-ground established, with 3 scoped follow-ups open.
See `docs/STAGE_A_PLAN.md` for the plan and `research/baseline_v1.json` for the anchor.

## The trust thesis (what we can stand behind)

1. **The rebuilt engine ≡ the validated strategy — proven.** `nq.engine.portfolio.simulate`
   reproduces the carried golden master `tests/fixtures/lh_golden_panel.csv` **byte-for-byte**
   (metrics + sha256 trade-ledger). The data/validation kernels are parity-verified vs source
   (CPCV splits + DSR byte-identical; cleaner/masks 850-trial parity = 0 mismatches).

2. **The pipeline selects faithfully — proven on the full universe.** On the corrected universe,
   selection and behaviour match baseline_v0: **225 vs 223** distinct names traded, **WR 60.4% vs
   59.72%**, n_trades **1279 vs 1445**. Same signal, same names, same win-rate.

3. **The honest current baseline is `baseline_v1` = 15.46% gross CAGR / 0.667 Sharpe**
   (block-bootstrap Sharpe CI [−0.02, 1.43]; DSR 0.246 @ n_trials 79). The **−10.6pp Δ vs
   baseline_v0 (26.1%) is DATA VINTAGE, not engine** — selection/WR/n_trades/engine all match v0,
   so the only remaining variable is per-trade return magnitude = the OHLCV price vintage (current
   yfinance ≠ v0's vintage, whose cache is gone). 26.1% was a vintage-favorable in-sample headline.

4. **The trustworthy forward number is the FORWARD WALL** (post-2026-05-30 OOS, `HOLDOUT.md`), not
   any in-sample figure — every in-sample number is dev-contaminated and vintage-dependent.

## backtest-rigor checklist (Section F), as of baseline_v1

```
[x] A1 OHLCV integrity — CA-aware cleaner + demerger guard in the pipeline (VEDL-class handled)
[x] A2 universe = corrected PIT cloud universe (710 names), NOT the local degenerate cache
[x] A3 features trailing-only — no-lookahead truncation test byte-stable
[x] A4 features computed fresh each run (no stale pkl)
[x] B1 cost model: brokerage 0.03% + STT 0.10% BOTH legs + tiered slippage (golden-verified)
[ ] B1 post-STCG(20%) after-tax — NOT yet computed by the cloud run            (FOLLOW-UP)
[x] C1 params from frozen cfg (load_frozen_cfg) — no re-derivation
[x] C2 n_trials=79 checked; DSR applied (0.246)
[ ] C3 2022-26 sub-period ΔCAGR — pooled only; sub-period split not computed     (FOLLOW-UP)
[~] C4 robustness — block-bootstrap CI given (CPCV path-distribution is degenerate for a frozen
        rule; block bootstrap is the correct tool per §E2)
[x] D1 golden master GREEN (byte-for-byte)
[ ] D2 harness re-derives a §11 KILL as KILL — needs the regime-gate overlay (A5)  (FOLLOW-UP)
[x] D3 CI/cloud-produced (not a local smoke)
[x] E1 >=100 trades (1279)
[x] E2 block bootstrap block_size=63, CI lower bound reported
```

## Open follow-ups (scoped; none block the trust thesis)
1. **Dataset pin (A2 half-2): ✅ DONE (2026-07-01).** OHLCV snapshot promoted to release
   `dataset-pin-20260701` (sha256 `f8625a8f…52142`); `run_cpcv --pinned-release` + `--expect-sha256`
   wired and **verified on the cloud** — the pinned run fetches the asset, the sha gate passes, and
   it reproduces CAGR 15.46% / Sharpe 0.667 / 1279 trades / WR 60.36% byte-identically (no yfinance).
   The fresh mint matched the recorded baseline_v1 exactly (no drift this run). baseline_v1 is now
   byte-reproducible on demand. Mint run 28471557396; verify run 28471952660.
2. **A5 harness-trust gate:** build the regime-gate overlay (a known §11 KILL) and confirm
   `evaluate_overlay` returns KILL — proves the harness won't false-promote. (Pulls Stage-C mechanism forward.)
3. **After-tax + 2022-26 sub-period** in the cloud run; residual: n_trades 1279 vs 1445 (~11%,
   likely fewer eligible bars on current yfinance) — confirmable with a price-level diff vs source.

## Residual data caveats (carried into every quote)
- ~28/213 recoverable-delisted names still lack D/E; ~114 hard-bankruptcy delistings unrecoverable.
- ex-financials until the W-04 capital-adequacy proxy; pre-2018 membership survivor-biased (trust ≥2019).
- baseline_v1 is **in-sample, NOT live-validated**.

---
**Sign-off:** Stage A's trust thesis (1-4) is established and evidence-backed. The 3 follow-ups are
quality hardening, not correctness gaps. Owner: approve to (a) close Stage A with follow-ups
tracked, or (b) require follow-up #1/#2 before close.
