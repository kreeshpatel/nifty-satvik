"""One health runner for the weekly scan: run EVERY post-commit check, classify, report, file issues.

Before this, the scanner ended in a chain of red-on-failure steps. The first failure skipped every later
one, so the owner never saw the full picture, and an amber condition (a watched side-book a day behind, a
declared-able measurement loss) looked identical to "the live cards are wrong". This runs all checks, none
able to skip another, and sorts each finding into one of three classes:

  RED    the live cards or the paper book are wrong or unpublished, or a governance tripwire fired
         (a closed trade's history was restated). Fails the run.
  AMBER  forward-evidence or bookkeeping problems that need a decision. The run stays green; one GitHub
         issue per problem key is opened/updated, and auto-closed when the condition clears.
  GREEN  nothing to report.

The checks themselves are untouched: the three script checks are run as subprocesses (their own exit code
and ::error:: lines are the signal) and the logger check is called as a function so its per-logger
messages can be classified individually. This module only changes how their outcomes are SURFACED.

    python scripts/scan_health.py                 # run, write results/scan_health.json, file issues
    python scripts/scan_health.py --no-issues     # local: no `gh` calls
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "scan_health.json"
SCHEMA_VERSION = 1
RED, AMBER, GREEN = "RED", "AMBER", "GREEN"
LABEL = "scan-health"
TITLE_PREFIX = "[scan-health] "
KEY_MARKER = "scan-health-key"
CHECK_MARKER = "scan-health-check"
SUBPROCESS_TIMEOUT_S = 300


@dataclass
class Finding:
    key: str            # stable dedupe key, e.g. "history-drift:restated:ABC|2026-08-31"
    severity: str       # RED | AMBER
    message: str


@dataclass
class CheckResult:
    name: str
    description: str
    status: str                                  # RED | AMBER | GREEN (worst finding)
    ok: bool                                     # False when the check itself crashed / timed out
    exit_code: int | None
    findings: list[Finding] = field(default_factory=list)
    duration_s: float = 0.0


# --------------------------------------------------------------------------------------- subprocess
def _run_script(args: list[str]) -> tuple[int | None, str]:
    """Run a check script; returns (exit code or None on timeout/launch failure, combined output)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=SUBPROCESS_TIMEOUT_S, env=env)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {SUBPROCESS_TIMEOUT_S}s"
    except OSError as exc:
        return None, f"could not launch: {exc}"
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _errors(output: str) -> list[str]:
    return [ln.split("::error::", 1)[1].strip() for ln in output.splitlines() if "::error::" in ln]


def _echo(out: str) -> None:
    print(out, end="" if out.endswith("\n") else "\n")


def _crash(name: str, code: int | None, output: str, severity: str) -> Finding:
    tail = " | ".join(output.strip().splitlines()[-3:]) if output.strip() else "no output"
    return Finding(f"check-crashed:{name}", severity,
                   f"the {name} check itself did not complete (exit {code}); its verdict is UNKNOWN. {tail}")


def _worst(fs: list[Finding]) -> str:
    if any(f.severity == RED for f in fs):
        return RED
    return AMBER if fs else GREEN


# --------------------------------------------------------------------------------------- the checks
def check_signal_quality(runner: Callable = _run_script) -> CheckResult:
    """AMBER. An undeclared axis hole is a lost forward MEASUREMENT: the live cards are unaffected, and
    the remedy is a decision (declare it in KNOWN_INCOMPLETE, or fix the capture)."""
    name = "signal-quality-axes"
    desc = "forward signal-quality axes recorded at signal time"
    code, out = runner(["scripts/collect_signal_quality_forward.py", "--validate"])
    _echo(out)
    if code not in (0, 1):
        fs = [_crash(name, code, out, AMBER)]
        return CheckResult(name, desc, _worst(fs), False, code, fs)
    fs: list[Finding] = []
    for msg in _errors(out):
        m = re.match(r"(\S+) (\d{4}-\d{2}-\d{2}) is missing", msg)
        if m:
            fs.append(Finding(f"{name}:{m.group(1)}|{m.group(2)}", AMBER, msg))
    if code == 1 and not fs:
        fs.append(Finding(f"{name}:failed", AMBER,
                          "collector --validate failed: " + " | ".join(_errors(out) or ["no detail"])))
    return CheckResult(name, desc, _worst(fs), True, code, fs)


