"""The history-truncation guard: a shortened vendor series must halt, not erase an open trade.

Regression for 2026-10-03 (HEG): the vendor served HEG.NS from 2026-07-17 only, the 44-week SMA could
not form, and the from-inception rebuild deleted the open trade while the run reported success.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nq.data import history_guard as H  # noqa: E402


def _series(start: str, end: str = "2026-10-01") -> pd.DataFrame:
    idx = pd.bdate_range(start, end)
    return pd.DataFrame({"Close": range(len(idx))}, index=idx)


def test_the_heg_replay_halts():
    """Exactly the 2026-10-03 shape: full history before, 2026-07-17 onward after, trade open."""
    prev = H.history_starts({"HEG": _series("2015-01-01")})
    with pytest.raises(ValueError, match="HEG: short"):
        H.assert_open_history_intact(prev, {"HEG": _series("2026-07-17")}, {"HEG"}, acknowledged={})


def test_truncation_without_an_open_trade_is_reported_not_raised():
    prev = H.history_starts({"AAA": _series("2015-01-01")})
    rep = H.assert_open_history_intact(prev, {"AAA": _series("2024-01-01")}, set(), acknowledged={})
    assert [d["symbol"] for d in rep["truncated"]] == ["AAA"] and rep["escalate"] == []


def test_a_truncated_but_still_long_open_series_halts():
    """Enough weeks for the SMA, but the start moved: the rebuild can still rewrite the entry."""
    prev = H.history_starts({"BBB": _series("2015-01-01")})
    with pytest.raises(ValueError, match="BBB: truncated"):
        H.assert_open_history_intact(prev, {"BBB": _series("2023-01-01")}, {"BBB"}, acknowledged={})


def test_a_missing_open_series_halts():
    with pytest.raises(ValueError, match="CCC: missing"):
        H.assert_open_history_intact({}, {}, {"CCC"}, acknowledged={})


def test_vendor_wobble_and_an_intact_book_pass():
    prev = H.history_starts({"DDD": _series("2015-01-01")})
    rep = H.assert_open_history_intact(prev, {"DDD": _series("2015-01-20")}, {"DDD"}, acknowledged={})
    assert rep["truncated"] == [] and rep["escalate"] == []


def test_an_owner_acknowledgement_silences_only_that_name():
    prev = H.history_starts({"HEG": _series("2015-01-01"), "EEE": _series("2015-01-01")})
    cur = {"HEG": _series("2026-07-17"), "EEE": _series("2026-07-17")}
    with pytest.raises(ValueError) as e:
        H.assert_open_history_intact(prev, cur, {"HEG", "EEE"}, acknowledged={"HEG": "2026-10-13 test"})
    assert "EEE" in str(e.value) and "HEG:" not in str(e.value)


def test_open_names_come_from_both_the_book_and_the_tracker(tmp_path):
    """HEG was erased from the TRACKER's history — the book alone would have missed it."""
    (tmp_path / "paper_portfolio_weekly.json").write_text(json.dumps({"positions": {"CUB": {}}}), encoding="utf-8")
    (tmp_path / "signals_history_weekly.json").write_text(json.dumps(
        [{"ticker": "HEG", "status": "ACTIVE"}, {"ticker": "OLD", "status": "HIT_STOP"}]), encoding="utf-8")
    assert H.open_tickers(tmp_path) == {"CUB", "HEG"}


def test_the_registry_starts_empty_and_every_entry_is_dated():
    for k, v in H.ACKNOWLEDGED.items():
        assert pd.Timestamp(v.split()[0]), f"{k}: an acknowledgement must start with its date"


def test_the_cron_runs_the_guard_outside_the_download_try():
    """Inside the try, a raise would print 'download failed ... using cached bars' and carry on."""
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    body = src[src.index("def _refresh_ohlcv"):src.index("def _detect_readjusted")]
    assert "prev_starts = history_starts(ohlcv)" in body
    guard_at = body.index("assert_open_history_intact(prev_starts")
    assert guard_at > body.index("except Exception as exc"), "the guard must run after the try/except"
    assert body.index("prev_starts = history_starts(ohlcv)") < body.index("download_ohlcv(cold"), \
        "the baseline must be taken before any download"
