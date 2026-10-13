"""ADR-0017: the live scan downloads current PIT members, so successors of dead symbols are scanned."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.membership import current_members, load_membership  # noqa: E402
from run_cpcv import build_universe  # noqa: E402


def test_the_cron_downloads_the_union_not_the_stale_snapshot():
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    body = src[src.index("def _refresh_ohlcv"):src.index("def _detect_readjusted")]
    assert 'build_universe("union")' in body and 'build_universe("current")' not in body


def test_every_current_member_is_downloaded():
    """The defect was a member that was never scanned. Union must cover all of them."""
    missing = current_members(load_membership()) - set(build_universe("union"))
    assert not missing, f"current members the live scan would not download: {sorted(missing)}"


def test_the_known_successors_are_in_the_live_universe():
    u = set(build_universe("union"))
    for t in ("TMPV", "TMCV", "LTM", "PIRAMALFIN", "SWANCORP"):
        assert t in u, f"{t} is a current member and must be scanned"


def test_the_change_is_recorded_as_a_dated_owner_decision():
    import json
    cfg = json.loads((ROOT / "models" / "bhanushali_weekly" / "config.json").read_text(encoding="utf-8"))
    assert cfg["live_universe_change"].startswith("2026-10-13 (owner decision)")
    assert (ROOT / "docs" / "decisions" / "0017-live-universe-union.md").is_file()
