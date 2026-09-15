"""The skills a session loads must be the skills the repo commits.

Claude Code loads project skills from `.claude/skills/`, a gitignored mirror generated from the
committed `skills/` by `scripts/register_skills.py`. Nothing checked the two agreed, and on
2026-09-15 they did not:

  * the mirror was STALE — `overlay-testing`, `edge-research-pipeline` and `research-log` were loading
    without their "clear the cheap gates before any trial" sections for about six weeks, and
    `methodology-synthesis` was missing a row;
  * two research digests were ORPHANS — written straight into the gitignored mirror, so they existed on
    one machine and in no commit, while `forward/action_plan.md` and finding 0101 cited them.

The hermetic tests prove the detectors work. The live test runs only where a real, registered mirror
exists (the owner's machine), because CI has no registered mirror and would report every file stale.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("register_skills", ROOT / "scripts" / "register_skills.py")
R = importlib.util.module_from_spec(_spec)
sys.modules["register_skills"] = R
_spec.loader.exec_module(R)


def _tree(base: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return base


# --------------------------------------------------------------------------- the detectors
def test_a_stray_file_inside_a_shared_skill_dir_is_an_orphan(tmp_path):
    """The shape that actually lost work: a digest written into the mirror's `_ingested/`."""
    src = _tree(tmp_path / "skills", {"_ingested/a.md": "a", "laws/SKILL.md": "x"})
    dest = _tree(tmp_path / "mirror", {"_ingested/a.md": "a", "_ingested/lost.md": "!",
                                       "laws/SKILL.md": "x"})
    assert R.find_orphans(src, dest) == [Path("_ingested/lost.md")]


def test_a_mirror_only_directory_is_a_tool_skill_not_an_orphan(tmp_path):
    """`caveman`, `frontend-design` etc. are installed locally and never lived in skills/."""
    src = _tree(tmp_path / "skills", {"laws/SKILL.md": "x"})
    dest = _tree(tmp_path / "mirror", {"laws/SKILL.md": "x", "caveman/SKILL.md": "terse"})
    assert R.find_orphans(src, dest) == []


def test_stale_catches_both_a_missing_and_a_changed_copy(tmp_path):
    src = _tree(tmp_path / "skills", {"a/SKILL.md": "new gates section", "b/SKILL.md": "same"})
    dest = _tree(tmp_path / "mirror", {"a/SKILL.md": "old", })
    assert R.find_stale(src, dest) == [Path("a/SKILL.md"), Path("b/SKILL.md")]


def test_an_in_sync_mirror_is_clean(tmp_path):
    files = {"a/SKILL.md": "x", "_ingested/d.md": "y"}
    src, dest = _tree(tmp_path / "skills", files), _tree(tmp_path / "mirror", files)
    assert R.find_stale(src, dest) == [] and R.find_orphans(src, dest) == []


# --------------------------------------------------------------------------- the rescued work
@pytest.mark.parametrize("digest", ["options_oi_tailhedge.md", "swing_return_drivers.md"])
def test_the_rescued_digests_are_committed_in_the_source_tree(digest):
    """They are cited by forward/action_plan.md and finding 0101; a clone must have them."""
    assert (ROOT / "skills" / "_ingested" / digest).is_file(), (
        f"skills/_ingested/{digest} is missing — it exists only in the gitignored mirror again")


# --------------------------------------------------------------------------- the real mirror
@pytest.mark.skipif(os.environ.get("CI") == "true",
                    reason="CI has no registered mirror; drift is a property of a working machine")
@pytest.mark.skipif(not (ROOT / ".claude" / "skills").is_dir(), reason="no local mirror registered")
def test_the_local_mirror_is_what_sessions_should_load():
    stale, orphans = R.find_stale(), R.find_orphans()
    assert not stale and not orphans, (
        "the skills Claude Code loads have drifted from skills/ — run `python scripts/register_skills.py`."
        + (f" STALE: {[p.as_posix() for p in stale][:8]}" if stale else "")
        + (f" ORPHANS (rescue into skills/ first): {[p.as_posix() for p in orphans]}" if orphans else ""))
