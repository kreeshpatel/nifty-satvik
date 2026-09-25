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

     Rules 2-5 cover the SHELL as well as the file tools, since 2026-09-25. Before that they were
     enforced only against Edit/Write/MultiEdit, and a shell heredoc walked straight through: the
     0127 re-open amended a reported pre-registration via `python - <<EOF ... write_text(...)` and the
     hook never saw it. The amendment was owner-authorised, so nothing was reverted — but CLAUDE.md
     claimed a protection the hook did not deliver, which is the same class of hole as the judge-log
     shell gap (rule 1, found 2026-09-15). A guard that is documented and absent is worse than no
     guard, because the documentation is what people rely on.
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


# Shell idioms that WRITE. Two tiers, because precision matters more for the common ones:
#   * targeted — the protected path is the destination of a redirect, tee, in-place edit or copy;
#   * generic  — a Python/PowerShell write idiom appears anywhere in a command that names the path
#                (this is what a heredoc looks like, and it is how the 0127 gap was walked through).
_REDIRECT_TO = r">>?\s*['\"]?{path}"
_TARGETED = [
    r"\btee\b[^|;&]*{path}",
    r"\bsed\b[^|;&]*-i[^|;&]*{path}",
    r"\b(cp|mv|rsync|install)\b[^|;&]*{path}",
    r"\b(Set-Content|Add-Content|Out-File|New-Item)\b[^|;&]*{path}",
    r"\b(rm|del|Remove-Item|truncate|shred)\b[^|;&]*{path}",
    r"\bgit\s+(checkout|restore)\b[^|;&]*{path}",
]
_GENERIC_WRITE = re.compile(
    r"(write_text\s*\(|\.to_csv\s*\(|\.to_json\s*\(|\.to_parquet\s*\(|json\.dump\s*\(|"
    r"open\s*\([^)]*['\"][wa]\+?['\"]|shutil\.(copy|move)|os\.(remove|rename|replace)|"
    r"\.unlink\s*\(|\.rename\s*\()",
    re.IGNORECASE)


def _path_re(rel: str) -> str:
    """The path as a shell would write it: either separator, and bounded at BOTH ends.

    The tail boundary is what stops `research/baseline_v1.json.bak` — an ordinary backup, not the
    frozen artifact — from reading as a hit.
    """
    body = re.escape(rel).replace("/", r"[\\/]+")
    return rf"(?<![\w./\\-]){body}(?![\w./\\-])"


def _mentions(command: str, rel: str) -> bool:
    return bool(re.search(_path_re(rel), command))


def _strip_heredoc_text(command: str) -> str:
    """Drop the body of a heredoc fed to `cat`/`tee` — that body is TEXT being written somewhere else.

    Writing this guard's own tests tripped it: the test file quotes `> models/long_horizon/config.json`
    as a string, inside `cat >> tests/... <<EOF`. A heredoc fed to an INTERPRETER (`python - <<EOF`) is
    left in, because that is precisely the shape that walked through on 2026-09-25. The header line is
    kept either way, so `cat > <protected> <<EOF` is still refused.
    """
    lines = command.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        m = re.search(r"\b(?:cat|tee)\b[^<]*<<-?\s*[\"']?(\w+)[\"']?", line)
        if m:
            while i < len(lines) and lines[i].strip() != m.group(1):
                i += 1  # the body is content, not commands
    return "\n".join(out)


def shell_writes_protected(command: str) -> tuple[str, str] | None:
    """(path, reason) when a shell command looks like it WRITES to a protected path.

    Reads stay allowed: a pre-registration and the frozen cfg are meant to be read, and a guard that
    blocked `cat` on them would be turned off within a week.
    """
    if not command:
        return None
    command = _strip_heredoc_text(command)
    for rel, why in FROZEN.items():
        if _mentions(command, rel) and _write_intent(command, rel):
            return rel, f"`{rel}` is {why}"
    for rel in _preregs_mentioned(command):
        closed_by = prereg_is_closed(rel)
        if closed_by and _write_intent(command, rel):
            return rel, (
                f"`{rel}` is a pre-registration whose run has already reported (`{closed_by}`). "
                "Editing it after the outcome is known removes the only thing that made the result "
                "worth anything. Write a dated amendment beside it instead."
            )
    return None


def _write_intent(command: str, rel: str) -> bool:
    pat = _path_re(rel)
    for tmpl in [_REDIRECT_TO, *_TARGETED]:
        if re.search(tmpl.format(path=pat), command, re.IGNORECASE):
            return True
    return bool(_GENERIC_WRITE.search(command))


def _preregs_mentioned(command: str) -> list[str]:
    """Repo-relative pre-registration paths named anywhere in the command."""
    out = []
    for m in re.finditer(r"[\w./\\-]*(?:preregistry[\\/]+[\w.-]+\.md|prereg\.md)", command):
        rel = relpath(m.group(0).lstrip("./").replace("\\", "/"))
        if rel and (ROOT / rel).exists():
            out.append(rel)
    return out


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
    written = shell_writes_protected(command)
    if written:
        _, reason = written
        return deny(reason + "\n\n(The shell is covered as well as the file tools, since 2026-09-25: "
                    "a heredoc that wrote a reported pre-registration walked through the earlier "
                    "version. Reads are still allowed — only writes are refused.)")
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