# Logger messages begin with the artifact name. The capital book's own streams are the paper-book record
# and cannot be rebuilt, so a stale one is RED; the watched side books and the research table are
# forward evidence for a decision, so AMBER.
RED_LOGGER_PREFIXES = ("brain/", "no results/signals_today_weekly.json")


def classify_logger_problem(msg: str) -> Finding:
    if msg.startswith("no results/signals_today_weekly.json"):
        return Finding("logger:no-scan-file", RED, msg)
    token = msg.split(" ", 1)[0]
    sev = RED if msg.startswith(RED_LOGGER_PREFIXES) else AMBER
    return Finding(f"logger:{token}", sev, msg)


def check_loggers(problems_fn: Callable[[], list[str]] | None = None) -> CheckResult:
    name = "watched-book-loggers"
    desc = "side-book + capital-book streams advanced to this scan"
    try:
        if problems_fn is None:
            sys.path.insert(0, str(ROOT / "scripts"))
            import check_weekly_loggers as L
            problems_fn = L.check
        problems = problems_fn()
    except Exception as exc:                          # noqa: BLE001 - a crashed check must not skip the rest
        f = Finding(f"check-crashed:{name}", AMBER, f"logger check raised {type(exc).__name__}: {exc}")
        return CheckResult(name, desc, AMBER, False, None, [f])
    fs = [classify_logger_problem(p) for p in problems]
    for p in problems:
        print(f"{name}: {p}")
    if not fs:
        print(f"{name}: all advanced")
    return CheckResult(name, desc, _worst(fs), True, 1 if fs else 0, fs)


def check_history_drift(runner: Callable = _run_script) -> CheckResult:
    """RED, always. The weekly history is rebuilt from inception; a restated or vanished CLOSED trade means
    the published record of the past changed. This is a governance tripwire: only its surfacing moved."""
    name = "history-drift"
    desc = "closed-trade history unchanged unless declared"
    code, out = runner(["scripts/check_history_drift.py"])
    _echo(out)
    if code not in (0, 1):
        fs = [_crash(name, code, out, RED)]       # an unreadable governance check is not a pass
        return CheckResult(name, desc, _worst(fs), False, code, fs)
    fs: list[Finding] = []
    for msg in _errors(out):
        m = re.match(r"history changed undeclared \((\w+)\): (\S+) at as_of", msg)
        fs.append(Finding(f"{name}:{m.group(1)}:{m.group(2)}" if m else f"{name}:undeclared", RED, msg))
    if code == 1 and not fs:
        fs.append(Finding(f"{name}:undeclared", RED, "history drift check failed with no parsable detail"))
    return CheckResult(name, desc, _worst(fs), True, code, fs)


def check_calendar(runner: Callable = _run_script) -> CheckResult:
    """AMBER while there is runway (the 30-day lead exists to leave time for a decision); RED once the
    calendar has actually run out, because holiday-shortened weeks can then be mis-dated on live cards."""
    name = "calendar-coverage"
    desc = "NSE holiday calendar has runway"
    code, out = runner(["scripts/check_calendar_coverage.py"])
    _echo(out)
    if code not in (0, 1):
        fs = [_crash(name, code, out, AMBER)]
        return CheckResult(name, desc, _worst(fs), False, code, fs)
    fs: list[Finding] = []
    if code == 1:
        m = re.search(r"\((-?\d+) days\)", out)
        left = int(m.group(1)) if m else None
        sev = RED if left is not None and left < 0 else AMBER
        msg = (_errors(out) or ["holiday calendar about to run out"])[0]
        fs.append(Finding(f"{name}:expiring", sev, msg))
    return CheckResult(name, desc, _worst(fs), True, code, fs)


CHECKS: list[tuple[str, Callable[[], CheckResult]]] = [
    ("signal-quality-axes", check_signal_quality),
    ("watched-book-loggers", check_loggers),
    ("history-drift", check_history_drift),
    ("calendar-coverage", check_calendar),
]


