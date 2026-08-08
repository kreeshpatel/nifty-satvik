"""The standing counts recited in every readout must match their ledgers.

CLAUDE.md instructs each session to state **screens N · sealed opens N · n_trials N** in every
research readout. Those numbers were hardcoded into CLAUDE.md and five skill files, and by
2026-08-07 every one of them was wrong: `n_trials` had been reset 138 -> 0 by owner decision and
climbed back to 2, while screens had advanced 12 -> 19. The instruction to recite them verbatim is
what made the drift expensive — a stale constant on that line does not sit quietly in a document, it
is copied into the output of every session that obeys the instruction.

So the counts are asserted against their authorities rather than trusted:

    n_trials       diagnostics/research/n_trials.json      (cumulative_n_trials)
    screens        diagnostics/research/label_screen_ledger.md   (numbered rows)
    sealed opens   diagnostics/research/label_screen_ledger.md   (S-prefixed rows)

This is the same pattern `tests/test_transferability_register.py` uses for a generated document: the
prose is allowed to exist, but it is not allowed to disagree with its source.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "diagnostics" / "research" / "label_screen_ledger.md"
N_TRIALS = ROOT / "diagnostics" / "research" / "n_trials.json"

# Files that state the counts as fact. Each is read, not assumed — a file that stops stating them
# simply contributes nothing rather than failing, so this cannot block an unrelated edit.
RECITERS = [
    ROOT / "CLAUDE.md",
    # The research board that CLAUDE.md carried until 2026-08-07, archived verbatim. An archive
    # still gets read, and a stale count in one is quoted exactly as confidently as a live one.
    ROOT / "docs" / "PROGRAM_STATE.md",
    ROOT / "skills" / "program-laws" / "SKILL.md",
    ROOT / "skills" / "research-log" / "SKILL.md",
    ROOT / "skills" / "edge-research-pipeline" / "SKILL.md",
    ROOT / "skills" / "overlay-testing" / "SKILL.md",
    ROOT / "skills" / "verdict-machine" / "SKILL.md",
    # The screen ledger is the AUTHORITY for screens and sealed opens, but it also *recited*
    # n_trials, and on 2026-08-08 that recitation still read 138 against a counter at 2. An
    # authority file is the last place a stale number should be able to hide.
    LEDGER,
]

_SCREENS = re.compile(r"screens\s+\*{0,2}(\d+)\*{0,2}", re.I)
_TRIALS = re.compile(r"n_trials\s+\*{0,2}(\d+)\*{0,2}", re.I)

# The punctuation-tolerant scanner. `_TRIALS` above requires whitespace directly after the word, so
# it silently missed "`n_trials` (currently **138**)" in skills/verdict-machine — a count that had
# been stale since the 2026-08-07 reset, sitting in a file sessions are told to read before every
# study. A test that catches one phrasing of a recited number and not another is worse than no test,
# because the passing suite is read as proof the numbers are clean.
_TRIALS_LOOSE = re.compile(r"n_trials[`\s]*(?:\(\s*currently[\s*]*)?\*{0,2}(\d{1,4})\b", re.I)

# The assertion scanner. Two further stale 138s survived even `_TRIALS_LOOSE` — "`n_trials` stays
# **138**" in the screen ledger and "`n_trials` currently **138**" in skills/overlay-testing — each
# defeated by a different bit of punctuation. Rather than widen the pattern until it matches
# anything (which starts flagging "a result that would be PROMOTE at n_trials=20", a hypothetical in
# backtest-rigor, and the "§11" in "DSR/n_trials integration"), key on the words that make a number
# a CLAIM ABOUT THE PRESENT rather than an illustration.
_TRIALS_ASSERTED = re.compile(
    r"n_trials`?[^\n]{0,15}?\b(?:currently|stays|remains|is now|now stands at)\b"
    r"[^0-9\n]{0,12}\*{0,2}(\d{1,4})\b",
    re.I,
)


def authoritative_screens() -> int:
    """Numbered rows in the screen ledger — `| 17 | 2026-08-06 | ... |`."""
    rows = [m for m in re.finditer(r"^\|\s*(\d+)\s*\|", LEDGER.read_text(encoding="utf-8"), re.M)]
    return max(int(m.group(1)) for m in rows)


def authoritative_sealed() -> int:
    """S-prefixed rows in the sealed-open table — `| S1 | ... |`."""
    return len(re.findall(r"^\|\s*S(\d+)\s*\|", LEDGER.read_text(encoding="utf-8"), re.M))


def authoritative_trials() -> int:
    return int(json.loads(N_TRIALS.read_text(encoding="utf-8"))["cumulative_n_trials"])


def test_the_authorities_are_readable_and_sane():
    """If the ledgers cannot be parsed, every assertion below is vacuous — check that first."""
    assert authoritative_screens() >= 1
    assert authoritative_sealed() >= 1
    assert authoritative_trials() >= 0


@pytest.mark.parametrize("path", RECITERS, ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name)
def test_recited_screen_count_matches_the_ledger(path: Path):
    if not path.exists():
        pytest.skip(f"{path} absent")
    want = authoritative_screens()
    for got in {int(m) for m in _SCREENS.findall(path.read_text(encoding="utf-8"))}:
        assert got == want, (
            f"{path.relative_to(ROOT)} states 'screens {got}' but the ledger "
            f"({LEDGER.relative_to(ROOT)}) has {want}. The ledger is the authority.")


@pytest.mark.parametrize("path", RECITERS, ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name)
def test_recited_trial_count_matches_the_counter(path: Path):
    if not path.exists():
        pytest.skip(f"{path} absent")
    want = authoritative_trials()
    for got in {int(m) for m in _TRIALS.findall(path.read_text(encoding="utf-8"))}:
        assert got == want, (
            f"{path.relative_to(ROOT)} states 'n_trials {got}' but "
            f"{N_TRIALS.relative_to(ROOT)} says {want}. Increment the counter BEFORE a run, then "
            f"update the prose — never the other way round.")


# --------------------------------------------------------------------- governance skill mirrors
# CLAUDE.md calls these two "the laws in enforceable form", and until 2026-08-07 they were the only
# two skills absent from `.claude/skills/` — so the loader could not see the most binding rules in
# the repo. They are now mirrored there. A mirror that silently diverges is worse than no mirror,
# because whichever copy the reader happens to open is then a coin flip.
#
# The router, the plausibility gate, and the four ritual commands joined them on 2026-08-07: a
# procedure a session is told to run is only a control if the loader can find it, and the ritual
# skills are the ones that carry the orderings (pre-reg before the run, counter before the run,
# thresholds before the numbers) that cannot be recovered once broken.
MIRRORED_SKILLS = [
    "program-laws",
    "verdict-machine",
    "session-router",
    "plausibility-check",
    "pre-register",
    "verdict",
    "seal",
    "re-anchor",
]


@pytest.mark.parametrize("name", MIRRORED_SKILLS)
def test_governance_skill_is_discoverable_by_the_loader(name: str):
    assert (ROOT / ".claude" / "skills" / name / "SKILL.md").exists(), (
        f"skills/{name} is not mirrored into .claude/skills/, so the skill loader cannot find it. "
        f"CLAUDE.md instructs sessions to load it before any research task.")


@pytest.mark.parametrize("name", MIRRORED_SKILLS)
def test_the_mirror_has_not_drifted(name: str):
    src, mirror = ROOT / "skills" / name, ROOT / ".claude" / "skills" / name
    if not mirror.exists():
        pytest.skip("mirror absent — covered by the test above")
    for f in sorted(p for p in src.rglob("*.md")):
        twin = mirror / f.relative_to(src)
        assert twin.exists(), f"{f.relative_to(ROOT)} has no counterpart at {twin.relative_to(ROOT)}"
        assert twin.read_text(encoding="utf-8") == f.read_text(encoding="utf-8"), (
            f"{twin.relative_to(ROOT)} has drifted from {f.relative_to(ROOT)}. "
            f"skills/ is the source; copy it over rather than editing the mirror.")


def test_claude_md_actually_carries_the_counts():
    """The paired positive. If CLAUDE.md ever stops stating the counts, the tests above pass
    vacuously — so assert the recitation exists rather than only that it is correct."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert _SCREENS.search(text), "CLAUDE.md no longer states a screen count"
    assert _TRIALS.search(text), "CLAUDE.md no longer states n_trials"


