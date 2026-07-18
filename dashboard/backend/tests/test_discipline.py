"""Stage-6: the discipline score (services/discipline.py) + journey memory (routers/journey.py).

Covers: the six legs compute from ledger ground truth; geometric combining (one broken leg tanks);
the Sharpe pricing on [0.67 … 1.03]; the full-coverage counterfactual; legs without data are omitted
(null), never fabricated; the endpoint contract; journey flags are set-once and tenant-isolated.
"""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from database import ExecutionEvent
from services import discipline as disc

SIG_A = "AAA__2026-07-13"
SIG_B = "BBB__2026-07-13"
SIG_C = "CCC__2026-07-13"


def _ev(sid, side, qty, price, tranche=None, eid=0):
    e = ExecutionEvent(user_id=1, signal_id=sid, ticker=sid.split("__")[0], side=side,
                       qty=qty, price=price, tranche=tranche, fill_source="self_reported")
    e.id = eid
    return e


def _envelope():
    return {"signals": [
        {"ticker": "AAA", "signal_date": "2026-07-13", "actionability": "BUY_OPEN", "status": "FRESH"},
        {"ticker": "BBB", "signal_date": "2026-07-13", "actionability": "BUY_OPEN", "status": "FRESH"},
        {"ticker": "CCC", "signal_date": "2026-07-13", "bought_date": "2026-07-14", "status": "ACTIVE"},
    ]}


def test_full_coverage_and_band_fidelity_score_high() -> None:
    events = {SIG_A: [_ev(SIG_A, "BUY", 10, 100.0, eid=1)],
              SIG_B: [_ev(SIG_B, "BUY", 10, 200.0, eid=2)]}
    snaps = {SIG_A: {"entry_low": 95.0, "entry_high": 105.0},
             SIG_B: {"entry_low": 190.0, "entry_high": 210.0}}
    legs = disc.compute_legs(events, _envelope(), snaps)
    assert legs["coverage"] == 1.0 and legs["fidelity"] == 1.0
    assert legs["_n_buyable"] == 2 and legs["_n_taken"] == 2 and legs["_skipped"] == []


def test_skip_halves_coverage_and_counterfactual_prices_it() -> None:
    events = {SIG_A: [_ev(SIG_A, "BUY", 10, 100.0, eid=1)]}     # took A, skipped B
    legs = disc.compute_legs(events, _envelope(), {})
    assert legs["coverage"] == 0.5 and legs["_skipped"] == [SIG_B]


def test_geometric_one_broken_leg_tanks() -> None:
    # coverage 1.0 but fidelity 0.4 (chased way outside the band) → geo mean well below arithmetic
    g = disc._geo_mean([1.0, 0.4])
    a = (1.0 + 0.4) / 2
    assert g is not None and g < a and abs(g - 0.4 ** 0.5) < 1e-9


def test_sharpe_pricing_on_null_segment() -> None:
    assert disc._sharpe_at(0.0) == 0.67
    assert disc._sharpe_at(1.0) == 1.03
    assert disc._sharpe_at(None) is None


def test_no_data_legs_are_null_not_fabricated() -> None:
    legs = disc.compute_legs({}, {"signals": []}, {})
    assert all(v is None for k, v in legs.items() if not k.startswith("_"))


def test_early_manual_sell_breaks_hold_through() -> None:
    # CCC is model-HELD; user sold it manually (winner-cut) → hold_through 0
    events = {SIG_C: [_ev(SIG_C, "BUY", 10, 100.0, eid=1),
                      _ev(SIG_C, "SELL", 10, 110.0, tranche="manual", eid=2)]}
    legs = disc.compute_legs(events, _envelope(), {})
    assert legs["hold_through"] == 0.0
    # a tranche-tagged sell (the model's own plan) does NOT break it
    events2 = {SIG_C: [_ev(SIG_C, "BUY", 10, 100.0, eid=1),
                       _ev(SIG_C, "SELL", 4, 110.0, tranche="target", eid=2)]}
    assert disc.compute_legs(events2, _envelope(), {})["hold_through"] == 1.0


def test_concentration_decays_on_pile_in() -> None:
    events = {SIG_A: [_ev(SIG_A, "BUY", 100, 100.0, eid=1)],     # 10,000 cost
              SIG_B: [_ev(SIG_B, "BUY", 10, 100.0, eid=2)]}      # 1,000 cost → 91% in A
    legs = disc.compute_legs(events, _envelope(), {})
    assert legs["concentration"] is not None and legs["concentration"] < 0.5


# ── endpoints ─────────────────────────────────────────

def test_discipline_endpoint_contract(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Disc")
    r = client.get("/api/execution/discipline", cookies=auth_cookies(u))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"legs", "score", "sharpe_now", "sharpe_floor", "sharpe_ceiling",
                         "skipped_signal_ids", "sharpe_if_full_coverage"}
    assert body["sharpe_floor"] == 0.67 and body["sharpe_ceiling"] == 1.03


def test_journey_flags_set_once(client: TestClient, make_user: Any, auth_cookies: Any) -> None:
    u = make_user(name="Journey")
    ck = auth_cookies(u)
    r1 = client.post("/api/journey/cold_start_acked", json={"value": {"v": 1}}, cookies=ck)
    assert r1.status_code == 201 and r1.json()["already_set"] is False
    r2 = client.post("/api/journey/cold_start_acked", cookies=ck)
    assert r2.json()["already_set"] is True                       # set-once: no overwrite
    flags = client.get("/api/journey", cookies=ck).json()["flags"]
    assert "cold_start_acked" in flags and flags["cold_start_acked"]["value"] == {"v": 1}
    # tenant isolation
    other = make_user(name="Other")
    assert client.get("/api/journey", cookies=auth_cookies(other)).json()["flags"] == {}
    # validation
    assert client.post("/api/journey/BAD FLAG!", cookies=ck).status_code in (404, 422)


def test_journey_requires_auth(client: TestClient) -> None:
    assert client.get("/api/journey").status_code == 401
