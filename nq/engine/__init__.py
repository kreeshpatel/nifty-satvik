"""Engine: shared exits, portfolio simulation, and the ranked-eligible-panel builder.

``decide_exit`` and ``simulate`` are the live≡backtest core; ``simulate`` reproduces the carried
golden master byte-for-byte (the Stage-2 keystone gate)."""
from __future__ import annotations

from .exits import ExitDecision, decide_exit
from .panel import build_ohlc_panel, compose_ranked_panel
from .portfolio import (
    Position,
    base_risk_qty,
    compute_metrics,
    simulate,
)

__all__ = [
    "decide_exit", "ExitDecision",
    "simulate", "compute_metrics", "base_risk_qty", "Position",
    "build_ohlc_panel", "compose_ranked_panel",
]
