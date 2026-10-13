# 0149 — Sleeve allocation between swing and low-vol: activation bound (Track P3)

**Class:** ACTIVATION BOUND. **No trial.** Screen ledger row **#22**, appended **before** this runs.
Standing counts at registration: **screens 21 → 22 · sealed opens 3 · n_trials 2**.
**Registered:** 2026-10-13, before the diagnostic exists.

## Question

The swing × low-vol blend (0107) is the one structure that has cut drawdown without touching a trade
(−42.4% → −33.0%). The live barbell weight, **0.60 swing**, was fixed by the owner (`prereg_swing` §7),
not measured. Does any standard allocation rule beat that fixed weight by enough to be worth a watched
forward book?

## What is already answered

- **0107** measured one rule (quarterly inverse-vol ERC) over 2017-09..2026-06 — a window that includes
  the sealed slice — and found Sharpe 1.237 / MaxDD −33.04%. **0115** recovered its unstated vol
  lookback (126 days) by matching the published triple. Neither compared rules against the 0.60 control.
- **0115** screened out a third sleeve on correlation: two sleeves only here.
- **0095** killed book-level vol targeting on the swing book (ΔSharpe −0.398): `KILL (epoch, book)`. A
  vol-targeted cash sleeve is the same mechanism and is **not** run.
- Position-level optimisation is out of scope (0145: no differential structure to exploit).

## What is new

A **comparison of allocation rules against the owner's 0.60 control**, on the train window only, with
family multiplicity priced through `adjudicate_family`. Never done: 0107 compared the blend to its
sleeves, not rules to each other or to the live weight.

## Inputs (frozen)

`research/exports/blend_hybrid_returns.csv`, columns `swing` and `lowvol` (daily returns, corrected
universe, as committed in `17af9dd`). Read **only through 2024-06-30**: rows after it are dropped at load
and never computed on. 2017-09..2018-12 is used only as estimation warm-up; every reported number is on
**2019-01-01..2024-06-30**.

## The family (frozen — no other rule is run)

All rebalanced quarterly (first session of each calendar quarter), weights from data strictly before
the rebalance date, long-only, summing to 1, no leverage, zero cost on rebalancing (stated).

| label | rule |
|---|---|
| **fixed_0.60** | **control — the live barbell** |
| fixed_0.50 | equal weight |
| invvol_126 | weight ∝ 1/σ, σ from the trailing 126 sessions (0107/0115's recipe) |
| minvar_126 | two-asset minimum variance from the trailing 126-session covariance, clipped to [0, 1] |
| maxdiv_126 | maximum diversification, w ∝ Σ⁻¹σ, trailing 126 sessions, clipped to [0, 1] |

HRP on two assets reduces to inverse-variance, which sits between `invvol` and `minvar`; it is not run
separately.

## Pre-committed reading

For each rule against `fixed_0.60`: ΔSharpe, ΔMaxDD, ΔCAGR, worst calendar year, and ΔSharpe in each
sub-period (2019–21, 2022–24H1, continuous slices of one curve). PBO and the family-deflated Sharpe come
from `adjudicate_family` over all five.

- A rule is **eligible to be proposed as a watched forward book** at a quarterly review only if ALL of:
  ΔSharpe ≥ **+0.10**, MaxDD **not worse**, ΔSharpe **> 0 in both** sub-periods, and family PBO **< 0.5**.
- Otherwise: **bound recorded**. The 0.60 control stays the default by inaction.
- Even a pass is **not certification**. With n_eff ≈ 37 the ΔSharpe half-width is ≈ 0.59; any in-sample
  difference here is below what this data can resolve. A pass earns a forward seat, nothing more, and
  live weights change only at a review.

## Reproduce

`python pipelines/diagnostics/diag_sleeve_allocation_0149.py` → `diagnostics/research/sleeve_allocation/result.json`.
