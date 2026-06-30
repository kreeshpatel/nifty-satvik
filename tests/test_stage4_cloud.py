"""F4 — cloud run-script: universe assembly (hermetic; no network).

The download + full backtest run on GitHub Actions (cpcv-research.yml); here we pin only the
pure universe-assembly logic that decides which names the cloud run pulls."""
from __future__ import annotations

import pytest

from config import NIFTY_500
from scripts.run_cpcv import build_universe


def test_universe_current_is_the_snapshot():
    assert build_universe("current") == list(NIFTY_500)


def test_universe_union_is_superset_with_members():
    union = build_universe("union")
    assert set(NIFTY_500).issubset(set(union))      # never drops a snapshot name
    assert len(union) >= len(NIFTY_500)             # adds current members joined since the snapshot


def test_universe_unknown_mode_raises():
    with pytest.raises(ValueError):
        build_universe("delisted-too")
