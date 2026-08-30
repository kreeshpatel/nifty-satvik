#!/usr/bin/env python3
"""Every SHORT-WINDOW `download_ohlcv` call must pass ``min_bars=1``.

WHY THIS EXISTS. `download_ohlcv` drops any name returning fewer than ``min_bars`` usable bars.
The default of 50 is right for a full-history pull and fatal for an incremental top-up, where the
window is a few weeks: every name is discarded, `merge_ohlcv` folds an empty dict into the cache,
and the job prints a success line over data that did not move. Nothing raises. Nothing goes red.

It has now happened twice, in two different callers:

  * `run_bhanushali_cron` held the LIVE swing book at 2026-07-31 through a successful 2026-08-10
    run. Fixed 2026-08, and the fix was guarded by a test asserting one literal line of that file.
  * `run_paper_cron` then did the same thing to the forward wall. Five green runs, 2026-08-24 to
    2026-08-28, left the OHLCV cache at 2026-08-21, rebuilt a byte-identical factor panel and
    appended 0 rows to `results/forward_wall.csv` — while committing a message naming a daily log
    it had not written. `forward/prereg.md` §3 registers that wall, so a pre-registered forward
    record lost five sessions. The line-pinning test stayed green throughout: it was watching the
    other file.

A guard that pins one call site cannot see the second one. This checks the CONTRACT wherever it
applies, so the third caller is caught before it is written.

WHAT IT CHECKS. A call is short-window if its ``start=`` argument resolves — through at most one
local assignment in the enclosing function — to an expression containing ``timedelta(days=N)`` with
N < MIN_SAFE_WINDOW_DAYS. Such a call must pass ``min_bars`` explicitly.

WHAT IT CANNOT CHECK. A window whose length is only known at runtime (a variable, a CLI argument, a
config value) is invisible here and passes. The rule is deliberately narrow: it fires on a literal
day count small enough to be provably fatal, so a green run means no call site is *provably* wrong,
not that every call site is right. `nq/data/ohlcv.py`'s docstring remains the statement of the rule;
this only enforces the part a script can see.

Stdlib only.

    run with: python scripts/check_ohlcv_topup_contract.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SEARCH_DIRS = ["scripts", "nq", "pipelines", "dashboard"]
SKIP_PARTS = {"node_modules", "__pycache__", ".git", "build", "dist"}

# 50 sessions need ~70 calendar days. A window at or above this can satisfy the default on its own,
# so the default is not provably fatal there and the call is left alone.
MIN_SAFE_WINDOW_DAYS = 70


def _timedelta_days(node: ast.AST) -> list[int]:
    """Literal `days=` values of every timedelta/Timedelta call inside `node`."""
    out: list[int] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        fn = sub.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name not in {"timedelta", "Timedelta"}:
            continue
        for kw in sub.keywords:
            if kw.arg == "days" and isinstance(kw.value, ast.Constant) \
                    and isinstance(kw.value.value, int):
                out.append(kw.value.value)
    return out


def _assignments(scope: ast.AST) -> dict[str, list[ast.AST]]:
    """{name -> [assigned expressions]} for simple `name = expr` bindings in this scope."""
    out: dict[str, list[ast.AST]] = {}
    for sub in ast.walk(scope):
        if isinstance(sub, ast.Assign):
            for t in sub.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(sub.value)
        elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name) and sub.value:
            out.setdefault(sub.target.id, []).append(sub.value)
    return out


def _calls_by_scope(tree: ast.AST):
    """Yield (call_node, enclosing_scope) with each call attributed to its INNERMOST scope.

    Walking every scope independently would report a nested call once per enclosing scope, and
    unioning all scopes' bindings would let a same-named variable in a sibling function decide this
    call's window. Descending once, carrying the current scope, gives each call exactly one owner.
    """
    def walk(node: ast.AST, scope: ast.AST):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                yield from walk(child, child)
                continue
            if isinstance(child, ast.Call):
                yield child, scope
            yield from walk(child, scope)
    yield from walk(tree, tree)


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for d in SEARCH_DIRS:
        base = ROOT / d
        if base.exists():
            files += [p for p in base.rglob("*.py") if not (SKIP_PARTS & set(p.parts))]
    return sorted(files)


def verify() -> list[str]:
    """Failure messages, one per short-window call that relies on the default. Empty means all hold."""
    problems: list[str] = []
    for f in iter_source_files():
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        binds_cache: dict[int, dict[str, list[ast.AST]]] = {}
        for node, scope in _calls_by_scope(tree):
            if getattr(node.func, "id", getattr(node.func, "attr", "")) != "download_ohlcv":
                continue
            start = next((k.value for k in node.keywords if k.arg == "start"), None)
            if start is None:
                continue
            days = _timedelta_days(start)
            if isinstance(start, ast.Name):              # one hop through a local binding
                binds = binds_cache.setdefault(id(scope), _assignments(scope))
                for expr in binds.get(start.id, []):
                    days += _timedelta_days(expr)
            short = [d for d in days if d < MIN_SAFE_WINDOW_DAYS]
            if not short or any(k.arg == "min_bars" for k in node.keywords):
                continue
            problems.append(
                f"{f.relative_to(ROOT).as_posix()}:{node.lineno}: download_ohlcv() over a "
                f"{min(short)}-day window relies on the default min_bars=50, which needs ~"
                f"{MIN_SAFE_WINDOW_DAYS}+ days. Every name will be dropped and the cache will "
                f"not advance, silently. Pass min_bars=1.")
    return problems


def main() -> int:
    problems = verify()
    for p in problems:
        print(f"::error::{p}")
    n = len(iter_source_files())
    print(f"checked {n} file(s) for short-window download_ohlcv calls: "
          f"{'contract holds' if not problems else f'{len(problems)} VIOLATION(S)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
