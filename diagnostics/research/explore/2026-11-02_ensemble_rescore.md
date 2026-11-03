# 2026-11-02 - Path-noise ensemble re-score of the live-switch leads and two fill levers

**Tier:** EXPLORE (`docs/PROCESS_TIERS.md`, tier 0). No pre-registration, no screen row, no `n_trials` change. Descriptive: it adopts nothing and recommends no change to the live config; any change is a CONFIRM-tier decision (`forward/prereg_swing.md`).

**Standing counts (read from the ledgers by the script):** screens **23** - sealed opens **3** - n_trials **2**. Unchanged by this note.

## Reading rule (fixed before any number was computed)

> A candidate is 'robust to path noise' only if its 5th-percentile paired dSharpe vs live is > 0; otherwise it is 'inside path noise'. 'Robust' means 'worth a pre-registered trial', never adoption: it is still train-window in-sample, with a statistical half-width of about 0.59 (n_eff about 37) on top of path noise.

## Method

`nq/lab/ensemble.py`, 2 paths per config, seed 20261102, the SAME perturbation draws for every config (paired). Perturbations: cost jitter U(-10bp,+10bp) added to every cost leg by rebinding `R94._cost_leg` in-process; start date drawn from the first 20 trading days of 2019. Every path is reported on **2019-03-01..2024-06-30** as a continuous slice of its own NAV (not a fresh-capital re-run). Fill-order tie jitter: fill-order tie jitter skipped: the engine's candidate key is (-rank, ticker), a total order, so ties are already broken deterministically and jittering them would change the engine's tie rule rather than sample noise. PIT membership on; prices cut at 2024-06-30 and the cut asserted (last bar seen 2024-06-28); nothing in 2024-07-01..2026-06-30 is read; the sealed judge log is not touched. Per-trade mean R applies the degenerate-stop rule (`nq/lab/stats`, initial risk < 0.5% of entry excluded).

**Manifest labels** (`nq/runner/manifest`):

- `live`: LIVE BOOK (replay exceptions: ca_hold_drop)
- `h5`: NOT LIVE BOOK: ext_cap (differs on: ext_cap, grade_gate, max_notional_pct, max_risk_pct)
- `g`: NOT LIVE BOOK: ext_cap (differs on: ext_cap, grade_gate, max_notional_pct, max_risk_pct, scaled_exit)
- `d6`: NOT LIVE BOOK: a_grade (differs on: a_grade)
- `rr1.0`: NOT LIVE BOOK: min_rr_at_fill (differs on: min_rr_at_fill)
- `rr1.5`: NOT LIVE BOOK: min_rr_at_fill (differs on: min_rr_at_fill)
- `whole`: NOT LIVE BOOK: whole_shares (differs on: whole_shares)

## Each book's own path-noise band (median [5th, 95th] over the paths)

| run | Sharpe | CAGR | MaxDD | trades | mean R ex degen (unperturbed) |
|---|---|---|---|---|---|
| **live** | 1.28 [1.23, 1.34] | 29.0% [25.4%, 32.5%] | -41.3% [-47.0%, -35.6%] | 69 [67, 71] | +0.88 (n=67, 0 degenerate) |
| **h5** | 1.41 [1.40, 1.42] | 31.8% [31.7%, 31.8%] | -36.0% [-38.9%, -33.1%] | 84 [82, 85] | +1.19 (n=73, 0 degenerate) |
| **g** | 1.44 [1.30, 1.58] | 33.9% [30.5%, 37.2%] | -38.7% [-45.3%, -32.1%] | 153 [152, 154] | +0.61 (n=148, 0 degenerate) |
| **d6** | 1.22 [1.12, 1.33] | 24.9% [21.6%, 28.1%] | -35.5% [-36.2%, -34.8%] | 70 [67, 72] | +0.74 (n=72, 0 degenerate) |
| **rr1.0** | 1.28 [1.23, 1.34] | 29.0% [25.4%, 32.5%] | -41.3% [-47.0%, -35.6%] | 69 [67, 71] | +0.88 (n=67, 0 degenerate) |
| **rr1.5** | 1.06 [1.00, 1.12] | 22.7% [19.2%, 26.2%] | -41.3% [-47.0%, -35.6%] | 71 [70, 72] | +0.65 (n=74, 0 degenerate) |
| **whole** | 1.24 [1.20, 1.27] | 25.4% [24.7%, 26.2%] | -33.5% [-34.9%, -32.2%] | 72 [72, 72] | +0.75 (n=70, 0 degenerate) |

## Paired differences vs live (candidate minus live, same draws)

| candidate | paired median dSharpe | 5-95% band | share of paths better | verdict | dMaxDD band (median) | dCAGR band (median) | median dTrades |
|---|---|---|---|---|---|---|---|
| **h5** | +0.13 | [+0.08, +0.18] | 100% | robust to path noise | [-3.3pp, +13.9pp] (+5.3pp) | [-0.7pp, +6.3pp] (+2.8pp) | +14 |
| **g** | +0.16 | [-0.04, +0.35] | 50% | inside path noise | [+1.7pp, +3.5pp] (+2.6pp) | [-2.0pp, +11.8pp] (+4.9pp) | +84 |
| **d6** | -0.06 | [-0.11, -0.01] | 0% | inside path noise | [+0.8pp, +10.8pp] (+5.8pp) | [-4.4pp, -3.8pp] (-4.1pp) | +0 |
| **rr1.0** | +0.00 | [+0.00, +0.00] | 0% | inside path noise | [+0.0pp, +0.0pp] (+0.0pp) | [+0.0pp, +0.0pp] (+0.0pp) | +0 |
| **rr1.5** | -0.23 | [-0.23, -0.22] | 0% | inside path noise | [+0.0pp, +0.0pp] (+0.0pp) | [-6.3pp, -6.3pp] (-6.3pp) | +2 |
| **whole** | -0.05 | [-0.07, -0.02] | 0% | inside path noise | [+0.7pp, +14.8pp] (+7.8pp) | [-6.4pp, -0.7pp] (-3.5pp) | +3 |

(Positive dMaxDD = shallower drawdown. n_paired = h5: 2, g: 2, d6: 2, rr1.0: 2, rr1.5: 2, whole: 2.)

## Per-trade mean R, paired (ex degenerate stops, medians over paths)

| candidate | median dMeanR (ex degenerate) | 5-95% band | median dMeanR (raw) |
|---|---|---|---|
| h5 | -0.67 | [-1.03, -0.32] | -0.67 |
| g | -1.41 | [-1.77, -1.04] | -1.41 |
| d6 | -0.34 | [-0.50, -0.18] | -0.34 |
| rr1.0 | +0.00 | [+0.00, +0.00] | +0.00 |
| rr1.5 | -0.55 | [-0.73, -0.37] | -0.55 |
| whole | -0.35 | [-0.63, -0.06] | -0.35 |

## whole_shares realism check (unperturbed, live vs whole_shares)

- Fills: 77 (fractional) vs 82 (whole shares); 69 fills share the same ticker and entry date; only in fractional: 8; only in whole-share: 13.
- Of the common fills, 69 change size. Entry-day share rounding loss: median 0.12%, max 5.41%; smallest whole-share position 14 shares.
- Single-replay Sharpe 1.025 -> 1.068, CAGR 20.5% -> 21.9% (full window from 2019-01-01, one path each; the paired ensemble row above is the noise-aware number). This is about record fidelity, not an edge.

