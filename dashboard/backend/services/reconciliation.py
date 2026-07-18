"""Reconciliation — model plan MINUS user ledger => per-user action items (Stage-4b, spec §5).

The model recomputes the shared book weekly and flags intra-week exit events (Stage-3 monitor); the
user reports their real fills into the durable ledger (Stage-4a). This service diffs the two and tells
each user what is OUTSTANDING for THEM specifically:

  * SELL_DUE   — the model flagged/booked an exit on a name the user still HOLDS, but the user hasn't
                 recorded the matching sell. Severity mirrors the P cadence (stop=high, +2R target=
                 action, blow-off/runner=info) — a WATCH-only tranche is surfaced, never as "act now".
  * STALE_HOLD — the user still holds a name the model has fully CLOSED (completed/exited). A stale
                 prior-episode hold the user never sold (QUESTIONING §17).
  * UNTAKEN_BUY — the model has an actionable buy the user hasn't recorded. Informational — a
                 recommendation, not an obligation.

Items are DERIVED, not persisted: a SELL_DUE clears itself the moment the user records the sell (their
remaining drops / the model stops flagging), so a popup resolving an item needs no extra bookkeeping.
'Missed actions stay open until a popup (or an explicit didn't-sell) closes them' falls out for free.
"""
from __future__ import annotations

import logging

from services import execution_ledger as ledger

logger = logging.getLogger("reconciliation")

# Monitor events (Stage-3) that mean the model wants an exit on a HELD name, with the cadence severity.
_EXIT_EVENTS = {
    "STOP_BREACH": "high",
    "TRANCHE_TARGET_2R": "action",
    "TARGET_2R": "action",
    "PATTERN_ARMED": "info",
    "RUNNER_BELOW_SMA": "warn",
}
_EXIT_ACTIONABILITY = {"EXIT_REQUIRED"}
_EXIT_STATUS = {"HIT_TARGET", "HIT_STOP", "EXPIRED", "CLOSED", "RESOLVED"}
_ACTIVE_STATUS = {"ACTIVE", "FRESH", "OPEN"}
_BUY_ACTIONABILITY = {"BUY_OPEN", "ACTIONABLE_BUY"}


def _signal_id(sig: dict) -> str | None:
    sid = sig.get("signal_id") or sig.get("nq_position_id")
    if sid:
        return str(sid)
    t, d = sig.get("ticker"), sig.get("signal_date")
    return f"{t}__{d}" if t and d else None


def build_model_index(envelope: dict, monitor: dict) -> dict:
    """Index the model state for O(1) lookup: per-signal_id envelope facts + per-ticker monitor flags."""
    by_signal: dict[str, dict] = {}
    for sig in (envelope or {}).get("signals", []):
        sid = _signal_id(sig)
        if not sid:
            continue
        by_signal[sid] = {
            "ticker": (sig.get("ticker") or "").upper(),
            "actionability": (sig.get("actionability") or "").upper(),
            "status": (sig.get("status") or "").upper(),
            "held_by_model": bool(sig.get("bought_date")),
        }
    flags_by_ticker: dict[str, list[dict]] = {}
    for f in (monitor or {}).get("flags", []):
        t = (f.get("ticker") or "").upper()
        if t:
            flags_by_ticker.setdefault(t, []).append(f)
    return {"by_signal": by_signal, "flags_by_ticker": flags_by_ticker,
            "as_of": (monitor or {}).get("as_of") or (envelope or {}).get("generated_at")}


def build_action_items(positions: list[dict], model_index: dict) -> list[dict]:
    """Diff the user's ledger positions against the model index → OPEN action items (pure)."""
    by_signal = model_index.get("by_signal", {})
    flags_by_ticker = model_index.get("flags_by_ticker", {})
    items: list[dict] = []

    held_signal_ids = set()
    for pos in positions:
        sid = pos.get("signal_id")
        ticker = (pos.get("ticker") or "").upper()
        remaining = pos.get("remaining_qty") or 0
        model = by_signal.get(sid, {})

        if remaining > 0:
            held_signal_ids.add(sid)
            # 1) exit flagged by the intra-week monitor on a name the user still holds
            for f in flags_by_ticker.get(ticker, []):
                sev = _EXIT_EVENTS.get(f.get("event"))
                if sev:
                    items.append({
                        "signal_id": sid, "ticker": ticker, "type": "SELL_DUE",
                        "event": f.get("event"), "severity": sev, "remaining_qty": remaining,
                        "message": f"{ticker}: the model flagged {f.get('event')} but you still hold "
                                   f"{remaining} sh. Record your sell if you exited.",
                    })
            # 2) the model has fully CLOSED the trade, but the user still holds
            if model and (model["actionability"] in _EXIT_ACTIONABILITY or model["status"] in _EXIT_STATUS):
                items.append({
                    "signal_id": sid, "ticker": ticker, "type": "STALE_HOLD",
                    "severity": "warn", "remaining_qty": remaining,
                    "message": f"{ticker}: the model has closed this trade, but your ledger still shows "
                               f"{remaining} sh held. Record your sell, or you're holding past the plan.",
                })

    # 3) model has an actionable buy the user hasn't recorded (informational)
    for sid, model in by_signal.items():
        if (model.get("actionability") in _BUY_ACTIONABILITY and sid not in held_signal_ids):
            items.append({
                "signal_id": sid, "ticker": model["ticker"], "type": "UNTAKEN_BUY",
                "severity": "info", "remaining_qty": 0,
                "message": f"{model['ticker']}: the model has an open buy you haven't recorded. "
                           f"If you took it, record your buy.",
            })

    # De-dup by (signal_id, type, event); rank most-urgent first.
    seen, unique = set(), []
    for it in items:
        key = (it["signal_id"], it["type"], it.get("event"))
        if key not in seen:
            seen.add(key)
            unique.append(it)
    order = {"high": 0, "action": 1, "warn": 2, "info": 3}
    unique.sort(key=lambda it: order.get(it["severity"], 9))
    return unique


def reconcile_user(db, user_id: int, envelope: dict, monitor: dict, stops: dict | None = None) -> dict:
    """Full reconciliation for one user: load their ledger positions, diff vs the model state."""
    positions = ledger.get_positions(db, user_id, stops=stops)
    model_index = build_model_index(envelope, monitor)
    items = build_action_items(positions, model_index)
    return {
        "as_of": model_index.get("as_of"),
        "n_open": len(items),
        "n_positions": len([p for p in positions if (p.get("remaining_qty") or 0) > 0]),
        "action_items": items,
    }
