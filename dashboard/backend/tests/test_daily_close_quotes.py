"""Quote endpoints serve the last COMPLETED daily close, cached until 16:00 IST.

Live quotes were removed (2026-11-02) so the Fly machine can suspend; these
tests pin the two pieces of logic that keep an intraday price from leaking in.
"""
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from routers.yahoo_finance import (
    _fresh_since_close,
    _last_close_boundary,
    _quote_from_daily_bars,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _ist(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=IST)


# 2026-11-02 is a Monday.
def test_boundary_after_settle_is_today():
    assert _last_close_boundary(_ist(2026, 11, 2, 17)) == _ist(2026, 11, 2, 16)


def test_boundary_during_market_is_previous_trading_day():
    # Monday 11:00 IST → Friday 16:00 IST (skips the weekend).
    assert _last_close_boundary(_ist(2026, 11, 2, 11)) == _ist(2026, 10, 30, 16)


def test_boundary_on_weekend_is_friday():
    assert _last_close_boundary(_ist(2026, 11, 1, 20)) == _ist(2026, 10, 30, 16)


def test_boundary_accepts_utc_input():
    # 10:31 UTC = 16:01 IST Monday.
    utc = datetime(2026, 11, 2, 10, 31, tzinfo=timezone.utc)
    assert _last_close_boundary(utc) == _ist(2026, 11, 2, 16)


def test_cache_entry_stale_after_next_close():
    written = _ist(2026, 10, 30, 18).timestamp()  # Friday evening
    assert _fresh_since_close(written, _ist(2026, 11, 2, 11))   # Mon intraday: still Friday's close
    assert not _fresh_since_close(written, _ist(2026, 11, 2, 17))  # Mon after close: refresh


def _bars(rows):
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d, *_ in rows])
    return pd.DataFrame(
        [r[1:] for r in rows], index=idx,
        columns=["Open", "High", "Low", "Close", "Volume"],
    )


def test_quote_drops_todays_forming_bar():
    bars = _bars([
        ("2026-10-29", 100, 105, 99, 102.0, 1000),
        ("2026-10-30", 102, 110, 101, 108.0, 2000),
        ("2026-11-02", 108, 120, 107, 119.0, 500),   # intraday, must be ignored
    ])
    q = _quote_from_daily_bars(bars, date(2026, 10, 30))
    assert q["last_price"] == 108.0
    assert q["previous_close"] == 102.0
    assert q["change"] == 6.0
    assert q["change_pct"] == round(6 / 102 * 100, 2)
    assert q["as_of"] == "2026-10-30"
    assert q["high"] == 110.0 and q["volume"] == 2000.0


def test_quote_single_bar_has_no_change():
    q = _quote_from_daily_bars(_bars([("2026-10-30", 1, 2, 1, 1.5, 10)]), date(2026, 10, 30))
    assert q["last_price"] == 1.5
    assert q["previous_close"] is None and q["change"] is None


def test_quote_empty_or_all_future_is_none():
    assert _quote_from_daily_bars(pd.DataFrame(), date(2026, 10, 30)) is None
    future = _bars([("2026-11-02", 1, 2, 1, 1.5, 10)])
    assert _quote_from_daily_bars(future, date(2026, 10, 30)) is None
