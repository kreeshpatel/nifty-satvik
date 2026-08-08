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
    # S-F1 closed 2026-08-06: the 3-book forward wall finally has a scheduled producer.
    # THE PROOF IS DELIBERATELY NOT THE WALL LOG. `forward/prereg.md` says decisions happen only at
    # quarterly reviews — between them, log and leave it alone — so the health probe must never open
    # `forward_wall.csv`. It stats the paper book's state file instead, which the same job rewrites
    # every run: `kind: "mtime"` never reads a byte of content, so liveness is observed without
    # anyone learning how the wall is doing.
    {"job": "forward-wall-log", "workflow": "cron-forward-wall", "cadence": "weekday",
     "proof": "paper_portfolio.json", "kind": "mtime", "overdue_days": 5},
]

# Jobs that SHOULD have a producer but have no scheduled trigger in the repo. Reported as a
# standing gap without reading the artifact (the forward-wall log is not read, per the no-peek rule).
UNSCHEDULED: list[dict] = [
    # Empty since 2026-08-06 (S-F1 closed — `.github/workflows/cron-forward-wall.yml`). Kept as a
    # standing slot: the check that matters is not "is this list short" but "does every producer in
    # the repo appear in JOBS above", and a future unscheduled producer belongs here, not nowhere.
]


DEFAULT_REPO = "kreeshpatel/nifty-satvik"


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _api_last_scheduled_success(workflow: str, *, token: str, repo: str,
                                fetch=None) -> tuple[datetime | None, int | None]:
    """Most recent SUCCESSFUL scheduled run of one workflow, from the Actions run log.

    This is the primary source of firing truth (constitution flag S2-F3: firing evidence is the run
    log, never a committed artifact alone). Returns (started_utc, run_id), or (None, None) when the
    API is unreachable or the workflow has no successful scheduled run.

    `fetch` is injectable for tests: a callable(url, headers) -> parsed JSON.
    """
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}.yml/runs"
           "?event=schedule&status=success&per_page=1")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "User-Agent": "nifty-satvik-scheduler-health"}
    try:
        if fetch is None:
            import urllib.request

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 — fixed https host
                payload = json.loads(resp.read().decode("utf-8"))
        else:
            payload = fetch(url, headers)
        runs = payload.get("workflow_runs") or []
        if not runs:
            return None, None
        run = runs[0]
        stamp = run.get("run_started_at") or run.get("created_at")
        if not stamp:
            return None, run.get("id")
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")), run.get("id")
    except Exception:  # noqa: BLE001 — a health probe must never raise into the monitor
        return None, None


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


def scheduler_health(results_dir: Path, now_utc: datetime | None = None, *,
                     token: str | None = None, repo: str | None = None, fetch=None) -> dict:
    """Reconstruct each scheduled job's last firing and flag jobs overdue for their own cadence.

    Source of truth is the **Actions run log** (S2-F3: a committed artifact is not firing evidence,
    because a human can produce the same artifact by hand). The artifact reconstruction is retained
    as *corroboration* and as the fallback when no token is available (local runs, or a token
    lacking `actions:read`).

    This is what closes S2-F6: `intraday-scan` fires every weekday but commits nothing, so the
    artifact-only reconstruction reported it MISSING and dragged `overall` red on a healthy system —
    an alarm that is red in the normal case stops being read.
    """
    now = now_utc or datetime.now(timezone.utc)
    import os

    token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    repo = repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO

    rows = []
    worst = "OK"
    for spec in JOBS:
        art_last = _last_fired(Path(results_dir), spec)
        run_last, run_id = (None, None)
        if token:
            run_last, run_id = _api_last_scheduled_success(spec["workflow"], token=token,
                                                           repo=repo, fetch=fetch)

        # run log wins; artifact is corroboration / fallback
        last = run_last or art_last
        source = "run-log" if run_last else ("artifact" if art_last else "none")

        if last is None:
            status, age_days = "MISSING", None
        else:
            age_days = round((now - last).total_seconds() / 86400.0, 2)
            status = "OVERDUE" if age_days > spec["overdue_days"] else "OK"

        corroborated = None
        if run_last and art_last:
            # artifact should not be far NEWER than the last successful scheduled run; if it is,
            # something wrote the artifact outside the cron (a hand run) — worth surfacing, not alarming.
            corroborated = (art_last - run_last).total_seconds() <= 6 * 3600

        rows.append({
            "job": spec["job"], "workflow": spec["workflow"], "cadence": spec["cadence"],
            "proof": spec["proof"], "source": source, "run_id": run_id,
            "last_fired_utc": last.isoformat() if last else None,
            "artifact_last_utc": art_last.isoformat() if art_last else None,
            "artifact_corroborates": corroborated,
            "age_days": age_days, "overdue_after_days": spec["overdue_days"], "status": status,
        })
        if status == "MISSING":
            worst = "MISSING"
        elif status == "OVERDUE" and worst != "MISSING":
            worst = "OVERDUE"
    return {
        "checked_utc": now.isoformat(),
        "overall": worst,
        "source_of_truth": "actions-run-log" if token else "artifacts-only (no token)",
        "jobs": rows,
        "unscheduled": UNSCHEDULED,
        "note": ("Dead-man reconstruction produced by the daily monitor (the proven weekday "
                 "heartbeat). Firing truth is the Actions run log; committed artifacts corroborate "
                 "only. If THIS block's checked_utc is itself stale, the monitor has stopped and "
                 "every downstream freshness claim is suspect."),
    }
