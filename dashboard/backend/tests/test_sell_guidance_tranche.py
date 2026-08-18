"""Sell-guidance surfaces the scaled-exit PROFIT TRANCHE, not only full exits.

Before this, `sell_guidance` fired only on a full close (HIT_TARGET / HIT_STOP / EXPIRED), so the
one prominent sell the book ever showed was a stop-out; the +2R take-profit tranche — the actual
"sell your winner" recommendation — lived only as a low-key monitor flag. These pin the new
behaviour: a reached target tranche on a still-held position is a first-class sell (ACTIONABLE_TRIM),
while blow-off / runner tranches stay weekly-close decisions and full exits are unchanged.
"""
from __future__ import annotations

from services.nq_positions import (
    _active_tranche_sell,
    _build_sell_guidance,
    _classify_status_for_user,
)

# The live 40/40/20 config-P exit plan shape (see scripts/run_bhanushali_cron.py `_exit_plan`).
_PLAN = {"tranches": [
    {"pct": 40, "type": "target", "level": 1172.6},
    {"pct": 40, "type": "pattern", "arm": 1182.0},
    {"pct": 20, "type": "runner", "level": 1050.21},
]}


def _held(price, status="ACTIVE"):
    return {"status": status, "current_price": price, "target": 1172.6, "exit_plan": _PLAN}


# ── _active_tranche_sell ─────────────────────────────────────────────────────────────────────────
def test_target_tranche_reached_is_actionable():
    tr = _active_tranche_sell(_held(1200.0), 1200.0)
    assert tr is not None and tr["type"] == "target" and tr["pct"] == 40


def test_target_tranche_not_reached_is_none():
    assert _active_tranche_sell(_held(1100.0), 1100.0) is None


def test_blowoff_and_runner_are_not_act_now():
    """Only target tranches are intra-week actionable; pattern/runner are Saturday's call."""
    plan = {"tranches": [{"pct": 40, "type": "pattern", "arm": 1182.0},
                         {"pct": 20, "type": "runner", "level": 1050.21}]}
    assert _active_tranche_sell({"exit_plan": plan}, 5000.0) is None   # miles past both, still None


def test_no_price_or_no_plan_is_none():
    assert _active_tranche_sell(_held(1200.0), None) is None
    assert _active_tranche_sell({"status": "ACTIVE"}, 1200.0) is None


def test_lowest_reached_target_tranche_wins():
    plan = {"tranches": [{"pct": 40, "type": "target", "level": 1172.6},
                         {"pct": 40, "type": "target", "level": 1250.0}]}
    tr = _active_tranche_sell({"exit_plan": plan}, 1300.0)             # past both
    assert tr["level"] == 1172.6                                      # the +2R book is the act-now one


# ── _build_sell_guidance ─────────────────────────────────────────────────────────────────────────
def test_held_with_reached_tranche_yields_trim_guidance():
    g = _build_sell_guidance(_held(1200.0), last_price=None)          # falls back to current_price
    assert g is not None and g["reason"] == "target_tranche" and g["tone"] == "bull"
    assert g["partial_pct"] == 40 and "trim 40%" in g["headline"]


def test_held_below_tranche_has_no_guidance():
    assert _build_sell_guidance(_held(1100.0), last_price=None) is None


def test_full_exits_are_unchanged():
    assert _build_sell_guidance({"status": "HIT_STOP", "stop": 900}, 890)["reason"] == "stop"
    assert _build_sell_guidance({"status": "HIT_TARGET", "target": 1200}, 1200)["reason"] == "target"
    assert _build_sell_guidance({"status": "EXPIRED"}, 1000)["reason"] == "time"


def test_live_kite_price_takes_precedence_over_stale_current_price():
    sig = _held(1100.0)                                               # stale envelope price: below
    assert _build_sell_guidance(sig, last_price=1200.0) is not None   # live price above -> trim fires


# ── _classify_status_for_user ────────────────────────────────────────────────────────────────────
def test_tranche_due_classifies_as_actionable_trim():
    assert _classify_status_for_user(10, 10, "BUY_CLOSED", "ACTIVE", has_tranche_sell=True) == "ACTIONABLE_TRIM"


def test_full_exit_still_beats_trim():
    assert _classify_status_for_user(10, 10, "EXIT_REQUIRED", "HIT_STOP", has_tranche_sell=True) == "ACTIONABLE_SELL"


def test_plain_hold_unchanged():
    assert _classify_status_for_user(10, 10, "BUY_CLOSED", "ACTIVE", has_tranche_sell=False) == "HOLDING"
