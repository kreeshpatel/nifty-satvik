"""Strategy: the long-horizon scan — rank by sma200_slope_63, emit top-15 non-held BUY signals."""
from __future__ import annotations

from .long_horizon import EQUITY, build_signal, scan

__all__ = ["scan", "build_signal", "EQUITY"]
