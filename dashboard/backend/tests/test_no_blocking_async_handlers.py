"""No route handler may be `async def` without awaiting anything (2026-11-05 login outage).

An `async def` handler runs on the event loop, so any sync work inside it (SQLAlchemy, requests, yfinance)
blocks every other request, the health check included. One hung DB socket after a Fly resume froze the
whole API. A handler with nothing to await must be a plain `def`: FastAPI runs those in its threadpool.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTE_ATTRS = {"get", "post", "put", "delete", "patch", "api_route"}


def _offenders():
    out = []
    for f in sorted(ROOT.rglob("*.py")):
        if "tests" in f.parts or "venv" in f.parts or ".venv" in f.parts:
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if not isinstance(n, ast.AsyncFunctionDef):
                continue
            is_route = any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") in ROUTE_ATTRS
                           for d in n.decorator_list)
            if is_route and not any(isinstance(x, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for x in ast.walk(n)):
                out.append(f"{f.relative_to(ROOT)}:{n.lineno} {n.name}")
    return out


def test_no_async_route_handler_without_an_await():
    assert _offenders() == [], "make these plain `def` so FastAPI threadpools them:\n" + "\n".join(_offenders())
