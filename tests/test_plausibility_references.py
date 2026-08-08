"""The plausibility anchors must not drift from the artifacts they claim to quote.

`docs/references/plausibility_anchors.md` exists so that "does that number look right?" is answered
against a source instead of a recollection. That only works while the page agrees with the source —
a stale anchor is worse than none, because it is quoted with the confidence of a citation. Same
pattern as `tests/test_standing_counts.py`: the prose may exist, it may not disagree.

The second half guards something subtler. `external_literature.md` is deliberately empty, and its
emptiness is load-bearing: the `plausibility-check` skill tells sessions to say the file is
unpopulated rather than supply a published band from memory. If someone ever fills it in with
plausible-looking ranges and no sources, that instruction silently becomes a lie with a filename.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ANCHORS = ROOT / "docs" / "references" / "plausibility_anchors.md"
EXTERNAL = ROOT / "docs" / "references" / "external_literature.md"
BASELINE = ROOT / "research" / "baseline_v1.json"
N_TRIALS = ROOT / "diagnostics" / "research" / "n_trials.json"
CONFIG = ROOT / "config.py"


@pytest.fixture(scope="module")
def anchors() -> str:
    return ANCHORS.read_text(encoding="utf-8")


@pytest.mark.parametrize("field", ["sharpe", "cagr_pct", "max_drawdown_pct"])
def test_headline_metrics_match_baseline_v1(anchors: str, field: str):
    want = json.loads(BASELINE.read_text(encoding="utf-8"))["gross"][field]
    assert str(abs(want)) in anchors, (
        f"plausibility_anchors.md no longer states baseline_v1 gross {field} = {want}. "
        f"research/baseline_v1.json is the authority; update the page, not the anchor."
    )


def test_the_pin_hash_prefix_matches(anchors: str):
    sha = json.loads(BASELINE.read_text(encoding="utf-8"))["pin"]["ohlcv_sha256"]
    assert sha[:8] in anchors, f"the anchors page cites a different pin than {sha[:8]}…"


def test_the_resolution_floor_matches_the_measurement(anchors: str):
    """n_eff and the dSharpe half-width are the most-quoted numbers in the programme — they decide
    whether a candidate is even resolvable, so a stale copy silently revives dead candidates."""
    reset = json.loads(N_TRIALS.read_text(encoding="utf-8"))["_reset"]
    source = reset["what_this_does_NOT_change"]
    n_eff = re.search(r"n_eff\s*=\s*(\d+)", source)
    half_width = re.search(r"half-width of (\d+\.\d+)", source)
    assert n_eff and half_width, "n_trials.json no longer states n_eff / half-width — update both"
    assert n_eff.group(1) in anchors, f"anchors page disagrees on n_eff (authority: {n_eff.group(1)})"
    assert half_width.group(1) in anchors, "anchors page disagrees on the dSharpe half-width"


def test_the_cost_stack_matches_config(anchors: str):
    text = CONFIG.read_text(encoding="utf-8")
    for const in ("BROKERAGE_PCT", "STT_PCT"):
        value = float(re.search(rf"^{const}\s*=\s*([\d.]+)", text, re.M).group(1)) * 100
        # The page may write 0.1% or 0.10% — both are the same rate, and only the rate is asserted.
        assert any(f"{value:{fmt}}%" in anchors for fmt in ("g", ".2f")), (
            f"anchors page states a {const} other than {value:g}% (config.py is the authority)"
        )


# --------------------------------------------------------------- the stub must stay honest
def test_external_literature_declares_itself_unpopulated():
    text = EXTERNAL.read_text(encoding="utf-8")
    assert "NOT POPULATED" in text or "STUB" in text.upper(), (
        "external_literature.md no longer declares itself a stub. If it has been populated, delete "
        "this test and add one asserting every entry carries a source; if it has not, restore the "
        "declaration — the plausibility-check skill tells sessions to rely on it."
    )


def test_an_unpopulated_stub_carries_no_bands():
    """A range like '14-18%' or '50-70%' in an empty stub is a band from memory. That is the exact
    artifact the file exists to refuse: unciteable, and quoted forever once it has a filename."""
    text = EXTERNAL.read_text(encoding="utf-8")
    if "NOT POPULATED" not in text and "STUB" not in text.upper():
        pytest.skip("stub has been populated — bands are expected, sourcing is tested elsewhere")
    bands = re.findall(r"\b\d{1,3}\s*[-–—]\s*\d{1,3}\s*%", text)
    assert not bands, (
        f"external_literature.md still declares itself unpopulated but states band(s) {bands}. "
        f"Either cite them properly (source, universe, period, costs, horizon) or remove them."
    )


def test_the_anchors_page_points_at_the_stub(anchors: str):
    assert "external_literature.md" in anchors and "NOT POPULATED" in anchors, (
        "the anchors page must say plainly that no external band is committed — otherwise a session "
        "reading only that page will assume one exists."
    )
