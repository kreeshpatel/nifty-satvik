# Blend gross-to-net decomposition — Step 0 anchor check (STOPPED on a miss)

**Class:** MEASUREMENT. No trial, no live change, no sealed read. Standing counts: **screens 24 · sealed opens 4 ·
n_trials 3** (read from `diagnostics/research/n_trials.json` / `label_screen_ledger.md`; unchanged).

**Goal link.** Before any cost or tax lever is proposed for the 70/30 blend, the size of each drag has to be
reproducible from the committed pipeline. This note records that the anchors were re-run, and that one did not match.

## Method

- Branch `research/blend-cost-tax`, cut from the head of PR #214 (`5ce007c`, after the hash-seed fix).
- Inputs: release-pinned `data/ohlcv.pkl` (sha256 prefix `f8625a8f`, matches the pin) and `data/ohlcv_backfill.pkl`
  from `dataset-pin-20260729`.
- Command, run twice:
  `PYTHONHASHSEED=0 python pipelines/diagnostics/explore_after_tax_comparison.py` and the same with `PYTHONHASHSEED=1`.
- Window 2019-03-01..2024-06-28, ₹20,00,000, the simulator exactly as committed.
- Drag definitions:
  - **Cost drag** = `reconciliation.lot_sim_pre_tax_no_blend_costs_cagr_pct − lot_sim_pre_tax_cagr_pct`.
  - **Tax drag** = `pre_tax_sim.a_blend_vt11 CAGR − after_tax.a_blend_vt11 CAGR`. This is the sequential split
    (gross → minus costs → minus tax).

## Result

Both seeds produce byte-identical JSON. That JSON is also byte-identical to the committed
`2026-11-18_after_tax_comparison.json`.

| anchor | expected | reproduced (both seeds) | within 0.1pp |
|---|---|---|---|
| blend at 11%, after-tax CAGR | 19.3% | 19.26% | yes |
| blend at 11%, 156w p95 drawdown | 26.5% | 26.46% | yes |
| static 65/35, after-tax CAGR | 23.0% | 23.02% | yes |
| static 65/35, 156w p95 drawdown | 24.8% | 24.81% | yes |
| daily-rebalance cost drag | ≈ 1.6pp | 1.58pp (25.38 → 23.80) | yes |
| **tax drag** | **≈ 4.3pp** | **4.54pp** (23.80 → 19.26); 4.56pp with blend costs off (25.38 → 20.82) | **no (+0.24pp)** |

## Why the tax anchor misses

The "about 4.3pp" figure in `diagnostics/research/2026-11-18_robust_sizing.md` (the line beginning "Its separate
split of (a)'s shortfall") is the **blind replica's** split, not this pipeline's. The replica's after-tax blend CAGR
was 19.52%, against this pipeline's 19.26%. Applying the replica's 19.52% gives 25.38 − 1.58 − 19.52 ≈ 4.28pp. The
committed pipeline's own sequential split has always been about 4.5pp. The published note attributes the 4.3pp split
to the replica, but the replica's 0.26pp gap on the blend line (1.3% relative, inside rule 3's 5%) never carried
through to the split.

The task rule was "stop and report on any miss", so Steps 1–5 were **not run**.

## Owner decision needed

To proceed, pick one of the following.

- **(a)** Re-anchor the tax drag at 4.54pp, the committed pipeline's number, and run Steps 1–5.
- **(b)** First reconcile the replica's 0.26pp blend gap, then run Steps 1–5.
