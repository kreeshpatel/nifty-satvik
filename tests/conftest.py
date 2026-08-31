"""Suite-wide invariant: running the tests must not modify `results/`.

`results/` holds committed cron output — the published envelope, the paper book, the hash-chained
forward wall, the sealed judge log. A test that writes there leaves the working tree dirty, and a
dirty tree is one `git add -A` away from committing a test artifact as if it were Saturday's cron
run. That is not hypothetical: `test_swing_grading_gate` ran the real
`scripts/bhanushali_review_scorecard.py` as a subprocess with `cwd=ROOT`, regenerating the committed
`results/weekly_review_scorecard.json` on every single suite run.

Tests that need the scorecard, the book, or the wall should point `RESULTS_DIR` at `tmp_path` — the
pattern already used by the `results_dir` fixture in `tests/test_swing_grading_gate.py`.

METADATA ONLY, deliberately. This stats size and mtime; it never opens a file. `results/judge_log.jsonl`
is SEALED until the first review read (`scripts/guard_protected_paths.py`), so a content hash here
would itself break the law this suite exists to protect. Size and mtime detect a write without
reading a verdict.

Consequence of the metadata choice, stated rather than hidden: a rewrite that preserves both size and
mtime is invisible to this check. Nothing in this repo does that, and the alternative reads a sealed
file, so the trade is taken knowingly.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# Directories under results/ that legitimately churn are still watched — nothing in the suite should
# touch any of it. Listed here only so a future exemption has an obvious home and must be argued.
EXEMPT: set[str] = set()


def _snapshot() -> dict[str, tuple[int, int]]:
    """{relative path -> (size, mtime_ns)} for every file under results/. Never opens a file."""
    if not RESULTS.is_dir():
        return {}
    out: dict[str, tuple[int, int]] = {}
    for p in RESULTS.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(RESULTS).as_posix()
        if any(rel.startswith(e) for e in EXEMPT):
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        out[rel] = (st.st_size, st.st_mtime_ns)
    return out


@pytest.fixture(scope="session", autouse=True)
def results_dir_is_read_only():
    before = _snapshot()
    yield
    after = _snapshot()

    changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
    created = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    if not (changed or created or removed):
        return

    lines = ["the test suite modified results/, which holds committed cron output:"]
    for label, items in (("modified", changed), ("created", created), ("deleted", removed)):
        if items:
            lines.append(f"  {label}: " + ", ".join(items[:12])
                         + (f" (+{len(items) - 12} more)" if len(items) > 12 else ""))
    lines.append("Point the code under test at tmp_path instead — see the `results_dir` fixture in "
                 "tests/test_swing_grading_gate.py. Restore the tree with `git checkout -- results/`.")
    pytest.fail("\n".join(lines), pytrace=False)
