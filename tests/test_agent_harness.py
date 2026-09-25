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


SEALED_LOG = "results/judge_log.jsonl"


def _shell_decision(tool: str, command: str, env_extra: dict | None = None) -> dict | None:
    out = _run(
        GUARD,
        {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}},
        env_extra,
    )
    return json.loads(out) if out.strip() else None


def test_the_guard_seals_the_path_the_writer_actually_uses():
    """The seal must name the file the judge writes, not a path someone remembers.

    Until 2026-09-15 the guard sealed `diagnostics/research/judge_log.jsonl`, which has never existed,
    and the test beside it asserted that same literal — so both passed while the real 710 KB log in
    `results/` was unprotected. Asserting a literal proves only that the literal is what was typed.
    This ties the guard to the writer's own constant, so moving the log moves the seal or goes red.
    """
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    from nq.paper.judge_log import DEFAULT_LOG
    import guard_protected_paths as G
    writer = Path(DEFAULT_LOG).resolve().relative_to(ROOT).as_posix()
    assert G.JUDGE_LOG == writer, (
        f"guard seals {G.JUDGE_LOG!r} but nq/paper/judge_log.py writes {writer!r}")


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write"])
def test_sealed_judge_log_is_denied_for_reads_and_writes(tool: str):
    verdict = _decision(tool, SEALED_LOG)
    assert verdict is not None, f"{tool} on the sealed judge log was allowed"
    assert verdict["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "SEALED" in verdict["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize("command", [
    "cat results/judge_log.jsonl",
    r"Get-Content results\judge_log.jsonl",
    "python -c \"print(open('results/judge_log.jsonl').read())\"",
    "tail -5 judge_log.jsonl",
])
def test_the_shell_cannot_read_the_sealed_log_either(tool: str, command: str):
    """The file-tool seal was the only one. A session told to prefer the shell for reads would have
    walked straight past it with `cat`."""
    verdict = _shell_decision(tool, command)
    assert verdict is not None, f"{tool} `{command}` read the sealed judge log"
    assert verdict["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "SEALED" in verdict["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    'grep -rn "judge_log.jsonl" docs/',        # finding where the name is MENTIONED reads no verdict
    "pytest tests/test_judge_log.py -q",        # count + hash-chain verification is the sanctioned path
    "git status --short",
    "cat results/signals_today_weekly.json",
])
def test_ordinary_shell_work_is_untouched(command: str):
    assert _shell_decision("Bash", command) is None, f"`{command}` was blocked"


def test_the_hook_is_actually_wired_to_the_shell():
    """Shell rules are dead code unless settings.json routes Bash and PowerShell through the guard."""
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    matchers = [g.get("matcher", "") for g in cfg["hooks"]["PreToolUse"]
                if any("guard_protected_paths" in a for h in g["hooks"] for a in h.get("args", []))]
    assert matchers, "guard_protected_paths is not wired as a PreToolUse hook"
    tools = {t for m in matchers for t in m.split("|")}
    for needed in ("Read", "Bash", "PowerShell"):
        assert needed in tools, f"the seal hook does not match {needed}"


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
    assert _decision("Read", SEALED_LOG, {"NQ_GOVERNANCE_OVERRIDE": "1"}) is None
    assert _shell_decision("Bash", f"cat {SEALED_LOG}", {"NQ_GOVERNANCE_OVERRIDE": "1"}) is None


# ------------------------------------------------------------- the shell can write, too (2026-09-25)
CLOSED_PREREG = "diagnostics/research/preregistry/0127-hegclass-activation-bound.md"


@pytest.mark.parametrize("command", [
    # the exact shape that walked through on 2026-09-25: a heredoc fed to an interpreter
    "python - <<'EOF'\nfrom pathlib import Path\n"
    f"p = Path('{CLOSED_PREREG}')\np.write_text(p.read_text() + 'amendment')\nEOF",
    f"echo '## amendment' >> {CLOSED_PREREG}",
    f"cat new.md > {CLOSED_PREREG}",
    f"sed -i 's/20%/15%/' {CLOSED_PREREG}",
    f"cp /tmp/edited.md {CLOSED_PREREG}",
    f"""python -c "open('{CLOSED_PREREG}', 'a').write('x')" """,
])
def test_the_shell_cannot_rewrite_a_reported_pre_registration(command: str):
    """The gap that commit 4229bce disclosed.

    `decide` covered Edit/Write and `decide_shell` covered only READS of the sealed judge log, so a
    `python - <<EOF ... write_text(...)` heredoc amended a pre-registration whose run had already
    reported and the hook never saw it. That amendment was owner-authorised — the defect is that
    CLAUDE.md documented a protection the hook did not deliver, which is the same shape as the
    judge-log hole found ten days earlier. A guard that is documented and absent is worse than none,
    because the documentation is what people rely on.
    """
    verdict = _shell_decision("Bash", command)
    assert verdict is not None, f"`{command}` rewrote a reported pre-registration"
    assert verdict["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "amendment" in verdict["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    "echo '{}' > models/long_horizon/config.json",
    "cp cand.json research/baseline_v1.json",
    r"Set-Content -Path forward\prereg.md -Value 'x'",
    "python - <<'EOF'\nfrom pathlib import Path\n"
    "Path('research/baseline_v1.json').write_text('{}')\nEOF",
    "rm forward/prereg.md",
    "git checkout HEAD~5 -- research/baseline_v1.json",
])
def test_the_shell_cannot_rewrite_a_frozen_artifact(command: str):
    verdict = _shell_decision("Bash", command)
    assert verdict is not None, f"`{command}` rewrote a frozen artifact"
    assert verdict["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("command", [
    # reads stay reads: a guard that blocked `cat` on a pre-reg would be switched off within a week
    f"cat {CLOSED_PREREG}",
    f"grep -n 'dd63' {CLOSED_PREREG}",
    "head -40 forward/prereg.md",
    # a read whose OUTPUT is redirected elsewhere is not a write to the protected path
    f"grep -c . {CLOSED_PREREG} > /tmp/lines.txt",
    # an OPEN pre-registration is meant to be written — that is how a study gets registered
    "echo '## 5. gate' >> forward/prereg_swing.md",
    # a path that merely looks like a protected one is not one
    "echo x > research/baseline_v1.json.bak",
    # and a heredoc fed to `cat`/`tee` is TEXT: writing this very test file must not be refused
    "cat >> tests/test_guard.py <<'EOF'\n"
    "CASES = [\"echo x > models/long_horizon/config.json\"]\nEOF",
])
def test_reading_and_ordinary_writing_still_work(command: str):
    assert _shell_decision("Bash", command) is None, f"`{command}` was blocked"


def test_the_shell_write_guard_honours_the_single_override():
    assert _shell_decision(
        "Bash", f"echo x >> {CLOSED_PREREG}", {"NQ_GOVERNANCE_OVERRIDE": "1"}) is None
