"""The overlay registry must name the current anchor, because it is read before anything else.

`CLAUDE.md`'s registry-first rule sends every session to `research/overlay_registry.md` before it
proposes anything. Its §4 "the baseline everything is measured against" stated `baseline_v0` —
26.1% CAGR / 1.02 Sharpe / −41.9% maxDD — for five weeks after ADR-0006 superseded it with
`baseline_v1` at 15.46% / 0.667 / −46.26% on 2026-07-01.

That is not a cosmetic staleness. A candidate judged against a base 10.65pp higher in CAGR and 0.35
higher in Sharpe is judged against a bar it cannot clear, and the programme's own record shows the
gap was OHLCV price vintage rather than engine (`baseline_v1.json.delta_vs_v0`) — so the harder bar
was never a real one. The archaeology of 2026-08-08 found this to be a contributing cause across the
E1-epoch verdicts.

Same pattern as `tests/test_standing_counts.py`: the prose may exist, and it may not disagree with
its source. The superseded figures are deliberately still in the file, marked as history for the
rows that cite them, so this test asserts the *correction* is present rather than that the old
numbers are gone.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "research" / "overlay_registry.md"
ANCHOR = ROOT / "research" / "baseline_v1.json"


@pytest.fixture(scope="module")
def registry() -> str:
    return REGISTRY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def gross() -> dict:
    return json.loads(ANCHOR.read_text(encoding="utf-8"))["gross"]


@pytest.mark.parametrize("field", ["cagr_pct", "sharpe", "max_drawdown_pct"])
def test_the_registry_states_the_current_anchor(registry: str, gross: dict, field: str):
    want = str(abs(gross[field]))
    assert want in registry, (
        f"research/overlay_registry.md does not state baseline_v1 gross {field} = {gross[field]}. "
        f"It is the first file a session reads under the registry-first rule; an anchor that "
        f"disagrees with research/baseline_v1.json sends every comparison to the wrong bar."
    )


def test_the_superseded_anchor_is_labelled_rather_than_left_bare(registry: str):
    """`baseline_v0`'s numbers may stay — rows below were genuinely measured against them — but they
    may not read as current."""
    if "26.1" not in registry:
        pytest.skip("the superseded figures have been removed entirely, which is also fine")
    head = registry[: registry.index("26.1")]
    assert re.search(r"CORRECTED|SUPERSEDED|baseline_v1", head, re.I), (
        "the baseline_v0 figures appear with no correction ahead of them, so a session reading "
        "top-down takes 26.1%/1.02 as the anchor of record"
    )


def test_the_anchor_file_is_named(registry: str):
    assert "baseline_v1.json" in registry, (
        "the registry must point at the anchor file, not only quote its numbers — the numbers are "
        "what drift, the path is what stays checkable"
    )
