"""S2-F6 — the dead-man reads the Actions run log, not committed artifacts alone.

The bug this pins: `intraday-scan` fires every weekday and commits nothing, so an artifact-only
reconstruction reported it MISSING and dragged `overall` red on a healthy system. An alarm that is
red in the ordinary case stops being read, and will not be believed on the day it is right.

Firing truth is now the run log (constitution S2-F3); artifacts corroborate only. The API is
injected via `fetch` so these tests never touch the network.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scheduler_health import JOBS, _api_last_scheduled_success, scheduler_health  # noqa: E402

NOW = datetime(2026, 7, 30, 20, 0, tzinfo=timezone.utc)


def _fetch_all_fresh(url: str, headers: dict) -> dict:
    """Every workflow reports a successful scheduled run one hour ago."""
    return {"workflow_runs": [{"id": 12345, "run_started_at": (NOW - timedelta(hours=1))
                               .isoformat().replace("+00:00", "Z")}]}


def _fetch_empty(url: str, headers: dict) -> dict:
    return {"workflow_runs": []}


def _fetch_boom(url: str, headers: dict) -> dict:
    raise RuntimeError("network down")


# --- the S2-F6 regression itself ---------------------------------------------------------

def test_artifactless_job_is_green_from_the_run_log(tmp_path):
    """intraday-scan commits nothing; with run-log truth it must read OK, not MISSING."""
    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=_fetch_all_fresh)
    intraday = next(j for j in out["jobs"] if j["job"] == "intraday-scan")
    assert intraday["status"] == "OK"
    assert intraday["source"] == "run-log"
    assert intraday["run_id"] == 12345
    assert out["overall"] == "OK", "a healthy system must not report MISSING"


def test_overall_ok_with_no_artifacts_at_all(tmp_path):
    """An empty results dir + healthy run log = OK. Artifacts are corroboration, not evidence."""
    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=_fetch_all_fresh)
    assert out["overall"] == "OK"
    assert all(j["source"] == "run-log" for j in out["jobs"])
    assert out["source_of_truth"] == "actions-run-log"


# --- alarm semantics preserved ------------------------------------------------------------

def test_no_successful_scheduled_run_is_missing(tmp_path):
    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=_fetch_empty)
    assert out["overall"] == "MISSING"
    assert all(j["status"] == "MISSING" for j in out["jobs"])


def test_stale_run_is_overdue_for_its_own_cadence(tmp_path):
    """A run older than the job's cadence window is OVERDUE — semantics unchanged."""
    def fetch_stale(url, headers):
        return {"workflow_runs": [{"id": 7, "run_started_at": (NOW - timedelta(days=30))
                                   .isoformat().replace("+00:00", "Z")}]}

    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=fetch_stale)
    assert out["overall"] == "OVERDUE"
    assert all(j["status"] == "OVERDUE" for j in out["jobs"])


# --- graceful degradation -----------------------------------------------------------------

def test_no_token_falls_back_to_artifacts(tmp_path):
    out = scheduler_health(tmp_path, now_utc=NOW, token="", repo="o/r")
    assert out["source_of_truth"].startswith("artifacts-only")
    assert all(j["source"] in ("artifact", "none") for j in out["jobs"])


def test_api_failure_never_raises_and_falls_back(tmp_path):
    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=_fetch_boom)
    assert out["overall"] in {"OK", "OVERDUE", "MISSING"}
    assert all(j["source"] in ("artifact", "none") for j in out["jobs"])


def test_api_helper_returns_none_on_error():
    assert _api_last_scheduled_success("wf", token="t", repo="o/r", fetch=_fetch_boom) == (None, None)
    assert _api_last_scheduled_success("wf", token="t", repo="o/r", fetch=_fetch_empty) == (None, None)


def test_api_helper_parses_a_run():
    got, rid = _api_last_scheduled_success("wf", token="t", repo="o/r", fetch=_fetch_all_fresh)
    assert rid == 12345
    assert got == NOW - timedelta(hours=1)


# --- corroboration ------------------------------------------------------------------------

def test_artifact_far_newer_than_run_is_flagged_not_alarmed(tmp_path):
    """A hand-made artifact newer than the last scheduled run is surfaced, not treated as firing."""
    (tmp_path / "forward_accum_health.json").write_text(
        '{"bulkblock": {"last_fetch_ts": "2026-07-30 19:00:00"}}', encoding="utf-8")

    def fetch_old(url, headers):
        return {"workflow_runs": [{"id": 9, "run_started_at": "2026-07-30T06:00:00Z"}]}

    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=fetch_old)
    accum = next(j for j in out["jobs"] if j["job"] == "forward-accumulators")
    assert accum["source"] == "run-log", "the run log still decides"
    assert accum["artifact_corroborates"] is False, "13h newer than the run => not corroborating"
    assert accum["status"] == "OK", "a stale-looking artifact is not itself an alarm"


def test_every_job_is_reported(tmp_path):
    out = scheduler_health(tmp_path, now_utc=NOW, token="t", repo="o/r", fetch=_fetch_all_fresh)
    assert {j["job"] for j in out["jobs"]} == {s["job"] for s in JOBS}
    # S-F1 closed 2026-08-06: the forward wall gained a producer, so `unscheduled` is now empty.
    # The slot stays in the module as the place a FUTURE unscheduled producer must be declared —
    # what this asserts is that the list exists and no known job has silently fallen into it.
    assert out["unscheduled"] == [], f"an unscheduled producer has appeared: {out['unscheduled']}"


@pytest.mark.parametrize("bad", [None, {}, {"workflow_runs": None}])
def test_malformed_payloads_do_not_raise(tmp_path, bad):
    got = _api_last_scheduled_success("wf", token="t", repo="o/r", fetch=lambda u, h: bad)
    assert got == (None, None)
