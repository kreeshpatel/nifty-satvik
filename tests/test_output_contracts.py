"""Output-contract checker tests — the dead-man must not vouch for a job that persisted nothing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from output_contracts import (  # noqa: E402
    _touched, annotations, check_output_contracts, load_contracts,
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
    res = check_output_contracts()
    assert res["overall"] in {"OK", "WARN", "RED", "ERROR"}
    json.dumps(res)                                        # must survive the monitor's json.dumps
    assert isinstance(res["jobs"], list) and res["jobs"]


def test_breaches_produce_error_annotations():
    fake = {"breaches": ["weekly-scanner: did not touch results/x.json"], "warnings": ["w"]}
    lines = annotations(fake)
    assert any(l.startswith("::error::") for l in lines)
    assert any(l.startswith("::warning::") for l in lines)


def test_judge_log_is_a_declared_artifact_somewhere():
    """Regression pin: the artifact whose loss motivated this whole mechanism must be contracted."""
    blob = json.dumps(load_contracts())
    assert "results/judge_log.jsonl" in blob
