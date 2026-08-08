"""Tests for :mod:`nq.universe` — the PIT tradable-universe service.

The screens are subtractive, which makes them dangerous in a specific way: a screen that is too
aggressive silently changes the experiment rather than failing. So every "this is excluded" test is
paired with a "this is NOT excluded" test, and the PIT test asserts that membership genuinely
follows the as-of date rather than today's list.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from nq.universe import (BANDS, CIRCUIT_MOVE, MIN_HISTORY, MIN_PRICE, MIN_TURNOVER,
                         build_universe, screen_report, size_bands)

DATES = pd.bdate_range("2024-01-01", periods=400)


def _stock(price: float = 100.0, volume: float = 1e6, n: int = len(DATES),
           shocks: dict[int, float] | None = None) -> pd.DataFrame:
    c = np.full(n, float(price))
    if shocks:
        for i, mult in shocks.items():
            c[i:] *= mult
    return pd.DataFrame({"Open": c, "High": c * 1.001, "Low": c * 0.999, "Close": c,
                         "Volume": np.full(n, float(volume))}, index=DATES[:n])


def _members(names, lo="2020-01-01", hi="2030-01-01"):
    return {n.upper(): [(date.fromisoformat(lo), date.fromisoformat(hi))] for n in names}


# --------------------------------------------------------------------------- basics
def test_eligible_stock_passes_every_screen():
    u = build_universe({"GOOD": _stock(volume=1e6)}, _members(["GOOD"]))
    tail = u[u["date"] > DATES[300]]
    assert tail["eligible"].all()
    assert (tail["size_band"] == "LARGE").all()


def test_panel_carries_prices_and_liquidity():
    u = build_universe({"GOOD": _stock()}, _members(["GOOD"]))
    for col in ("open", "high", "low", "close", "volume", "adv_rupees_20d", "turnover_63d"):
        assert col in u.columns


# --------------------------------------------------------------------------- screens, paired
def test_illiquid_is_excluded_and_liquid_is_not():
    thin = build_universe({"THIN": _stock(volume=100.0)}, _members(["THIN"]))
    assert not thin[thin["date"] > DATES[300]]["liq_ok"].any()
    fat = build_universe({"FAT": _stock(volume=1e6)}, _members(["FAT"]))
    assert fat[fat["date"] > DATES[300]]["liq_ok"].all()


def test_short_history_is_excluded_then_becomes_eligible():
    """A young listing must be excluded early and admitted once it has a year — not banned forever."""
    u = build_universe({"NEW": _stock()}, _members(["NEW"]))
    assert not u.iloc[MIN_HISTORY - 5]["hist_ok"]
    assert u.iloc[MIN_HISTORY + 5]["hist_ok"]


def test_penny_price_is_excluded_and_normal_is_not():
    penny = build_universe({"P": _stock(price=MIN_PRICE - 1, volume=1e8)}, _members(["P"]))
    assert not penny["price_ok"].any()
    normal = build_universe({"N": _stock(price=MIN_PRICE + 1, volume=1e8)}, _members(["N"]))
    assert normal["price_ok"].all()


def test_circuit_proxy_excludes_a_repeatedly_limit_moving_name():
    n = len(DATES)
    c = np.full(n, 100.0)
    for i in range(200, 300):                       # 100 consecutive ~20% moves
        c[i] = c[i - 1] * (1.0 + (CIRCUIT_MOVE + 0.01) * (1 if i % 2 else -1))
    df = pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c,
                       "Volume": np.full(n, 1e6)}, index=DATES)
    u = build_universe({"LOCK": df}, _members(["LOCK"]))
    assert not u[u["date"] > DATES[320]]["circuit_ok"].any()


def test_circuit_proxy_does_not_trip_on_an_ordinary_name():
    """The paired negative — a screen that fires on everything removes the universe, not the risk."""
    u = build_universe({"CALM": _stock()}, _members(["CALM"]))
    assert u[u["date"] > DATES[200]]["circuit_ok"].all()


def test_circuit_screen_can_be_disabled():
    n = len(DATES)
    c = np.full(n, 100.0)
    for i in range(200, 300):
        c[i] = c[i - 1] * (1.0 + (CIRCUIT_MOVE + 0.01) * (1 if i % 2 else -1))
    df = pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c,
                       "Volume": np.full(n, 1e6)}, index=DATES)
    off = build_universe({"L": df}, _members(["L"]), apply_circuit_screen=False)
    assert bool(off["circuit_ok"].all())


# --------------------------------------------------------------------------- PIT membership
def test_membership_is_point_in_time_not_todays_list():
    """The survivorship fix: a name is only in the universe on the dates it was actually a member."""
    mem = {"MID": [(date(2024, 3, 1), date(2024, 6, 30))]}
    u = build_universe({"MID": _stock(volume=1e8)}, mem)
    before = u[u["date"] < pd.Timestamp("2024-03-01")]
    during = u[(u["date"] >= pd.Timestamp("2024-03-01")) & (u["date"] <= pd.Timestamp("2024-06-30"))]
    after = u[u["date"] > pd.Timestamp("2024-06-30")]
    assert not before["is_member"].any()
    assert during["is_member"].all()
    assert not after["is_member"].any()


def test_a_name_never_in_the_index_is_dropped_entirely():
    u = build_universe({"NEVER": _stock(), "OK": _stock()}, _members(["OK"]))
    assert set(u["ticker"].unique()) == {"OK"}


def test_reentry_periods_are_honoured():
    mem = {"RE": [(date(2024, 2, 1), date(2024, 4, 1)), (date(2024, 8, 1), date(2024, 12, 1))]}
    u = build_universe({"RE": _stock()}, mem).set_index("date")
    assert u.loc["2024-03-01", "is_member"]
    assert not u.loc["2024-06-03", "is_member"]
    assert u.loc["2024-09-02", "is_member"]


# --------------------------------------------------------------------------- size bands
def test_size_bands_split_on_turnover_rank():
    assert list(size_bands(np.array([1, 100, 101, 250, 251, np.nan]))) == \
        ["LARGE", "LARGE", "MID", "MID", "SMALL", ""]


def test_bands_are_assigned_per_date_from_trailing_turnover():
    """Build 300 names with distinct volumes; the busiest 100 must land LARGE, the next 150 MID."""
    ohlcv = {f"T{i:03d}": _stock(volume=1e5 * (300 - i), n=300) for i in range(300)}
    u = build_universe(ohlcv, _members(ohlcv))
    day = u[(u["date"] == u["date"].max()) & u["eligible"]]
    assert (day.nsmallest(50, "turnover_rank")["size_band"] == "LARGE").all()
    mid = day[(day["turnover_rank"] > 100) & (day["turnover_rank"] <= 250)]
    assert len(mid) > 0 and (mid["size_band"] == "MID").all()


def test_only_eligible_names_receive_a_band():
    u = build_universe({"THIN": _stock(volume=1.0), "FAT": _stock(volume=1e8)},
                       _members(["THIN", "FAT"]))
    thin = u[u["ticker"] == "THIN"]
    assert (thin["size_band"] == "").all()
    assert thin["turnover_rank"].isna().all()


# --------------------------------------------------------------------------- report
def test_screen_report_attributes_shrinkage():
    u = build_universe({"THIN": _stock(volume=1.0), "FAT": _stock(volume=1e8)},
                       _members(["THIN", "FAT"]))
    rep = screen_report(u)
    assert rep["liq_ok_fail"] > 0
    assert rep["eligible_rows"] < rep["rows"]
    assert "mean_eligible_per_day" in rep


def test_screen_report_always_carries_the_coverage_caveat():
    """The reconstructed-bands / proxy-circuit limitation must travel with every readout."""
    rep = screen_report(build_universe({"A": _stock()}, _members(["A"])))
    assert "NOT NSE constituent" in rep["caveat"]
    assert "proxy" in rep["caveat"]


def test_empty_inputs_are_safe():
    assert build_universe({}, {}).empty
    assert screen_report(pd.DataFrame()) == {}
