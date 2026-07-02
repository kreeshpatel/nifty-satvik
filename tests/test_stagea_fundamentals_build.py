"""Stage A — Screener PIT-frame builder (hermetic).

Pins the pure HTML-table → PIT-frame derivation that gives delisted/historical names their D/E
(the survivorship-correction fundamentals). The network scrape is in scripts/scrape_screener.py;
here we feed synthetic parsed Screener tables and check the derived ratios + the lookahead-safe
availability date."""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.fundamentals import build_pit_frame_from_screener


DEPTH_COLS = ["sales", "operating_profit", "opm_pct", "net_profit", "total_assets", "interest", "depreciation"]


def _pl():
    return pd.DataFrame({
        "x": ["Sales", "Operating Profit", "OPM %", "Interest", "Depreciation", "EPS in Rs", "Net Profit"],
        "Mar 2023": [800.0, 160.0, 20.0, 10.0, 30.0, 10.0, 100.0],
        "Mar 2024": [1000.0, 220.0, 22.0, 12.0, 35.0, 12.0, 120.0],
        "TTM":      [1100.0, 240.0, 22.0, 13.0, 36.0, 13.0, 130.0]})


def _bs():
    return pd.DataFrame({"x": ["Equity Capital", "Reserves", "Borrowings", "Total Assets"],
                         "Mar 2023": [10.0, 90.0, 50.0, 200.0], "Mar 2024": [10.0, 110.0, 60.0, 240.0]})


def test_build_pit_frame_ratios_and_availability():
    f = build_pit_frame_from_screener(_pl(), _bs())
    # two fiscal years; the 'TTM' column is skipped (not a period label)
    assert list(f["period_end"]) == [pd.Timestamp("2023-03-31"), pd.Timestamp("2024-03-31")]
    # available_date = period_end + 90d (conservative annual lag, strictly after the period)
    assert list(f.index) == [pd.Timestamp("2023-06-29"), pd.Timestamp("2024-06-29")]
    # Mar 2024: net worth 10+110=120; D/E 60/120=0.5; ROE 120/120*100=100; shares 120/12=10; bvps 12
    r24 = f.loc[pd.Timestamp("2024-06-29")]
    assert r24["debt_equity"] == 0.5 and r24["roe"] == 100.0
    assert r24["eps_ttm"] == 12.0 and r24["book_value_ps"] == 12.0
    # Part-1.2 depth fields parse as raw annual levels
    assert r24["sales"] == 1000.0 and r24["operating_profit"] == 220.0 and r24["opm_pct"] == 22.0
    assert r24["net_profit"] == 120.0 and r24["total_assets"] == 240.0
    assert r24["interest"] == 12.0 and r24["depreciation"] == 35.0
    # original 5 columns keep their positions; depth fields are appended (backward-compatible superset)
    assert list(f.columns) == ["period_end", "eps_ttm", "book_value_ps", "roe", "debt_equity"] + DEPTH_COLS
    assert f.index.name == "available_date"


def test_build_pit_frame_missing_borrowings_is_nan_not_crash():
    bs = pd.DataFrame({"x": ["Equity Capital", "Reserves"], "Mar 2024": [10.0, 110.0]})
    f = build_pit_frame_from_screener(_pl(), bs)
    assert np.isnan(f.loc[pd.Timestamp("2024-06-29"), "debt_equity"])   # no Borrowings row -> NaN D/E
    assert f.loc[pd.Timestamp("2024-06-29"), "roe"] == 100.0            # roe still derives


def test_build_pit_frame_empty_when_no_tables():
    f = build_pit_frame_from_screener(None, None)
    assert f.empty
    assert list(f.columns) == ["period_end", "eps_ttm", "book_value_ps", "roe", "debt_equity"] + DEPTH_COLS


def test_depth_fields_nan_when_rows_absent():
    """A minimal P&L (only EPS + Net Profit, no Sales/OPM/etc.) yields NaN depth fields, not a crash —
    the backward-compat path for pages/quarters that lack the depth rows (or the ~5% financials schema)."""
    pl = pd.DataFrame({"x": ["EPS in Rs", "Net Profit"], "Mar 2024": [12.0, 120.0]})
    bs = pd.DataFrame({"x": ["Equity Capital", "Reserves"], "Mar 2024": [10.0, 110.0]})
    f = build_pit_frame_from_screener(pl, bs)
    r = f.loc[pd.Timestamp("2024-06-29")]
    assert r["net_profit"] == 120.0            # net_profit still derives (shared with roe path)
    assert np.isnan(r["sales"]) and np.isnan(r["total_assets"]) and np.isnan(r["opm_pct"])
