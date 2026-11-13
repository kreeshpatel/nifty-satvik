"""scripts/print_trade_status.py: the stopgap table printed after each scan until PR #181 ships."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import print_trade_status as P  # noqa: E402


def test_every_open_trade_and_buy_card_is_printed():
    env = json.loads((ROOT / "results" / "signals_today_weekly.json").read_text(encoding="utf-8"))
    text = P.render()
    for c in env.get("signals", []):
        assert f"| {c['ticker']} |" in text


def test_queued_exit_comes_before_the_plan():
    card = {"exit_stage": {"target_booked": True, "pending_exit": {"kind": "full", "reason": "stop"}},
            "exit_plan": {"tranches": [{"type": "runner", "do": "Hold the runner"}]}}
    assert P.next_step(card) == "Sell all remaining shares at the next open (stop)."


def test_next_open_tranche_is_the_instruction():
    card = {"exit_stage": {"target_booked": True, "pattern_booked": False, "runner_open": True},
            "exit_plan": {"tranches": [{"type": "target", "do": "Sell 40% at +2R"},
                                       {"type": "pattern", "do": "Sell 40% on a blow-off week"}]}}
    assert P.next_step(card) == "Sell 40% on a blow-off week"
