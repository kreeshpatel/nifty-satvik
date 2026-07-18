"""Immutable signal snapshots — the Stage-2 keystone (docs/PRODUCT_STATE_AND_DATA.md §2).

The cron recomputes the whole book from inception every Saturday, so the served envelope is
mutable. But a card a user acted on must NEVER change retroactively. This service freezes each
signal the FIRST time it is served and never touches it again, with a sha256 hash chain for
tamper-evidence + a publish-time integrity gate (OK | QUARANTINED).

Public API:
    freeze_signals(db, signals, generated_at) -> int   # rows newly frozen (idempotent)
    get_snapshot(db, signal_id) -> dict | None
"""
from __future__ import annotations

import hashlib
import json
import logging

from database import SignalSnapshot

logger = logging.getLogger("signal_snapshots")


def _signal_id(sig: dict) -> str | None:
    sid = sig.get("signal_id") or sig.get("nq_position_id")
    if sid:
        return str(sid)
    t, d = sig.get("ticker"), sig.get("signal_date")
    return f"{t}__{d}" if t and d else None


def _canonical(sig: dict) -> dict:
    """The frozen, order-stable fields that define the contract (what the user acted on)."""
    return {
        "entry": sig.get("entry"),
        "stop": sig.get("stop"),
        "target": sig.get("target"),
        "entry_low": sig.get("entry_low"),
        "entry_high": sig.get("entry_high"),
        "exit_plan": sig.get("exit_plan"),
        "actionability": sig.get("actionability") or sig.get("status"),
    }


def _content_hash(canonical: dict, prev_hash: str | None) -> str:
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{prev_hash or ''}|{payload}".encode()).hexdigest()


def _integrity(sig: dict) -> str:
    """Publish-time sanity gate. A long signal must have entry > stop > 0 and a sane band.
    Returns 'OK' or 'QUARANTINED' (still frozen, but flagged so the API can refuse BUYs)."""
    try:
        e, s = float(sig.get("entry")), float(sig.get("stop"))
    except (TypeError, ValueError):
        return "QUARANTINED"
    if not (e > 0 and s > 0 and e > s):
        return "QUARANTINED"
    lo, hi = sig.get("entry_low"), sig.get("entry_high")
    if lo is not None and hi is not None:
        try:
            if not (float(lo) > 0 and float(hi) >= float(lo)):
                return "QUARANTINED"
        except (TypeError, ValueError):
            return "QUARANTINED"
    return "OK"


def freeze_signals(db, signals: list[dict], generated_at: str | None) -> int:
    """Freeze any signal whose signal_id has not been frozen yet. NEVER overwrites an
    existing snapshot (that is the whole point). Idempotent; best-effort (never raises)."""
    frozen = 0
    try:
        for sig in signals or []:
            sid = _signal_id(sig)
            entry, stop = sig.get("entry"), sig.get("stop")
            if not sid or entry is None or stop is None:
                continue
            if db.query(SignalSnapshot).filter(SignalSnapshot.signal_id == sid).first():
                continue                                  # already frozen — immutable
            prev = db.query(SignalSnapshot).order_by(SignalSnapshot.id.desc()).first()
            prev_hash = prev.content_hash if prev else None
            canonical = _canonical(sig)
            row = SignalSnapshot(
                signal_id=sid, ticker=sig.get("ticker"), signal_date=str(sig.get("signal_date")),
                entry=float(entry), stop=float(stop),
                target=sig.get("target"), entry_low=sig.get("entry_low"), entry_high=sig.get("entry_high"),
                exit_plan_json=json.dumps(sig.get("exit_plan")) if sig.get("exit_plan") is not None else None,
                actionability=(sig.get("actionability") or sig.get("status")),
                generated_at=str(generated_at) if generated_at else None,
                status=_integrity(sig),
                content_hash=_content_hash(canonical, prev_hash), prev_hash=prev_hash,
            )
            db.add(row)
            frozen += 1
        if frozen:
            db.commit()
    except Exception as exc:                              # never break serving on a snapshot fault
        logger.warning("freeze_signals failed (non-fatal): %s", exc)
        db.rollback()
    return frozen


def get_snapshot(db, signal_id: str) -> dict | None:
    row = db.query(SignalSnapshot).filter(SignalSnapshot.signal_id == signal_id).first()
    if not row:
        return None
    return {
        "signal_id": row.signal_id, "ticker": row.ticker, "signal_date": row.signal_date,
        "entry": row.entry, "stop": row.stop, "target": row.target,
        "entry_low": row.entry_low, "entry_high": row.entry_high,
        "exit_plan": json.loads(row.exit_plan_json) if row.exit_plan_json else None,
        "actionability": row.actionability, "generated_at": row.generated_at,
        "status": row.status, "content_hash": row.content_hash, "prev_hash": row.prev_hash,
        "frozen_at": row.created_at.isoformat() if row.created_at else None,
    }
