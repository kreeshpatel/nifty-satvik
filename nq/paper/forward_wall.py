"""Forward-wall append-only, hash-chained daily log — the §3 integrity mechanism of forward/prereg.md.

ONE atomic row per trading day carries all THREE books (base, veto, drift), hashed together into a
single chain so a partial write (one book logged, another missed) cannot open a silent hole:

    row_hash = SHA-256( prior_row_hash | canonical_payload )

The genesis seed anchors the chain to the pinned dataset. :func:`append_row` recomputes and verifies
the ENTIRE existing chain before writing and REFUSES to append if any prior row was mutated or
reordered — retroactive edits are structurally blocked, not merely discouraged. No back-dating: a
row's date must be strictly after the last.

Canonical payload — fixed field order, deterministic formatting (the doc pins this construction):

    date(YYYY-MM-DD) | base_ret(.8f) | base_equity(.2f) | base_npos(int) | veto_ret | veto_equity |
    veto_npos | drift_ret | drift_equity | drift_npos

The written CSV cells ARE the canonical strings, so read-back re-hashes identically (no float
round-trip drift).
"""
from __future__ import annotations

import csv
import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from config import RESULTS_DIR

BOOKS: tuple[str, ...] = ("base", "veto", "drift")
_METRICS: tuple[str, ...] = ("ret", "equity", "npos")
DATA_FIELDS: list[str] = ["date"] + [f"{b}_{m}" for b in BOOKS for m in _METRICS]
FIELDS: list[str] = DATA_FIELDS + ["row_hash"]

# Genesis seed: SHA-256 of a fixed preimage tying the chain to the pinned dataset. Pinned in
# forward/prereg.md §3 — changing it (or the hash construction) breaks verification of every prior
# row against the doc, which is the point: the doc is the contract.
GENESIS: str = hashlib.sha256(b"nifty-satvik/forward-wall/genesis@dataset-pin-20260701").hexdigest()
DEFAULT_LOG: Path = RESULTS_DIR / "forward_wall.csv"


class IntegrityError(RuntimeError):
    """Raised when the chain fails to verify — a tampered, reordered, or back-dated log."""


def _canon_parts(row: Mapping[str, Any]) -> list[str]:
    """Canonical, deterministically-formatted field strings in the fixed order."""
    parts = [str(row["date"])[:10]]
    for b in BOOKS:
        parts.append(f"{float(row[f'{b}_ret']):.8f}")
        parts.append(f"{float(row[f'{b}_equity']):.2f}")
        parts.append(str(int(row[f'{b}_npos'])))
    return parts


def _chain_hash(prior: str, parts: Sequence[str]) -> str:
    return hashlib.sha256(f"{prior}|{'|'.join(parts)}".encode()).hexdigest()


def _load(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_chain(rows: Sequence[Mapping[str, str]]) -> tuple[bool, int]:
    """Recompute the chain from GENESIS. Returns ``(ok, first_bad_index)`` — ``(True, -1)`` if intact.
    Position-sensitive: a reordered row breaks the chain because each hash binds its predecessor."""
    prior = GENESIS
    for i, r in enumerate(rows):
        parts = [r[f] for f in DATA_FIELDS]        # already-canonical strings, as written
        if _chain_hash(prior, parts) != r["row_hash"]:
            return False, i
        prior = r["row_hash"]
    return True, -1


def append_row(row: Mapping[str, Any], path: str | Path = DEFAULT_LOG) -> str:
    """Verify the entire existing chain, then atomically append ONE row (all three books, one hash).
    Refuses (:class:`IntegrityError`) if the existing chain is broken or the date is not strictly
    after the last logged date. Returns the new ``row_hash``."""
    path = Path(path)
    rows = _load(path)
    ok, bad = verify_chain(rows)
    if not ok:
        raise IntegrityError(f"existing chain fails to verify at row {bad}; refusing to append")
    date = str(row["date"])[:10]
    if rows and date <= rows[-1]["date"]:
        raise IntegrityError(f"no back-dating: {date} <= last logged {rows[-1]['date']}")
    parts = _canon_parts(row)
    prior = rows[-1]["row_hash"] if rows else GENESIS
    h = _chain_hash(prior, parts)
    new = dict(zip(DATA_FIELDS, parts))
    new["row_hash"] = h
    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(new)
    return h


def read_verified(path: str | Path = DEFAULT_LOG) -> list[dict[str, str]]:
    """Load the log and raise :class:`IntegrityError` if the chain does not verify."""
    rows = _load(Path(path))
    ok, bad = verify_chain(rows)
    if not ok:
        raise IntegrityError(f"chain fails to verify at row {bad}")
    return rows