def run_all(checks=None) -> list[CheckResult]:
    """Run every check. A check that raises is recorded as a crash and the loop continues."""
    results: list[CheckResult] = []
    for name, fn in (checks if checks is not None else CHECKS):
        t0 = time.time()
        try:
            r = fn()
        except Exception as exc:                      # noqa: BLE001 - never let one check skip another
            sev = RED if name == "history-drift" else AMBER
            f = Finding(f"check-crashed:{name}", sev, f"{name} raised {type(exc).__name__}: {exc}")
            r = CheckResult(name, name, sev, False, None, [f])
        r.duration_s = round(time.time() - t0, 2)
        results.append(r)
    return results


# --------------------------------------------------------------------------------------- report
def overall(results: list[CheckResult]) -> str:
    if any(r.status == RED for r in results):
        return RED
    return AMBER if any(r.status == AMBER for r in results) else GREEN


def scan_as_of() -> str | None:
    p = ROOT / "results" / "signals_today_weekly.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("generated_at")
    except Exception:                                  # noqa: BLE001
        return None


def build_report(results: list[CheckResult], issue_actions: list[dict] | None = None,
                 issues_enabled: bool = False) -> dict:
    findings = [f for r in results for f in r.findings]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scan_as_of": scan_as_of(),
        "status": overall(results),
        "counts": {"red": sum(f.severity == RED for f in findings),
                   "amber": sum(f.severity == AMBER for f in findings),
                   "checks_green": sum(r.status == GREEN for r in results),
                   "checks_total": len(results)},
        "checks": [{"name": r.name, "description": r.description, "status": r.status, "ok": r.ok,
                    "exit_code": r.exit_code, "duration_s": r.duration_s,
                    "findings": [{"key": f.key, "severity": f.severity, "message": f.message}
                                 for f in r.findings]} for r in results],
        "issues": {"enabled": issues_enabled, "actions": issue_actions or []},
    }


def render_summary(report: dict) -> str:
    lines = [f"## Scan health: {report['status']}", "",
             f"Scan as-of `{report.get('scan_as_of')}` - {report['counts']['red']} red, "
             f"{report['counts']['amber']} amber finding(s).", "",
             "| check | status | findings |", "|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | {len(c['findings'])} |")
    for c in report["checks"]:
        for f in c["findings"]:
            lines += ["", f"- **{f['severity']}** `{f['key']}`: {f['message']}"]
    acts = report["issues"]["actions"]
    if acts:
        lines += ["", "Issues: " + ", ".join(f"{a['action']} `{a['key']}`" for a in acts)]
    elif not report["issues"]["enabled"]:
        lines += ["", "Issue filing was not enabled for this run."]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------- issues
def _marker(kind: str, value: str) -> str:
    return f"<!-- {kind}: {value} -->"


def issue_body(f: Finding, check: str, as_of: str | None) -> str:
    return (f"{_marker(KEY_MARKER, f.key)}\n{_marker(CHECK_MARKER, check)}\n\n"
            f"**Class: {f.severity}** - raised by the weekly scan health runner "
            f"(`scripts/scan_health.py`), last seen at scan as-of `{as_of}`.\n\n{f.message}\n\n"
            f"This issue is opened and updated automatically, one per problem key, and closes itself "
            f"when the condition clears. Resolve it by acting on the finding (declare a measurement "
            f"loss, fix the capture, or declare a history restatement), not by closing it by hand.\n")


def parse_marker(body: str, kind: str) -> str | None:
    m = re.search(rf"<!--\s*{kind}:\s*(.*?)\s*-->", body or "")
    return m.group(1) if m else None


