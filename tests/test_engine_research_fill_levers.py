"""The two gated fill levers (`min_rr_at_fill`, `whole_shares`) on the engine, 2026-11-02.

Both default OFF and must be byte-identical when off (the two golden masters are the pinned proof; this file
adds the direct off-vs-explicit-off check and shows each lever DOES something when on). Hermetic: the synthetic
fixture, no network, no live cache.
"""
from __future__ import annotations

import copy
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.lab import runs as L  # noqa: E402

KW = L.engine_kwargs(L.DEFAULT_CONFIG)


def _all_members(ohlcv):
    return {t: [(date(2000, 1, 1), date(2100, 1, 1))] for t in ohlcv}


@pytest.fixture(scope="module")
def universe():
    from build_r94_golden_fixture import synth_universe
    ohlcv, _ = synth_universe()
    return ohlcv


@pytest.fixture(scope="module")
def P(universe):
    return R94.prep_weekly_rank(universe, **C.LIVE_PREP)


def _run(P, mem, **extra):
    led: list = []
    plog: list = []
    out = R94.backtest(P, mem, ledger=led, a_grade=R94.grade_a_entries(P), position_log=plog, **{**KW, **extra})
    return out, pd.DataFrame(led), pd.DataFrame(plog)


@pytest.fixture(scope="module")
def base(P, universe):
    mem = _all_members(universe)
    out, led, plog = _run(P, mem)
    assert len(led) > 0, "fixture produced no trades; every assertion here would be vacuous"
    return mem, out, led, plog


# --------------------------------------------------------------------------- off == byte-identical
def test_off_is_byte_identical(P, base):
    mem, out, led, plog = base
    out2, led2, plog2 = _run(P, mem, min_rr_at_fill=None, whole_shares=False)
    pd.testing.assert_frame_equal(led, led2)
    pd.testing.assert_frame_equal(plog, plog2)
    pd.testing.assert_series_equal(out["curve"], out2["curve"])


def test_a_floor_that_can_never_bind_changes_nothing(P, base):
    mem, out, led, _ = base
    out2, led2, _ = _run(P, mem, min_rr_at_fill=-1e9)           # the lever's code path, never skipping
    pd.testing.assert_frame_equal(led, led2)
    pd.testing.assert_series_equal(out["curve"], out2["curve"])


# --------------------------------------------------------------------------- min_rr_at_fill
def _band(lo=90.0, hi=110.0, close=100.0, days=(5, 6, 7)):
    s = {"c": np.array([0.0] * 4 + [close] + [0.0] * 5)}        # index 4 = the signal Friday
    return s, {"lo": lo, "hi": hi, "days": set(days), "atr": float("nan")}


def test_rr_of_a_fill_at_the_signal_reference_is_exactly_tp1_r():
    s, o_ = _band()
    exit_cfg = C.LIVE_EXIT["scaled_exit"]
    rr = R94._fill_rr(s, o_, 100.0, C.LIVE_EXIT["scaled_exit"], 0.10, None, 0.0)
    assert rr == pytest.approx(exit_cfg["tp1_r"])
    assert R94._fill_rr(s, o_, 100.0, None, None, None, 0.0) == pytest.approx(2.0)   # no scaled exit -> +2R


def test_rr_falls_as_the_fill_gaps_up_and_is_target_anchored_to_the_signal():
    s, o_ = _band()
    ex = C.LIVE_EXIT["scaled_exit"]
    lo_rr = R94._fill_rr(s, o_, 98.0, ex, 0.10, None, 0.0)
    ref = R94._fill_rr(s, o_, 100.0, ex, 0.10, None, 0.0)
    gap = R94._fill_rr(s, o_, 108.0, ex, 0.10, None, 0.0)
    assert lo_rr > ref > gap
    # target = 100 + 2 x (100 - 90) = 120 (the 10% cap does not bind at E0=100: stop = max(90, 90) = 90)
    assert gap == pytest.approx((120.0 - 108.0) / (108.0 - max(90.0, 108.0 * 0.90)))


def test_rr_reference_falls_back_to_the_band_midpoint_when_the_close_is_not_inside():
    s, o_ = _band(close=110.0)                                  # close == hi: not strictly inside -> midpoint 100
    ex = C.LIVE_EXIT["scaled_exit"]
    assert R94._fill_rr(s, o_, 100.0, ex, 0.10, None, 0.0) == pytest.approx(ex["tp1_r"])


