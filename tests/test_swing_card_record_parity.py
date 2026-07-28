"""Card/record parity for the live weekly-swing book — constitution D5.

The buy card is what the owner acts on; the modeled book is what the record books. They used to
disagree: the card printed the RAW signal-week low as the stop and derived its +2R target and all
three exit tranches from it, while the engine lifts the stop to
``max(week_low, entry x (1 - max_risk_pct))`` before sizing. The owner therefore sized off a wider
stop than the book, rested a +2R limit at a price the record never used, and ran a different R than
the record booked — invisible because there is no fill feedback (constitution D4).

These tests pin the arithmetic relationship, not a snapshot: the card's stop/target must be
reproducible from the ENGINE's own rule, and the card must warn when the engine's extension cap
would make the record refuse the fill the card is advertising.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_bhanushali_cron import (  # noqa: E402
    LIVE_DISCIPLINE,
    TARGET_R,
    _exit_plan,
    _ext_flags,
    _record_stop,
)


def _engine_stop(entry: float, week_low: float) -> float:
    """The engine's sizing-block rule, transcribed independently of the cron helper.

    Mirrors run_bhanushali_weekly_rank.backtest: ``st = o_["lo"]`` then, when max_risk_pct is set,
    ``st = max(st, en * (1 - max_risk_pct))``. If this transcription and ``_record_stop`` ever
    disagree, the card has drifted from the book again."""
    st = week_low
    mrp = LIVE_DISCIPLINE.get("max_risk_pct")
    if mrp is not None:
        st = max(st, entry * (1.0 - mrp))
    return st


@pytest.mark.parametrize(("entry", "week_low"), [
    (100.0, 80.0),     # low far below -> the discipline lift binds (R capped at 10%)
    (100.0, 96.0),     # low near entry -> the taught low binds (tighter than the cap)
    (100.0, 90.0),     # exactly at the cap boundary
    (1450.13, 1180.0),
    (212.0, 205.0),
])
def test_card_stop_equals_engine_stop(entry, week_low):
    assert _record_stop(entry, week_low) == pytest.approx(_engine_stop(entry, week_low))


def test_card_stop_never_below_the_taught_week_low_rule():
    """The lift may only RAISE the stop (cap R); it must never loosen it below the candle low."""
    for entry, low in ((100.0, 80.0), (100.0, 99.0), (57.5, 40.0)):
        assert _record_stop(entry, low) >= low


def test_card_target_is_two_R_off_the_record_stop():
    """The card's target must be +2R measured on the RECORD's stop, matching the engine's tp1."""
    entry, low = 100.0, 80.0
    stop = _record_stop(entry, low)
    card_target = entry + TARGET_R * (entry - stop)
    # engine: tp1 level = en + tp1_r * risk0, risk0 = en - st
    from run_bhanushali_cron import LIVE_EXIT
    tp1_r = LIVE_EXIT["scaled_exit"]["tp1_r"]
    assert card_target == pytest.approx(entry + tp1_r * (entry - stop))
    assert card_target == pytest.approx(120.0)          # R capped at 10 => +2R = +20%


def test_exit_plan_tranches_price_off_the_record_stop():
    """Every tranche level on the card derives from the record's R, not the raw-low R."""
    entry, low, sma = 100.0, 80.0, 92.0
    stop = _record_stop(entry, low)
    plan = _exit_plan(entry, stop, sma)
    tranches = {t["type"]: t for t in plan["tranches"]}
    assert tranches["target"]["level"] == pytest.approx(entry + 2.0 * (entry - stop))
    assert tranches["pattern"]["arm"] == pytest.approx(entry + 2.5 * (entry - stop))
    assert tranches["runner"]["level"] == pytest.approx(sma)
    assert sum(t["pct"] for t in plan["tranches"]) == 100


def test_ext_flags_mark_fills_the_record_would_refuse():
    """A card priced above the engine's ext_cap must say so — otherwise it advertises a buy the
    book will never record."""
    cap = LIVE_DISCIPLINE["ext_cap"]
    sma = 100.0
    over = _ext_flags(sma * (1 + cap) + 0.01, sma)
    under = _ext_flags(sma * (1 + cap) - 0.01, sma)
    assert over["record_would_skip_as_extended"] is True
    assert under["record_would_skip_as_extended"] is False
    assert under["ext_cap_pct"] == pytest.approx(cap * 100)


def test_ext_flags_degrade_safely_without_an_sma():
    """A NaN/absent SMA must not fabricate a flag."""
    assert _ext_flags(100.0, float("nan")) == {}
    assert _ext_flags(100.0, 0.0) == {}
