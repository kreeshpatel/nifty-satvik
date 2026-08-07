"""commit-msg guard — the LIVE book may be changed, but never silently.

The external structuring report proposed marking the Bhanushali thread "untouchable": a hook that
rejects any commit touching it. That rule is wrong here, and the way it is wrong matters.

`weekly-swing-0094-rank` is not a frozen research thread. It is **the production book** — two cron
workflows, real owner capital, and three dated override blocks in `models/bhanushali_weekly/
config.json` each marked *"owner decision, sole capital-at-risk"*. A rule that blocks fixing a live
system running real money is a rule that gets bypassed the first time something breaks at 09:15, and
a bypassed rule protects nothing while still appearing in the documentation.

So the guard does not ask *whether* the live book changed. It asks **what kind** of change it was,
and forces the author to say so in a word the git log can be audited on:

    prod-fix:       a defect fix. The book does what it always intended; the code now agrees.
                    Must ship a regression test — a live fix without one is a story, not a fix.
    prod-override:  a deliberate change of behaviour, on the owner's explicit call. Must be a dated,
                    documented block in the config, not a quiet edit to a number.

Everything else touching those paths is refused, because everything else is one of the two things
that must never happen to a live book: silent strategy drift, or parameter retuning outside a
pre-registration. Both feel locally reasonable. Both are indistinguishable from tuning-to-taste when
read back a quarter later, which is exactly when it matters.

Override with ``NQ_GOVERNANCE_OVERRIDE=1`` — one variable, deliberately, and say so in the message.

    python scripts/guard_production_commit.py <commit-msg-file>
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# The live book: what the crons actually invoke, plus the config that parameterises it.
# Deliberately narrow. A path lands here only if a wrong value in it reaches real capital.
PRODUCTION_PATHS = (
    "models/bhanushali_weekly/",
    "scripts/run_bhanushali_cron.py",
    "scripts/run_bhanushali_weekly_rank.py",
    "scripts/run_bhanushali_monitor.py",
    "scripts/bhanushali_review_scorecard.py",
)

ALLOWED_TYPES = ("prod-fix", "prod-override")
_TYPE = re.compile(r"^(prod-fix|prod-override)(\([^)]*\))?:", re.M)


def staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                         capture_output=True, text=True, check=False)
    return [ln.strip().replace("\\", "/") for ln in out.stdout.splitlines() if ln.strip()]


def touches_production(files: list[str]) -> list[str]:
    return sorted({f for f in files for p in PRODUCTION_PATHS if f.startswith(p)})


def has_production_type(message: str) -> bool:
    """True when the subject line declares one of the production change types."""
    subject = message.lstrip().splitlines()[0] if message.strip() else ""
    return bool(_TYPE.match(subject))


def check(message: str, files: list[str]) -> str | None:
    """Return an error string when the commit must be refused, else None."""
    hit = touches_production(files)
    if not hit or has_production_type(message):
        return None
    return "\n".join([
        "",
        "REFUSED — this commit changes the LIVE book and does not say what kind of change it is.",
        "",
        "  touched:",
        *[f"    {f}" for f in hit],
        "",
        "  The live weekly-swing book runs on real capital via two cron workflows. Changes to it are",
        "  permitted, but only as one of two declared kinds:",
        "",
        "    prod-fix:       a defect fix. MUST ship a regression test that fails on the old code.",
        "    prod-override:  a deliberate behaviour change on the owner's explicit call. MUST be a",
        "                    dated, documented block in models/bhanushali_weekly/config.json.",
        "",
        "  Anything else touching these paths is silent strategy drift or parameter retuning outside",
        "  a pre-registration. Prefix the subject line with one of the two types, or move the change",
        "  out of the production path.",
        "",
        "  Deliberate exception: NQ_GOVERNANCE_OVERRIDE=1, and say so in the commit message.",
        "",
    ])


def main(argv: list[str]) -> int:
    if os.environ.get("NQ_GOVERNANCE_OVERRIDE") == "1":
        return 0
    if len(argv) < 2:
        return 0
    err = check(Path(argv[1]).read_text(encoding="utf-8"), staged_files())
    if err:
        print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
