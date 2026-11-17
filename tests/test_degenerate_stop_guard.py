"""The degenerate-stop guard (owner amendment 2026-11-17): a stop inside 0.5% of entry is a data error.

The guard refuses the signal, says so RED in the health report, and lists it. These tests hold the three
properties the amendment promises: it fires below the floor, it is invisible above the floor, and a clean scan
publishes exactly what it published before the guard existed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

import run_bhanushali_cron as C  # noqa: E402
import scan_health as H  # noqa: E402

SRC = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")


def test_the_floor_is_the_value_the_amendment_names():
    assert C.MIN_STOP_DISTANCE == 0.005


def test_the_guard_runs_before_the_card_is_built_not_after():
    """A signal refused after the card exists would still reach the dashboard."""
    i = SRC.index("if entry - stop < MIN_STOP_DISTANCE * entry:")
    j = SRC.index('signals.append({', i - 4000)
    assert i < j, "the guard must sit above the append that creates the card"


@pytest.mark.parametrize(
    "entry,stop,refused",
    [(100.0, 99.6, True),      # 0.40% apart -> inside the floor
     (100.0, 99.5, False),     # exactly 0.50% -> passes; the amendment makes the floor exclusive
     (100.0, 99.4, False),     # 0.60% apart -> an ordinary tight stop, untouched
     (676.74, 676.69, True),   # the historical case, VMART 2019-05-06, a Rs 0.05 basis
     (100.0, 100.0, True),     # zero distance
     (100.0, 101.0, True),     # stop above entry: the same failure
     (100.0, 90.0, False)],    # an ordinary 10% stop
)
def test_the_predicate_fires_exactly_where_the_amendment_says(entry, stop, refused):
    assert ((entry - stop) < C.MIN_STOP_DISTANCE * entry) is refused


def test_the_health_check_is_green_when_no_file_exists(tmp_path):
    r = H.check_degenerate_stops(path=tmp_path / "absent.json")
    assert (r.status, r.ok, r.findings) == (H.GREEN, True, [])


def test_the_health_check_is_red_and_names_the_ticker_entry_and_stop(tmp_path):
    p = tmp_path / "degenerate_stops.json"
    p.write_text(json.dumps({"as_of": "2026-11-21T12:00:00Z", "threshold_pct": 0.5, "refused": [
        {"ticker": "VMART", "signal_date": "2026-11-20", "entry": 676.74, "stop": 676.69,
         "stop_distance_pct": 0.0074, "signal_week_low": 676.69}]}), encoding="utf-8")
    r = H.check_degenerate_stops(path=p)
    assert r.status == H.RED and len(r.findings) == 1
    m = r.findings[0].message
    assert "VMART" in m and "676.74" in m and "676.69" in m
    assert r.findings[0].key == "degenerate-stop:VMART|2026-11-20"


def test_an_unreadable_record_is_amber_not_a_crash(tmp_path):
    p = tmp_path / "degenerate_stops.json"
    p.write_text("{not json", encoding="utf-8")
    r = H.check_degenerate_stops(path=p)
    assert r.status == H.AMBER and r.ok is False


def test_the_check_is_registered_in_the_runner():
    assert "degenerate-stop" in [n for n, _ in H.CHECKS]


def test_a_clean_scan_publishes_nothing_new():
    """The envelope key and the file are both omitted when the guard refuses nothing, so a scan with the guard
    is byte-identical to one without it. This is the condition the owner set for wiring it."""
    assert 'if degenerate:' in SRC and '"degenerate_stops"] = degenerate' in SRC
    assert 'elif _degen.exists():' in SRC and '_degen.unlink()' in SRC
