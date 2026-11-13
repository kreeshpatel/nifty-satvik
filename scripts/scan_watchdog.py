"""Scan watchdog: re-dispatch the weekly scanner when the latest completed week is not published.

Why: the Saturday 12:30 UTC cron (``cron-bhanushali-scanner.yml``) can fail, and until now the week
stayed lost until a human re-ran it (4 of the last 6 Saturdays). The scheduled workflow
``cron-scan-watchdog.yml`` calls this script, which decides whether to dispatch a re-run.

The decision (``decide``) is PURE: every input is passed in, nothing is read from the clock, the
network or the repo, so it is unit-tested in ``tests/test_scan_watchdog.py``.

Rules
-----
* Target = the last NSE session of the most recent ISO week that has fully closed as of ``now``.
  Weekends are not sessions, listed holidays are not, but ``SPECIAL_SESSIONS`` (Diwali Muhurat
  Sunday, Budget Saturday) are: ``config.NSE_HOLIDAYS`` lists only closures, so a weekend session
  has to be declared here (see nq/data/ohlcv.py: weekends are legitimate sessions).
* Published = ``results/signals_today_weekly.json`` ``generated_at`` (the last OHLCV bar the scan
  saw) is >= the target session date.
* Dispatch only if no scanner run is queued/in progress and fewer than ``MAX_ATTEMPTS``
  ``workflow_dispatch`` runs of the scanner have been created since the target session closed.
  Human dispatches count too, which is deliberately conservative. The cap is what guarantees the
  watchdog can never loop, whatever the scanner does.

Re-run safety (why a re-dispatch cannot corrupt a published week)
-----------------------------------------------------------------
* The scan is recomputed from inception every run (deterministic from the cached OHLCV), so a re-run
  over unchanged data rewrites byte-identical artifacts and ``git commit`` reports "no state change".
* ``run_bhanushali_cron._assert_data_advanced`` returns quietly when no NSE session has elapsed since
  the last published ``generated_at`` (same-day re-run) and raises ``StaleDataError`` when sessions
  elapsed but the panel did not advance, so a re-run never republishes stale data as fresh.
* The workflow's ``concurrency`` group (cancel-in-progress: false) serialises overlapping runs.
* The watchdog only dispatches when ``generated_at`` is behind the target, so it never re-runs an
  already-published week.

CLI:  python scripts/scan_watchdog.py [--dry-run] [--now ISO_UTC]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCANNER_WORKFLOW = "cron-bhanushali-scanner.yml"
SIGNALS_FILE = ROOT / "results" / "signals_today_weekly.json"
MAX_ATTEMPTS = 2

# Weekend/other special sessions that config.NSE_HOLIDAYS (closures only) cannot express.
# Diwali Muhurat is a ~1h evening session; Budget day falls on a Saturday/Sunday some years.
# Add each year's special sessions here when the holiday calendar is loaded.
SPECIAL_SESSIONS: dict[str, str] = {
    "2026-11-08": "Diwali Muhurat (Sunday)",
}
REGULAR_CLOSE_UTC = time(11, 0)      # 15:30 IST close + ~1h for vendor bars to settle
SPECIAL_CLOSE_UTC = time(14, 30)     # Muhurat ends ~19:15 IST; allow settling time


@dataclass(frozen=True)
class Decision:
    action: str                       # "noop" | "dispatch" | "skip"
    reason: str
    target_session: str | None = None
    attempts: int = 0


def is_session(d: date, holidays: set[str], special: dict[str, str] | None = None) -> bool:
    special = SPECIAL_SESSIONS if special is None else special
    iso = d.isoformat()
    if iso in special:
        return True
    return d.weekday() < 5 and iso not in holidays


def session_close(d: date, special: dict[str, str] | None = None) -> datetime:
    special = SPECIAL_SESSIONS if special is None else special
    t = SPECIAL_CLOSE_UTC if d.isoformat() in special else REGULAR_CLOSE_UTC
    return datetime.combine(d, t, tzinfo=timezone.utc)


def latest_completed_week_target(now: datetime, holidays: set[str],
                                 special: dict[str, str] | None = None) -> date | None:
    """Last session of the most recent ISO week whose final session has closed by ``now`` (UTC)."""
    monday = now.date() - timedelta(days=now.date().weekday())
    for back in range(0, 8):                                   # tolerate a run of closed weeks
        wk = monday - timedelta(weeks=back)
        sessions = [wk + timedelta(days=k) for k in range(7)
                    if is_session(wk + timedelta(days=k), holidays, special)]
        if sessions and session_close(sessions[-1], special) <= now:
            return sessions[-1]
    return None


def decide(*, now: datetime, generated_at: str | None, holidays: set[str],
           dispatch_run_times: list[datetime], scanner_active: bool,
           special: dict[str, str] | None = None, max_attempts: int = MAX_ATTEMPTS) -> Decision:
    """Pure decision. ``dispatch_run_times``: creation times (UTC) of scanner workflow_dispatch runs."""
    target = latest_completed_week_target(now, holidays, special)
    if target is None:
        return Decision("noop", "no completed trading week found")
    tgt = target.isoformat()
    if generated_at and str(generated_at)[:10] >= tgt:
        return Decision("noop", f"week ending {tgt} already published (generated_at={generated_at})", tgt)
    since = session_close(target, special)
    attempts = sum(1 for t in dispatch_run_times if t >= since)
    if scanner_active:
        return Decision("skip", f"week ending {tgt} unpublished but a scanner run is queued/in progress",
                        tgt, attempts)
    if attempts >= max_attempts:
        return Decision("skip", f"week ending {tgt} unpublished; attempt cap {max_attempts} reached "
                        "- needs a human", tgt, attempts)
    return Decision("dispatch", f"week ending {tgt} unpublished (generated_at={generated_at}); "
                    f"attempt {attempts + 1}/{max_attempts}", tgt, attempts)


# ── impure shell ──────────────────────────────────────────────────────────────────────────────

def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _read_generated_at(p: Path = SIGNALS_FILE) -> str | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("generated_at")
    except Exception:                                          # noqa: BLE001 - absent == unpublished
        return None


def _gh_runs() -> list[dict]:
    out = subprocess.run(
        ["gh", "run", "list", "--workflow", SCANNER_WORKFLOW, "--limit", "60",
         "--json", "event,status,createdAt"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--now", default=None, help="override clock, ISO UTC")
    a = ap.parse_args(argv)
    from config import NSE_HOLIDAYS, NSE_HOLIDAYS_COVERED_THROUGH
    now = _parse_ts(a.now) if a.now else datetime.now(timezone.utc)
    if now.date().isoformat() > NSE_HOLIDAYS_COVERED_THROUGH:
        print(f"::warning::holiday calendar ends {NSE_HOLIDAYS_COVERED_THROUGH}; watchdog assumes no holidays after")
    runs = _gh_runs()
    d = decide(
        now=now, generated_at=_read_generated_at(), holidays=set(NSE_HOLIDAYS),
        dispatch_run_times=[_parse_ts(r["createdAt"]) for r in runs if r.get("event") == "workflow_dispatch"],
        scanner_active=any(r.get("status") in ("queued", "in_progress", "waiting", "requested", "pending")
                           for r in runs))
    print(f"watchdog: {d.action} - {d.reason}")
    if d.action == "dispatch" and not a.dry_run:
        subprocess.run(["gh", "workflow", "run", SCANNER_WORKFLOW], check=True)
        print(f"dispatched {SCANNER_WORKFLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
