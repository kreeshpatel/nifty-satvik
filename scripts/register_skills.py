"""Register the committed `skills/` as Claude Code project skills (`.claude/skills/`).

`.claude/` is local config (gitignored), so the registration does not travel with
the repo. Run this once after cloning, and again whenever `skills/` changes, so a
Claude Code session rooted in this repo surfaces + can invoke the skills:

    python scripts/register_skills.py

Source of truth is always `skills/`; `.claude/skills/` is a generated mirror.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "skills"
DEST = ROOT / ".claude" / "skills"


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"no skills/ dir at {SRC}")
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


if __name__ == "__main__":
    main()
