"""Repo reorganisation — move only what is provably safe to move.

THE PROBLEM. `scripts/` holds 208 .py files in one flat directory, fusing three layers that have
nothing to do with each other:

  * LIBRARIES     modules other code imports. `run_bhanushali_path1.py` alone has ~90 importers and
                  two tests depend on it, yet it is named like a script.
  * ENTRY POINTS  things a scheduler or a workflow actually invokes.
  * ONE-OFFS      `diag_*` explorations that ran once and were never imported again.

The verb prefixes (`run_`, `diag_`) describe how a file was born, not what it is now, so the naming
actively misleads.

THE RULE. A file moves only if ALL of these hold:

  1. no other .py in the repo imports it
  2. no test imports it OR mentions its path as a string literal
  3. no .github/workflows/*.yml mentions its path

Anything else stays put. Renaming the library modules is a separate, larger change: it would touch
~90 import sites and deserves its own commit with its own verification, not a drive-by rename in a
directory sweep.

Import detection is deliberately textual (`import X`, `from X import`, `from scripts.X`) rather
than AST-based, because these files are executable scripts with side effects at import time and
importing them to inspect them would run them.

    python scripts/reorg_tree.py            # dry run: print the plan, touch nothing
    python scripts/reorg_tree.py --apply    # execute via `git mv`
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
WORKFLOWS = ROOT / ".github" / "workflows"

# Destination by filename prefix. Order matters — first match wins.
ROUTES: list[tuple[str, str]] = [
    ("diag_", "pipelines/diagnostics"),
    ("audit_", "pipelines/audit"),
    ("check_", "pipelines/audit"),
    ("render_", "pipelines/report"),
    ("export_", "pipelines/report"),
    ("spec_sheet", "pipelines/report"),
    ("build_", "pipelines/build"),
    ("harvest_", "pipelines/build"),
    ("fetch_", "pipelines/build"),
    ("scrape_", "pipelines/build"),
    ("finalize_", "pipelines/build"),
    ("scope_", "pipelines/build"),
    ("probe_", "pipelines/build"),
    ("screen_", "pipelines/research"),
    ("phase", "pipelines/research"),
    ("grade_", "pipelines/research"),
    ("mc_", "pipelines/research"),
    ("rolling_", "pipelines/research"),
    ("dry_run_", "pipelines/research"),
    ("loser_", "pipelines/research"),
    ("run_", "pipelines/research"),
]


def module_name(p: Path) -> str:
    return p.stem


def importers() -> dict[str, set[str]]:
    """{module_stem -> set of files that import it}, across the whole repo."""
    graph: dict[str, set[str]] = defaultdict(set)
    stems = {module_name(p) for p in SCRIPTS.glob("*.py")}
    for src in list(ROOT.rglob("*.py")):
        if any(part in {".git", "node_modules", "frontend", ".claude"} for part in src.parts):
            continue
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for stem in stems:
            if src.stem == stem:
                continue
            pat = rf"(?:^|\n)\s*(?:import\s+{re.escape(stem)}\b|from\s+{re.escape(stem)}\s+import|from\s+scripts\.{re.escape(stem)}\s+import)"
            if re.search(pat, text):
                graph[stem].add(str(src.relative_to(ROOT)).replace("\\", "/"))
    return graph


def path_literals() -> set[str]:
    """Module stems mentioned as a 'scripts/<name>.py' string anywhere in tests or workflows."""
    pinned: set[str] = set()
    files = list(TESTS.rglob("*.py")) + (list(WORKFLOWS.glob("*.yml")) if WORKFLOWS.exists() else [])
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r"scripts[/\\\"']+\s*[\"']?([A-Za-z0-9_]+)\.py", text):
            pinned.add(m.group(1))
        for m in re.finditer(r"[\"']scripts[\"']\s*/\s*[\"']([A-Za-z0-9_]+)\.py[\"']", text):
            pinned.add(m.group(1))
    return pinned


def destination(name: str) -> str | None:
    for prefix, dest in ROUTES:
        if name.startswith(prefix):
            return dest
    return None


def main() -> int:
    apply = "--apply" in sys.argv
    graph = importers()
    pinned_paths = path_literals()

    movable: list[tuple[Path, Path]] = []
    stay: list[tuple[str, str]] = []

    for p in sorted(SCRIPTS.glob("*.py")):
        name = module_name(p)
        if name == "reorg_tree":
            continue
        imps = graph.get(name, set())
        test_imports = {i for i in imps if i.startswith("tests/")}
        other_imports = imps - test_imports

        if name in pinned_paths:
            stay.append((name, "path literal in tests/ or workflows"))
        elif test_imports:
            stay.append((name, f"imported by {len(test_imports)} test(s)"))
        elif other_imports:
            stay.append((name, f"imported by {len(other_imports)} module(s)"))
        else:
            dest = destination(name)
            if dest is None:
                stay.append((name, "no route (unclassified)"))
            else:
                movable.append((p, ROOT / dest / p.name))

    by_dest: dict[str, list[str]] = defaultdict(list)
    for src, dst in movable:
        by_dest[str(dst.parent.relative_to(ROOT)).replace("\\", "/")].append(src.name)

    print(f"=== REORG PLAN {'(APPLYING)' if apply else '(dry run)'} ===\n")
    print(f"  scripts/*.py total : {len(list(SCRIPTS.glob('*.py')))}")
    print(f"  MOVABLE            : {len(movable)}")
    print(f"  STAYING            : {len(stay)}\n")

    for dest in sorted(by_dest):
        print(f"  -> {dest}/  ({len(by_dest[dest])} files)")
    print()

    reasons: dict[str, int] = defaultdict(int)
    for _, why in stay:
        reasons[why.split(" (")[0] if "(" not in why else why] = reasons[why] + 1
    print("  STAYING, by reason:")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>3}  {why}")
    print()
    print("  the load-bearing ones (kept, and why):")
    for name, why in sorted(stay, key=lambda s: s[0]):
        if "imported by" in why or "path literal" in why:
            print(f"    {name:<42} {why}")

    if not apply:
        print("\n  dry run — nothing moved. Re-run with --apply.")
        return 0

    for dest in sorted(by_dest):
        d = ROOT / dest
        d.mkdir(parents=True, exist_ok=True)
        init = d / "__init__.py"
        if not init.exists():
            init.write_text(f'"""{dest} — see docs/REPO_STRUCTURE.md."""\n', encoding="utf-8")
    moved = fixed = 0
    for src, dst in movable:
        r = subprocess.run(["git", "mv", str(src.relative_to(ROOT)), str(dst.relative_to(ROOT))],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            shutil.move(str(src), str(dst))
        moved += 1
        # DEPTH FIXUP — every script computes ROOT as `.parent.parent`, which assumes it sits one
        # level below the repo root. At pipelines/<area>/ that resolves to `pipelines/`, so every
        # data path silently points at the wrong tree. Rewrite to a depth-explicit form.
        try:
            text = dst.read_text(encoding="utf-8")
        except OSError:
            continue
        new = text.replace("Path(__file__).resolve().parent.parent",
                           "Path(__file__).resolve().parents[2]")
        if new != text:
            dst.write_text(new, encoding="utf-8")
            fixed += 1
    print(f"\n  moved {moved} files; rewrote ROOT depth in {fixed}.")
    print("  NOTE: moved files still `sys.path.insert(ROOT/'scripts')`, which remains correct —")
    print("  the library modules they import deliberately stayed in scripts/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
