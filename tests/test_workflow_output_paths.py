"""The whitelist guard — makes the silent-`git add` class structurally impossible.

**Why this test exists.** The same trap has fired four times (weekly_monitor, the D2 archive, the
judge cohort, PROBE) and each cost real time or real money. The 2026Q3 audit caught the worst
instance six weeks late: `.gitignore` carries `results/*` plus an explicit whitelist, and
`results/judge_log.jsonl` was never added to it — so the scanner's `git add` was a **silent no-op**.
The 2026-08-01 run judged 17 cards at a cost of $4.00 and persisted none of them, and the
hash-chained forward log restarted from GENESIS every Saturday.

`git add` on an ignored, untracked path exits 0 and stages nothing. There is no error to catch. The
only way to make that failure loud is to assert the invariant up front:

    for every path a workflow declares in `git add`:
        it must be TRACKED, or it must NOT be IGNORED.

A path that is ignored AND untracked would be silently skipped, so the test fails the same day
someone introduces it — not six weeks later when a number is missing.

**This test is the fourth-instance-impossible guarantee.** Do not weaken it to make a new path pass;
whitelist the path in `.gitignore` instead, which is the actual fix.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# tokens that appear on a `git add` line but are not paths
_NOISE = re.compile(r"^(-|\d?>|\|\||&&|;|true|false|2>/dev/null|>/dev/null)")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def declared_add_paths() -> dict[str, list[str]]:
    """{workflow filename -> [paths it passes to `git add`]}, following backslash continuations."""
    out: dict[str, list[str]] = {}
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        # join backslash-continued lines so multi-line add lists are one logical line
        joined = re.sub(r"\\\s*\n\s*", " ", text)
        paths: list[str] = []
        for line in joined.splitlines():
            # Strip comments and skip the helper DEFINITIONS (`need() { ... git add "$1" ... }`).
            # Without this the parser scrapes prose out of the guard-policy comment block and the
            # test goes vacuously green on tokens like "construct" — a guard diluted by junk is a
            # guard that no longer means what its name says.
            stripped = line.split("#", 1)[0].strip()
            if not stripped or re.match(r"^\w+\(\)", stripped):
                continue
            # Three declaration forms, all equivalent for our purposes — each ends in `git add`:
            #   `git add a b c`   the literal list
            #   `need <path>`     required artifact (missing => ::error + red step)
            #   `opt  <path>`     optional artifact (missing => ::warning)
            # The helpers were introduced by the 2026-08-05 guard rewrite. They MUST be parsed here:
            # a path that moves from the literal list into a helper would otherwise silently leave
            # this test's coverage, which is the exact class of blind spot the test exists to kill.
            # `git add` is matched ANYWHERE on the line, not just at the start: the intraday cron
            # guards its add behind `if [ -d ... ]; then git add ...`, and an anchored match would
            # have silently dropped it from coverage.
            if "git add " in stripped:
                body = stripped.split("git add ", 1)[1]
            elif stripped.startswith(("need ", "opt ")):
                body = stripped.split(None, 1)[1] if len(stripped.split(None, 1)) > 1 else ""
            else:
                continue
            for tok in body.split():
                if _NOISE.match(tok):
                    continue
                # Shell variables ("$1" inside the need()/opt() helpers) are not statically
                # checkable. They are safe by construction: the helpers are only ever called with
                # literals that results/output_contracts.json also names, and the contract checker
                # verifies those landed in the commit. Skipping them keeps this test honest rather
                # than vacuously green on a token it cannot resolve.
                if "$" in tok or tok.startswith(('"', "'")):
                    continue
                # stop at a shell operator; everything after is not a path
                if tok in {"||", "&&", ";", "2>/dev/null"}:
                    break
                paths.append(tok.rstrip(";"))
        if paths:
            out[wf.name] = paths
    return out


def _is_tracked(path: str) -> bool:
    """Tracked paths are staged by `git add` even when ignored, so tracking rescues a path."""
    if _git("ls-files", "--error-unmatch", path).returncode == 0:
        return True
    # a directory counts as tracked if it contains any tracked file
    r = _git("ls-files", "--", path)
    return bool(r.returncode == 0 and r.stdout.strip())


def _is_ignored(path: str) -> bool:
    """True if .gitignore would make `git add <path>` a silent no-op.

    Directory-aware by probe. `git check-ignore` on a bare directory path is not a reliable
    answer to the question we care about — the question is whether an artifact the cron WRITES
    there would be discarded. So for a directory we test a hypothetical child, which is exactly
    the real failure mode (and exactly how the PROBE instance was found).
    """
    bare = path.rstrip("/")
    looks_like_dir = path.endswith("/") or (ROOT / bare).is_dir()
    target = f"{bare}/__probe__.json" if looks_like_dir else bare
    return _git("check-ignore", "-q", "--no-index", target).returncode == 0


def test_workflows_declare_at_least_one_add_path():
    """Guard the guard: if the parser stops finding paths, this test is vacuous and must fail."""
    declared = declared_add_paths()
    assert declared, "parsed no `git add` paths from any workflow — the parser has broken"
    total = sum(len(v) for v in declared.values())
    assert total >= 10, f"only {total} paths parsed; the parser has likely broken silently"


@pytest.mark.parametrize("wf,path", [(w, p) for w, ps in declared_add_paths().items() for p in ps])
def test_workflow_add_path_is_not_silently_ignored(wf: str, path: str):
    """A path that is IGNORED and UNTRACKED would be silently skipped by `git add`.

    This is the exact D5 condition: the scanner declared `results/judge_log.jsonl`, `.gitignore`
    ignored it, nothing tracked it, and six weeks of $4/week verdicts evaporated.
    """
    if _is_tracked(path):
        return                                   # tracked wins: `git add` stages it regardless
    assert not _is_ignored(path), (
        f"{wf} declares `git add {path}`, but that path is IGNORED and UNTRACKED.\n"
        f"`git add` will exit 0 and stage NOTHING — the artifact will be silently discarded.\n"
        f"FIX: add `!{path}` to .gitignore (whitelist it). Do NOT weaken this test."
    )


def test_gitignore_whitelists_the_judge_log_specifically():
    """Regression pin for D5 — the instance that cost $4.00/week and reset the hash chain."""
    ign = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!results/judge_log.jsonl" in ign, (
        "the judge log's whitelist has been removed from .gitignore; the forward record would be "
        "silently discarded every Saturday and its hash chain would restart from GENESIS"
    )


def test_no_silent_guards_in_workflows():
    """No `|| true` and no `2>/dev/null` on a live command line — every guard names its watcher.

    THE `|| true` AUDIT (2026-08-05). A bare `|| true` converts a failure into a green step with
    no annotation, which is how a $4.00/week judge run, a dead monitor and four archive instances
    all stayed invisible. Non-fatal is still allowed — the monitor must publish even when a sidecar
    dies — but it must be spelled `|| echo "::warning::..."` so the failure is ON the run.
    """
    offenders = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        for i, line in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]              # comments may discuss the banned pattern
            if "|| true" in code or "2>/dev/null" in code:
                offenders.append(f"{wf.name}:{i}: {line.strip()}")
    assert not offenders, (
        "silent guard(s) reintroduced — replace with an annotated fallback:\n  "
        + "\n  ".join(offenders)
    )