@pytest.mark.parametrize("path", RECITERS, ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name)
def test_no_stale_trial_count_survives_punctuation(path: Path):
    """The same assertion as above, but tolerant of how the number is dressed."""
    if not path.exists():
        pytest.skip(f"{path} absent")
    want = authoritative_trials()
    for got in {int(m) for m in _TRIALS_LOOSE.findall(path.read_text(encoding="utf-8"))}:
        assert got == want, (
            f"{path.relative_to(ROOT)} states an n_trials of {got}; "
            f"{N_TRIALS.relative_to(ROOT)} says {want}. Prefer stating no literal at all and "
            f"pointing at the authority — a number that cannot drift beats one a test happens "
            f"to catch.")


@pytest.mark.parametrize("path", RECITERS, ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name)
def test_no_asserted_trial_count_is_stale(path: Path):
    """Catch a count dressed as a claim: 'n_trials currently 138', 'n_trials stays 138'."""
    if not path.exists():
        pytest.skip(f"{path} absent")
    want = authoritative_trials()
    for got in {int(m) for m in _TRIALS_ASSERTED.findall(path.read_text(encoding="utf-8"))}:
        assert got == want, (
            f"{path.relative_to(ROOT)} asserts n_trials is {got}; the counter says {want}. "
            f"Prefer pointing at diagnostics/research/n_trials.json over restating the number.")


def test_the_assertion_scanner_catches_what_slipped_past_the_others():
    """Guard the guard. These are the two literals that survived every earlier pattern, verbatim as
    they appeared on 2026-08-08. If a future simplification of the regex stops matching them, the
    class of bug they represent is unguarded again."""
    escaped_past_earlier_patterns = [
        "`n_trials` stays **138** — both are measurement class.",
        "> every future test (`n_trials` currently **138**).",
    ]
    for text in escaped_past_earlier_patterns:
        assert _TRIALS_ASSERTED.findall(text) == ["138"], f"scanner missed: {text!r}"
        assert not _TRIALS.findall(text), "the strict pattern was supposed to miss this"


def test_the_assertion_scanner_ignores_hypotheticals():
    """It must NOT fire on illustrations, or it will be silenced within a week."""
    for text in [
        "A result that would be PROMOTE at n_trials=20 may only reach SHADOW at n_trials=50.",
        "corporate-action handling, golden master gate, DSR/n_trials integration, and the §11 harness",
        "read it from `diagnostics/research/n_trials.json` (2026-08-07)",
    ]:
        assert not _TRIALS_ASSERTED.findall(text), f"false positive on: {text!r}"
