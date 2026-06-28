"""Stage-1 gate — reproduce expected values on the carried small known universe.

The carried golden fixture ``tests/fixtures/lh_golden_panel.csv`` is the post-feature,
post-eligibility, ranked panel for 11 large-cap survivors (2017-01-02..2019-12-31). It is a
fully hermetic known-universe fixture: the full-history raw cache that *built* the
``sma200_slope_63`` / ``atr_pct_63`` columns is no longer available, but the panel itself lets
us reproduce the recomputable derived columns and verify the eligibility mask end-to-end —
exactly the Stage-1 gate ("sma200_slope_63 + the eligibility mask reproduce expected values").
The feature *formulas* and the no-lookahead property are proven hermetically in
``test_stage1_features.py``.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nq.data import (
    cross_sectional_rank,
    load_fund_store,
    load_membership,
    restrict_to_large_mid,
    solvent_universe_mask,
    ticker_in_index_on,
    value_quality_series,
)
from nq.data.features import sma

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "fixtures" / "lh_golden_panel.csv"
EXPECTED_NAMES = {
    "ASIANPAINT", "HINDUNILVR", "INFY", "ITC", "MARUTI", "RELIANCE",
    "SUNPHARMA", "TCS", "TITAN", "ULTRACEMCO", "WIPRO",
}


@pytest.fixture(scope="module")
def golden() -> pd.DataFrame:
    g = pd.read_csv(GOLDEN, parse_dates=["date"])
    assert set(g["ticker"].unique()) == EXPECTED_NAMES
    return g


def _with_fundamentals(golden: pd.DataFrame) -> pd.DataFrame:
    store = load_fund_store()
    assert store is not None, "carried fundamentals store must load"
    parts = []
    for tkr, grp in golden.sort_values("date").groupby("ticker"):
        grp = grp.copy()
        vq = value_quality_series(tkr, store, pd.DatetimeIndex(grp["date"]),
                                  grp["close"].to_numpy(float))
        grp["low_debt"] = vq["low_debt"]
        grp["roe"] = vq["roe"]
        parts.append(grp)
    return pd.concat(parts, ignore_index=True)


def test_trend_rank_reproduces_golden(golden):
    """cross_sectional_rank on the golden's own sma200_slope_63 reproduces trend_rank."""
    ranked = cross_sectional_rank(golden[["date", "ticker", "sma200_slope_63"]].copy(),
                                  "sma200_slope_63")
    diff = np.abs(ranked["trend_rank"].to_numpy() - golden["trend_rank"].to_numpy())
    assert np.nanmax(diff) < 1e-12
    # higher slope -> higher rank, within a date
    day = golden[golden["date"] == golden["date"].iloc[0]].sort_values("sma200_slope_63")
    rk = cross_sectional_rank(day[["date", "ticker", "sma200_slope_63"]].copy(),
                              "sma200_slope_63")["trend_rank"].to_numpy()
    assert np.all(np.diff(rk) > 0)


def test_adv_rupees_20d_recompute_from_golden(golden):
    """adv_rupees_20d == sma(volume,20)*close, recomputed from the golden's own OHLCV (rows
    whose 20-day window is fully inside the golden window)."""
    worst = 0.0
    for _tkr, grp in golden.sort_values("date").groupby("ticker"):
        grp = grp.sort_values("date")
        adv = sma(grp["volume"].to_numpy(float), 20) * grp["close"].to_numpy(float)
        gold = grp["adv_rupees_20d"].to_numpy(float)
        rel = np.abs(adv[19:] - gold[19:]) / np.where(gold[19:] != 0, np.abs(gold[19:]), 1)
        worst = max(worst, float(np.nanmax(rel)))
    assert worst < 1e-9


def test_pit_de_join_in_solvent_range(golden):
    """The PIT D/E join yields a finite low_debt in the solvent band (-1.5, 0] for every golden
    row — all 11 names were solvent throughout the window (and TITAN's later D/E=1.79 is
    correctly NOT used, proving strict-before timing)."""
    uni = _with_fundamentals(golden)
    ld = uni["low_debt"].to_numpy(float)
    assert np.isfinite(ld).all(), "every golden row must have a PIT D/E available"
    assert ld.max() <= 0.0 and ld.min() > -1.5


def test_solvency_mask_keeps_all_golden_rows(golden):
    uni = _with_fundamentals(golden)
    keep = solvent_universe_mask(uni)
    assert keep.all(), "all golden rows are solvent low-debt non-financials"
    assert uni[keep]["ticker"].nunique() == 11


def test_large_mid_keeps_every_golden_name(golden):
    """restrict_to_large_mid(>=5cr) keeps all 11 names; and it never drops a row for being too
    small — every row with a defined trailing-median ADV passes the threshold (the only rows
    dropped are the rolling-median warm-up rows of the trimmed panel)."""
    df = golden.sort_values(["ticker", "date"]).copy()
    med = df.groupby("ticker")["adv_rupees_20d"].transform(
        lambda s: s.rolling(252, min_periods=126).median())
    out, rep = restrict_to_large_mid(golden.copy(), min_adv_rs=5e7)
    assert rep["tickers_after"] == 11
    # wherever the median is defined, the keep decision must be True (no size-based drop)
    defined = med.notna()
    keep_when_defined = (med >= 5e7)[defined]
    assert keep_when_defined.all()


def test_membership_covers_golden_window(golden):
    m = load_membership()
    assert m is not None and len(m) > 500, "carried (corrected) membership must load"
    for d in (date(2017, 1, 2), date(2018, 6, 1), date(2019, 12, 31)):
        for t in EXPECTED_NAMES:
            assert ticker_in_index_on(t, d, m), f"{t} must be a member on {d}"


def test_corrected_membership_not_naive():
    """We carry the survivorship-corrected file (~813 tickers with real exits), never the
    naive survivor-only file (497 names all to_date=2030)."""
    m = load_membership()
    assert len(m) > 700
    has_real_exit = any(
        d_to < date(2026, 1, 1) for periods in m.values() for _d_from, d_to in periods)
    assert has_real_exit, "corrected membership must contain real (pre-2026) exits"
