"""The 2026-08-08 owner amendment must survive the session that recorded it.

The owner ruled that **no path may be given a negative verdict without a run under the current
harness** — not a KILL, not a screen-derived bound, not "refused relitigation". A prior verdict is
evidence about the regime that produced it, and most of those regimes are gone: between them and
today sit the continuous-slice fix, the calendar-annualisation correction, the v0 -> v1 re-anchor,
the macro PIT truncation gate, and the survivorship backfill. Only 7 of 108 closed verdicts were
measured on the book that actually trades.

The amendment is dangerous precisely because it *loosens* a rule. `program-laws` opens with "CITE
AND NARROW, DO NOT RELITIGATE", which reads, at a glance, as licence to close a path by citation —
and a session under time pressure reads at a glance. So the amendment is asserted into every file
that carries the old framing, and a future edit that quietly drops it fails here rather than
silently restoring kill-by-citation.

This does not pin the wording. It pins the presence: the date, and the load-bearing claim in the
authority. Rewriting the argument is fine; deleting it is not.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

AMENDMENT_DATE = "2026-08-08"

# Every file that states, or could be read as stating, that a path can be closed without a run.
CARRIERS = [
    ROOT / "CLAUDE.md",
    ROOT / "skills" / "program-laws" / "SKILL.md",
    ROOT / "skills" / "verdict-machine" / "SKILL.md",
    ROOT / "skills" / "session-router" / "SKILL.md",
    ROOT / "skills" / "verdict" / "SKILL.md",
]

AUTHORITY = ROOT / "skills" / "program-laws" / "SKILL.md"


@pytest.mark.parametrize("path", CARRIERS, ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name)
def test_the_amendment_is_still_carried(path: Path):
    text = path.read_text(encoding="utf-8")
    assert AMENDMENT_DATE in text, (
        f"{path.relative_to(ROOT)} no longer references the {AMENDMENT_DATE} owner amendment "
        f"(no negative verdict without a run). If the owner has reversed it, delete this test in "
        f"the same commit and say so; do not let the rule lapse by omission."
    )


def test_the_authority_states_the_rule_itself():
    """program-laws is where a session goes to find out whether an idea is closed. The amendment
    has to say what it forbids, not merely carry a date."""
    # The amendment is a wrapped markdown blockquote, so a phrase can straddle a "\n> " boundary.
    # Match against the unwrapped text or the assertion tests the line-filling, not the rule.
    text = re.sub(r"\s*\n>?\s*", " ", AUTHORITY.read_text(encoding="utf-8"))
    assert re.search(r"negative verdict without a run", text, re.I), (
        "the program-laws amendment no longer states the rule it exists to impose"
    )
    assert re.search(r"not re-tested under the current harness", text, re.I), (
        "program-laws no longer gives the status string a cited KILL must be quoted as; without it "
        "the amendment is advice rather than a convention"
    )


def test_the_activation_bound_no_longer_claims_to_kill():
    """GATE 3 was described as having 'killed every usage candidate that reached it, at zero trial
    cost'. That sentence is the amendment's most direct contradiction — a free kill."""
    text = (ROOT / "skills" / "verdict-machine" / "SKILL.md").read_text(encoding="utf-8")
    assert not re.search(r"killed every usage candidate", text), (
        "verdict-machine GATE 3 again claims to kill candidates at zero trial cost. Since "
        f"{AMENDMENT_DATE} the bound measures a ceiling and sets priority; only a pre-registered "
        "run may issue a negative verdict."
    )
