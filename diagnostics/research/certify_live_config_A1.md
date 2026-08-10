# A1 — certifying the live configuration (MEASUREMENT, no trial)

Pre-registered: `forward/prereg_swing_A1.md`. `n_trials` unchanged at 2.

| | **PRIMARY 2025-12-31** | secondary (full window) |
|---|--:|--:|
| closed trades | **112** | 130 |
| Sharpe | **1.201** | 1.279 |
| CAGR % | **25.024** | 27.175 |
| after-tax CAGR % | **22.044** | 23.204 |
| MaxDD % | **-39.49** | -39.49 |
| Calmar | **0.634** | 0.688 |
| DSR @ certified 114 | **0.8096** | 0.8828 |
| DSR @ live | **0.9962** | 0.9981 |
| DSR @ lifetime | **0.7924** | 0.871 |
| positions still open | **8** | 0 |

Bootstrap 95% Sharpe CI: **[0.516, 1.915]** (primary)

| slice | CAGR % | Sharpe |
|---|--:|--:|
| 2017-18 | 11.14 | 0.715 |
| 2019-21 | 56.83 | 1.946 |
| 2022-onward (2022-2025 at the primary stop) | 11.53 | 0.693 |

## Gates (pre-committed §6)

- `dsr_gt_0.95_at_114`: **FAIL**
- `ci_low_gt_0`: **PASS**
- `all_slices_positive`: **PASS**

## Outcome: **UNCERTIFIED, BOUNDED**

Pre-declared NOT RESOLVABLE in prereg §6: config P scores 0.91 against a 1.04 bar, a -0.13 miss that is roughly one fifth of the ±0.59 dSharpe half-width. Recorded, not litigated.
