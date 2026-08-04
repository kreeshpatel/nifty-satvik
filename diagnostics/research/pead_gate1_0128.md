# 0128 — PEAD Gate-1: does post-earnings drift exist on our universe, 2019+?

**MEASUREMENT — 0 trials, no screen-ledger row, sealed set and judge log untouched.**
**Standing counts: screens 14 · sealed opens 1 · n_trials 138.**

## Coverage census

58871 NSE result events → **20230** joinable to OHLCV → **14672** PIT Nifty-500 members → **12186** usable after ADV ≥ ₹5cr and history (738 dropped on history).

| year | usable_events | top_decile |
|---|---|---|
| 2019 | 1083 | 110 |
| 2020 | 1360 | 138 |
| 2021 | 1738 | 175 |
| 2022 | 1773 | 178 |
| 2023 | 1810 | 183 |
| 2024 | 1948 | 195 |
| 2025 | 1985 | 200 |
| 2026 | 489 | 49 |

## Drift by surprise decile × horizon (train 2019-2022, market-adjusted %)

| decile | N | meanCAR01 | drift10 | drift21 | drift42 | drift63 |
|---|---|---|---|---|---|---|
| 1.0 | 602.0 | -9.38 | -1.878 | -1.001 | -0.781 | -2.909 |
| 2.0 | 596.0 | -5.2 | -0.589 | -0.205 | 1.024 | -0.446 |
| 3.0 | 591.0 | -3.48 | -0.908 | -0.087 | 0.894 | 0.096 |
| 4.0 | 597.0 | -2.2 | -0.336 | 0.134 | 0.268 | 0.624 |
| 5.0 | 596.0 | -1.07 | -0.508 | 0.166 | 0.95 | 0.575 |
| 6.0 | 589.0 | -0.0 | 0.501 | 0.947 | 1.596 | 1.571 |
| 7.0 | 595.0 | 1.08 | -0.248 | 0.434 | 0.653 | 0.717 |
| 8.0 | 593.0 | 2.49 | 0.245 | 1.193 | 2.293 | 2.865 |
| 9.0 | 594.0 | 4.52 | 0.127 | 1.665 | 2.094 | 1.727 |
| 10.0 | 601.0 | 9.99 | 0.903 | 2.366 | 3.545 | 3.737 |

## Top-minus-bottom decile spread (train)

```
{
  "10": {
    "top_mean": 0.903,
    "top_ci": [
      0.158,
      1.651
    ],
    "bottom_mean": -1.878,
    "spread": 2.781,
    "spread_ci": [
      1.796,
      3.791
    ],
    "n_top": 601,
    "n_bot": 602
  },
  "21": {
    "top_mean": 2.366,
    "top_ci": [
      1.265,
      3.491
    ],
    "bottom_mean": -1.001,
    "spread": 3.367,
    "spread_ci": [
      1.877,
      4.883
    ],
    "n_top": 601,
    "n_bot": 602
  },
  "42": {
    "top_mean": 3.545,
    "top_ci": [
      2.09,
      5.023
    ],
    "bottom_mean": -0.781,
    "spread": 4.325,
    "spread_ci": [
      2.28,
      6.337
    ],
    "n_top": 601,
    "n_bot": 602
  },
  "63": {
    "top_mean": 3.737,
    "top_ci": [
      1.934,
      5.682
    ],
    "bottom_mean": -2.909,
    "spread": 6.645,
    "spread_ci": [
      4.234,
      9.173
    ],
    "n_top": 601,
    "n_bot": 602
  }
}
```

## Per-year at the strongest train horizon (H=63)

| year | in_train | n_top | top_drift | spread |
|---|---|---|---|---|
| 2019 | True | 110 | 0.377 | 6.738 |
| 2020 | True | 138 | 1.643 | 1.992 |
| 2021 | True | 175 | 8.555 | 9.585 |
| 2022 | True | 178 | 2.7 | 7.296 |
| 2023 | False | 183 | 10.025 | 4.441 |
| 2024 | False | 195 | 2.327 | 2.189 |
| 2025 | False | 200 | -0.519 | 2.508 |
| 2026 | False | 49 | 12.998 | 0.547 |

## §4 confound checks

```
{
  "momentum63": {
    "momentum63_lo": {
      "n_top": 185,
      "spread": 3.166,
      "ci": [
        -1.035,
        7.509
      ]
    },
    "momentum63_mid": {
      "n_top": 185,
      "spread": 5.87,
      "ci": [
        2.262,
        9.375
      ]
    },
    "momentum63_hi": {
      "n_top": 231,
      "spread": 9.928,
      "ci": [
        5.403,
        14.523
      ]
    }
  },
  "adv": {
    "adv_lo": {
      "n_top": 211,
      "spread": 6.693,
      "ci": [
        2.216,
        11.378
      ]
    },
    "adv_mid": {
      "n_top": 207,
      "spread": 8.783,
      "ci": [
        4.789,
        12.902
      ]
    },
    "adv_hi": {
      "n_top": 183,
      "spread": 3.638,
      "ci": [
        -0.297,
        7.605
      ]
    }
  }
}
```

## Out-of-window 2023-2026 (descriptive, NOT the decision basis)

```
{
  "n_top": 627,
  "top_drift": 4.5,
  "spread": 2.822,
  "spread_ci": [
    0.74,
    4.855
  ],
  "note": "descriptive only \u2014 NOT the Gate-1 decision basis (pre-reg \u00a71)"
}
```

## Gate (pre-committed §3)

```
{
  "best_horizon": 63,
  "1_existence_CI_excludes_zero": true,
  "2_majority_train_year_sign": "4/4",
  "2_pass": true,
  "3_top_decile_net_pct": 3.477,
  "3_pass": true,
  "4_min_topdecile_per_yr": 49,
  "4_pass": false,
  "PASS": false
}
```

## VERDICT: FAIL — door closes; SL-002 moves OPEN -> verdict

Reproduce: `python scripts/diag_pead_gate1_0128.py`
