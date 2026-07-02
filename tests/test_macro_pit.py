"""PIT / leakage guard for the rebuilt macro factors (nq.data.macro).

The un-audited `data/macro_data.pkl` had no builder and could not be truncation-tested, so finding 0016's
cross-asset IC was provisional. `derive_macro_factors` must be TRAILING-ONLY: deriving on a series truncated
at date d must give byte-identical values (at every date <= d) as deriving on the full series. Any
forward-looking op (centered window, full-sample z-score, bfill, shift(-k)) would break this.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.macro import derive_macro_factors


def _synthetic_closes(n: int = 160) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {name: 100.0 * np.cumprod(1 + rng.normal(0, 0.012, n)) for name in ("crude", "usd", "vix", "nifty")},
        index=dates,
    )


def test_derive_is_trailing_only():
    """Truncating the future leaves every past factor value unchanged (no lookahead)."""
    closes = _synthetic_closes()
    d = closes.index[100]

    full = derive_macro_factors(closes)
    trunc = derive_macro_factors(closes.loc[:d])

    common = full.loc[:d].index
    # every derived value at each date <= d must match between full and truncated runs
    pd.testing.assert_frame_equal(full.loc[common], trunc.loc[common])


def test_derive_columns_and_first_row_nan():
    """Expected factor columns; return-based columns start NaN (pct_change has no t-1 on row 0)."""
    fac = derive_macro_factors(_synthetic_closes(20))
    assert {"crude_ret", "usd_ret", "vix_level", "vix_chg", "nifty_ret"} <= set(fac.columns)
    for c in ("crude_ret", "usd_ret", "vix_chg", "nifty_ret"):
        assert np.isnan(fac[c].iloc[0])
    assert not np.isnan(fac["vix_level"].iloc[0])  # a level, defined on row 0
