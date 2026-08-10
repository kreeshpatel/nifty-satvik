"""Committed result artifacts must not carry stringified booleans.

`json.dumps(..., default=str)` is used in 114 places across the pipelines, and it is the right
default for timestamps and numpy scalars. It has one sharp edge: a numpy `bool_` is not a Python
`bool`, so it falls through to `default` and serialises as the STRING "True" or "False".

That is worse than a cosmetic defect. Every consumer that reads the artifact back and branches on
the value gets the wrong answer half the time, because the string "False" is truthy. A gate recorded
as failed would read as passed.

Comparisons between numpy floats produce `np.bool_`, so this is easy to reintroduce whenever a gate
verdict is computed from measured numbers -- which is exactly where it matters most. Wrap such
values in `bool()` before they reach the payload.

Introduced after `cost_sensitivity.clears_passive_at_1_5x` in 0001's results.json serialised as
'True' on 2026-08-10.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = ("research", "results")

# Prose fields legitimately contain the words True/False when describing behaviour.
PROSE_KEYS = {"note", "_doc", "reading", "reproduce", "why", "_why", "detail", "verdict", "spec_note"}


def _artifacts() -> list[Path]:
    out: list[Path] = []
    for d in SEARCH_DIRS:
        p = ROOT / d
        if p.is_dir():
            out.extend(sorted(p.rglob("*.json")))
    return out


def _offenders(node, path: str = "") -> list[str]:
    """Every leaf equal to the string 'True'/'False', with the path that reaches it."""
    found: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in PROSE_KEYS:
                found += _offenders(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += _offenders(v, f"{path}[{i}]")
    elif node in ("True", "False"):
        found.append(f"{path} = {node!r}")
    return found


def test_no_committed_artifact_carries_a_stringified_boolean():
    bad: list[str] = []
    for p in _artifacts():
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue                                   # not our problem here
        bad += [f"{p.relative_to(ROOT)}{loc}" for loc in _offenders(payload)]
    assert not bad, (
        "stringified booleans in committed artifacts -- wrap the value in bool() before it reaches "
        "json.dumps(..., default=str); the string 'False' is truthy to every consumer:\n  "
        + "\n  ".join(bad))


def test_the_detector_actually_detects():
    """Guard the guard: a passing suite must not mean the walker silently returns nothing."""
    assert _offenders({"gate": "True"}) == [".gate = 'True'"]
    assert _offenders({"arms": [{"ok": "False"}]}) == [".arms[0].ok = 'False'"]
    assert _offenders({"ok": True, "n": 1, "s": "yes"}) == []
    assert _offenders({"note": "True when the cap binds"}) == [], "prose keys are exempt"


def test_there_are_artifacts_to_check():
    assert len(_artifacts()) > 10, "a green run over an empty file list would prove nothing"
