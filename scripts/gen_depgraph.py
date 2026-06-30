#!/usr/bin/env python3
"""Generate a first-party module dependency map for the nq/ package.

Walks every .py file under nq/ plus the root config.py, parses imports with the
stdlib `ast` module, keeps only first-party edges (module roots `nq`, `config`),
and emits a Mermaid flowchart at file-module granularity into
docs/DEPENDENCY_MAP.md.

Stdlib only. Output is fully sorted so the generated doc diffs cleanly.

    regenerate with: python scripts/gen_depgraph.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST_PARTY_ROOTS = {"nq", "config"}
SOURCES = ["nq", "config.py"]  # dirs (walked) or single files, relative to ROOT
OUT = ROOT / "docs" / "DEPENDENCY_MAP.md"
# If the file-level graph exceeds this many nodes, collapse to sub-package level.
COLLAPSE_THRESHOLD = 40


def iter_py_files() -> list[Path]:
    files: list[Path] = []
    for entry in SOURCES:
        p = ROOT / entry
        if p.is_dir():
            files.extend(p.rglob("*.py"))
        elif p.is_file():
            files.append(p)
    # Skip cache / vendored dirs; keep it deterministic.
    files = [f for f in files if "__pycache__" not in f.parts]
    return sorted(files)


def module_name(path: Path) -> str:
    """Dotted module name of a source file relative to ROOT.

    nq/engine/portfolio.py -> nq.engine.portfolio
    nq/engine/__init__.py  -> nq.engine
    config.py              -> config
    """
    rel = path.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def package_parts(path: Path) -> list[str]:
    """Directory parts of a file relative to ROOT (the containing package)."""
    rel = path.relative_to(ROOT)
    return list(rel.parent.parts)


def resolve_known(dotted: str, known: set[str]) -> str | None:
    """Longest known-module prefix of a dotted name, else None."""
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in known:
            return cand
    return None


def edges_for_file(path: Path, known: set[str]) -> set[str]:
    src = module_name(path)
    targets: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    pkg = package_parts(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                t = resolve_known(alias.name, known)
                if t:
                    targets.add(t)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base = pkg[: len(pkg) - (node.level - 1)] if node.level > 1 else pkg
                base_dotted = ".".join(base)
                mod = f"{base_dotted}.{node.module}" if node.module else base_dotted
            else:
                mod = node.module or ""
            if not mod:
                continue
            # Prefer the most specific target: module.name (a submodule) if known,
            # otherwise the module itself.
            matched = False
            for alias in node.names:
                t = resolve_known(f"{mod}.{alias.name}", known)
                if t:
                    targets.add(t)
                    matched = True
            if not matched:
                t = resolve_known(mod, known)
                if t:
                    targets.add(t)
    targets.discard(src)
    # First-party only (root in nq/config) — resolve_known already enforces this
    # since `known` is built solely from first-party files.
    return {f"{src} -> {t}" for t in targets}


def to_slash(dotted: str) -> str:
    return dotted.replace(".", "/")


def node_id(dotted: str) -> str:
    return dotted.replace(".", "_")


def subpackage(dotted: str) -> str:
    """Collapse a file module to its sub-package (nq.engine.portfolio -> nq.engine)."""
    parts = dotted.split(".")
    if parts[0] != "nq":
        return parts[0]
    return ".".join(parts[:2]) if len(parts) >= 2 else dotted


def render(edge_pairs: list[tuple[str, str]], collapsed: bool) -> str:
    nodes = sorted({n for pair in edge_pairs for n in pair})
    lines = ["flowchart LR"]
    for n in nodes:
        lines.append(f'    {node_id(n)}["{to_slash(n)}"]')
    for s, t in sorted(set(edge_pairs)):
        lines.append(f"    {node_id(s)} --> {node_id(t)}")
    mermaid = "\n".join(lines)

    gran = "sub-package" if collapsed else "file-module"
    note = ""
    if collapsed:
        note = (
            f"\n> Collapsed to sub-package granularity "
            f"(file-level graph exceeded {COLLAPSE_THRESHOLD} nodes).\n"
        )
    return (
        "# nq dependency map\n\n"
        "First-party module wiring of the `nq/` package (+ root `config.py`).\n"
        f"Granularity: **{gran}**. Edges point from importer to imported.\n"
        f"{note}\n"
        "_Auto-generated — do not edit by hand._\n"
        "regenerate with: `python scripts/gen_depgraph.py`\n\n"
        "```mermaid\n"
        f"{mermaid}\n"
        "```\n"
    )


def main() -> int:
    files = iter_py_files()
    known = {module_name(f) for f in files}

    raw: set[str] = set()
    for f in files:
        raw |= edges_for_file(f, known)

    pairs = [tuple(e.split(" -> ")) for e in raw]
    pairs = [(s, t) for (s, t) in pairs if s.split(".")[0] in FIRST_PARTY_ROOTS
             and t.split(".")[0] in FIRST_PARTY_ROOTS]

    node_count = len({n for pair in pairs for n in pair})
    collapsed = node_count > COLLAPSE_THRESHOLD
    if collapsed:
        pairs = [(subpackage(s), subpackage(t)) for (s, t) in pairs]
        pairs = [(s, t) for (s, t) in pairs if s != t]

    if not pairs:
        print("ERROR: no first-party import edges found", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(pairs, collapsed), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(set(pairs))} edges, "
          f"{len({n for p in pairs for n in p})} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
