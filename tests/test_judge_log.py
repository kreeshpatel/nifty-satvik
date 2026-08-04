"""Integrity tests for the informed-judge hash-chained log (pre-reg 0125)."""
from __future__ import annotations

import json

import pytest

from nq.paper.judge_log import (
    GENESIS, IntegrityError, append_row, logged_keys, read_verified, verify_chain,
)


def _row(ticker: str, as_of: str = "2026-08-01") -> dict:
    return {"as_of": as_of, "ticker": ticker, "ok": True, "verdict": "take", "conviction": 3}


def test_empty_log_verifies_and_genesis_is_pinned(tmp_path):
    assert verify_chain([]) == (True, -1)
    # A changed genesis preimage would silently orphan every prior row — pin it.
    assert GENESIS == __import__("hashlib").sha256(
        b"nifty-satvik/informed-judge/genesis@prereg-0125").hexdigest()
    assert read_verified(tmp_path / "absent.jsonl") == []


def test_append_assigns_seq_and_chains(tmp_path):
    p = tmp_path / "judge.jsonl"
    h1 = append_row(_row("AAA"), p)
    h2 = append_row(_row("BBB"), p)
    rows = read_verified(p)
    assert [r["seq"] for r in rows] == [0, 1]
    assert rows[0]["row_hash"] == h1 and rows[1]["row_hash"] == h2
    assert h1 != h2


def test_duplicate_card_is_refused(tmp_path):
    """A replayed cron run must not double-log a card."""
    p = tmp_path / "judge.jsonl"
    append_row(_row("AAA"), p)
    with pytest.raises(IntegrityError, match="duplicate card"):
        append_row(_row("AAA"), p)
    # same ticker, different week is fine
    append_row(_row("AAA", as_of="2026-08-08"), p)
    assert len(read_verified(p)) == 2


def test_logged_keys_drives_idempotency(tmp_path):
    p = tmp_path / "judge.jsonl"
    append_row(_row("AAA"), p)
    append_row(_row("BBB"), p)
    assert logged_keys(p) == {("2026-08-01", "AAA"), ("2026-08-01", "BBB")}


def test_edited_row_breaks_the_chain(tmp_path):
    p = tmp_path / "judge.jsonl"
    append_row(_row("AAA"), p)
    append_row(_row("BBB"), p)
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    rows[0]["verdict"] = "skip"                              # tamper with a logged verdict
    p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
    ok, bad = verify_chain(rows)
    assert not ok and bad == 0
    with pytest.raises(IntegrityError):
        read_verified(p)


def test_reordering_breaks_the_chain(tmp_path):
    """Position-sensitive: each hash binds its predecessor, so a swap is detectable."""
    p = tmp_path / "judge.jsonl"
    append_row(_row("AAA"), p)
    append_row(_row("BBB"), p)
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    ok, bad = verify_chain(list(reversed(rows)))
    assert not ok and bad == 0


def test_deleted_row_breaks_the_chain(tmp_path):
    p = tmp_path / "judge.jsonl"
    for t in ("AAA", "BBB", "CCC"):
        append_row(_row(t), p)
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    ok, bad = verify_chain([rows[0], rows[2]])               # middle row silently dropped
    assert not ok and bad == 1


def test_append_refuses_onto_a_broken_chain(tmp_path):
    p = tmp_path / "judge.jsonl"
    append_row(_row("AAA"), p)
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    rows[0]["ok"] = False
    p.write_text(json.dumps(rows[0], sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="refusing to append"):
        append_row(_row("BBB"), p)


def test_failure_rows_are_logged_like_any_other(tmp_path):
    """A failed call is a record of what was attempted, not an absence."""
    p = tmp_path / "judge.jsonl"
    append_row({"as_of": "2026-08-01", "ticker": "AAA", "ok": False, "error": "APIError: boom"}, p)
    rows = read_verified(p)
    assert rows[0]["ok"] is False and "boom" in rows[0]["error"]
