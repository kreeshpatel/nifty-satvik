"""Data layer: OHLCV acquisition + cleaning, PIT membership mask, PIT D/E join, and the
long-horizon features (``sma200_slope_63``, ``atr_pct_63``, ``adv_rupees_20d``) + the
eligibility predicates. Trailing-only by construction (no lookahead)."""
from __future__ import annotations

from .eligibility import (
    cross_sectional_rank,
    restrict_to_large_mid,
    solvent_universe_mask,
)
from .features import (
    LONG_HORIZON_FEATURE_COLS,
    SIGNAL,
    compute_all_features,
    compute_features,
)
from .fundamentals import (
    VALUE_QUALITY_COLS,
    load_fund_store,
    value_quality_series,
)
from .membership import (
    current_members,
    filter_features_dict,
    load_membership,
    membership_stats,
    ticker_in_index_on,
)
from .ohlcv import (
    clean_ohlcv_dict,
    clean_ohlcv_for_features,
    demerger_suspect,
    demerger_suspect_names,
    load_demerger_reference,
    load_ohlcv_cache,
    load_ohlcv_json,
)

__all__ = [
    # ohlcv
    "clean_ohlcv_for_features", "clean_ohlcv_dict", "load_demerger_reference",
    "demerger_suspect", "demerger_suspect_names", "load_ohlcv_cache", "load_ohlcv_json",
    # membership
    "load_membership", "ticker_in_index_on", "current_members",
    "filter_features_dict", "membership_stats",
    # fundamentals
    "load_fund_store", "value_quality_series", "VALUE_QUALITY_COLS",
    # features
    "compute_features", "compute_all_features", "SIGNAL", "LONG_HORIZON_FEATURE_COLS",
    # eligibility
    "restrict_to_large_mid", "solvent_universe_mask", "cross_sectional_rank",
]
