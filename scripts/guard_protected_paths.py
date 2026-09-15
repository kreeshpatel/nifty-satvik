"""PreToolUse hook — refuse the edits that would quietly destroy the programme's evidence.

Every rule here is a law CLAUDE.md already states in prose. Prose is skipped under pressure, and
each of these is skipped in exactly the moment it matters most: you amend a pre-registration when
the result came back wrong, you touch the frozen cfg when a fix "obviously" belongs there, you read
the sealed judge log when you are curious how it is going. None of those feel like misconduct at
the time. A hook cannot be talked round.

Rules (each cites the law it enforces):

  1. `results/judge_log.jsonl` — no read, no write, from the file tools AND from the shell. The judge
     verdicts are SEALED until the first review read (>= 2 quarters from 2026-08-01); reading them
     early destroys the only blind evidence the programme has. Verify by counts and hash-chain
     instead (`tests/test_judge_log.py`).

     Until 2026-09-15 this rule named `diagnostics/research/judge_log.jsonl`, a path that has never
     existed — the writer (`nq/paper/judge_log.py::DEFAULT_LOG`) puts the log in `results/`. The
     guard's own test asserted the same wrong literal, so both were green while the real 710 KB
     sealed log sat unprotected. `tests/test_agent_harness.py` now ties this constant to the writer's
     path, so the two cannot drift apart silently again.

     Shell coverage is a tripwire, not a vault: it refuses any command naming the log by its
     `results/` path, and a plain reader (`cat`, `head`, `tail`, `Get-Content`, …) given the bare
     file name. A search that merely mentions the name is allowed, and a command that reaches the
     file without naming it (`cd results && …`, a Python script) is not caught. The seal rests on
     intent; this makes stepping over it deliberate rather than accidental.

     Known false positive: the whole command string is scanned, so a commit message or PR body typed
     inline that *mentions* the path is refused too. Write the text to a file and pass it by
     reference (`git commit -F msg.txt`, `gh pr create --body-file body.md`). Found on the commit
     that introduced this rule.
  2. A pre-registration whose run has already produced a result — no write. The pre-reg is the
     record of what was committed to *before* seeing the outcome; editing it afterwards is not a
     correction, it is the loss of the thing that made the result worth anything. Amend with a new
     dated file alongside it.
  3. `models/long_horizon/config.json` — no write. The frozen cfg; changes go through
     `research/config_CHANGELOG.md` and a quarterly review.
  4. `research/baseline_v1.json` — no write. The pinned anchor of record. Re-anchoring is a
     governance-class decision with hash verification (`/re-anchor`).
  5. `forward/prereg.md` — no write. Forward-wall thresholds may be tightened, never retroactively
     relaxed, and only by dated amendment at a quarterly review. Between reviews: log and leave it
     alone.

Deliberately NOT protected: `diagnostics/research/n_trials.json` must stay writable — it has to be
incremented *before* every run, and a guard that made incrementing awkward would produce exactly
the "count it afterwards" breach the file's own log already records once.

Escape hatch: set `NQ_GOVERNANCE_OVERRIDE=1`. It is one environment variable, which is the point —
the barrier is not difficulty, it is having to state that you are stepping over a law on purpose.

Contract (https://code.claude.com/docs/en/hooks): stdin is the event JSON; a deny is
`hookSpecificOutput.permissionDecision` with exit 0. Anything unrecognised falls through silently —
this hook decides only what it is sure about.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
READ_TOOLS = {"Read"}

JUDGE_LOG = "results/judge_log.jsonl"   # == nq/paper/judge_log.py::DEFAULT_LOG (held by a test)
SHELL_TOOLS = {"Bash", "PowerShell"}

import re  # noqa: E402  (kept beside the only rule that needs it)

# Any command naming the sealed log through its results/ path, with either separator.
_SEALED_PATH = re.compile(r"results[\\/]+judge_log\.jsonl", re.IGNORECASE)
# The bare file name handed to a plain reader. Searches (grep/rg/Select-String) are deliberately NOT
# listed: looking for where the name is *mentioned* is ordinary work and reads no verdict.
_READER_ON_BARE_NAME = re.compile(
    r"\b(cat|head|tail|less|more|type|gc|Get-Content|jq)\b[^|;&]*\bjudge_log\.jsonl\b",
    re.IGNORECASE)


def shell_reads_sealed_log(command: str) -> bool:
    """True when a shell command names the sealed log in a way that reads or rewrites it."""
    if not command:
        return False
    return bool(_SEALED_PATH.search(command) or _READER_ON_BARE_NAME.search(command))

FROZEN = {
    "models/long_horizon/config.json": (
        "the frozen cfg (`config.load_frozen_cfg`). A config change is a governance-class decision: "
        "record it in `research/config_CHANGELOG.md` and take it to a quarterly review."
    ),
    "research/baseline_v1.json": (
        "the pinned baseline of record. Re-anchoring changes what every past finding was measured "
        "against — run `/re-anchor`, which verifies the OHLCV hash and migrates the citations."
    ),
    "forward/prereg.md": (
        "the forward-wall pre-registration — the only certifier the programme has left. Thresholds "
        "may be tightened, never retroactively relaxed, and only by a dated amendment at a "
        "quarterly review (first trading day Jan/Apr/Jul/Oct)."
    ),
}


def relpath(raw: str) -> str | None:
    """Repo-relative POSIX path, or None if the target is outside the repo."""
    if not raw:
        return None
    try:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        return p.resolve().relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        return None


def prereg_is_closed(rel: str) -> str | None:
    """A pre-registration is closed once its run has produced a result next to it.

    Two layouts are in use: the per-study folder (`research/NNNN-slug/prereg.md` beside
    `result.md`) and the flat registry (`diagnostics/research/preregistry/NNNN-*.md` with its
    finding at `research/findings/NNNN-*.md`). Returns the evidence path that closed it.
    """
    path = ROOT / rel
    name = path.name

    if name == "prereg.md":
        for sibling in ("result.md", "results.json"):
            if (path.parent / sibling).exists():
                return f"{(path.parent / sibling).relative_to(ROOT).as_posix()}"
        return None

    if "preregistry" in rel and name[:4].isdigit():
        findings = ROOT / "research" / "findings"
        if findings.is_dir():
            for f in findings.glob(f"{name[:4]}-*.md"):
                return f.relative_to(ROOT).as_posix()
    return None


def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def decide(tool: str, rel: str | None) -> dict | None:
    if rel is None:
        return None

    if rel == JUDGE_LOG and tool in (WRITE_TOOLS | READ_TOOLS):
        return deny(
            f"`{JUDGE_LOG}` is SEALED until the first review read (>= 2 quarters from 2026-08-01). "
            "Reading the verdicts early is what makes them worthless — the blindness is the "
            "evidence. Verify by count and hash-chain instead (`tests/test_judge_log.py`)."
        )

    if tool not in WRITE_TOOLS:
        return None

    if rel in FROZEN:
        return deny(f"`{rel}` is {FROZEN[rel]}")

    closed_by = prereg_is_closed(rel)
    if closed_by:
        return deny(
            f"`{rel}` is a pre-registration whose run has already reported (`{closed_by}`). "
            "Editing it after the outcome is known removes the only thing that made the result "
            "worth anything. Write a dated amendment beside it instead, and state in the amendment "
            "what changed and why."
        )
    return None


def decide_shell(command: str) -> dict | None:
    if shell_reads_sealed_log(command):
        return deny(
            f"`{JUDGE_LOG}` is SEALED until the first review read (>= 2 quarters from 2026-08-01), "
            "and this shell command names it. The seal covers the shell as well as the file tools — "
            "reading the verdicts early is what makes them worthless. Verify by count and hash-chain "
            "instead (`tests/test_judge_log.py`)."
        )
    return None


def main() -> int:
    if os.environ.get("NQ_GOVERNANCE_OVERRIDE") == "1":
        return 0
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return 0

    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    if tool in SHELL_TOOLS:
        verdict = decide_shell(str(tool_input.get("command", "")))
    else:
        verdict = decide(tool, relpath(str(tool_input.get("file_path", ""))))
    if verdict:
        sys.stdout.write(json.dumps(verdict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
