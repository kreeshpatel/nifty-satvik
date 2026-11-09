"""scripts/scan_health.py: classification, no-skip behaviour, issue dedupe (mocked gh), JSON schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scan_health as H  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml"


def _runner(code, out):
    return lambda args: (code, out)


# ---------------------------------------------------------------- classification
def test_history_restatement_is_red():
    out = "::error::history changed undeclared (restated): ABC|2026-08-31 at as_of 2026-11-07 - declare it"
    r = H.check_history_drift(_runner(1, out))
    assert r.status == H.RED
    assert r.findings[0].key == "history-drift:restated:ABC|2026-08-31"
    assert r.findings[0].severity == H.RED


def test_vanished_trade_is_red_and_clean_history_is_green():
    out = "::error::history changed undeclared (vanished): XYZ|2026-09-01 at as_of 2026-11-07 - x"
    assert H.check_history_drift(_runner(1, out)).findings[0].key == "history-drift:vanished:XYZ|2026-09-01"
    assert H.check_history_drift(_runner(0, "history drift: ok")).status == H.GREEN


def test_crashed_governance_check_is_red_not_a_pass():
    r = H.check_history_drift(_runner(2, "Traceback ..."))
    assert r.status == H.RED and r.ok is False


def test_signal_quality_hole_is_amber_per_signal():
    out = ("::error::PHOENIXLTD 2026-08-24 is missing body_ratio and is not declared. x\n"
           "::error::FOO 2026-09-07 is missing crs_rank and is not declared. x\n")
    r = H.check_signal_quality(_runner(1, out))
    assert r.status == H.AMBER
    assert [f.key for f in r.findings] == ["signal-quality-axes:PHOENIXLTD|2026-08-24",
                                           "signal-quality-axes:FOO|2026-09-07"]
    assert H.check_signal_quality(_runner(0, "fine")).status == H.GREEN


def test_logger_classification_side_books_amber_capital_book_red():
    msgs = ["blend_hybrid_paper.json last logged 2026-10-30 but the scan is 2026-11-06",
            "signal_quality_forward.csv has no rows",
            "brain/position_log.csv.gz last stamped 2026-10-30 but the scan is 2026-11-06",
            "no results/signals_today_weekly.json - cannot tell which week this is"]
    r = H.check_loggers(lambda: msgs)
    sev = {f.key: f.severity for f in r.findings}
    assert sev["logger:blend_hybrid_paper.json"] == H.AMBER
    assert sev["logger:signal_quality_forward.csv"] == H.AMBER
    assert sev["logger:brain/position_log.csv.gz"] == H.RED
    assert sev["logger:no-scan-file"] == H.RED
    assert r.status == H.RED
    assert H.check_loggers(lambda: []).status == H.GREEN


def test_calendar_amber_with_runway_red_once_expired():
    run = lambda left: _runner(1, f"::error::NSE holiday calendar ends 2026-12-31 ({left} days). Run x")
    assert H.check_calendar(run(20)).status == H.AMBER
    assert H.check_calendar(run(-3)).status == H.RED
    assert H.check_calendar(_runner(0, "calendar coverage: ok")).status == H.GREEN


def test_overall_is_worst_of():
    g = H.CheckResult("a", "", H.GREEN, True, 0)
    a = H.CheckResult("b", "", H.AMBER, True, 1, [H.Finding("k", H.AMBER, "m")])
    r = H.CheckResult("c", "", H.RED, True, 1, [H.Finding("k2", H.RED, "m")])
    assert H.overall([g]) == H.GREEN and H.overall([g, a]) == H.AMBER and H.overall([g, a, r]) == H.RED


# ---------------------------------------------------------------- no-skip
def test_a_raising_check_does_not_skip_later_checks():
    ran = []

    def boom():
        ran.append("boom")
        raise RuntimeError("kaboom")

    def after():
        ran.append("after")
        return H.CheckResult("after", "", H.GREEN, True, 0)

    res = H.run_all([("first", lambda: H.CheckResult("first", "", H.RED, True, 1, [H.Finding("k", H.RED, "m")])),
                     ("boom", boom), ("history-drift", boom), ("after", after)])
    assert ran == ["boom", "boom", "after"]
    assert len(res) == 4
    by = {r.name: r for r in res}
    assert by["boom"].status == H.AMBER and by["boom"].ok is False
    assert by["history-drift"].status == H.RED, "a crashed governance check must not read as a pass"


def test_red_early_does_not_hide_later_amber(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "CHECKS", [
        ("history-drift", lambda: H.check_history_drift(_runner(1, "::error::history changed undeclared (restated): A|d at as_of x"))),
        ("signal-quality-axes", lambda: H.check_signal_quality(_runner(1, "::error::T 2026-08-24 is missing body_ratio and"))),
    ])
    out = tmp_path / "h.json"
    assert H.main(["--no-issues", "--out", str(out)]) == 1
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["status"] == "RED" and rep["counts"] == {**rep["counts"], "red": 1, "amber": 1}


def test_amber_only_run_exits_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "CHECKS", [
        ("signal-quality-axes", lambda: H.check_signal_quality(_runner(1, "::error::T 2026-08-24 is missing body_ratio and")))])
    assert H.main(["--no-issues", "--out", str(tmp_path / "h.json")]) == 0


# ---------------------------------------------------------------- issue dedupe
def _res(findings, name="signal-quality-axes", ok=True):
    st = H.AMBER if findings else H.GREEN
    return H.CheckResult(name, "", st, ok, 1 if findings else 0, findings)


def _existing(f, check="signal-quality-axes", number=7, as_of="W1", labels=("scan-health", "scan-health:amber")):
    return {"number": number, "title": H.TITLE_PREFIX + f.key, "body": H.issue_body(f, check, as_of),
            "labels": [{"name": n} for n in labels]}


def test_new_problem_creates_one_issue():
    f = H.Finding("signal-quality-axes:T|2026-08-24", H.AMBER, "m")
    acts = H.reconcile([], [_res([f])], "W1")
    assert [(a["action"], a["key"]) for a in acts] == [("create", f.key)]
    assert acts[0]["title"] == "[scan-health] " + f.key and "scan-health" in acts[0]["labels"]


def test_existing_unchanged_issue_is_not_duplicated_or_touched():
    f = H.Finding("signal-quality-axes:T|2026-08-24", H.AMBER, "m")
    assert H.reconcile([_existing(f)], [_res([f])], "W1") == []


def test_existing_issue_is_updated_not_duplicated_when_content_changes():
    f = H.Finding("signal-quality-axes:T|2026-08-24", H.AMBER, "m")
    acts = H.reconcile([_existing(f, as_of="W1")], [_res([f])], "W2")
    assert [(a["action"], a["number"]) for a in acts] == [("update", 7)]


def test_severity_escalation_swaps_label():
    f = H.Finding("k", H.RED, "m")
    acts = H.reconcile([_existing(H.Finding("k", H.AMBER, "m"), "c")], [_res([f], "c")], "W1")
    assert acts[0]["action"] == "update" and acts[0]["add_label"] == "scan-health:red"
    assert acts[0]["remove_labels"] == ["scan-health:amber"]


def test_cleared_condition_closes_issue():
    f = H.Finding("signal-quality-axes:T|2026-08-24", H.AMBER, "m")
    acts = H.reconcile([_existing(f)], [_res([])], "W2")
    assert [(a["action"], a["number"]) for a in acts] == [("close", 7)]


def test_crashed_check_never_auto_closes_its_issues():
    f = H.Finding("signal-quality-axes:T|2026-08-24", H.AMBER, "m")
    assert H.reconcile([_existing(f)], [_res([], ok=False)], "W2") == []


def test_sync_issues_drives_gh_with_mock():
    calls = []
    f = H.Finding("signal-quality-axes:T|2026-08-24", H.AMBER, "m")
    stale = _existing(H.Finding("signal-quality-axes:GONE|2026-01-01", H.AMBER, "old"), number=9)

    def gh(args):
        calls.append(args)
        if args[:2] == ["issue", "list"]:
            return 0, json.dumps([stale])
        return 0, ""

    done = H.sync_issues([_res([f])], "W1", gh=gh)
    assert {(d["action"], d["key"]) for d in done} == {
        ("create", f.key), ("close", "signal-quality-axes:GONE|2026-01-01")}
    assert any(c[:2] == ["issue", "create"] for c in calls)
    assert any(c[:3] == ["issue", "close", "9"] for c in calls)


def test_gh_failure_never_raises_and_is_recorded():
    done = H.sync_issues([_res([H.Finding("k", H.AMBER, "m")])], "W1", gh=lambda a: (1, "nope"))
    assert done == [{"action": "skipped", "key": "*", "reason": "gh issue list failed"}]


# ---------------------------------------------------------------- schema
def test_report_schema():
    f = H.Finding("k", H.AMBER, "m")
    rep = H.build_report([_res([f])], [{"action": "create", "key": "k"}], True)
    assert set(rep) == {"schema_version", "generated_at", "scan_as_of", "status", "counts", "checks", "issues"}
    assert rep["schema_version"] == 1 and rep["status"] in ("RED", "AMBER", "GREEN")
    assert set(rep["counts"]) == {"red", "amber", "checks_green", "checks_total"}
    c = rep["checks"][0]
    assert set(c) == {"name", "description", "status", "ok", "exit_code", "duration_s", "findings"}
    assert set(c["findings"][0]) == {"key", "severity", "message"}
    assert set(rep["issues"]) == {"enabled", "actions"}
    json.dumps(rep)
    assert "## Scan health: AMBER" in H.render_summary(rep)


# ---------------------------------------------------------------- wiring
def test_workflow_uses_single_runner_that_cannot_withhold_the_week():
    wf = WORKFLOW.read_text(encoding="utf-8")
    run_at = wf.index("python scripts/scan_health.py")
    commit_at = wf.index("- name: Commit weekly paper state")
    # Runner sits before the commit so the report is published with the week, but cannot block it ...
    assert run_at < commit_at
    block = wf[wf.index("- name: Scan health"):commit_at]
    assert "continue-on-error: true" in block and "id: health" in block
    # ... and RED is enforced by a read-only gate after the publish.
    gate_at = wf.index("- name: Fail the run on RED scan health")
    gate = wf[gate_at:]
    assert gate_at > commit_at
    assert gate.index("steps.health.outcome == 'failure'") < gate.index("exit 1")
    assert "git " not in gate, "the gate must be read-only"
    assert "opt results/scan_health.json" in wf
    assert "issues: write" in wf
    assert "!cancelled()" in wf, "the health step must still run when an earlier step failed"
    for old in ("python scripts/check_weekly_loggers.py", "python scripts/check_history_drift.py",
                "python scripts/check_calendar_coverage.py"):
        assert old not in wf, f"{old} must run via the health runner, not as its own step"


def test_runner_covers_every_legacy_check():
    src = (ROOT / "scripts" / "scan_health.py").read_text(encoding="utf-8")
    for s in ("collect_signal_quality_forward.py", "check_weekly_loggers", "check_history_drift.py",
              "check_calendar_coverage.py"):
        assert s in src


def test_report_is_whitelisted_and_contracted():
    assert "!results/scan_health.json" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    d = json.loads((ROOT / "results" / "output_contracts.json").read_text(encoding="utf-8"))
    scanner = next(c for c in d["contracts"] if c["job"] == "weekly-scanner")
    assert "results/scan_health.json" in scanner["must_update_if_produced"]
