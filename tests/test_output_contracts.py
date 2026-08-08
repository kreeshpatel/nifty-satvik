"""Output-contract checker tests — the dead-man must not vouch for a job that persisted nothing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from output_contracts import (  # noqa: E402
    _OVERALL_TO_HEALTH, _SEVERITY, _touched, annotations, check_output_contracts, load_contracts,
)


def test_contracts_manifest_is_present_and_shaped():
    cs = load_contracts()
    assert cs, "results/output_contracts.json has no contracts — the dead-man would vouch blindly"
    for c in cs:
        assert {"job", "workflow", "commit_prefix", "cadence_days"} <= set(c)
        assert isinstance(c.get("must_update", []), list)


def test_every_scheduled_workflow_has_a_contract():
    """A cron that commits state but declares no contract is exactly the blind spot this closes."""
    declared = {c["workflow"] for c in load_contracts()}
    committing = set()
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        if "git commit -m" in wf.read_text(encoding="utf-8"):
            committing.add(wf.stem)
    missing = committing - declared
    assert not missing, f"workflows commit state but have no output contract: {sorted(missing)}"


def test_touched_matches_files_and_directories():
    changed = {"results/a.json", "results/intraday_scan/2026-08-05.json"}
    assert _touched("results/a.json", changed)
    assert _touched("results/intraday_scan", changed)      # directory contract
    assert _touched("results/intraday_scan/", changed)     # trailing slash
    assert not _touched("results/missing.json", changed)


def test_checker_runs_and_is_json_serialisable():
    """The verdict must be a state the fold RECOGNISES — asserted against the checker's own
    vocabulary, not a literal set copied into the test.

    This test previously pinned a hand-written ``{OK, WARN, RED, ERROR}``. When ``INDETERMINATE``
    was added (2026-08-05) the test went red in CI and nowhere else, because ``actions/checkout``
    defaults to fetch-depth 1: the CI clone is shallow, so the checker correctly reports that it
    could not search the history. The state was right and the assertion was stale. Reading the
    vocabulary from the source removes the class of failure rather than this one instance."""
    res = check_output_contracts()
    assert res["overall"] in _OVERALL_TO_HEALTH, (
        f"checker emitted {res['overall']!r}, which fold_into_health() does not recognise and would "
        "silently map to ERROR — add it to _OVERALL_TO_HEALTH with its intended severity")
    json.dumps(res)                                        # must survive the monitor's json.dumps
    assert isinstance(res["jobs"], list) and res["jobs"]


def test_every_overall_state_has_a_severity_rank():
    """Guard on the guard: a state that folds to a health label with no severity rank would be
    treated as ERROR (rank 5) by the ladder — louder than intended, and for the wrong reason."""
    for overall, health in _OVERALL_TO_HEALTH.items():
        assert health in _SEVERITY, f"{overall!r} folds to {health!r}, which has no severity rank"


def test_breaches_produce_error_annotations():
    fake = {"breaches": ["weekly-scanner: did not touch results/x.json"], "warnings": ["w"]}
    lines = annotations(fake)
    assert any(l.startswith("::error::") for l in lines)
    assert any(l.startswith("::warning::") for l in lines)


def test_judge_log_is_a_declared_artifact_somewhere():
    """Regression pin: the artifact whose loss motivated this whole mechanism must be contracted."""
    blob = json.dumps(load_contracts())
    assert "results/judge_log.jsonl" in blob


# ── Layer 3: the checker must not convict a repo that cannot answer the question ────────
#
# The first CI run of the contract checker went RED with "no cron commit ever found" for all three
# jobs, against commits that plainly existed on main. Root cause: `actions/checkout` defaults to
# fetch-depth 1, so the checker searched a one-commit clone. It reported absence of evidence as
# evidence of absence — the exact error S2.14 was written about, reproduced inside the alarm meant
# to prevent it. These tests pin the distinction.

import subprocess  # noqa: E402


def _run(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)


def _fixture_repo(tmp_path, n_cron_commits=3):
    """A tiny repo with real cron-shaped commits — hermetic, no dependence on this checkout."""
    src = tmp_path / "src"
    (src / "results").mkdir(parents=True)
    _run("init", "-q", "-b", "main", cwd=src)
    _run("config", "user.email", "t@t.t", cwd=src)
    _run("config", "user.name", "t", cwd=src)
    (src / "README.md").write_text("seed\n", encoding="utf-8")
    _run("add", "-A", cwd=src)
    _run("commit", "-qm", "seed", cwd=src)
    for i in range(n_cron_commits):
        (src / "results" / "state.json").write_text(f'{{"run": {i}}}\n', encoding="utf-8")
        _run("add", "-A", cwd=src)
        _run("commit", "-qm", f"chore(fix): scheduled run {i}", cwd=src)
    return src


def _contract_file(tmp_path, must_update):
    p = tmp_path / "contracts.json"
    p.write_text(json.dumps({"contracts": [{
        "job": "fixture", "workflow": "wf", "commit_prefix": "chore(fix): scheduled run",
        "cadence_days": 3650, "must_update": must_update}]}), encoding="utf-8")
    return p


def test_shallow_clone_reports_INDETERMINATE_not_a_breach(tmp_path):
    """THE REGRESSION. A depth-1 clone must yield INDETERMINATE — never NO_COMMIT, never RED."""
    src = _fixture_repo(tmp_path)
    shallow = tmp_path / "shallow"
    r = _run("clone", "--depth", "1", f"file://{src.as_posix()}", str(shallow), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert _run("rev-parse", "--is-shallow-repository", cwd=shallow).stdout.strip() == "true"

    res = check_output_contracts(contracts_path=_contract_file(tmp_path, ["results/state.json"]),
                                 repo=shallow)
    assert res["overall"] == "INDETERMINATE", res
    assert res["breaches"] == [], "a checkout that cannot answer must not convict"
    assert [j["status"] for j in res["jobs"]] == ["INDETERMINATE"]
    assert res["history"]["shallow"] is True


def test_full_clone_of_the_same_repo_resolves_the_job(tmp_path):
    """Control: the identical contract against full history finds the commit and passes."""
    src = _fixture_repo(tmp_path)
    full = tmp_path / "full"
    assert _run("clone", f"file://{src.as_posix()}", str(full), cwd=tmp_path).returncode == 0

    res = check_output_contracts(contracts_path=_contract_file(tmp_path, ["results/state.json"]),
                                 repo=full)
    assert res["overall"] == "OK", res
    assert res["jobs"][0]["status"] == "OK"
    assert res["history"]["adequate"] is True


def test_never_persisted_artifact_still_breaches(tmp_path):
    """The alarm must still fire for the real defect — the judge-log signature.

    Guards against fixing the false positive by making the checker toothless: a contracted path
    that no cron commit ever wrote is exactly what a silent `git add` looks like.
    """
    src = _fixture_repo(tmp_path)
    full = tmp_path / "full2"
    assert _run("clone", f"file://{src.as_posix()}", str(full), cwd=tmp_path).returncode == 0

    res = check_output_contracts(
        contracts_path=_contract_file(tmp_path, ["results/state.json", "results/never_added.jsonl"]),
        repo=full)
    assert res["overall"] == "RED", res
    assert res["jobs"][0]["status"] == "CONTRACT_BREACH"
    assert any("never_added.jsonl" in b for b in res["breaches"]), res["breaches"]


def test_unchanged_output_is_not_a_breach(tmp_path):
    """A cron that re-runs and produces byte-identical output is healthy, not broken.

    This is the false positive that the 2026-08-04 re-dispatch exposed: the weekly book was
    recomputed identically, git recorded no diff, and the first draft called it a contract breach.
    """
    src = _fixture_repo(tmp_path)
    # a further cron commit that touches something else entirely, leaving state.json untouched
    (src / "other.txt").write_text("x\n", encoding="utf-8")
    _run("add", "-A", cwd=src)
    _run("commit", "-qm", "chore(fix): scheduled run 99", cwd=src)
    full = tmp_path / "full3"
    assert _run("clone", f"file://{src.as_posix()}", str(full), cwd=tmp_path).returncode == 0

    res = check_output_contracts(contracts_path=_contract_file(tmp_path, ["results/state.json"]),
                                 repo=full)
    assert res["overall"] == "OK", res
    assert res["breaches"] == []


def test_indeterminate_annotates_warning_not_error():
    res = {"indeterminate": ["a", "b"], "history": {"shallow": True, "n_commits": 1},
           "breaches": [], "warnings": []}
    lines = annotations(res)
    assert lines and all(l.startswith("::warning::") for l in lines)
    assert "fetch-depth: 0" in lines[0]


def test_monitor_checkout_fetches_full_history():
    """Layer 1 pin: the job that RUNS the checker must give it history to search."""
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-monitor.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in wf, (
        "the monitor's checkout no longer fetches full history — the output-contract checker "
        "will read every job as unanswerable (INDETERMINATE) and the alarm goes deaf"
    )


def test_fold_lets_a_breach_move_the_top_level_overall():
    """A nested red key that leaves `overall: OK` is the same defect one level up."""
    from output_contracts import fold_into_health
    h = fold_into_health({"overall": "OK", "jobs": []}, {"overall": "RED"})
    assert h["overall"] == "CONTRACT_BREACH"
    assert h["overall_driver"] == "output_contracts"
    assert h["output_contracts"]["overall"] == "RED"


def test_fold_surfaces_indeterminate_but_never_downgrades_a_worse_state():
    from output_contracts import fold_into_health
    assert fold_into_health({"overall": "OK"}, {"overall": "INDETERMINATE"})["overall"] == "INDETERMINATE"
    # a job that never fired stays the headline; contracts must not paper over it
    assert fold_into_health({"overall": "MISSING"}, {"overall": "OK"})["overall"] == "MISSING"
    assert fold_into_health({"overall": "MISSING"}, {"overall": "WARN"})["overall"] == "MISSING"
    # a WARN must not mask a healthy board into looking broken
    assert fold_into_health({"overall": "OK"}, {"overall": "WARN"})["overall"] == "WARN"
