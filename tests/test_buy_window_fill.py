"""The buy window's memory — did this signal EVER trigger, not just "can I buy at today's open".

**Why this exists.** `filled_today` is recomputed against the LAST daily bar on every run, so it
answers a question whose truth changes daily. The card's instruction does not: "buy at the open
inside the band" is satisfied once, on the first session of the window that opens in range, and
stays satisfied.

Reading one for the other put a false instruction on the live board. JSWSTEEL opened 1,298.00
inside its [1,293.70, 1,310.60] band on Monday 2026-08-24 — a clean fill — then opened 1,326 /
1,329 / 1,351 on the next three sessions. By Thursday `filled_today` was False and the Research
board showed "Gapped — wait" on a trade that had already been taken. SAIL did the same thing
(174.80 in [173.46, 177.00] on the Monday, then 180.70 / 185.95 / 193.90).

These pin the three properties that make the new field safe to instruct from.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_bhanushali_monitor import _window_fill, build_monitor  # noqa: E402


def _frame(rows: list[tuple[str, float]]) -> pd.DataFrame:
    """Daily bars as (date, open). Close tracks open — these tests only read the open."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d, _ in rows])
    opens = [o for _, o in rows]
    return pd.DataFrame({"Open": opens, "High": opens, "Low": opens, "Close": opens}, index=idx)


# The real JSWSTEEL card and its real opens, which is what made the defect visible.
JSW = _frame([
    ("2026-08-21", 1298.00),      # the signal's OWN session — issued at this close, not buyable
    ("2026-08-24", 1298.00),      # Monday: opens inside the band -> THE fill
    ("2026-08-25", 1326.00),
    ("2026-08-26", 1329.00),
    ("2026-08-27", 1351.00),
])
BAND = {"lo": 1293.7, "hi": 1310.6}


def test_a_window_that_filled_on_monday_still_says_so_on_thursday():
    fill = _window_fill(JSW, signal_date="2026-08-21", buy_window_until="2026-08-28", **BAND)
    assert fill == {"date": "2026-08-24", "open": 1298.0}


def test_the_signals_own_session_is_not_a_fill():
    """The card is issued at that close and executed at the NEXT open. Counting the signal
    session would book a fill a day before the reader could have acted on the instruction."""
    only_signal_day = _frame([("2026-08-21", 1298.00)])
    assert _window_fill(only_signal_day, signal_date="2026-08-21",
                        buy_window_until="2026-08-28", **BAND) is None


def test_a_session_after_the_window_closes_is_not_a_fill():
    late = _frame([("2026-08-21", 1400.0), ("2026-08-31", 1298.0)])   # in-band, but too late
    assert _window_fill(late, signal_date="2026-08-21", buy_window_until="2026-08-28", **BAND) is None


def test_a_window_that_never_opened_in_band_reports_nothing():
    gapped = _frame([("2026-08-21", 1298.0), ("2026-08-24", 1326.0), ("2026-08-25", 1351.0)])
    assert _window_fill(gapped, signal_date="2026-08-21", buy_window_until="2026-08-28", **BAND) is None


def test_the_first_in_band_open_wins_not_the_last():
    twice = _frame([("2026-08-21", 1400.0), ("2026-08-24", 1298.0), ("2026-08-25", 1305.0)])
    assert _window_fill(twice, signal_date="2026-08-21",
                        buy_window_until="2026-08-28", **BAND)["date"] == "2026-08-24"


# ── the published card ────────────────────────────────────────────────────────

def _card(**kw) -> dict:
    card = {"ticker": "JSWSTEEL", "signal_date": "2026-08-21", "status": "FRESH",
            "entry": 1293.7, "stop": 1250.4, "target": 1380.3,
            "entry_low": 1250.4, "entry_high": 1310.6,          # the signal WEEK's candle
            "buy_zone_low": 1293.7, "buy_zone_high": 1310.6,    # what the record buys inside
            "buy_window_until": "2026-08-28", "current_price": 1351.0}
    card.update(kw)
    return card


def test_the_monitor_publishes_the_fill_beside_the_today_only_flag():
    out = build_monitor({"generated_at": "2026-08-21", "signals": [_card()]}, {"JSWSTEEL": JSW})
    (rec,) = out["monitors"]
    assert rec["filled_today"] is False        # Thursday's open is far above the band — still true
    assert rec["window_filled"] is True        # … and no longer the whole story
    assert rec["filled_on"] == "2026-08-24"
    assert rec["filled_price"] == 1298.0


def test_the_band_is_the_buy_zone_not_the_signal_week_candle():
    """`entry_low` IS the stop. Using the candle as the band counts a fill AT the stop as a fill
    inside the zone — a trade the record would never have taken."""
    at_the_stop = _frame([("2026-08-21", 1400.0), ("2026-08-24", 1255.0)])   # inside the candle only
    out = build_monitor({"generated_at": "2026-08-21", "signals": [_card()]},
                        {"JSWSTEEL": at_the_stop})
    (rec,) = out["monitors"]
    assert rec["entry_low"] == 1293.7 and rec["entry_high"] == 1310.6
    assert rec["window_filled"] is False


def test_a_card_without_buy_zone_fields_falls_back_to_the_candle():
    """Cards written before the zone fields existed must keep working, not go silent."""
    old = _card()
    del old["buy_zone_low"], old["buy_zone_high"]
    out = build_monitor({"generated_at": "2026-08-21", "signals": [old]}, {"JSWSTEEL": JSW})
    (rec,) = out["monitors"]
    assert rec["entry_low"] == 1250.4 and rec["window_filled"] is True
