"""Every citation marker must quote something the document it names actually says.

A marker is the token CITES, a document path, and a quoted string. This file never
writes that form literally: the checker scans `tests/`, so a literal example here would
be picked up as a real citation and fail. Markers are assembled at runtime below.

**Why this exists.** Three defects in two days came from a claim outliving its source, not from
faulty reasoning:

  * `routers/signals.py` justified an auth path with "the repo is PRIVATE"; the repo is public and
    unauthenticated reads return 200.
  * `PortfolioV3.jsx` set a drawdown kill at 15% citing "documented in CLAUDE.md". CLAUDE.md says
    no such thing, and both pre-registrations say −50% — three times larger, and inside the band
    `prereg.md` §4 explicitly calls normal pain. That panel would have alarmed on roughly a third
    of all days.
  * I then derived a −46.26% warning level from the sentence explaining where −50% came from,
    wrote it with a citation, and it read as sourced. Same failure, with me as the author.

An untraceable number gets questioned; a number with a source attached gets believed. That is why
a false citation costs more than no citation.

**What this proves, and what it does not.** It cannot judge whether a comment fairly summarises a
document — that is not a check a script makes. It proves a quoted string is present in the file it
is attributed to, which is the failure that has actually bitten. And it is opt-in: nothing forces a
citation to carry a marker, so a green run does not mean the codebase is free of false citations.
It means the marked ones are honest, and marking is cheap.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("check_citations", ROOT / "scripts" / "check_citations.py")
_cc = importlib.util.module_from_spec(_spec)
sys.modules["check_citations"] = _cc
_spec.loader.exec_module(_cc)


def test_every_citation_in_the_tree_is_substantiated():
    problems = _cc.verify()
    assert not problems, (
        "these comments cite a document that does not say what they claim:\n  "
        + "\n  ".join(problems)
        + "\n\nQuote the document exactly, or stop attributing the claim to it."
    )


def test_there_are_citations_to_check():
    """A checker with nothing to check passes vacuously and teaches nobody anything."""
    assert _cc.find_citations(), "no CITES markers found — the check has become decorative"


_TOKEN = "CIT" "ES"          # assembled, so this file contains no literal marker to be scanned


def _marker(doc: str, quote: str) -> str:
    return f'{_TOKEN} {doc}: "{quote}"'


def test_it_catches_a_quote_the_document_does_not_contain(monkeypatch):
    """The 15%-in-CLAUDE.md case, which is the one that shipped."""
    _assert_caught(monkeypatch, _marker("CLAUDE.md", "15% drawdown"), "does not say")


def test_it_catches_a_claim_inferred_from_a_document_rather_than_stated_by_it(monkeypatch):
    """My own −46.26% band: reasoned from §4's rationale, written as though quoted."""
    _assert_caught(monkeypatch, _marker("forward/prereg.md", "warning level of -46.26%"),
                   "does not say")


def test_it_catches_a_cited_document_that_does_not_exist(monkeypatch):
    """Covers a rename or a move, which is how a true citation silently becomes false."""
    _assert_caught(monkeypatch, _marker("forward/gone.md", "anything"), "does not exist")


def test_a_real_quote_survives_dash_and_whitespace_differences(monkeypatch):
    """A quote wraps differently in a comment than in the document, and an en dash, a minus and a
    hyphen read identically. The check must fail on a changed claim, not on typography."""
    marker = _marker("forward/prereg.md", "live max drawdown breaches **-50%**")  # ASCII hyphen
    probe = ROOT / "tests" / "__citation_probe.py"
    probe.write_text(f"# {marker}\n", encoding="utf-8")
    try:
        assert not [p for p in _cc.verify() if "__citation_probe" in p]
    finally:
        probe.unlink()


def _assert_caught(monkeypatch, marker: str, expected: str) -> None:
    probe = ROOT / "tests" / "__citation_probe.py"
    probe.write_text(f"# {marker}\n", encoding="utf-8")
    try:
        hits = [p for p in _cc.verify() if "__citation_probe" in p]
        assert hits, f"the checker did not flag {marker!r}"
        assert expected in hits[0], f"unexpected message: {hits[0]}"
    finally:
        probe.unlink()
