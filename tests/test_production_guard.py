"""The live-book commit guard — `scripts/guard_production_commit.py`.

The rule it enforces is a correction to an external recommendation, and the correction is the point.
That report proposed making the Bhanushali thread "untouchable" — a hook rejecting any commit that
touches it. Applied here it would have blocked fixing a book that runs real capital on two cron
schedules, which is a rule that gets bypassed under pressure and therefore protects nothing.

The guard asks what KIND of change it is instead, and forces the answer into the subject line where
the git log can be audited on it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from guard_production_commit import (PRODUCTION_PATHS, check,  # noqa: E402
                                     has_production_type, touches_production)

PROD = "models/bhanushali_weekly/config.json"
OTHER = "nq/engine/rebalance_book.py"


def test_a_commit_that_does_not_touch_the_live_book_is_never_questioned():
    assert check("refactor(tree): move things about", [OTHER, "docs/README.md"]) is None


def test_an_undeclared_live_book_change_is_refused():
    err = check("fix: tweak the exit tranche", [PROD])
    assert err is not None
    assert "REFUSED" in err and PROD in err
    # the message must state BOTH routes, or it just blocks without telling the author what to do
    assert "prod-fix:" in err and "prod-override:" in err


@pytest.mark.parametrize("subject", [
    "prod-fix: the tranche boundary was off by one session",
    "prod-override: owner call — widen ext_cap to 0.20 (ADR-0009)",
    "prod-fix(exits): gap-aware stop now fills at the open",
])
def test_a_declared_live_book_change_is_allowed(subject: str):
    assert check(subject + "\n\nbody\n", [PROD]) is None


@pytest.mark.parametrize("subject", [
    "fix: something",                       # a normal type is not enough
    "feat(bhanushali): new exit",           # naming the book in the scope does not declare the kind
    "chore: bump",
    "PROD-FIX: shouting does not count",    # the token is lowercase by convention
])
def test_near_miss_subjects_do_not_satisfy_the_guard(subject: str):
    assert not has_production_type(subject)
    assert check(subject, [PROD]) is not None


def test_the_type_must_be_on_the_subject_line_not_buried_in_the_body():
    """A body mention is a description; the subject is what `git log --oneline` shows and what an
    audit greps. Accepting a buried token would make the log unauditable while looking compliant."""
    assert check("fix: adjust\n\nthis is really a prod-fix: honest\n", [PROD]) is not None


def test_every_guarded_path_is_actually_guarded():
    for p in PRODUCTION_PATHS:
        sample = p + "x.py" if p.endswith("/") else p
        assert touches_production([sample]) == [sample]


def test_the_guarded_set_stays_narrow_and_real():
    """A guard that covers everything is a guard nobody can work around honestly, so it gets
    disabled. Each path here must exist and must be one a wrong value in reaches real capital."""
    assert len(PRODUCTION_PATHS) <= 8
    for p in PRODUCTION_PATHS:
        assert (ROOT / p).exists(), f"guarded path {p} does not exist — the guard is stale"


def test_research_and_engine_paths_are_not_guarded():
    """The paired negative. If ordinary work tripped this, it would be turned off within a week."""
    assert touches_production([OTHER, "research/0001-xsec-momentum/result.md",
                               "pipelines/research/run_0001_xsec_momentum.py"]) == []
