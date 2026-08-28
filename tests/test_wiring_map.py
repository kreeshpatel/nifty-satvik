"""The product wiring map must be regenerated with the code it describes.

A generated map that lags its source is worse than no map: it is read with the same trust and
answers with stale facts. `docs/DEPENDENCY_MAP.md` has this guarantee via the pre-commit hook;
these give `docs/PRODUCT_WIRING.md` the same one, and make the check survive a clone where
`core.hooksPath` was never set.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "gen_wiring_map.py"
OUT = ROOT / "docs" / "PRODUCT_WIRING.md"


def _regenerate() -> str:
    """Run the generator into a scratch copy and return what it WOULD write."""
    before = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    subprocess.run([sys.executable, str(GEN)], check=True, capture_output=True, cwd=ROOT)
    after = OUT.read_text(encoding="utf-8")
    if before is not None and before != after:
        OUT.write_text(before, encoding="utf-8")     # leave the tree as we found it
    return after


def test_the_committed_map_matches_the_code_it_describes():
    committed = OUT.read_text(encoding="utf-8")
    assert committed == _regenerate(), (
        "docs/PRODUCT_WIRING.md is stale. Regenerate it in the same commit as the change that "
        "moved a field:\n\n    python scripts/gen_wiring_map.py\n"
    )


def test_regeneration_is_deterministic():
    """Two runs, byte-identical — or the map cannot be diffed and nobody will read the diff."""
    assert _regenerate() == _regenerate()


def test_the_map_names_the_alias_hazards_that_have_actually_bitten():
    """The hazard table is the map's whole point: the ticks prove reference, this proves the
    reader was warned about the pairs where reference is not enough."""
    body = OUT.read_text(encoding="utf-8")
    for pair in ("`buy_zone_low` | `entry_low`", "`window_filled` | `filled_today`"):
        assert pair in body, f"the map no longer warns about {pair}"
