"""Append-only, hash-chained JSONL log for the informed-judge forward stream (pre-reg 0125).

Same integrity construction as ``nq.paper.forward_wall`` — each row's hash binds its predecessor, so
a reordered, back-dated, edited, or silently deleted row breaks verification — but shaped for the
judge's needs rather than the wall's fixed three-book row:

* **JSONL, free-form payload.** The wall logs a fixed numeric row per trading day; the judge logs one
  variable-shape row per *card*, including the raw request/response it is a record of.
* **Monotonic ``seq`` instead of monotonic date.** Many cards share one Saturday, so the wall's
  "date must be strictly after the last" rule cannot apply. ``seq`` is the ordering invariant.
* **Idempotency by ``(as_of, ticker)``.** A replayed cron run must not double-log a card, and the
  scanner is explicitly allowed to re-run.

Rows are never rewritten. A correction is a new row whose ``supersedes`` names the prior ``row_hash``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from config import RESULTS_DIR

# Ties the chain to this pre-registration. Changing the preimage (or the hash construction) breaks
# verification of every prior row against the doc — which is the point: the doc is the contract.
GENESIS: str = hashlib.sha256(b"nifty-satvik/informed-judge/genesis@prereg-0125").hexdigest()
DEFAULT_LOG: Path = RESULTS_DIR / "judge_log.jsonl"


class IntegrityError(RuntimeError):
    """Raised when the chain fails to verify — a tampered, reordered, or back-dated log."""


def _canon(payload: Mapping[str, Any]) -> str:
    """Canonical JSON of everything except the chain field itself. Sorted keys + tight separators, so
    two semantically identical rows always hash identically."""
    body = {k: v for k, v in payload.items() if k != "row_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _chain_hash(prior: str, canon: str) -> str:
    return hashlib.sha256(f"{prior}|{canon}".encode()).hexdigest()


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def verify_chain(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, int]:
    """Recompute from GENESIS. ``(True, -1)`` if intact, else ``(False, first_bad_index)``.
    Position-sensitive: a reordered row breaks the chain because each hash binds its predecessor."""
    prior = GENESIS
    for i, r in enumerate(rows):
        if _chain_hash(prior, _canon(r)) != r.get("row_hash"):
            return False, i
        prior = r["row_hash"]
    return True, -1


def logged_keys(path: str | Path = DEFAULT_LOG) -> set[tuple[str, str]]:
    """``{(as_of, ticker)}`` already present — the idempotency set a re-run consults."""
    return {(str(r.get("as_of")), str(r.get("ticker"))) for r in _load(Path(path))}


def append_row(payload: Mapping[str, Any], path: str | Path = DEFAULT_LOG) -> str:
    """Verify the whole existing chain, then atomically append ONE row. Returns the new ``row_hash``.

    Refuses (:class:`IntegrityError`) if the chain is broken, if ``seq`` is not strictly increasing,
    or if ``(as_of, ticker)`` is already logged. ``seq`` is assigned here, not by the caller.
    """
    path = Path(path)
    rows = _load(path)
    ok, bad = verify_chain(rows)
    if not ok:
        raise IntegrityError(f"existing chain fails to verify at row {bad}; refusing to append")

    key = (str(payload.get("as_of")), str(payload.get("ticker")))
    if key in {(str(r.get("as_of")), str(r.get("ticker"))) for r in rows}:
        raise IntegrityError(f"duplicate card {key}; a re-run must skip already-logged cards")

    row = dict(payload)
    row["seq"] = (int(rows[-1]["seq"]) + 1) if rows else 0
    prior = rows[-1]["row_hash"] if rows else GENESIS
    row["row_hash"] = _chain_hash(prior, _canon(row))

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    return row["row_hash"]


def read_verified(path: str | Path = DEFAULT_LOG) -> list[dict[str, Any]]:
    """Load and raise :class:`IntegrityError` if the chain does not verify.

    NOTE — pre-reg 0125 §5: the judge log is SEALED. This reader exists for integrity checks and for
    the first quarterly review read. It is not to be called from any path that could surface a
    verdict to the owner before then.
    """
    rows = _load(Path(path))
    ok, bad = verify_chain(rows)
    if not ok:
        raise IntegrityError(f"chain fails to verify at row {bad}")
    return rows


def iter_rows(path: str | Path = DEFAULT_LOG) -> Iterator[dict[str, Any]]:
    yield from read_verified(path)
