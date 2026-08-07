"""PreToolUse hook — refuse the edits that would quietly destroy the programme's evidence.

Every rule here is a law CLAUDE.md already states in prose. Prose is skipped under pressure, and
each of these is skipped in exactly the moment it matters most: you amend a pre-registration when
the result came back wrong, you touch the frozen cfg when a fix "obviously" belongs there, you read
the sealed judge log when you are curious how it is going. None of those feel like misconduct at
the time. A hook cannot be talked round.

Rules (each cites the law it enforces):

  1. `diagnostics/research/judge_log.jsonl` — no read, no write. The judge verdicts are SEALED until
     the first review read (>= 2 quarters from 2026-08-01); reading them early destroys the only
     blind evidence the programme has. Verify by counts and hash-chain instead
     (`tests/test_judge_log.py`).
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

JUDGE_LOG = "diagnostics/research/judge_log.jsonl"

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

    verdict = decide(tool, relpath(str(tool_input.get("file_path", ""))))
    if verdict:
        sys.stdout.write(json.dumps(verdict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