def reconcile(open_issues: list[dict], results: list[CheckResult], as_of: str | None) -> list[dict]:
    """Pure: decide create / update / close from the open issues and this run's results.

    * one issue per key (an existing open issue with the key is updated, never duplicated);
    * only keys of checks that COMPLETED may be auto-closed - a crashed check proves nothing cleared.
    """
    by_key: dict[str, dict] = {}
    for i in open_issues:
        k = parse_marker(i.get("body", ""), KEY_MARKER)
        if k and k not in by_key:
            by_key[k] = i
    active: dict[str, tuple[Finding, str]] = {}
    for r in results:
        for f in r.findings:
            active[f.key] = (f, r.name)
    completed = {r.name for r in results if r.ok}
    actions: list[dict] = []
    for key, (f, check) in sorted(active.items()):
        body = issue_body(f, check, as_of)
        sev_label = f"{LABEL}:{f.severity.lower()}"
        ex = by_key.get(key)
        if ex is None:
            actions.append({"action": "create", "key": key, "severity": f.severity,
                            "title": TITLE_PREFIX + key, "body": body, "labels": [LABEL, sev_label]})
        else:
            names = {lb["name"] if isinstance(lb, dict) else lb for lb in ex.get("labels", [])}
            if ex.get("body", "").strip() != body.strip() or sev_label not in names:
                actions.append({"action": "update", "key": key, "severity": f.severity,
                                "number": ex["number"], "body": body, "add_label": sev_label,
                                "remove_labels": [f"{LABEL}:{s}" for s in ("red", "amber")
                                                  if f"{LABEL}:{s}" != sev_label]})
    for key, ex in sorted(by_key.items()):
        if key in active:
            continue
        if parse_marker(ex.get("body", ""), CHECK_MARKER) in completed:
            actions.append({"action": "close", "key": key, "number": ex["number"],
                            "comment": "Condition cleared at the latest scan; closing automatically."})
    return actions


def _gh(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sync_issues(results: list[CheckResult], as_of: str | None,
                gh: Callable[[list[str]], tuple[int, str]] = _gh) -> list[dict]:
    """Apply reconcile() through `gh`. Best effort: an issue-API failure is reported, never raised."""
    for name, color, desc in ((LABEL, "d93f0b", "weekly scan health finding"),
                              (f"{LABEL}:red", "b60205", "scan health: live cards / paper book / governance"),
                              (f"{LABEL}:amber", "fbca04", "scan health: forward-evidence or bookkeeping decision")):
        gh(["label", "create", name, "--color", color, "--description", desc, "--force"])
    rc, out = gh(["issue", "list", "--label", LABEL, "--state", "open", "--limit", "200",
                  "--json", "number,title,body,labels"])
    if rc != 0:
        print(f"::warning::scan-health could not list issues ({out.strip()[:200]}); not filing this run")
        return [{"action": "skipped", "key": "*", "reason": "gh issue list failed"}]
    try:
        open_issues = json.loads(out or "[]")
    except json.JSONDecodeError:
        return [{"action": "skipped", "key": "*", "reason": "gh issue list returned non-JSON"}]
    done: list[dict] = []
    for a in reconcile(open_issues, results, as_of):
        if a["action"] == "create":
            args = ["issue", "create", "--title", a["title"], "--body", a["body"]]
            for lb in a["labels"]:
                args += ["--label", lb]
        elif a["action"] == "update":
            args = ["issue", "edit", str(a["number"]), "--body", a["body"], "--add-label", a["add_label"]]
            for lb in a["remove_labels"]:
                args += ["--remove-label", lb]
        else:
            args = ["issue", "close", str(a["number"]), "--comment", a["comment"]]
        rc, out = gh(args)
        done.append({"action": a["action"], "key": a["key"], "ok": rc == 0,
                     **({"number": a["number"]} if "number" in a else {})})
        if rc != 0:
            print(f"::warning::scan-health issue {a['action']} failed for {a['key']}: {out.strip()[:200]}")
    return done


# --------------------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-issues", action="store_true", help="do not call `gh` (local runs)")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)

    results = run_all()
    issues_enabled = not a.no_issues and bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    actions = sync_issues(results, scan_as_of()) if issues_enabled else []
    report = build_report(results, actions, issues_enabled)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = render_summary(report)
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as fh:
            fh.write(summary)
    print(summary)
    for r in results:
        for f in r.findings:
            print(f"::{'error' if f.severity == RED else 'warning'}::[{f.severity}] {f.key}: {f.message}")
    return 1 if report["status"] == RED else 0


if __name__ == "__main__":
    raise SystemExit(main())
