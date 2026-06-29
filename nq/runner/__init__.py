"""Runner: the live signal scanner entry point — writes results/signals_today.json."""
from __future__ import annotations

from .scan import OUT_TODAY, run_scan

__all__ = ["run_scan", "OUT_TODAY"]