def test_min_rr_at_fill_skips_a_constructed_gap_up_fill(universe, base):
    mem, _out, led, _plog = base
    P2 = copy.deepcopy(R94.prep_weekly_rank(universe, **C.LIVE_PREP))
    ex = C.LIVE_EXIT["scaled_exit"]
    target = None
    for _, tr in led.iterrows():                                # find a filled signal with room to gap up
        s = P2[tr["tkr"]]
        i = {d: k for k, d in enumerate(s["dates"])}[pd.Timestamp(tr["entry_date"])]
        win = next(w for e0, w in s["entry_win"].items() if i in w[0])
        lo, hi = win[1], win[2]
        o_ = {"lo": lo, "hi": hi, "days": set(win[0]), "atr": float("nan")}
        gap_px = lo + 0.999 * (hi - lo)
        if R94._fill_rr(s, o_, gap_px, ex, KW["max_risk_pct"], None, 0.0) < 1.0:
            target = (tr["tkr"], pd.Timestamp(tr["entry_date"]), i, gap_px)
            break
    assert target is not None, "no fixture signal has a band wide enough to gap up through R:R 1.0"
    tkr, ed, i, gap_px = target
    P2[tkr]["o"] = np.array(P2[tkr]["o"], dtype=float)
    P2[tkr]["o"][i] = gap_px                                    # the entry session now OPENS near the signal high
    _o, led_off, _ = _run(P2, mem)
    hit = led_off[(led_off["tkr"] == tkr) & (pd.to_datetime(led_off["entry_date"]) == ed)]
    assert len(hit) == 1 and hit.iloc[0]["entry"] == pytest.approx(round(gap_px, 2)), "gap-up fill not taken when off"
    _o, led_on, _ = _run(P2, mem, min_rr_at_fill=1.0)
    again = led_on[(led_on["tkr"] == tkr) & (pd.to_datetime(led_on["entry_date"]) == ed)]
    assert again.empty, "min_rr_at_fill=1.0 failed to skip a fill whose R:R is below 1.0"


# --------------------------------------------------------------------------- whole_shares
def test_whole_shares_makes_every_held_share_count_an_integer(P, base):
    mem, _o, led_off, plog_off = base
    _out, led, plog = _run(P, mem, whole_shares=True)
    assert len(led) > 0 and len(plog) > 0
    sh = plog["shares"].to_numpy(float)
    assert np.allclose(sh, np.round(sh)), "a fractional share survived whole_shares"
    assert (sh >= 1).all()
    off = plog_off["shares"].to_numpy(float)
    assert not np.allclose(off, np.round(off)), "the baseline was already integral; the test proves nothing"


def test_whole_shares_tranches_are_whole_and_the_remainder_rides_in_the_runner(P, base):
    mem, *_ = base
    ev: list = []
    led: list = []
    R94.backtest(P, mem, ledger=led, a_grade=R94.grade_a_entries(P), event_log=ev, **{**KW, "whole_shares": True})
    parts = [e for e in ev if e.get("event_type") == "partial_book"]
    plog = pd.DataFrame(ev)
    assert "shares_after" in plog.columns
    after = pd.to_numeric(plog["shares_after"], errors="coerce").dropna().to_numpy(float)
    assert np.allclose(after, np.round(after)), "a tranche left a fractional remainder"
    assert len(parts) > 0, "no tranche was booked on the fixture; the whole-tranche assertion is vacuous"


def test_whole_shares_skips_a_name_too_expensive_to_buy_one_share(universe):
    t = None
    mem = _all_members(universe)
    P0 = R94.prep_weekly_rank(universe, **C.LIVE_PREP)
    _o, led0, _p = _run(P0, mem)
    t = led0.iloc[0]["tkr"]
    big = {k: v.copy() for k, v in universe.items()}
    for col in ("Open", "High", "Low", "Close"):
        big[t][col] = big[t][col] * 1e6                         # one share now costs more than the whole book
    Pb = R94.prep_weekly_rank(big, **C.LIVE_PREP)
    _o, led_frac, _p = _run(Pb, mem)
    assert (led_frac["tkr"] == t).any(), "fractional sizing should still buy the dear name"
    _o, led_whole, _p = _run(Pb, mem, whole_shares=True)
    assert not (led_whole["tkr"] == t).any(), "whole_shares bought a name it cannot afford one share of"
    assert len(led_whole) > 0, "the other names should still trade"


def test_lab_config_exposes_both_levers_and_the_manifest_counts_them():
    assert L.DEFAULT_CONFIG["min_rr_at_fill"] is None and L.DEFAULT_CONFIG["whole_shares"] is False
    # OFF leaves every pre-existing config hash untouched; ON changes it and joins the engine kwargs
    assert L.config_hash({"min_rr_at_fill": None, "whole_shares": False}) == L.config_hash()
    assert L.config_hash({"min_rr_at_fill": 1.5}) != L.config_hash()
    assert "min_rr_at_fill" not in L.engine_kwargs() and "whole_shares" not in L.engine_kwargs()
    assert L.engine_kwargs({"min_rr_at_fill": 1.5, "whole_shares": True})["min_rr_at_fill"] == 1.5
    assert L._manifest(L.normalize_config(None), None)["is_live_book"] is True
    m1 = L._manifest(L.normalize_config({"min_rr_at_fill": 1.0}), None)
    m2 = L._manifest(L.normalize_config({"whole_shares": True}), None)
    assert m1["label"] == "NOT LIVE BOOK: min_rr_at_fill" and m2["label"] == "NOT LIVE BOOK: whole_shares"
    with pytest.raises(ValueError):
        L.normalize_config({"min_rr_at_fill": 0})
