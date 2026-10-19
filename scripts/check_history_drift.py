"""History tripwire: the forward record must not change undeclared.

`scripts/archive_weekly_snapshot.py` appends one line per scan to ``results/archive/drift_log.jsonl``
comparing the rebuilt weekly history with the previous snapshot. A trade that was restated, or that
VANISHED (closed or still open), means the past was rewritten by the rebuild-from-inception design -
the 2026-10-16 scan did exactly that (ZYDUSWELL displaced HINDZINC, ABDL displaced BANDHANBNK) and it
sat in the log unread. This reads the LAST entry and exits 1 (``::error::``) on any restated /
vanished / vanished_open trade not declared in ``results/history_restatements.json``
(``{"<TICKER|date>": "dated reason"}``) - the route for an expected, deliberate restatement.

``appeared`` (newly closed trades) is the normal way a history grows and never fails the check.
Read-only: it writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIFT_LOG = ROOT / "results" / "archive" / "drift_log.jsonl"
DECLARED = ROOT / "results" / "history_restatements.json"


def last_entry(path: Path) -> dict | None:
    if not path.exists():
        return None
    rows = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return json.loads(rows[-1]) if rows else None


def undeclared(entry: dict, declared: dict) -> list[tuple[str, str]]:
    """``[(kind, trade_key)]`` for every changed past trade not named in ``declared``."""
    found: list[tuple[str, str]] = []
    for r in entry.get("restated") or []:
        found.append(("restated", r["trade"] if isinstance(r, dict) else str(r)))
    for k in entry.get("vanished") or []:
        found.append(("vanished", str(k)))
    for k in entry.get("vanished_open") or []:
        found.append(("vanished_open", str(k)))
    return [(kind, key) for kind, key in found if not str(declared.get(key, "")).strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--log", type=Path, default=DRIFT_LOG)
    ap.add_argument("--declared", type=Path, default=DECLARED)
    a = ap.parse_args(argv)
    entry = last_entry(a.log)
    if entry is None:
        print(f"history drift: no entries in {a.log} - nothing to check")
        return 0
    declared = json.loads(a.declared.read_text(encoding="utf-8")) if a.declared.exists() else {}
    bad = undeclared(entry, declared)
    asof = entry.get("as_of") or entry.get("cur_snapshot")
    if not bad:
        print(f"history drift: as_of {asof} - no undeclared restated/vanished trades "
              f"({entry.get('n_appeared', 0)} appeared, which is normal)")
        return 0
    for kind, key in bad:
        print(f"::error::history changed undeclared ({kind}): {key} at as_of {asof} - declare it in "
              f"{a.declared.name} with a dated reason if deliberate, otherwise find what rewrote the past")
    return 1


if __name__ == "__main__":
    sys.exit(main())
