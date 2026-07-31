# 0127 — HEG-class activation bound (ledger #14)

**0 trials. Sealed slice not read. Judge log unread. No engine change.**
**Standing counts: screens 14 · sealed opens 1 · n_trials 138.**

Population: **1415 uncapped touch44 trades**, 7.46y, total 600.6R (80.6 R/yr). Uncapped and excursion-order-optimistic — **both bounds are inflated on purpose**.

## Cohort table (recomputed here — reproduce-before-trust)

| threshold | N | share_pct | primary |
|---|---|---|---|
| >=4wk & >=20% | 229 | 16.2 | True |
| >=4wk & >=15% | 406 | 28.7 | False |
| >=6wk & >=20% | 203 | 14.3 | False |

Descent quartiles — duration [4.0, 7.0, 11.0] wk · depth [4.59, 10.0, 16.56]% · velocity [0.78, 1.52, 2.78] %/wk

## Bound (a) — EXCLUSION (Law III bookend)

```
{
  "R_per_yr_refused": 1.92,
  "interpretation": "refusing the cohort COSTS this much R/yr (positive-EV cohort)",
  "clairvoyant_refuse_only_losers_R_per_yr": 26.22,
  "note": "the clairvoyant leg is an unreachable ceiling (perfect foresight on which lose); it also ignores redeployment, which 0121 measured as the dominant term",
  "per_year": {
    "by_year": {
      "2019": -3.74,
      "2020": 60.01,
      "2021": 8.18,
      "2022": -10.95,
      "2023": 15.4,
      "2024": -11.28,
      "2025": -32.09,
      "2026": -11.24
    },
    "n_years": 8,
    "n_positive": 3,
    "majority_sign": "-",
    "majority_share": "5/8"
  }
}
```

## Bound (b) — CONDITIONAL MANAGEMENT (clairvoyant)

```
{
  "management_totals_R": {
    "as-is": 600.6,
    "TP@2R": 418.8,
    "TP@3R": 678.1,
    "stop@-0.5R": 212.0
  },
  "cohort_totals_R": {
    "as-is": 14.3,
    "TP@2R": -2.7,
    "TP@3R": 37.7,
    "stop@-0.5R": -33.9
  },
  "rest_totals_R": {
    "as-is": 586.3,
    "TP@2R": 421.5,
    "TP@3R": 640.4,
    "stop@-0.5R": 245.9
  },
  "best_single_for_all": "TP@3R",
  "best_for_cohort": "TP@3R",
  "best_for_rest": "TP@3R",
  "clairvoyant_conditional_gain_R": -0.0,
  "clairvoyant_conditional_gain_R_per_yr": -0.0,
  "note": "the gain of CONDITIONING on cohort membership, over the best single management applied to everyone \u2014 with perfect hindsight on which management to pick",
  "per_year": {
    "by_year": {
      "2019": 0.0,
      "2020": 0.0,
      "2021": 0.0,
      "2022": 0.0,
      "2023": 0.0,
      "2024": 0.0,
      "2025": 0.0,
      "2026": 0.0
    },
    "n_years": 8,
    "n_positive": 0,
    "majority_sign": "-",
    "majority_share": "8/8"
  }
}
```

## Gate (pre-committed: |bound| > 10 R/yr AND majority-year sign)

```
{
  "floor_R_per_yr": 10.0,
  "a_exclusion_as_a_saving": {
    "value_R_per_yr": -1.92,
    "clears_floor": false,
    "majority_year_consistent": true,
    "PASS": false
  },
  "a_exclusion_clairvoyant_ceiling": {
    "value_R_per_yr": 26.22,
    "clears_floor": true,
    "sign_test": "NOT APPLICABLE \u2014 positive by construction (tautology, not evidence)",
    "reachable": false,
    "why_unreachable": "requires perfect foresight on which trades lose \u2014 the pre-entry wall (bar-level ML, loser forensics, path shape, formulas, perception); and 0121 showed redeployment dominates anyway",
    "PASS": false
  },
  "b_conditional_management": {
    "value_R_per_yr": -0.0,
    "clears_floor": false,
    "majority_year_consistent": true,
    "PASS": false
  }
}
```

## VERDICT: FAIL — no screen #14; thread closed until habit-ledger labels

Reproduce: `python scripts/diag_hegclass_bound_0127.py`
