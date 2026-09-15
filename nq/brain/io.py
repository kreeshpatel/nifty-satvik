"""The read access the Brain is allowed — and the one artifact it may never open.

The 0125 informed-judge verdicts are sealed until the first quarterly review read. The PreToolUse hook
guards interactive sessions, but the Brain runs as code in crons, where no hook exists. A module that
reads `results/` wholesale is exactly the reader the seal is for, so refusal lives here, in code.

The sealed path is taken from the writer's own constant (`nq.paper.judge_log.DEFAULT_LOG`), never typed.
Until 2026-09-15 the hook sealed a path that did not exist while its test asserted the same wrong
literal; deriving the path from the writer is what stops that happening twice.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nq.paper.judge_log import DEFAULT_LOG

SEALED: frozenset[Path] = frozenset({Path(DEFAULT_LOG).resolve()})


class SealedArtifactError(PermissionError):
    """Raised instead of opening a sealed artifact."""


def assert_not_sealed(path: str | Path) -> Path:
    """Return the resolved path, or raise if it is sealed. Never opens the file."""
    p = Path(path).resolve()
    if p in SEALED:
        raise SealedArtifactError(
            f"{p.name} is the sealed 0125 judge log. It may not be read before the first review read "
            f"(>= 2 quarters from 2026-08-01). Verify it by row count and hash chain only.")
    return p


def read_json(path: str | Path) -> Any:
    """Parse a JSON artifact, refusing sealed ones before any byte is read."""
    p = assert_not_sealed(path)
    return json.loads(p.read_text(encoding="utf-8"))
