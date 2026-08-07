"""The Claude Code harness — subagents, hooks, and the skill mirrors — has to actually exist.

`skills/skills-first/SKILL.md` has told every session since it was written to spawn `flaw-hunter`,
`backtest-validator` and `overfit-skeptic` "instead of doing the work inline". Until 2026-08-07 none
of the three existed: `.claude/agents/` was un-ignored in `.gitignore` and empty. An instruction
pointing at a capability that is not there does not fail loudly — the session reads it, cannot act
on it, and quietly does the work inline, which is the outcome the instruction was written to
prevent. So the references are asserted against the files.

The hooks get the same treatment. A guard nobody has watched fire is a belief, not a control, so
each rule in `scripts/guard_protected_paths.py` is exercised here against a real repo path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".claude" / "agents"
SETTINGS = ROOT / ".claude" / "settings.json"
GUARD = ROOT / "scripts" / "guard_protected_paths.py"
BRIEF = ROOT / "scripts" / "session_brief.py"

# Named in skills/skills-first (the first three) and in the router / ritual skills (the rest).
REQUIRED_AGENTS = [
    "flaw-hunter",
    "backtest-validator",
    "overfit-skeptic",
    "red-team",
    "blind-replica",
]


def _frontmatter(path: Path) -> dict[str, str]:
    """Minimal `key: value` YAML front-matter reader — no dependency for a five-field header."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    body = text.split("---", 2)
    if len(body) < 3:
        return {}
    out: dict[str, str] = {}
    for line in body[1].splitlines():
        if line.strip() and not line.startswith((" ", "\t")) and ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


# ------------------------------------------------------------------------------ subagents
@pytest.mark.parametrize("name", REQUIRED_AGENTS)
def test_referenced_subagent_exists(name: str):
    path = AGENTS / f"{name}.md"
    assert path.exists(), (
        f"skills reference the `{name}` subagent but {path.relative_to(ROOT)} does not exist. "
        f"A session told to spawn a missing agent silently does the work inline instead."
    )


@pytest.mark.parametrize("name", REQUIRED_AGENTS)
def test_subagent_frontmatter_is_loadable(name: str):
    fm = _frontmatter(AGENTS / f"{name}.md")
    assert fm.get("name") == name, f"{name}.md must declare `name: {name}` (got {fm.get('name')!r})"
    assert len(fm.get("description", "")) > 40, (
        f"{name}.md needs a description substantial enough for delegation to match on."
    )


# ------------------------------------------------------------------------------ hook wiring
def test_settings_json_parses_and_points_at_real_scripts():
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = cfg["hooks"]
    assert "SessionStart" in hooks and "PreToolUse" in hooks

    referenced = [
        arg
        for event in hooks.values()
        for group in event
        for hook in group["hooks"]
        for arg in hook.get("args", [])
    ]
    assert referenced, "no hook script arguments found in settings.json"
    for arg in referenced:
        rel = arg.replace("${CLAUDE_PROJECT_DIR}/", "")
        assert (ROOT / rel).exists(), f"hook references {rel}, which does not exist"


def _run(script: Path, event: dict, env_extra: dict | None = None) -> str:
    env = {**os.environ, **(env_extra or {})}
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(event), capture_output=True, text=True, timeout=60, env=env, check=False,
    )
    assert proc.returncode == 0, f"{script.name} exited {proc.returncode}: {proc.stderr}"
    return proc.stdout


# ------------------------------------------------------------------------------ SessionStart brief
def test_session_brief_emits_the_authoritative_counts():
    out = _run(BRIEF, {"hook_event_name": "SessionStart"})
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]

    n_trials = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text("utf-8"))
    assert f"n_trials {n_trials['cumulative_n_trials']}" in ctx, (
        "the brief must carry the count read from n_trials.json — that is the whole point of "
        "generating it rather than reciting it"
    )
    assert "screens" in ctx and "sealed opens" in ctx
    assert "unknown" not in ctx, f"an authority failed to parse:\n{ctx}"


def test_session_brief_survives_a_broken_repo(tmp_path: Path):
    """It must degrade, never block. A hook that can fail a session gets deleted, and then there
    is no brief at all."""
    stub = tmp_path / "scripts"
    stub.mkdir()
    (stub / "session_brief.py").write_text(BRIEF.read_text(encoding="utf-8"), encoding="utf-8")
    out = _run(stub / "session_brief.py", {"hook_event_name": "SessionStart"})
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "unknown" in ctx, "missing authorities should surface as a visible 'unknown'"


# ------------------------------------------------------------------------------ protected paths
def _decision(tool: str, file_path: str, env_extra: dict | None = None) -> dict | None:
    out = _run(
        GUARD,
        {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"file_path": file_path}},
        env_extra,
    )
    return json.loads(out) if out.strip() else None


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write"])
def test_sealed_judge_log_is_denied_for_reads_and_writes(tool: str):
    verdict = _decision(tool, "diagnostics/research/judge_log.jsonl")
    assert verdict is not None, f"{tool} on the sealed judge log was allowed"
    assert verdict["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "SEALED" in verdict["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize(
    "rel",
    ["models/long_horizon/config.json", "research/baseline_v1.json", "forward/prereg.md"],
)
def test_frozen_artifacts_are_write_protected(rel: str):
    assert _decision("Write", rel) is not None, f"{rel} is not protected"
    # ...but readable: a guard that blocked reading the frozen cfg would break ordinary work.
    assert _decision("Read", rel) is None, f"{rel} should stay readable"


def test_a_closed_pre_registration_cannot_be_edited():
    """0001 has results.json beside its prereg, so the run has reported and the plan is frozen."""
    target = "research/0001-xsec-momentum/prereg.md"
    assert (ROOT / target).exists(), "fixture study moved — update this test"
    verdict = _decision("Edit", target)
    assert verdict is not None, "a reported study's pre-registration was left editable"
    assert "amendment" in verdict["hookSpecificOutput"]["permissionDecisionReason"]


def test_ordinary_files_are_untouched():
    for rel in ["README.md", "nq/engine/portfolio.py", "diagnostics/research/n_trials.json"]:
        assert _decision("Write", rel) is None, (
            f"{rel} was blocked. n_trials.json in particular MUST stay writable — it has to be "
            f"incremented before every run, and friction there produces the count-it-afterwards "
            f"breach the file's own log already records once."
        )


def test_the_override_is_a_single_deliberate_step():
    assert _decision("Read", "diagnostics/research/judge_log.jsonl", {"NQ_GOVERNANCE_OVERRIDE": "1"}) is None
