"""Stage-1 gate — data-quality units: the cleaner (split vs demerger vs bad tick), the
demerger quarantine guard, the PIT membership mask, the strict-before D/E join, and the
solvency mask branches. These pin the failure modes that ``skills/data-quality`` and
``skills/leakage-audit`` exist to prevent (the VEDL demerger-as-split fabrication, same-day
fundamentals leakage, survivorship contamination)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from nq.data.eligibility import solvent_universe_mask
from nq.data.fundamentals import value_quality_series
from nq.data.membership import filter_features_dict, ticker_in_index_on
from nq.data.ohlcv import (
    clean_ohlcv_for_features,
    demerger_suspect,
    load_demerger_reference,
)


def _frame(prices, vols=None):
    idx = pd.date_range("2020-01-01", periods=len(prices), freq="D")
    p = np.asarray(prices, float)
    v = np.asarray(vols if vols is not None else [1000.0] * len(prices), float)
    return pd.DataFrame({"Open": p, "High": p, "Low": p, "Close": p, "Volume": v}, index=idx)


# ── Cleaner ───────────────────────────────────────────────────────────────────────────

def test_split_backadjusted_and_volume_inverse_scaled():
    df = _frame([100, 101, 102, 103, 104, 40, 41, 42, 43, 44])   # ~-61.5% at bar 5
    out, rep = clean_ohlcv_for_features(df, holidays=set())
    assert rep["splits_adjusted"] == 1 and rep["demergers_detected"] == 0
    assert out["Close"].iloc[0] == pytest.approx(100 * 40 / 104)        # pre-event scaled
    assert out["Volume"].iloc[0] == pytest.approx(1000 * 104 / 40)      # turnover invariant


def test_demerger_left_as_discontinuity():
    df = _frame([100, 101, 102, 103, 104, 40, 41, 42, 43, 44])
    dt = df.index[5].strftime("%Y-%m-%d")
    out, rep = clean_ohlcv_for_features(df, holidays=set(), ticker="VEDL", demerger_dates={dt})
    assert rep["demergers_detected"] == 1 and rep["splits_adjusted"] == 0
    assert out["Close"].iloc[0] == pytest.approx(100.0)                 # NOT back-adjusted


def test_bad_tick_dropped():
    # a >50% spike at bar 5 that reverses the next bar -> dropped, not adjusted
    df = _frame([100, 101, 102, 103, 104, 220, 105, 106, 107, 108])
    out, rep = clean_ohlcv_for_features(df, holidays=set())
    assert rep["bad_ticks_dropped"] == 1
    assert 220.0 not in out["Close"].to_numpy()


def test_zero_volume_flat_bar_dropped():
    df = _frame([100, 100, 102, 103, 104], vols=[1000, 0, 1000, 1000, 1000])
    df.iloc[1, df.columns.get_loc("Open")] = 100   # flat OHLC + zero vol at bar 1
    df.iloc[1, df.columns.get_loc("High")] = 100
    df.iloc[1, df.columns.get_loc("Low")] = 100
    df.iloc[1, df.columns.get_loc("Close")] = 100
    out, rep = clean_ohlcv_for_features(df, holidays=set())
    assert rep["dropped_zero_vol"] == 1 and len(out) == 4


def test_holiday_bar_dropped():
    df = _frame([100, 101, 102, 103, 104])
    hol = {df.index[2].strftime("%Y-%m-%d")}
    out, rep = clean_ohlcv_for_features(df, holidays=hol)
    assert rep["dropped_holiday"] == 1 and len(out) == 4


# ── Demerger quarantine guard ───────────────────────────────────────────────────────────

def test_demerger_suspect_flags_vedl_like_drop():
    # a sustained -65% drop that does NOT recover -> suspect
    px = list(np.linspace(700, 770, 60)) + list(np.linspace(270, 290, 60))
    assert demerger_suspect(px) is True


def test_demerger_suspect_ignores_steady_and_recovering():
    steady = list(np.linspace(100, 130, 120))
    assert demerger_suspect(steady) is False
    # a bad tick that snaps back within a few sessions is NOT a demerger
    recov = [100] * 30 + [40] + [98, 99, 100, 101] + [100] * 30
    assert demerger_suspect(recov) is False


def test_demerger_reference_carried():
    ref = load_demerger_reference()
    assert {"VEDL", "ABFRL", "RAYMOND", "SKFINDIA"}.issubset(ref.keys())
    assert "2026-04-30" in ref["VEDL"]


# ── PIT membership mask ─────────────────────────────────────────────────────────────────

def test_membership_mask_drops_nonmembers_and_masks_dates():
    idx = pd.date_range("2020-01-01", "2020-12-31", freq="D")
    feats = {
        "AAA": pd.DataFrame({"x": 1.0}, index=idx),   # member only H1 2020
        "BBB": pd.DataFrame({"x": 1.0}, index=idx),   # never a member
    }
    membership = {"AAA": [(date(2020, 1, 1), date(2020, 6, 30))]}
    out = filter_features_dict(feats, membership)
    assert set(out.keys()) == {"AAA"}                              # BBB dropped
    assert out["AAA"].index.max() <= pd.Timestamp("2020-06-30")    # H2 masked off
    assert ticker_in_index_on("AAA", date(2020, 3, 1), membership)
    assert not ticker_in_index_on("AAA", date(2020, 9, 1), membership)


def test_membership_none_is_noop():
    feats = {"AAA": pd.DataFrame({"x": [1.0]}, index=pd.to_datetime(["2020-01-01"]))}
    assert filter_features_dict(feats, None) is feats


# ── PIT D/E join: strictly before (no same-day leak) ───────────────────────────────────

def test_pit_de_join_strict_before():
    store = {
        "T": pd.DataFrame(
            {"debt_equity": [0.5, 1.2], "roe": [15.0, 9.0]},
            index=pd.to_datetime(["2019-06-30", "2020-06-30"]),
        )
    }
    dates = pd.DatetimeIndex(["2020-06-29", "2020-06-30", "2020-07-01"])
    close = np.array([100.0, 100.0, 100.0])
    out = value_quality_series("T", store, dates, close)
    ld = out["low_debt"]
    # 2020-06-29: only the 2019 filing is strictly-before -> D/E 0.5 -> low_debt -0.5
    assert ld[0] == pytest.approx(-0.5)
    # 2020-06-30: the same-day filing is NOT used (allow_exact_matches=False) -> still 2019
    assert ld[1] == pytest.approx(-0.5)
    # 2020-07-01: now the 2020 filing (D/E 1.2) is available -> low_debt -1.2
    assert ld[2] == pytest.approx(-1.2)


def test_pit_de_join_missing_ticker_all_nan():
    out = value_quality_series("ZZZ", {}, pd.DatetimeIndex(["2020-01-01"]), np.array([100.0]))
    assert np.isnan(out["low_debt"]).all()


# ── Solvency mask branches ──────────────────────────────────────────────────────────────

def test_solvency_mask_all_branches():
    df = pd.DataFrame({
        "low_debt": [-0.8, -1.6, 0.0, 0.2, np.nan, np.nan, -0.5],
        "roe": [12.0, 12.0, 12.0, 12.0, 15.0, -3.0, 8.0],
        "sector": ["IT", "IT", "IT", "IT", "Banking", "Banking", "Banking"],
    })
    keep = solvent_universe_mask(df).to_numpy()
    assert list(keep) == [
        True,    # D/E 0.8 in band
        False,   # D/E 1.6 >= de_max
        True,    # D/E 0.0 (boundary, kept)
        False,   # low_debt > 0 -> negative D/E, dropped
        True,    # financial, D/E NaN, ROE > 0 -> re-admitted
        False,   # financial, D/E NaN, ROE <= 0 -> dropped
        True,    # financial WITH D/E present uses the leverage gate (0.5 in band)
    ]
