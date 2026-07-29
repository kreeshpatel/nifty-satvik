"""Dead-man's-switch reconstruction for every scheduled job — constitution scheduler appendix.

The problem this solves: each cron writes its own artifact, but nothing checks that the OTHER jobs
are still firing. If the Saturday scanner, the accumulators, or the D2 archive silently stop, the
only human-facing signal today is the dashboard's `cron_health` banner — which watches ONLY the
weekly envelope and is miscalibrated for the weekly cadence (see the appendix). A job that stops
firing is invisible until someone notices missing data by eye.

The fix rides the one job proven to fire every weekday — the daily monitor
(`cron-bhanushali-monitor`, 8/8 recent firings). This module reconstructs, from each job's committed
proof-artifact, when it last ran, and flags any job overdue for its own cadence. The monitor calls
it and folds the result into `weekly_monitor.json`, so the reconstruction runs daily on a proven
heartbeat with no new service. If the monitor itself dies, the whole file's `generated_utc` goes
stale — the backend can detect a dead heartbeat from that single timestamp.

Pure and read-only: it reads artifact mtimes and a couple of freshness fields; it NEVER reads the
forward-wall log (that job is reported as a static known-gap — it has no scheduled producer in the
repo — without opening its file). Nothing here changes any strategy behaviour.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# job -> proof artifact + cadence. `overdue_days` is a CADENCE-AWARE coarse bound that already
# absorbs weekends and GitHub-Actions best-effort delay (measured ~1.5-3.7h): a weekday job checked
# the following Monday after a Friday firing is 3 days old, so 4-5 days is "healthy but quiet";
# a weekly Saturday job gets a full week + grace. The monitor re-runs every weekday, so a real gap
# is caught within a day or two of opening.
JOBS = [
    {"job": "weekly-scanner", "workflow": "cron-bhanushali-scanner", "cadence": "weekly (Sat)",
     "proof": "signals_today_weekly.json", "kind": "envelope", "overdue_days": 9},
    {"job": "forward-accumulators", "workflow": "cron-bhanushali-monitor", "cadence": "weekday",
     "proof": "forward_accum_health.json", "kind": "accum", "overdue_days": 5},
    {"job": "review-scorecard", "workflow": "cron-bhanushali-scanner", "cadence": "weekly (Sat)",
     "proof": "weekly_review_scorecard.json", "kind": "mtime", "overdue_days": 9},
    {"job": "d2-archive", "workflow": "cron-bhanushali-scanner", "cadence": "weekly (Sat)",
     "proof": "archive", "kind": "archive_dir", "overdue_days": 9},
    {"job": "intraday-scan", "workflow": "cron-intraday-scan", "cadence": "weekday",
     "proof": "intraday_scan", "kind": "dir", "overdue_days": 5},
]

# Jobs that SHOULD have a producer but have no scheduled trigger in the repo. Reported as a
# standing gap without reading the artifact (the forward-wall log is not read, per the no-peek rule).
UNSCHEDULED = [
    {"job": "forward-wall-log", "producer": "scripts/run_paper_cron.py -> nq.paper.wall_cron.update_wall",
     "note": "no GitHub Actions workflow invokes run_paper_cron.py; the 3-book wall log has no "
             "scheduled producer in the repo (momentum sleeve is suspended — owner door)."},
]


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _last_fired(results_dir: Path, spec: dict) -> datetime | None:
    """Best available 'last fired' timestamp for one job's proof artifact (UTC), or None if absent."""
    p = results_dir / spec["proof"]
    kind = spec["kind"]
    try:
        if kind == "envelope":
            if not p.exists():
                return None
            raw = json.loads(p.read_text(encoding="utf-8"))
            g = raw.get("generated_at")
            # generated_at is the DATA date (a Friday), not the run time — a lower bound on freshness,
            # which is the conservative choice for a dead-man (never reports fresher than reality).
            if g:
                try:
                    return datetime.fromisoformat(str(g)).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if kind == "accum":
            if not p.exists():
                return None
            raw = json.loads(p.read_text(encoding="utf-8"))
            stamps = []
            for feed in raw.values():
                fetch = feed.get("last_fetch_ts") if isinstance(feed, dict) else None
                if fetch:
                    try:
                        stamps.append(datetime.strptime(fetch, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc))
                    except ValueError:
                        pass
            return max(stamps) if stamps else datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if kind in ("archive_dir", "dir"):
            if not p.exists() or not p.is_dir():
                return None
            children = [c for c in p.iterdir() if not c.name.startswith(".")]
            if not children:
                return None
            return datetime.fromtimestamp(max(c.stat().st_mtime for c in children), tz=timezone.utc)
        # plain mtime
        if p.exists():
            return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    except Exception:  # noqa: BLE001 — a health probe must never raise into the monitor
        return None
    return None


def scheduler_health(results_dir: Path, now_utc: datetime | None = None) -> dict:
    """Reconstruct each scheduled job's last firing from its committed artifact and flag overdue
    jobs. Pure except for reading artifact mtimes/fields under ``results_dir``."""
    now = now_utc or datetime.now(timezone.utc)
    rows = []
    worst = "OK"
    for spec in JOBS:
        last = _last_fired(Path(results_dir), spec)
        if last is None:
            status, age_days = "MISSING", None
        else:
            age_days = round((now - last).total_seconds() / 86400.0, 2)
            status = "OVERDUE" if age_days > spec["overdue_days"] else "OK"
        rows.append({
            "job": spec["job"], "workflow": spec["workflow"], "cadence": spec["cadence"],
            "proof": spec["proof"], "last_fired_utc": last.isoformat() if last else None,
            "age_days": age_days, "overdue_after_days": spec["overdue_days"], "status": status,
        })
        if status == "MISSING":
            worst = "MISSING"
        elif status == "OVERDUE" and worst != "MISSING":
            worst = "OVERDUE"
    return {
        "checked_utc": now.isoformat(),
        "overall": worst,
        "jobs": rows,
        "unscheduled": UNSCHEDULED,
        "note": ("Dead-man reconstruction from committed artifacts, produced by the daily monitor "
                 "(the proven weekday heartbeat). If THIS block's checked_utc is itself stale, the "
                 "monitor has stopped and every downstream freshness claim is suspect."),
    }
