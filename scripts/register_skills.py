"""Register the committed `skills/` as Claude Code project skills (`.claude/skills/`).

`.claude/` is local config (gitignored), so the registration does not travel with
the repo. Run this once after cloning, and again whenever `skills/` changes, so a
Claude Code session rooted in this repo surfaces + can invoke the skills:

    python scripts/register_skills.py

Source of truth is always `skills/`; `.claude/skills/` is a generated mirror.

WHY IT NOW REPORTS DRIFT (2026-09-15). The copy only ever ran forwards and was never re-run, and two
things went wrong silently:

  * STALE MIRROR. Claude Code loads skills from `.claude/skills/`, not `skills/`. The mirror predated
    the 2026-07-30 and 2026-08-07/08 edits, so for about six weeks a session invoking
    `overlay-testing`, `edge-research-pipeline` or `research-log` loaded versions WITHOUT their
    "clear the cheap gates before any trial" sections, and `methodology-synthesis` lacked a row. The
    guidance existed in the repo and was invisible to the sessions it was written for.
  * ORPHANS. Two research digests (`_ingested/options_oi_tailhedge.md`, `swing_return_drivers.md`)
    had been written straight into the gitignored mirror, so they existed on one laptop and nowhere
    in git. A fresh clone would have lost them while `forward/action_plan.md` and finding 0101 still
    cited them.

So after copying, this lists any file left in the mirror that has no source (an orphan: rescue it
into `skills/` or delete it) and exits non-zero, because a quiet success is how both problems lasted.
Skills that exist only in the mirror as whole directories — tool skills such as `caveman` — are not
orphans; the check is scoped to directories that also exist in `skills/`.
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "skills"
DEST = ROOT / ".claude" / "skills"
_SKIP = {"__pycache__"}


def _files(base: Path) -> set[Path]:
    """Relative paths of every file under `base`, ignoring bytecode caches."""
    if not base.is_dir():
        return set()
    return {p.relative_to(base) for p in base.rglob("*")
            if p.is_file() and not (_SKIP & set(p.parts))}


def find_stale(src: Path = SRC, dest: Path = DEST) -> list[Path]:
    """Source files whose mirror copy is missing or differs — what a session would load wrongly."""
    return sorted(rel for rel in _files(src)
                  if not (dest / rel).is_file() or not filecmp.cmp(src / rel, dest / rel, shallow=False))


def find_orphans(src: Path = SRC, dest: Path = DEST) -> list[Path]:
    """Mirror files with no source, inside a skill directory that DOES exist in `skills/`.

    Scoped that way on purpose: a whole directory present only in the mirror is a locally-installed
    tool skill, not lost research. A stray file inside a shared directory is the thing that bit us.
    """
    shared = {d.name for d in src.iterdir() if d.is_dir()} if src.is_dir() else set()
    have = _files(src)
    return sorted(rel for rel in _files(dest)
                  if rel.parts and rel.parts[0] in shared and rel not in have)


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit(f"no skills/ dir at {SRC}")
    stale_before = find_stale()
    DEST.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in sorted(SRC.iterdir()):
        if d.is_dir():
            shutil.copytree(d, DEST / d.name, dirs_exist_ok=True)
            n += 1
        elif d.suffix == ".md":  # README.md etc.
            shutil.copy2(d, DEST / d.name)
    installed = len(list(DEST.glob("*/SKILL.md")))
    print(f"registered {n} skill dir(s) -> {DEST}  ({installed} SKILL.md)")
    if stale_before:
        print(f"refreshed {len(stale_before)} stale mirror file(s) that sessions had been loading:")
        for rel in stale_before:
            print(f"  {rel.as_posix()}")

    orphans = find_orphans()
    if orphans:
        print(f"\nORPHANS — {len(orphans)} file(s) exist only in the gitignored mirror, so they are in "
              f"no commit and a fresh clone loses them. Move each into skills/ (or delete it):")
        for rel in orphans:
            print(f"  .claude/skills/{rel.as_posix()}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
