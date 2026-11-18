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


def test_a_missing_record_is_amber_because_the_guard_cannot_be_shown_to_have_run(tmp_path):
    """The scan writes the record on every run, so an absent file is NOT a clean scan - it is no evidence."""
    r = H.check_degenerate_stops(path=tmp_path / "absent.json")
    assert (r.status, r.ok) == (H.AMBER, True)
    assert [f.key for f in r.findings] == ["degenerate-stop:not-run"]
    assert "NO RECORD" in r.note


def test_a_clean_record_is_green_and_still_reports_that_the_guard_ran(tmp_path):
    """Owner request 2026-11-17: the health report says the guard ran even when it refused nothing."""
    p = tmp_path / "degenerate_stops.json"
    p.write_text(json.dumps({"as_of": "2026-11-21T12:00:00Z", "threshold_pct": 0.5, "ran": True,
                             "n_candidates": 12, "n_refused": 0, "refused": []}), encoding="utf-8")
    r = H.check_degenerate_stops(path=p)
    assert (r.status, r.findings) == (H.GREEN, [])
    assert r.note == "degenerate-stop guard: ran, 0 refused (threshold 0.5% of entry, 12 candidate(s) checked)"


def test_the_guard_line_reaches_the_rendered_summary(tmp_path):
    p = tmp_path / "degenerate_stops.json"
    p.write_text(json.dumps({"as_of": "2026-11-21T12:00:00Z", "threshold_pct": 0.5, "ran": True,
                             "n_candidates": 12, "n_refused": 0, "refused": []}), encoding="utf-8")
    txt = H.render_summary(H.build_report([H.check_degenerate_stops(path=p)]))
    assert "degenerate-stop guard: ran, 0 refused" in txt


def test_the_scan_writes_the_record_on_every_run(tmp_path):
    """No `if refusals:` around the write, and no unlink path: the record is unconditional."""
    assert '"n_refused": len(_refused)' in SRC and '"ran": True' in SRC
    assert "_degen.unlink()" not in SRC


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
    """The envelope key is omitted when the guard refuses nothing, so every PUBLISHED card payload is
    byte-identical to one built without the guard. This is the condition the owner set for wiring it. The
    separate degenerate_stops.json record is written either way and is not one of those payloads."""
    assert 'if degenerate:' in SRC and '"degenerate_stops"] = degenerate' in SRC
