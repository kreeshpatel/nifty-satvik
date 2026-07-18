"""Stage-4: the durable append-only self-reported execution ledger.

Covers the spec contract (docs/EXECUTION_CAPTURE_SPEC.md):
  * the scripted P journey (buy -> 2R partial -> pattern partial -> runner) yields the correct
    remaining qty and quantity-weighted realized P&L / R,
  * averaging in (multiple buys) uses average cost,
  * a correction is a NEW event that supersedes the prior one — the prior row is RETAINED in the
    audit trail (append-only; the Postgres UPDATE/DELETE trigger is defense-in-depth not exercised
    under SQLite — the service-level immutability is the functional guard),
  * the endpoints capture buys/sells, warn (never block) on an oversell, and expose the audit trail.
"""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import ExecutionEvent
from services import execution_ledger as ledger

SIG = "LTFOODS__2026-07-17"


def _ev(side, qty, price, tranche=None, eid=0, corrects=None):
    """A lightweight ExecutionEvent stand-in for the pure position_state maths."""
    e = ExecutionEvent(user_id=1, signal_id=SIG, ticker="LTFOODS", side=side, qty=qty,
                       price=price, tranche=tranche, fill_source="self_reported",
                       corrects_event_id=corrects)
    e.id = eid                     # created_at stays None -> _sort_key falls back to id order
    return e


# ── the scripted P journey (pure maths) ───────────────

def test_scripted_p_journey_remaining_and_pnl() -> None:
    # buy 100 @100; then the three P tranches: 40 @120 (+2R), 40 @130 (pattern), 20 @110 (runner)
    events = [
        _ev("BUY", 100, 100.0, eid=1),
        _ev("SELL", 40, 120.0, "target", eid=2),
        _ev("SELL", 40, 130.0, "pattern", eid=3),
        _ev("SELL", 20, 110.0, "runner", eid=4),
    ]
    st = ledger.position_state(events, stop=90.0)
    assert st["remaining_qty"] == 0 and st["status"] == "CLOSED"
    assert st["total_bought_qty"] == 100 and st["total_sold_qty"] == 100
    assert st["avg_buy_price"] == 100.0
    # 40*(120-100) + 40*(130-100) + 20*(110-100) = 800 + 1200 + 200 = 2200
    assert st["realized_pnl"] == 2200.0
    # sold cost basis = 100 shares * 100 = 10000 -> 22.0%
    assert st["realized_pnl_pct"] == 22.0
    # risk/share = 100-90 = 10; realized_r = 2200 / (10 * 100) = 2.2
    assert st["realized_r"] == 2.2


def test_partial_leaves_position_open() -> None:
    st = ledger.position_state([_ev("BUY", 100, 100.0, eid=1), _ev("SELL", 40, 120.0, "target", eid=2)])
    assert st["remaining_qty"] == 60 and st["status"] == "OPEN"
    assert st["total_sold_qty"] == 40 and st["realized_pnl"] == 800.0


def test_average_in_uses_average_cost() -> None:
    st = ledger.position_state([_ev("BUY", 100, 100.0, eid=1), _ev("BUY", 100, 110.0, eid=2)])
    assert st["remaining_qty"] == 200 and st["avg_buy_price"] == 105.0 and st["status"] == "OPEN"


def test_correction_supersedes_prior_event() -> None:
    # buy 100, then a correcting event says it was really 50 -> effective remaining is 50, not 150.
    events = [
        _ev("BUY", 100, 100.0, eid=1),
        _ev("BUY", 50, 100.0, eid=2, corrects=1),
    ]
    st = ledger.position_state(events)
    assert st["remaining_qty"] == 50 and st["total_bought_qty"] == 50


# ── append-only + audit trail (service level) ─────────

def test_record_is_append_only_and_keeps_corrected_row(db_session: Session, make_user: Any) -> None:
    u = make_user(name="Ledger")
    b = ledger.record_event(db_session, user_id=u.id, signal_id=SIG, ticker="LTFOODS",
                            side="BUY", qty=100, price=100.0)
    # a correction is a NEW row; the original is retained (append-only)
    ledger.record_event(db_session, user_id=u.id, signal_id=SIG, ticker="LTFOODS",
                        side="BUY", qty=50, price=100.0, corrects_event_id=b["id"])
    rows = db_session.query(ExecutionEvent).filter(ExecutionEvent.user_id == u.id).all()
    assert len(rows) == 2                                  # nothing was overwritten
    trail = ledger.get_events(db_session, u.id, SIG)
    assert [e["superseded"] for e in trail] == [True, False]   # the corrected buy is flagged, still present
    state = ledger.position_state(rows)
    assert state["remaining_qty"] == 50


