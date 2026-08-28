#!/usr/bin/env python3
"""Verify that a comment citing a document actually quotes something that document says.

WHY THIS EXISTS. Three defects in two days came from the same place, and it was not reasoning —
it was a claim that outlived its source:

  * `routers/signals.py` and `github_data.py` justified an auth path with "the repo is PRIVATE";
    the repo is public and unauthenticated reads return 200.
  * `PortfolioV3.jsx` set a drawdown kill at 15% and cited "documented in CLAUDE.md". CLAUDE.md
    documents no such thing, and both pre-registrations say -50% — a number three times larger,
    inside the band prereg.md SS4 explicitly calls normal pain.
  * I then inferred a -46.26% warning level from the sentence that explains where -50% came from,
    wrote it with a citation, and it read as sourced. Same failure, with me as the author.

An untraceable number gets questioned. A number with a source attached gets believed. That is
what makes a false citation more expensive than no citation at all.

WHAT THIS CAN AND CANNOT DO. Judging whether a comment fairly SUMMARISES a document is not a
check a script can make. Judging whether a quoted string is actually IN the document is, and it
covers the failure that has actually bitten us: a specific claim attributed to a specific file.

    // CITES forward/prereg.md: "live max drawdown breaches **-50%**"

Every marker found anywhere in the tree is verified. If the document changes, is renamed, or
never said it, the build fails on the commit that made it untrue.

OPT-IN, deliberately. Nothing forces a citation to carry a marker, so this does not prove the
codebase is free of false citations — it makes the load-bearing ones cheap to keep honest, and
those are the ones people mark. Stated plainly here so nobody reads a green run as more than it
is.

Stdlib only.

    run with: python scripts/check_citations.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where citations may live. Documents themselves are excluded: a doc quoting itself proves nothing.
SEARCH_DIRS = ["frontend/src", "dashboard/backend", "scripts", "nq", "tests"]
SEARCH_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".css"}
SKIP_PARTS = {"node_modules", "__pycache__", ".git", "build", "dist"}

CITATION = re.compile(r'CITES\s+([^\s:"]+)\s*:\s*"([^"]+)"')


def _normalise(text: str) -> str:
    """Collapse whitespace and unify dash/quote variants.

    A quote wraps differently in a comment than in the document it came from, and an en dash, a
    minus sign and a hyphen are the same character to a reader. Normalising both sides means the
    check fails on a claim that changed, not on a line break or a typographic dash.
    """
    text = unicodedata.normalize("NFKC", text)
    for ch in "‐‑‒–—―−":       # hyphens, dashes, minus
        text = text.replace(ch, "-")
    for ch in "‘’‛":
        text = text.replace(ch, "'")
    for ch in "“”‟":
        text = text.replace(ch, '"')
    return re.sub(r"\s+", " ", text).strip()


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for d in SEARCH_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix in SEARCH_SUFFIXES and not (SKIP_PARTS & set(p.parts)):
                files.append(p)
    return sorted(files)


def find_citations() -> list[tuple[Path, int, str, str]]:
    """[(source file, line number, cited document, quoted text)] across the tree."""
    out = []
    for f in iter_source_files():
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for m in CITATION.finditer(line):
                out.append((f, i, m.group(1), m.group(2)))
    return out


def verify() -> list[str]:
    """Failure messages, one per citation that cannot be substantiated. Empty means all hold."""
    problems: list[str] = []
    cache: dict[str, str | None] = {}
    for src, lineno, doc_rel, quote in find_citations():
        if doc_rel not in cache:
            doc = ROOT / doc_rel
            cache[doc_rel] = _normalise(doc.read_text(encoding="utf-8", errors="ignore")) \
                if doc.is_file() else None
        body = cache[doc_rel]
        where = f"{src.relative_to(ROOT).as_posix()}:{lineno}"
        if body is None:
            problems.append(f"{where}: cites {doc_rel!r}, which does not exist")
        elif _normalise(quote) not in body:
            problems.append(
                f"{where}: cites {doc_rel!r} for {quote!r}, which that document does not say"
            )
    return problems


def main() -> int:
    citations = find_citations()
    problems = verify()
    for p in problems:
        print(f"::error::{p}")
    print(f"checked {len(citations)} citation(s) across {len(iter_source_files())} files: "
          f"{'all substantiated' if not problems else f'{len(problems)} FAILED'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
