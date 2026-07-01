"""T1-C: admin system-health cron block reads cron_health.json correctly.

The old panel read a 'cron_health' key from signals_today.json that the cron
never writes, so it was permanently UNKNOWN. _cron_health_block maps the real
cron_health.json fields and derives a staleness flag.
"""
from datetime import datetime, timedelta, timezone

from routers.admin import _cron_health_block

_NOW = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)


def test_empty_or_missing_is_unknown():
    assert _cron_health_block({}, _NOW)["status"] == "UNKNOWN"
    assert _cron_health_block(None, _NOW)["status"] == "UNKNOWN"


def test_maps_real_cron_health_fields():
    ch = {
        "last_run_at": "2026-06-15T10:45:00",  # naive UTC, 75 min before _NOW
        "status": "ok",
        "features_computed": 256,
        "signals_count": 0,
        "watchlist_count": 8,
        "macro_mode": "fresh",
        "macro_stale_days": 0,
        "ohlcv_stale_days": 0,
        "message": "",
    }
    b = _cron_health_block(ch, _NOW)
    assert b["status"] == "ok"
    assert b["last_run"] == "2026-06-15T10:45:00"
    assert b["features_computed"] == 256
    assert b["n_signals"] == 0
    assert b["watchlist_count"] == 8
    assert b["macro_mode"] == "fresh"
    assert b["ohlcv_stale_days"] == 0
    assert b["age_minutes"] == 75
    assert b["stale"] is False


def test_stale_when_last_run_is_old():
    old = (_NOW - timedelta(hours=40)).replace(tzinfo=None).isoformat()
    b = _cron_health_block({"last_run_at": old, "status": "ok"}, _NOW)
    assert b["stale"] is True
    # the cron's own status is preserved; staleness is a separate signal
    assert b["status"] == "ok"


def test_fresh_within_threshold_not_stale():
    recent = (_NOW - timedelta(hours=20)).replace(tzinfo=None).isoformat()
    b = _cron_health_block({"last_run_at": recent, "status": "ok"}, _NOW)
    assert b["stale"] is False


def test_bad_last_run_is_tolerated():
    b = _cron_health_block({"last_run_at": "not-a-date", "status": "degraded"}, _NOW)
    assert b["status"] == "degraded"
    assert b["age_minutes"] is None
    assert b["stale"] is False
