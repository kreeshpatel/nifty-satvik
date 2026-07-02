"""Part 1.4 — PIT / leakage gate for the fundamentals-depth builder (`build_pit_frame_from_screener`).

The builder stores raw annual levels per fiscal period. The point-in-time guarantee: a period's row depends
ONLY on that period's column in the source Screener table — never on a later period. So dropping the future
period columns must leave every surviving period's row **byte-identical**. Any forward-peeking derivation
(e.g. a growth/margin calc that referenced a future column) would break this test. This is the data-layer
analogue of `tests/test_macro_pit.py`; it must be green before Part 2 builds features on the depth fields.

Note: growth/ratio features (revenue_yoy, …) are Part 2, computed downstream from these raw levels; their own
truncation gate lives with the feature code. Here we lock the *store* to be strictly period-independent.
"""
from __future__ import annotations

import pandas as pd

from nq.data.fundamentals import build_pit_frame_from_screener


def _pl() -> pd.DataFrame:
    return pd.DataFrame({
        "x": ["Sales", "Operating Profit", "OPM %", "Interest", "Depreciation", "EPS in Rs", "Net Profit"],
        "Mar 2022": [700.0, 140.0, 20.0, 9.0, 28.0, 9.0, 90.0],
        "Mar 2023": [800.0, 160.0, 20.0, 10.0, 30.0, 10.0, 100.0],
        "Mar 2024": [1000.0, 220.0, 22.0, 12.0, 35.0, 12.0, 120.0],
        "TTM":      [1100.0, 240.0, 22.0, 13.0, 36.0, 13.0, 130.0]})


def _bs() -> pd.DataFrame:
    return pd.DataFrame({"x": ["Equity Capital", "Reserves", "Borrowings", "Total Assets"],
                         "Mar 2022": [10.0, 70.0, 45.0, 180.0],
                         "Mar 2023": [10.0, 90.0, 50.0, 200.0],
                         "Mar 2024": [10.0, 110.0, 60.0, 240.0]})


def test_truncation_period_independence():
    """Dropping the latest fiscal year leaves every earlier period's full row byte-identical."""
    full = build_pit_frame_from_screener(_pl(), _bs())
    pl_t = _pl().drop(columns=["Mar 2024"])   # remove the "future" period relative to Mar 2023
    bs_t = _bs().drop(columns=["Mar 2024"])
    trunc = build_pit_frame_from_screener(pl_t, bs_t)

    # truncated build must have exactly the surviving periods, and each row identical to the full build
    assert list(trunc["period_end"]) == [pd.Timestamp("2022-03-31"), pd.Timestamp("2023-03-31")]
    pd.testing.assert_frame_equal(full.loc[trunc.index], trunc)


def test_availability_strictly_after_period_end():
    """Every value's availability date is strictly after its fiscal period-end (the +90d publication lag)."""
    f = build_pit_frame_from_screener(_pl(), _bs())
    for avail, pe in zip(f.index, f["period_end"], strict=True):
        assert avail > pe


def test_depth_levels_are_raw_not_derived_across_periods():
    """A depth level for a period equals its own source cell — not a growth/blend of neighbouring periods."""
    f = build_pit_frame_from_screener(_pl(), _bs())
    r23 = f.loc[f["period_end"] == pd.Timestamp("2023-03-31")].iloc[0]
    assert r23["sales"] == 800.0 and r23["operating_profit"] == 160.0 and r23["total_assets"] == 200.0
