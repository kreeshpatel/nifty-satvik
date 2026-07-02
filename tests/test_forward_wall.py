"""Forward-wall hash-chain integrity tests — the acceptance criterion for forward/prereg.md §3.

The harness is not "done" because it writes three books; it is done because a mutated or reordered
historical row makes the chain refuse the next append. These tests ARE that guarantee.
"""
from __future__ import annotations

import csv

import pytest

from nq.paper.forward_wall import (FIELDS, GENESIS, IntegrityError, append_row,
                                   read_verified, verify_chain)


def _row(date: str, eq: float = 1_000_000.0) -> dict:
    r: dict = {"date": date, "status": "ok", "drift_mult": 1.0}
    for b in ("base", "veto", "drift"):
        r[f"{b}_ret"] = 0.001234
        r[f"{b}_equity"] = eq
        r[f"{b}_npos"] = 15
    return r


def _read(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _rewrite(path, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def test_append_and_verify_atomic_three_books(tmp_path):
    log = tmp_path / "wall.csv"
    append_row(_row("2026-07-03"), log)
    append_row(_row("2026-07-04", 1_010_000.0), log)
    append_row(_row("2026-07-06", 1_020_000.0), log)
    rows = _read(log)
    assert len(rows) == 3
    assert all(f in rows[0] for f in FIELDS)                # one atomic row carries all 3 books
    for b in ("base", "veto", "drift"):
        assert rows[0][f"{b}_equity"] and rows[0][f"{b}_npos"] == "15"
    assert rows[0]["drift_mult"] == "1.0000"
    ok, bad = verify_chain(rows)
    assert ok and bad == -1
    assert read_verified(log) == rows                        # first row chains off the pinned genesis


def test_tampered_historical_row_refuses_next_append(tmp_path):
    log = tmp_path / "wall.csv"
    append_row(_row("2026-07-03"), log)
    append_row(_row("2026-07-04", 1_010_000.0), log)
    rows = _read(log)
    rows[0]["base_equity"] = "999999.99"                     # mutate a historical row's content
    _rewrite(log, rows)
    ok, bad = verify_chain(_read(log))
    assert not ok and bad == 0
    with pytest.raises(IntegrityError):
        append_row(_row("2026-07-06", 1_020_000.0), log)


def test_reordered_rows_break_chain(tmp_path):
    log = tmp_path / "wall.csv"
    for d, e in [("2026-07-03", 1e6), ("2026-07-04", 1.01e6), ("2026-07-06", 1.02e6)]:
        append_row(_row(d, e), log)
    rows = _read(log)
    rows[0], rows[1] = rows[1], rows[0]                      # same payloads, wrong positions
    _rewrite(log, rows)
    ok, _bad = verify_chain(_read(log))
    assert not ok                                            # position-sensitive: prior-hash binding
    with pytest.raises(IntegrityError):
        append_row(_row("2026-07-07"), log)


def test_no_backdating(tmp_path):
    log = tmp_path / "wall.csv"
    append_row(_row("2026-07-04"), log)
    with pytest.raises(IntegrityError):
        append_row(_row("2026-07-03"), log)                 # earlier than last logged


def test_genesis_is_pinned():
    import hashlib
    assert GENESIS == hashlib.sha256(b"nifty-satvik/forward-wall/genesis@dataset-pin-20260701").hexdigest()
