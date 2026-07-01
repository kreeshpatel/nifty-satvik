"""Regression tests for nq_orders transaction-cost computation.

Covers the fix where brokerage/STT were never populated on filled NQOrder rows,
leaving the Accounting page's tax KPIs at 0 and net_pnl == gross. The cost model
mirrors config.py delivery equity: brokerage on both legs, and STT on BOTH legs
(0.1% per leg — buy AND sell; sell-only is the intraday/F&O rule, not delivery).
"""
from routers.nq_orders import _compute_costs
from config import BROKERAGE_PCT, STT_PCT


def test_buy_leg_has_brokerage_and_stt():
    # Delivery STT is charged on the buy leg too (C1 fix, 2026-06-17).
    brokerage, stt = _compute_costs("BUY", 250.0, 10)
    assert brokerage == round(BROKERAGE_PCT * 2500.0, 2)
    assert stt == round(STT_PCT * 2500.0, 2)


def test_sell_leg_has_brokerage_and_stt():
    brokerage, stt = _compute_costs("SELL", 250.0, 10)
    assert brokerage == round(BROKERAGE_PCT * 2500.0, 2)
    assert stt == round(STT_PCT * 2500.0, 2)


def test_action_is_case_insensitive():
    _, stt_lower = _compute_costs("sell", 100.0, 1)
    _, stt_upper = _compute_costs("SELL", 100.0, 1)
    assert stt_lower == stt_upper == round(STT_PCT * 100.0, 2)


def test_zero_qty_is_zero_cost():
    assert _compute_costs("SELL", 250.0, 0) == (0.0, 0.0)


def test_costs_are_rounded_to_paise():
    # Notional that produces a long-decimal cost must round to 2dp.
    brokerage, stt = _compute_costs("SELL", 333.33, 7)
    assert brokerage == round(brokerage, 2)
    assert stt == round(stt, 2)
