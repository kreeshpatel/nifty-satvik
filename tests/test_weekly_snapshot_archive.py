"""Append-only archive + drift detection for the weekly-swing record — constitution D2.

The record is recomputed from inception every Saturday, so it can silently rewrite its own past
when the inputs move. These tests pin the two properties that make that measurable instead of
invisible: snapshots are write-once, and a retroactively changed closed trade is DETECTED as a
restatement rather than absorbed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import archive_weekly_snapshot as A  # noqa: E402


def _write_record(d: Path, *, as_of: str, trades: list, nav: float):
    d.mkdir(parents=True, exist_ok=True)
    (d / "signals_today_weekly.json").write_text(
        json.dumps({"generated_at": as_of, "signals": []}), encoding="utf-8")
    (d / "signals_history_weekly.json").write_text(json.dumps(trades), encoding="utf-8")
    (d / "paper_portfolio_weekly.json").write_text(
        json.dumps({"total_value": nav}), encoding="utf-8")
    (d / "signal_analytics_weekly.json").write_text(
        json.dumps({"total_closed": len([t for t in trades if t.get("status") != "ACTIVE"])}),
        encoding="utf-8")


def _trade(tkr, sig_date, entry, close_px, r, status="HIT_TARGET", close_date="2026-05-01"):
    return {"ticker": tkr, "signal_date": sig_date, "entry": entry, "close_price": close_px,
            "close_date": close_date, "r_multiple": r, "status": status, "exit_reason": "targets"}


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Redirect the archive at a temp tree so tests never touch the real record."""
    arch = tmp_path / "archive"
    monkeypatch.setattr(A, "ARCHIVE_DIR", arch)
    monkeypatch.setattr(A, "DRIFT_LOG", arch / "drift_log.jsonl")
    monkeypatch.setattr(A, "input_fingerprint", lambda _rd: {"stub": True})
    return tmp_path


def test_first_snapshot_is_clean_and_logged(sandbox):
    res = sandbox / "results"
    _write_record(res, as_of="2026-07-24", trades=[_trade("AAA", "2026-03-06", 100.0, 120.0, 2.0)],
                  nav=1_000_000.0)
    d = A.archive(res, baseline=True)
    assert d["prev_snapshot"] is None and d["clean"] is True and d["is_baseline"] is True
    assert (A.ARCHIVE_DIR / "2026-07-24" / "signals_history_weekly.json").exists()
    assert (A.ARCHIVE_DIR / "2026-07-24" / "input_fingerprint.json").exists()
    assert len(A.DRIFT_LOG.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_snapshots_are_write_once(sandbox):
    """Re-running the same as-of must NOT overwrite the existing dated snapshot."""
    res = sandbox / "results"
    _write_record(res, as_of="2026-07-24", trades=[_trade("AAA", "2026-03-06", 100.0, 120.0, 2.0)],
                  nav=1_000_000.0)
    A.archive(res)
    original = json.loads((A.ARCHIVE_DIR / "2026-07-24" / "signals_history_weekly.json")
                          .read_text(encoding="utf-8"))

    # same week recomputed with a DIFFERENT past — the original must survive untouched
    _write_record(res, as_of="2026-07-24", trades=[_trade("AAA", "2026-03-06", 100.0, 111.0, 1.1)],
                  nav=990_000.0)
    d = A.archive(res)
    assert d["cur_snapshot"].startswith("2026-07-24__rerun-")
    still = json.loads((A.ARCHIVE_DIR / "2026-07-24" / "signals_history_weekly.json")
                       .read_text(encoding="utf-8"))
    assert still == original, "an existing dated snapshot was overwritten — archive is not write-once"


def test_retroactive_restatement_is_detected(sandbox):
    """A closed trade whose price/R changes after the fact is the exact D2 failure mode."""
    res = sandbox / "results"
    _write_record(res, as_of="2026-07-17", trades=[_trade("AAA", "2026-03-06", 100.0, 120.0, 2.0)],
                  nav=1_000_000.0)
    A.archive(res)
    _write_record(res, as_of="2026-07-24",
                  trades=[_trade("AAA", "2026-03-06", 50.0, 60.0, 2.0)],   # e.g. a 1:2 split re-adjust
                  nav=1_010_000.0)
    d = A.archive(res)

    assert d["clean"] is False
    assert d["n_restated"] == 1
    changed = d["restated"][0]["changed"]
    assert changed["entry"] == [100.0, 50.0]
    assert changed["close_price"] == [120.0, 60.0]
    assert d["nav_delta"] == pytest.approx(10_000.0)


def test_vanished_and_appeared_trades_are_flagged(sandbox):
    res = sandbox / "results"
    _write_record(res, as_of="2026-07-17",
                  trades=[_trade("AAA", "2026-03-06", 100.0, 120.0, 2.0),
                          _trade("BBB", "2026-03-13", 200.0, 180.0, -1.0, status="HIT_STOP")],
                  nav=1_000_000.0)
    A.archive(res)
    _write_record(res, as_of="2026-07-24",
                  trades=[_trade("AAA", "2026-03-06", 100.0, 120.0, 2.0),
                          _trade("CCC", "2026-04-10", 300.0, 330.0, 1.5)],
                  nav=1_000_000.0)
    d = A.archive(res)

    assert d["vanished"] == ["BBB|2026-03-13"], "a disappeared past trade must be flagged"
    assert d["appeared"] == ["CCC|2026-04-10"]
    assert d["clean"] is False


def test_unchanged_history_reports_clean(sandbox):
    """A week that only ADDS a new closed trade is normal accrual, not a restatement."""
    res = sandbox / "results"
    old = [_trade("AAA", "2026-03-06", 100.0, 120.0, 2.0)]
    _write_record(res, as_of="2026-07-17", trades=old, nav=1_000_000.0)
    A.archive(res)
    _write_record(res, as_of="2026-07-24",
                  trades=[*old, _trade("DDD", "2026-05-01", 400.0, 460.0, 1.8)], nav=1_060_000.0)
    d = A.archive(res)

    assert d["n_restated"] == 0 and d["n_vanished"] == 0
    assert d["appeared"] == ["DDD|2026-05-01"]
    assert d["closed_delta"] == 1
    assert d["clean"] is True


def test_active_positions_are_not_treated_as_closed_trades(sandbox):
    """Open marks move every week by design; only CLOSED trades can be 'restated'."""
    res = sandbox / "results"
    _write_record(res, as_of="2026-07-17",
                  trades=[_trade("AAA", "2026-03-06", 100.0, 118.0, 1.8, status="ACTIVE")],
                  nav=1_000_000.0)
    A.archive(res)
    _write_record(res, as_of="2026-07-24",
                  trades=[_trade("AAA", "2026-03-06", 100.0, 131.0, 3.1, status="ACTIVE")],
                  nav=1_030_000.0)
    d = A.archive(res)
    assert d["n_restated"] == 0 and d["clean"] is True
