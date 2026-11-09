"""At-signal capture of the quality axes must not depend on the Saturday archive.

A signal whose Saturday scan failed used to be archived already ACTIVE with no axes, permanently.
`capture_signal_axes` logs them to a write-once file from the panel itself, and the collector reads
that file when the archive lacks them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import collect_signal_quality_forward as Q  # noqa: E402
import run_bhanushali_cron as C  # noqa: E402
import signal_axes_capture as SAC  # noqa: E402


def _panel(rank=0.8123456):
    """One name, two weeks of daily bars; signal Friday 2026-10-09, week opened Mon 2026-10-05."""
    dates = pd.bdate_range("2026-10-05", "2026-10-16")        # 10 sessions
    n = len(dates)
    o = [100.0 + i for i in range(n)]
    c = [100.5 + i for i in range(n)]
    fri_idx = 4                                                # 2026-10-09
    s = {"dates": [str(d.date()) for d in dates], "o": o, "c": c,
         "last_signal": {"fri_idx": fri_idx, "lo": 98.0, "hi": 108.0, "rank": rank}}
    return {"TESTCO": s}, fri_idx


def _card(P, fri_idx):
    """The FRESH card's axes, taken from the card path's own helpers (build_envelopes' calls)."""
    s = P["TESTCO"]
    ls = s["last_signal"]
    lo, hi = ls["lo"], ls["hi"]
    g = C._buy_guidance(103.0, lo, hi, *C._sig_week_oc(s, ls["fri_idx"]))
    return {"body_ratio": g["body_ratio"], "signal_conviction": g["signal_conviction"],
            "crs_rank": round(float(ls.get("rank", 0.0)), 4)}


def test_capture_equals_the_fresh_card_values(tmp_path):
    P, fri = _panel()
    log = tmp_path / "signal_axes_capture.jsonl"
    new = C.capture_signal_axes(P, None, "2026-10-10", "weekly_scan", path=log)
    assert len(new) == 1
    got = SAC.load_capture(log)[("TESTCO", "2026-10-09")]
    want = _card(P, fri)
    for k in ("body_ratio", "signal_conviction", "crs_rank"):
        assert got[k] == want[k], k


def test_same_value_whether_captured_saturday_or_a_later_day(tmp_path):
    """The inputs are signal-week bars + the stored rank, so a mid-window capture reads the same."""
    P, _ = _panel()
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    C.capture_signal_axes(P, None, "2026-10-10", "weekly_scan", path=a)
    C.capture_signal_axes(P, None, "2026-10-14", "capture_only", path=b)
    ra, rb = (SAC.load_capture(x)[("TESTCO", "2026-10-09")] for x in (a, b))
    assert {k: ra[k] for k in SAC.CAPTURE_FIELDS} == {k: rb[k] for k in SAC.CAPTURE_FIELDS}


def test_write_once_first_write_wins(tmp_path):
    P, _ = _panel(rank=0.5)
    log = tmp_path / "signal_axes_capture.jsonl"
    C.capture_signal_axes(P, None, "2026-10-10", "weekly_scan", path=log)
    before = log.read_bytes()
    P2, _ = _panel(rank=0.9)                                   # a later run sees a different rank
    assert C.capture_signal_axes(P2, None, "2026-10-13", "capture_only", path=log) == []
    assert log.read_bytes() == before, "an existing key must never be rewritten"
    assert SAC.load_capture(log)[("TESTCO", "2026-10-09")]["crs_rank"] == 0.5


def test_retroactive_signal_outside_its_entry_window_is_not_captured(tmp_path):
    """ADR-0017 style: a past signal placed in a past week is a backfill, which the prereg forbids."""
    P, _ = _panel()
    log = tmp_path / "signal_axes_capture.jsonl"
    assert C.capture_signal_axes(P, None, "2026-10-20", "weekly_scan", path=log) == []
    assert not log.exists()


def test_a_torn_line_is_skipped_not_repaired(tmp_path):
    log = tmp_path / "signal_axes_capture.jsonl"
    log.write_text('{"ticker": "A", "signal_date": "2026-10-09", "body_ratio": 0.5}\n{"ticker": "B", "sig',
                   encoding="utf-8")
    assert list(SAC.load_capture(log)) == [("A", "2026-10-09")]


def test_collector_takes_axes_from_capture_when_the_archive_lacks_them(tmp_path, monkeypatch):
    """A signal archived already ACTIVE (its Saturday scan failed) carries no axes in the archive."""
    res = tmp_path / "results"
    snap = res / "archive" / "2026-10-16"
    snap.mkdir(parents=True)
    (snap / "signals_today_weekly.json").write_text(json.dumps({"signals": [
        {"ticker": "TESTCO", "signal_date": "2026-10-09", "status": "ACTIVE", "grade": "A",
         "entry": 100.0, "stop": 92.0},                         # no body_ratio / conviction / crs_rank
        {"ticker": "FULLCO", "signal_date": "2026-10-09", "status": "FRESH", "grade": "A",
         "body_ratio": 0.4, "signal_conviction": "normal", "crs_rank": 0.7},
    ]}), encoding="utf-8")
    SAC.append_write_once(SAC.capture_path(res), [
        {"ticker": "TESTCO", "signal_date": "2026-10-09", "body_ratio": 0.55,
         "signal_conviction": "normal", "crs_rank": 0.8123},
        {"ticker": "FULLCO", "signal_date": "2026-10-09", "body_ratio": 0.99,
         "signal_conviction": "low", "crs_rank": 0.1},
    ])
    monkeypatch.setattr(Q, "ARCHIVE", res / "archive")
    monkeypatch.setattr(Q, "RESULTS_DIR", res)
    eps = Q._first_fresh_flags()
    t = eps[("TESTCO", "2026-10-09")]
    assert (t["body_ratio"], t["signal_conviction"], t["crs_rank"]) == (0.55, "normal", 0.8123)
    f = eps[("FULLCO", "2026-10-09")]                           # archive value wins over the capture
    assert (f["body_ratio"], f["crs_rank"]) == (0.4, 0.7)
