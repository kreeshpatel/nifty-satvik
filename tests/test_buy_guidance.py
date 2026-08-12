"""Execution guidance on the buy card — the wide-band / small-body fix.

The signal-week band [entry_low, entry_high] is 8.9% wide at the median and >10% for 42% of signals.
A user told to "buy in the band" can fill at the top (and get caught by the pullback) or near the
bottom — which is the STOP, i.e. buying into weakness. These fields add a tight buy zone, a no-chase
ceiling, and a conviction flag for the indecision candle the owner flagged.

The binding property: this is ADDITIVE. No traded value (entry/stop/target/bands) may change, and the
signal-week open/close added to `last_signal` must not perturb the backtest golden master.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_cron as C  # noqa: E402


def test_a_wide_small_body_week_is_flagged_low_conviction():
    """The owner's case: big range, small body -> indecision -> measured +0.03R vs +0.39R."""
    g = C._buy_guidance(entry=100.0, lo=94.0, hi=106.0, wo=99.5, wc=100.0)   # 12% band, ~0 body
    assert g["signal_conviction"] == "low"
    assert g["band_is_wide"] is True
    assert g["body_ratio"] < C.LOW_CONVICTION_BODY_RATIO


def test_a_tight_solid_body_week_is_normal_conviction():
    g = C._buy_guidance(entry=100.0, lo=98.0, hi=102.0, wo=98.5, wc=101.5)   # 4% band, solid body
    assert g["signal_conviction"] == "normal"
    assert g["band_is_wide"] is False


def test_the_no_chase_ceiling_caps_the_buy_zone_on_a_wide_band():
    """Buying at the top of a wide band is the exact failure the owner described."""
    g = C._buy_guidance(entry=100.0, lo=90.0, hi=112.0, wo=95.0, wc=100.0)
    assert g["no_chase_above"] == pytest.approx(103.0)          # entry * 1.03
    assert g["buy_zone_high"] == pytest.approx(103.0)           # min(hi=112, 103)
    assert g["buy_zone_low"] == 100.0, "never below the modelled entry (that is toward the stop)"


def test_a_tight_band_zone_is_the_band_top_not_an_arbitrary_chase():
    """When the band is already tighter than the chase cap, don't invent room above it."""
    g = C._buy_guidance(entry=100.0, lo=99.0, hi=101.5, wo=99.5, wc=101.0)
    assert g["buy_zone_high"] == pytest.approx(101.5)           # min(hi=101.5, 103) = the band top


def test_conviction_is_omitted_cleanly_without_the_signal_week_candle():
    """Older P dicts have no wo/wc; the flag must be absent, not guessed."""
    g = C._buy_guidance(entry=100.0, lo=95.0, hi=105.0, wo=None, wc=None)
    assert "signal_conviction" not in g and "body_ratio" not in g
    assert "no_chase_above" in g, "the price guidance does not depend on the candle and must stay"


def test_signal_week_oc_is_reconstructed_from_daily_arrays_not_last_signal():
    """wo/wc come from the card builder's daily arrays, NOT from last_signal — adding a field to
    last_signal would break the r94 golden fixture that snapshots it."""
    class _S(dict): pass
    import pandas as pd
    dates = pd.bdate_range("2026-01-05", periods=10)   # two ISO weeks
    s = {"dates": dates.values, "o": list(range(10)), "c": [x + 0.5 for x in range(10)]}
    wo, wc = C._sig_week_oc(s, 6)                        # Fri of week 2 is index ~6-9
    assert wo is not None and wc is not None
    # the engine's last_signal must NOT carry wo/wc (keeps the golden byte-identical)
    src = (ROOT / "scripts" / "run_bhanushali_weekly_rank.py").read_text(encoding="utf-8")
    assert '"wo": float(wopen' not in src, "wo/wc must not be added to last_signal"


def test_no_traded_value_is_touched():
    """The guidance keys must be disjoint from the traded/record keys."""
    g = C._buy_guidance(entry=100.0, lo=95.0, hi=105.0, wo=99.0, wc=100.0)
    traded = {"entry", "stop", "target", "entry_low", "entry_high", "stop_week_low"}
    assert not (set(g) & traded), "guidance must not overwrite a traded value"


def test_entry_week_open_is_the_first_bar_after_the_signal_friday():
    """The modelled fill = the Monday open of the entry week (first session after the signal Friday).
    None at the last bar (fresh signal, entry week not opened). New helper — fails on old code."""
    s = {"o": [10.0, 11.0, 12.0, 13.0]}
    assert C._entry_week_open(s, 0) == 11.0          # bar after fri_idx 0
    assert C._entry_week_open(s, 2) == 13.0
    assert C._entry_week_open(s, 3) is None          # last bar -> entry week not open yet
    assert C._entry_week_open({"o": []}, 0) is None  # degenerate


def test_the_card_emits_entry_week_open():
    """Guard the wiring: the card builder must include the field, or the P&L tracker has no buy ref."""
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert '"entry_week_open": _entry_week_open(s, ls["fri_idx"])' in src
