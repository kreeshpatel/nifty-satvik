"""Every `run:` block in every workflow must be syntactically valid shell.

The 2026-08-08 weekly scan failed with `line 10: syntax error near unexpected token '||'`. The judge
step is a LITERAL block scalar (`run: |`), so its newlines survive into the generated script, and an
`||` alone on the following line is a syntax error rather than a fallback. Its sibling steps use the
same visual shape and are fine only because they are PLAIN scalars, which YAML folds onto one line —
so the broken one looked exactly like the working ones.

The cost was not the judge. `run_bhanushali_cron.py` had already run and written the week's state,
including the first `base_swing_forward.json` the §4 comparator needs. The failure came before the
commit step, so none of it was ever published and a week of forward record was discarded. §3 forbids
backfilling it. That is the second time this repo has computed a week and thrown it away — the commit
step still carries a comment about 2026-07-11, when 18 signals and 3 holds went unpublished.

`bash -n` parses without executing, so this is a pure syntax gate.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
BASH = shutil.which("bash")

# `${{ ... }}` is GitHub expression syntax, not shell. Substitute a benign literal so the shell sees
# a well-formed word wherever an expression would have been interpolated.
EXPR = re.compile(r"\$\{\{[^}]*\}\}")


def _bash_n(script: str) -> subprocess.CompletedProcess:
    """`bash -n` parses without executing. encoding is explicit: these workflows contain em-dashes,
    and the Windows default (cp1252) cannot encode them, which would fail the gate for the wrong
    reason."""
    return subprocess.run([BASH, "-n"], input=script, text=True, capture_output=True,
                          encoding="utf-8", errors="replace")


def _run_blocks(path: Path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for job in (doc.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                shell = step.get("shell", "bash")
                if shell.startswith(("bash", "sh")):
                    yield step.get("name", "<unnamed>"), step["run"]


def test_there_are_workflows_with_run_blocks():
    """Guard the guard: a green sweep over an empty list would prove nothing."""
    total = sum(1 for p in WORKFLOWS for _ in _run_blocks(p))
    assert len(WORKFLOWS) >= 3 and total >= 10, f"{len(WORKFLOWS)} workflows, {total} run blocks"


@pytest.mark.skipif(BASH is None, reason="bash not available on this runner")
@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_every_run_block_parses(wf: Path):
    bad = []
    for name, script in _run_blocks(wf):
        proc = _bash_n(EXPR.sub("EXPR", script))
        if proc.returncode != 0:
            bad.append(f"  [{name}] {proc.stderr.strip().splitlines()[-1] if proc.stderr else '?'}")
    assert not bad, f"shell syntax errors in {wf.name}:\n" + "\n".join(bad)


@pytest.mark.skipif(BASH is None, reason="bash not available on this runner")
def test_the_detector_catches_the_defect_that_caused_this():
    """The exact 2026-08-08 shape must fail, or the gate above is decorative."""
    broken = 'python scripts/run_judge_cron.py\n  || echo "fallback"\n'
    fixed = 'python scripts/run_judge_cron.py \\\n  || echo "fallback"\n'
    assert subprocess.run([BASH, "-n"], input=broken, text=True, capture_output=True).returncode != 0
    assert subprocess.run([BASH, "-n"], input=fixed, text=True, capture_output=True).returncode == 0
