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


def test_no_published_field_is_unread_without_a_recorded_reason():
    """The ratchet. Every field the book publishes is either read by a surface, or declared in
    `INTENTIONALLY_UNREAD` with the reason it stays unread.

    Without this the unread list is a report: it can grow and nothing stops it. A published field
    nobody reads is a decision the model made and the product withheld, and "nobody looked" is not
    an acceptable reason for that — "engine-internal, because X" is. This makes the next such
    field fail here instead of sitting in a doc until someone happens to scan it.

    Asserts against the generator's own join rather than a second implementation of it, so the
    test and the doc cannot agree while both are wrong.
    """
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from gen_wiring_map import undeclared_unread

    missing = undeclared_unread()
    assert not missing, (
        "these published fields are read by nothing and have no recorded reason:\n"
        + "\n".join(f"  {rel}: {', '.join(fs)}" for rel, fs in missing.items())
        + "\n\nWire each to a surface, or add it to INTENTIONALLY_UNREAD in "
          "scripts/gen_wiring_map.py with the reason it stays unread."
    )


def test_the_status_column_survives_a_week_with_no_stopped_out_name():
    """The map must not churn on data. It briefly did, and that is the harder failure to notice.

    The `card statuses` column was read from the CURRENT envelope only, so the mix of card statuses
    in one Saturday's scan decided it. The 2026-08-29 scan carried no HIT_STOP card, which dropped
    `HIT_STOP` from nineteen rows at once and turned this file red on a cron commit that changed no
    code. A map that reports a data fluctuation as a wiring change trains its reader to regenerate
    without looking — which is exactly how a real wiring change would then slip past.

    Reading the archive union makes an absent status silent and a genuinely NEW one still a diff.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_wiring_map", GEN)
    gen = importlib.util.module_from_spec(spec)
    sys.modules["gen_wiring_map"] = gen
    spec.loader.exec_module(gen)

    rel = "results/signals_today_weekly.json"

    def statuses(blob):
        return {str(r.get("status") or "") for r in (blob.get("signals") or [])}

    current = statuses(gen.json.loads((ROOT / rel).read_text(encoding="utf-8")))
    archived = set().union(*(statuses(b) for b in gen._archived(rel))) if gen._archived(rel) else set()
    only_archived = archived - current
    assert only_archived, (
        "no status exists only in the archive, so this test cannot prove the union is being used. "
        "Re-point it at a producer whose archive is richer than its current file.")

    listed = {s for shapes in gen.envelope_fields()[rel].values() for s in shapes}
    assert only_archived <= listed, (
        f"{sorted(only_archived)} appear only in the archive and are absent from the generated map "
        "— the column is being read from the current envelope alone, and will churn every week the "
        "card mix changes")
