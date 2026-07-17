"""Stage-2: the immutable signal-snapshot floor (services/signal_snapshots.py).

Covers the contract: a signal frozen once NEVER changes on a recompute (the card a user
acted on is immutable), the hash chain links rows, and the integrity gate quarantines a
bad signal. (The Postgres append-only TRIGGER is defense-in-depth and not exercised under
the in-memory SQLite test engine — the service-level immutability is the functional guard.)
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import sessionmaker

from services.signal_snapshots import freeze_signals, get_snapshot

SIG = {
    "ticker": "LTFOODS", "signal_date": "2026-07-17",
    "entry": 479.98, "stop": 386.52, "target": 666.44,
    "entry_low": 386.52, "entry_high": 500.10,
    "exit_plan": {"entry_pattern": "44-week SMA pullback",
                  "tranches": [{"pct": 40, "type": "target", "level": 666.44, "do": "..."}]},
    "status": "FRESH",
}


def _session(engine: Any):
    return sessionmaker(bind=engine)()


def test_freeze_is_idempotent_and_immutable(engine: Any) -> None:
    db = _session(engine)
    sid = "LTFOODS__2026-07-17"

    # first freeze
    assert freeze_signals(db, [SIG], "2026-07-17") == 1
    snap = get_snapshot(db, sid)
    assert snap is not None and snap["entry"] == 479.98 and snap["status"] == "OK"
    assert snap["exit_plan"]["tranches"][0]["level"] == 666.44
    h1 = snap["content_hash"]

    # a recompute changes the entry/stop — the frozen snapshot must NOT change
    changed = {**SIG, "entry": 999.0, "stop": 900.0, "target": 1200.0}
    assert freeze_signals(db, [changed], "2026-07-24") == 0        # skipped — immutable
    snap2 = get_snapshot(db, sid)
    assert snap2["entry"] == 479.98 and snap2["content_hash"] == h1  # unchanged


def test_hash_chain_links_rows(engine: Any) -> None:
    db = _session(engine)
    freeze_signals(db, [SIG], "2026-07-17")
    sig_b = {**SIG, "ticker": "USHAMART", "entry": 400.0, "stop": 360.0, "target": 480.0}
    freeze_signals(db, [sig_b], "2026-07-17")
    a = get_snapshot(db, "LTFOODS__2026-07-17")
    b = get_snapshot(db, "USHAMART__2026-07-17")
    assert a["prev_hash"] is None                 # first ever row
    assert b["prev_hash"] == a["content_hash"]    # chained to the prior snapshot


def test_integrity_gate_quarantines_bad_signal(engine: Any) -> None:
    db = _session(engine)
    bad = {**SIG, "ticker": "BADCO", "entry": 100.0, "stop": 120.0}  # stop above entry
    freeze_signals(db, [bad], "2026-07-17")
    snap = get_snapshot(db, "BADCO__2026-07-17")
    assert snap["status"] == "QUARANTINED"
