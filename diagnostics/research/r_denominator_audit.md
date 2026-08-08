# R-denominator audit — is R a comparable unit?

**VERIFICATION CLASS — free. No ledger row. No trial. No rule proposed.**
**Standing counts: screens 15 · sealed opens 1 · n_trials 138.**

```
{
  "_doc": "R-denominator audit \u2014 VERIFICATION CLASS (free; no ledger row; no rule proposed).",
  "population": "uncapped Stage-1 substrate, entry_date>=2019-01-01, all setups",
  "n_trades": 3819,
  "span_years": 7.46,
  "book_total_R": 1907.3,
  "standing_counts": {
    "screens": 15,
    "sealed_opens": 1,
    "n_trials": 138
  },
  "leg1_stop_width_pct": {
    "n": 3819,
    "mean": 12.513,
    "pctiles": {
      "p1": 1.631,
      "p5": 2.806,
      "p10": 3.586,
      "p25": 5.463,
      "p50": 9.175,
      "p75": 17.673,
      "p90": 25.253,
      "p95": 30.541,
      "p99": 43.77
    },
    "min": 0.087,
    "max": 74.821,
    "p90_over_p10": 7.04
  },
  "leg1_by_setup": {
    "ascending_base": {
      "n": 100,
      "median_stop_width_pct": 22.43,
      "mean_R": 0.665
    },
    "box": {
      "n": 518,
      "median_stop_width_pct": 19.34,
      "mean_R": 0.663
    },
    "cup_handle": {
      "n": 181,
      "median_stop_width_pct": 17.32,
      "mean_R": 0.703
    },
    "double_bottom": {
      "n": 461,
      "median_stop_width_pct": 24.87,
      "mean_R": 0.634
    },
    "sr_pivot": {
      "n": 55,
      "median_stop_width_pct": 8.46,
      "mean_R": 0.594
    },
    "touch44": {
      "n": 1415,
      "median_stop_width_pct": 6.93,
      "mean_R": 0.424
    },
    "trend_pullback": {
      "n": 1058,
      "median_stop_width_pct": 5.98,
      "mean_R": 0.388
    }
  },
  "leg2_stop_width_over_weekly_ATR": {
    "n": 3617,
    "mean": 1.541,
    "pctiles": {
      "p1": 0.248,
      "p5": 0.413,
      "p10": 0.515,
      "p25": 0.733,
      "p50": 1.127,
      "p75": 2.249,
      "p90": 3.175,
      "p95": 3.593,
      "p99": 4.528
    },
    "min": 0.014,
    "max": 6.514,
    "p90_over_p10": 6.16
  },
  "leg2_share_below_1x_ATR_pct": 41.6,
  "leg2_share_below_0p5x_ATR_pct": 8.7,
  "leg3_correlations": {
    "stop_width_vs_R": {
      "n": 3819,
      "pearson": 0.0484,
      "spearman": 0.1279,
      "spearman_p": 0.0
    },
    "stop_width_vs_stop_hit": {
      "n": 3819,
      "pearson": -0.241,
      "spearman": -0.2192,
      "spearman_p": 0.0
    },
    "sw_over_atr_vs_R": {
      "n": 3617,
      "pearson": 0.0576,
      "spearman": 0.1288,
      "spearman_p": 0.0
    },
    "sw_over_atr_vs_stop_hit": {
      "n": 3617,
      "pearson": -0.2482,
      "spearman": -0.2269,
      "spearman_p": 0.0
    },
    "stop_width_vs_abs_R": {
      "n": 3819,
      "pearson": -0.2189,
      "spearman": -0.2556,
      "spearman_p": 0.0
    },
    "stop_width_vs_price_outcome_pnl_pct": {
      "n": 3819,
      "pearson": 0.2822,
      "spearman": 0.1018,
      "spearman_p": 0.0
    }
  },
  "leg3_by_stop_width_decile": [
    {
      "decile": 1,
      "n": 382,
      "median_stop_width_pct": 2.8,
      "median_sw_over_atr": 0.45,
      "mean_R": 0.305,
      "mean_price_outcome_pct": 1.04,
      "stop_hit_pct": 54.2,
      "share_of_book_R_pct": 6.1
    },
    {
      "decile": 2,
      "n": 382,
      "median_stop_width_pct": 4.31,
      "median_sw_over_atr": 0.64,
      "mean_R": 0.387,
      "mean_price_outcome_pct": 1.58,
      "stop_hit_pct": 54.5,
      "share_of_book_R_pct": 7.7
    },
    {
      "decile": 3,
      "n": 383,
      "median_stop_width_pct": 5.46,
      "median_sw_over_atr": 0.74,
      "mean_R": 0.452,
      "mean_price_outcome_pct": 2.48,
      "stop_hit_pct": 50.9,
      "share_of_book_R_pct": 9.1
    },
    {
      "decile": 4,
      "n": 381,
      "median_stop_width_pct": 6.78,
      "median_sw_over_atr": 0.89,
      "mean_R": 0.445,
      "mean_price_outcome_pct": 3.02,
      "stop_hit_pct": 52.2,
      "share_of_book_R_pct": 8.9
    },
    {
      "decile": 5,
      "n": 382,
      "median_stop_width_pct": 8.29,
      "median_sw_over_atr": 0.98,
      "mean_R": 0.394,
      "mean_price_outcome_pct": 3.25,
      "stop_hit_pct": 54.2,
      "share_of_book_R_pct": 7.9
    },
    {
      "decile": 6,
      "n": 381,
      "median_stop_width_pct": 10.4,
      "median_sw_over_atr": 1.2,
      "mean_R": 0.415,
      "mean_price_outcome_pct": 4.41,
      "stop_hit_pct": 49.9,
      "share_of_book_R_pct": 8.3
    },
    {
      "decile": 7,
      "n": 382,
      "median_stop_width_pct": 13.89,
      "median_sw_over_atr": 1.71,
      "mean_R": 0.623,
      "mean_price_outcome_pct": 8.55,
      "stop_hit_pct": 40.8,
      "share_of_book_R_pct": 12.5
    },
    {
      "decile": 8,
      "n": 382,
      "median_stop_width_pct": 17.67,
      "median_sw_over_atr": 2.24,
      "mean_R": 0.65,
      "mean_price_outcome_pct": 11.49,
      "stop_hit_pct": 35.1,
      "share_of_book_R_pct": 13.0
    },
    {
      "decile": 9,
      "n": 382,
      "median_stop_width_pct": 22.25,
      "median_sw_over_atr": 2.76,
      "mean_R": 0.683,
      "mean_price_outcome_pct": 15.5,
      "stop_hit_pct": 28.5,
      "share_of_book_R_pct": 13.7
    },
    {
      "decile": 10,
      "n": 382,
      "median_stop_width_pct": 30.54,
      "median_sw_over_atr": 3.26,
      "mean_R": 0.642,
      "mean_price_outcome_pct": 22.09,
      "stop_hit_pct": 18.6,
      "share_of_book_R_pct": 12.9
    }
  ],
  "leg4_lindeindia_signature": {
    "definition": "stopped out, then a daily CLOSE above the original entry within 4 weeks (20 sessions) of the exit",
    "narrow_stop_below_1x_weekly_ATR": {
      "n_stopped": 845,
      "n_evaluable": 844,
      "n_closed_above_entry_within_4wk": 313,
      "recovery_pct": 37.1
    },
    "wide_stop_at_or_above_1x_weekly_ATR": {
      "n_stopped": 745,
      "n_evaluable": 745,
      "n_closed_above_entry_within_4wk": 79,
      "recovery_pct": 10.6
    },
    "gap_pp": 26.5,
    "mechanical_caveat": "PART OF THIS GAP IS DEFINITIONAL and must not be read as pure discovery: a narrow stop is breached by a smaller adverse move, so recovering back above entry requires a smaller favourable move. The gap is reported because of what it says about the UNIT, not because it is a surprise: a -1R booked on a sub-ATR stop and a -1R booked on a 3x-ATR stop are not the same event, yet the book records both as -1R and averages them together."
  },
  "leg5_denominator_decomposition": {
    "common_denominator_used_pct": 9.175,
    "book_total_R_as_reported": 1907.3,
    "book_total_R_at_common_denominator": 3056.0,
    "ratio": 1.602,
    "mean_R_as_reported": 0.499,
    "mean_R_at_common_denominator": 0.8,
    "spearman_R_vs_R_common": 0.829,
    "narrowest_stop_tercile_share_of_book_R_pct": 26.7,
    "narrowest_stop_tercile_share_at_common_denominator_pct": 8.6,
    "log_abs_R_on_log_stop_width_slope": -0.309,
    "interpretation": "a slope near -1 means |R| is very nearly the reciprocal of the stop width \u2014 i.e. R is measuring the denominator, not the price outcome"
  },
  "leg6_sizing_regime": {
    "run_of_record_and_substrate": "UNCAPPED \u2014 sh = eq*2%/(entry-stop); 1R == 2% of equity for EVERY trade, so R IS rupee-comparable there",
    "live_book": "LIVE_DISCIPLINE (max_risk_pct=0.1, max_notional_pct=0.2) \u2014 sh = min(risk-sizing, notional cap)",
    "live_binding_threshold_stop_width_pct": 10.0,
    "share_of_trades_where_live_cap_binds_pct": 53.4,
    "live_effective_equity_risk_pct": {
      "n": 3819,
      "mean": 1.546,
      "pctiles": {
        "p1": 0.326,
        "p5": 0.561,
        "p10": 0.717,
        "p25": 1.093,
        "p50": 1.835,
        "p75": 2.0,
        "p90": 2.0,
        "p95": 2.0,
        "p99": 2.0
      },
      "min": 0.017,
      "max": 2.0,
      "p90_over_p10": 2.79
    },
    "live_rupee_value_of_1R_vs_nominal": {
      "n": 3819,
      "mean": 0.773,
      "pctiles": {
        "p1": 0.163,
        "p5": 0.281,
        "p10": 0.359,
        "p25": 0.546,
        "p50": 0.918,
        "p75": 1.0,
        "p90": 1.0,
        "p95": 1.0,
        "p99": 1.0
      },
      "min": 0.009,
      "max": 1.0,
      "p90_over_p10": 2.79
    },
    "citation": "already carried structurally as constitution H1/H3 ('Off in run of record') and divergence D3 \u2014 this leg quantifies the UNIT consequence, it does not claim a new divergence",
    "book_R_uncapped_weighting": 1907.3,
    "book_R_live_rupee_weighting": 1581.9,
    "live_translation_ratio": 0.829,
    "what_this_means": "the SAME trades, re-weighted by the rupees the live cap actually puts behind each R. A ratio < 1 means the live book converts reported R into proportionally fewer rupees, because the cap binds hardest exactly on the narrow-stop trades that carry the most R."
  },
  "exposure_check_ext_band": {
    "why": "the <5% extension band's +0.717R core (ext_band_census) is an R-denominated result; if that band is also the narrow-stop band, part of the effect is denominator, not edge",
    "corr_ext_vs_stop_width": {
      "n": 3819,
      "pearson": 0.6721,
      "spearman": 0.6207,
      "spearman_p": 0.0
    },
    "median_stop_width_pct_ext_below_5": 5.97,
    "median_stop_width_pct_ext_at_or_above_5": 9.9,
    "mean_R_ext_below_5": 0.803,
    "mean_R_at_common_denominator_ext_below_5": 0.549,
    "mean_R_ext_at_or_above_5": 0.469,
    "mean_R_at_common_denominator_ext_at_or_above_5": 0.825,
    "verdict_is_owner_door": "FLAG ONLY \u2014 this audit proposes nothing; the reading is the owner's to make",
    "live_rupee_weight_ext_below_5": 0.621,
    "live_rupee_weighted_meanR_ext_below_5": 0.466,
    "live_rupee_weight_ext_at_or_above_5": 0.788,
    "live_rupee_weighted_meanR_ext_at_or_above_5": 0.409,
    "how_to_read": "THREE yardsticks, and which is correct depends on how the book sizes. (1) fixed-RISK sizing (the uncapped run of record): R as reported is already the rupee truth \u2014 the low-ext edge is real there. (2) fixed-NOTIONAL sizing: the common-denominator column is the truth, and the ordering reverses. (3) the LIVE book is neither \u2014 it is min(risk-sizing, 20% notional), so it sits BETWEEN them, and the live-rupee-weighted column is the one that governs live capital. The exposure is that low-ext trades carry narrow stops, so the live cap binds hardest on precisely the cohort the research calls the core edge."
  }
}
```

Reproduce: `python scripts/diag_r_denominator_audit.py`