# ── endpoints ─────────────────────────────────────────

def test_buy_then_partial_sell_endpoints(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Journey")
    ck = auth_cookies(u)

    r = client.post("/api/execution/buy",
                    json={"signal_id": SIG, "ticker": "LTFOODS", "qty": 100, "price": 100.0}, cookies=ck)
    assert r.status_code == 201, r.text
    assert r.json()["position"]["remaining_qty"] == 100 and r.json()["position"]["status"] == "OPEN"

    r = client.post("/api/execution/sell",
                    json={"signal_id": SIG, "qty": 40, "price": 120.0, "tranche": "target"}, cookies=ck)
    assert r.status_code == 201, r.text
    pos = r.json()["position"]
    assert pos["remaining_qty"] == 60 and pos["realized_pnl"] == 800.0 and not r.json()["warnings"]

    # the durable position survives and lists
    lp = client.get("/api/execution/positions", cookies=ck).json()["positions"]
    assert len(lp) == 1 and lp[0]["signal_id"] == SIG and lp[0]["remaining_qty"] == 60


def test_oversell_warns_but_records(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Oversell")
    ck = auth_cookies(u)
    client.post("/api/execution/buy", json={"signal_id": SIG, "ticker": "LTFOODS", "qty": 10, "price": 100.0}, cookies=ck)
    r = client.post("/api/execution/sell", json={"signal_id": SIG, "qty": 25, "price": 110.0}, cookies=ck)
    assert r.status_code == 201
    assert any("only 10 remain" in w for w in r.json()["warnings"])     # warned...
    assert r.json()["position"]["remaining_qty"] == 0                    # ...but recorded (floored)


def test_position_audit_trail_endpoint(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Trail")
    ck = auth_cookies(u)
    b = client.post("/api/execution/buy", json={"signal_id": SIG, "ticker": "LTFOODS", "qty": 100, "price": 100.0}, cookies=ck)
    eid = b.json()["event"]["id"]
    client.post("/api/execution/correct",
                json={"corrects_event_id": eid, "signal_id": SIG, "ticker": "LTFOODS",
                      "side": "BUY", "qty": 50, "price": 100.0}, cookies=ck)
    body = client.get(f"/api/execution/position/{SIG}", cookies=ck).json()
    assert body["remaining_qty"] == 50
    assert len(body["events"]) == 2 and body["events"][0]["superseded"] is True


def test_execution_routes_require_auth(client: TestClient) -> None:
    assert client.get("/api/execution/positions").status_code == 401
    assert client.post("/api/execution/buy", json={"signal_id": SIG, "qty": 1, "price": 1.0}).status_code == 401


# ── tenant isolation (user-data mapping audit, 2026-07-18) ─────────

def test_execution_ledger_is_tenant_isolated(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    """User B must never see, sum over, or CORRECT user A's events — even on the same signal_id."""
    a, b = make_user(name="Alpha"), make_user(name="Beta")
    ck_a, ck_b = auth_cookies(a), auth_cookies(b)

    r = client.post("/api/execution/buy",
                    json={"signal_id": SIG, "ticker": "LTFOODS", "qty": 100, "price": 100.0}, cookies=ck_a)
    a_event_id = r.json()["event"]["id"]

    # B sees an empty book, not A's position
    assert client.get("/api/execution/positions", cookies=ck_b).json()["positions"] == []
    assert client.get(f"/api/execution/position/{SIG}", cookies=ck_b).status_code == 404
    # B cannot append a "correction" over A's event (would rewrite A's history)
    resp = client.post("/api/execution/correct",
                       json={"corrects_event_id": a_event_id, "signal_id": SIG, "ticker": "LTFOODS",
                             "side": "BUY", "qty": 1, "price": 1.0}, cookies=ck_b)
    assert resp.status_code == 404
    # B's discipline gauge + reconciliation see only B's (empty) ledger
    assert client.get("/api/execution/discipline", cookies=ck_b).json()["legs"]["fidelity"] is None
    assert client.get("/api/execution/reconciliation", cookies=ck_b).json()["n_positions"] == 0
    # and A's own view is intact
    assert client.get("/api/execution/positions", cookies=ck_a).json()["positions"][0]["remaining_qty"] == 100
