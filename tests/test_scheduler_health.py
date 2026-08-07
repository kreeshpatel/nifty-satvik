"""Dead-man's-switch reconstruction — constitution scheduler appendix.

Pins the behaviour the audit relies on: a job whose artifact is fresh reads OK, a job whose
artifact is overdue for its cadence reads OVERDUE, a missing artifact reads MISSING, the
forward-wall is scheduled but its LOG is never opened, and a probe fault never raises.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scheduler_health import scheduler_health  # noqa: E402

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def _write(sd: Path):
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "signals_today_weekly.json").write_text(
        json.dumps({"generated_at": "2026-07-25", "signals": []}), encoding="utf-8")   # 5d old, weekly OK
    (sd / "forward_accum_health.json").write_text(
        json.dumps({"bulkblock": {"last_fetch_ts": "2026-07-29 21:00:00"}}), encoding="utf-8")  # 1d old
    (sd / "weekly_review_scorecard.json").write_text("{}", encoding="utf-8")
    arch = sd / "archive" / "2026-07-25"
    arch.mkdir(parents=True, exist_ok=True)
    (arch / "snapshot_meta.json").write_text("{}", encoding="utf-8")
    (sd / "intraday_scan").mkdir(exist_ok=True)
    (sd / "intraday_scan" / "scan.json").write_text("{}", encoding="utf-8")
    # the forward-wall job's liveness proof: the paper book state, stat-only. NOT the wall log.
    (sd / "paper_portfolio.json").write_text("{}", encoding="utf-8")


def test_fresh_artifacts_read_ok(tmp_path):
    _write(tmp_path)
    h = scheduler_health(tmp_path, now_utc=NOW)
    by = {j["job"]: j for j in h["jobs"]}
    assert by["weekly-scanner"]["status"] == "OK"          # 5d < 9d weekly bound
    assert by["forward-accumulators"]["status"] == "OK"
    assert h["overall"] in ("OK", "OVERDUE", "MISSING")    # depends on tmp mtimes for scorecard/dir
    # the scorecard/archive/intraday were just written, so their mtime is ~now => OK
    assert by["review-scorecard"]["status"] == "OK"
    assert by["d2-archive"]["status"] == "OK"
    assert by["intraday-scan"]["status"] == "OK"
    assert h["overall"] == "OK"


def test_overdue_scanner_is_flagged(tmp_path):
    _write(tmp_path)
    # a scanner that last produced data 12 days ago (two missed Saturdays) must trip OVERDUE
    (tmp_path / "signals_today_weekly.json").write_text(
        json.dumps({"generated_at": "2026-07-18", "signals": []}), encoding="utf-8")
    h = scheduler_health(tmp_path, now_utc=NOW)
    by = {j["job"]: j for j in h["jobs"]}
    assert by["weekly-scanner"]["status"] == "OVERDUE"
    assert by["weekly-scanner"]["age_days"] > 9
    assert h["overall"] == "OVERDUE"


def test_missing_artifact_reads_missing(tmp_path):
    _write(tmp_path)
    (tmp_path / "forward_accum_health.json").unlink()
    h = scheduler_health(tmp_path, now_utc=NOW)
    by = {j["job"]: j for j in h["jobs"]}
    assert by["forward-accumulators"]["status"] == "MISSING"
    assert by["forward-accumulators"]["last_fired_utc"] is None
    assert h["overall"] == "MISSING"


def test_forward_wall_is_scheduled_and_its_log_is_never_opened(tmp_path):
    """S-F1 closed 2026-08-06 — the wall now has a producer, so it moved from `unscheduled` into
    `jobs`. The no-peek rule survives the move: the probe stats the paper state file, and must never
    read `forward_wall.csv`. `forward/prereg.md` — between quarterly reviews, log and leave it alone.
    """
    _write(tmp_path)
    (tmp_path / "forward_wall.csv").write_text(
        "date,base_ret\n2026-08-06,0.01\n", encoding="utf-8")
    h = scheduler_health(tmp_path, now_utc=NOW)
    by = {j["job"]: j for j in h["jobs"]}
    assert "forward-wall-log" in by, "the wall must now be a scheduled job, not a standing gap"
    assert not any(u["job"] == "forward-wall-log" for u in h["unscheduled"])
    assert "forward_wall" not in json.dumps(by["forward-wall-log"]), (
        "the health probe must not name or read the wall log — it stats the paper state file")
    assert by["forward-wall-log"]["status"] == "OK"


def test_accumulator_uses_fetch_ts_not_mtime(tmp_path):
    """The accumulator health carries an explicit fetch timestamp; the probe must prefer it over the
    file mtime (which is ~now on a fresh checkout and would mask a stale feed)."""
    _write(tmp_path)
    (tmp_path / "forward_accum_health.json").write_text(
        json.dumps({"bulkblock": {"last_fetch_ts": "2026-07-10 21:00:00"}}), encoding="utf-8")  # 20d old
    h = scheduler_health(tmp_path, now_utc=NOW)
    by = {j["job"]: j for j in h["jobs"]}
    assert by["forward-accumulators"]["status"] == "OVERDUE"
    assert by["forward-accumulators"]["age_days"] > 5


def test_probe_never_raises_on_garbage(tmp_path):
    _write(tmp_path)
    (tmp_path / "signals_today_weekly.json").write_text("{ not json", encoding="utf-8")
    h = scheduler_health(tmp_path, now_utc=NOW)          # must not raise
    by = {j["job"]: j for j in h["jobs"]}
    # unparseable envelope falls back to mtime (just written) => OK, but crucially no exception
    assert by["weekly-scanner"]["status"] in ("OK", "OVERDUE", "MISSING")
