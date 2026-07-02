"""Part 2 — PIT / value tests for the fundamentals-depth conviction features (`depth_feature_series`).

Growth features (rev_yoy, …) reference period Y-1, so they carry a real lookahead risk if computed wrong.
These lock: (1) correct values, (2) the truncation/PIT gate — a feature attached to date `t` uses only annual
periods whose availability is strictly < `t`, so dropping future fiscal years cannot change a past-date value,
(3) strict-before (no same-day leak), (4) old-schema stores degrade to NaN (backward-compat).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.fundamentals import DEPTH_FEATURE_COLS, build_pit_frame_from_screener, depth_feature_series


def _pl() -> pd.DataFrame:
    return pd.DataFrame({
        "x": ["Sales", "Operating Profit", "OPM %", "Interest", "Depreciation", "EPS in Rs", "Net Profit"],
        "Mar 2022": [700.0, 140.0, 20.0, 9.0, 28.0, 9.0, 90.0],
        "Mar 2023": [800.0, 160.0, 20.0, 10.0, 30.0, 10.0, 100.0],
        "Mar 2024": [1000.0, 220.0, 22.0, 12.0, 35.0, 12.0, 120.0]})


def _bs() -> pd.DataFrame:
    return pd.DataFrame({"x": ["Equity Capital", "Reserves", "Borrowings", "Total Assets"],
                         "Mar 2022": [10.0, 70.0, 45.0, 180.0],
                         "Mar 2023": [10.0, 90.0, 50.0, 200.0],
                         "Mar 2024": [10.0, 110.0, 60.0, 240.0]})


def _store(pl=None, bs=None) -> dict:
    return {"T": build_pit_frame_from_screener(_pl() if pl is None else pl, _bs() if bs is None else bs)}


def test_depth_feature_values():
    """After Mar-2024 availability, the features reflect FY2024 (vs FY2023)."""
    dates = pd.DatetimeIndex(["2024-07-01"])
    f = depth_feature_series("T", _store(), dates)
    assert np.isclose(f["rev_yoy"][0], 1000 / 800 - 1)          # +25%
    assert np.isclose(f["eps_yoy"][0], 12 / 10 - 1)             # +20%
    assert np.isclose(f["np_yoy"][0], 120 / 100 - 1)            # +20%
    assert np.isclose(f["op_to_assets"][0], 220 / 240)          # operating profitability proxy
    assert np.isclose(f["op_margin"][0], 22.0)
    assert np.isclose(f["op_margin_delta"][0], 22.0 - 20.0)     # margin trend +2pp
    assert np.isclose(f["asset_turnover"][0], 1000 / 240)


def test_truncation_pit_growth_feature():
    """The PIT gate: dropping the future fiscal year cannot change a past-date feature value.

    For a date between FY2023 and FY2024 availability, the full store and a store truncated to FY2023 must
    give identical features (both see only ≤ FY2023) — proving rev_yoy at that date does not peek at FY2024."""
    dates = pd.DatetimeIndex(["2023-09-01", "2024-01-01"])   # after FY2023 avail (2023-06-29), before FY2024
    full = depth_feature_series("T", _store(), dates)
    trunc = depth_feature_series("T", _store(_pl().drop(columns=["Mar 2024"]), _bs().drop(columns=["Mar 2024"])), dates)
    for k in DEPTH_FEATURE_COLS:
        np.testing.assert_array_equal(full[k], trunc[k])
    assert np.isclose(full["rev_yoy"][0], 800 / 700 - 1)       # FY2023 growth, not FY2024


def test_strict_before_no_same_day_leak():
    """A date exactly on an availability boundary sees the PRIOR period (allow_exact_matches=False)."""
    dates = pd.DatetimeIndex(["2024-06-29"])                   # == FY2024 availability (period_end+90d)
    f = depth_feature_series("T", _store(), dates)
    assert np.isclose(f["rev_yoy"][0], 800 / 700 - 1)          # FY2023, NOT FY2024's +25%


def test_old_schema_store_returns_nan():
    """A store frame with only the original 5 fields (no depth levels) → all-NaN features, no crash."""
    old = pd.DataFrame(
        {"period_end": [pd.Timestamp("2023-03-31")], "eps_ttm": [10.0], "book_value_ps": [12.0],
         "roe": [15.0], "debt_equity": [0.4]},
        index=pd.DatetimeIndex([pd.Timestamp("2023-06-29")], name="available_date"))
    f = depth_feature_series("T", {"T": old}, pd.DatetimeIndex(["2024-07-01"]))
    assert all(np.isnan(f[k][0]) for k in DEPTH_FEATURE_COLS)
