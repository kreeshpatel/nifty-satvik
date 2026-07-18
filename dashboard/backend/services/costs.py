"""Transaction-cost computation for a filled leg.

Extracted from routers/nq_orders.py when the per-user Kite trading integration was
removed (ADR 0011 — no broker connection; users self-report fills). The cost logic is
pure (config-driven) and reused by services/fifo_matcher.py for realised P&L, so it is
kept here as a service rather than deleted with the router. The Stage-4 self-report
execution ledger consumes this to compute each leg's brokerage + STT.
"""
from __future__ import annotations

from config import BROKERAGE_PCT, STT_PCT


def compute_costs(action: str, fill_price: float, qty: int) -> tuple[float, float]:
    """Transaction costs for a filled leg → (brokerage, stt), rounded to paise.

    Delivery equity (config.py): brokerage = BROKERAGE_PCT on BOTH legs, and STT =
    STT_PCT on BOTH legs (buy AND sell — 0.1% per leg; sell-only is the intraday/F&O
    rule and does NOT apply to delivery swing trades). Matches the backtest cost model +
    config.delivery_leg_cost so the displayed cost reflects what the user actually paid.
    """
    notional = float(fill_price) * int(qty)
    brokerage = round(BROKERAGE_PCT * notional, 2)
    stt = round(STT_PCT * notional, 2)
    return brokerage, stt


# Backwards-compatible alias for the original private name.
_compute_costs = compute_costs
