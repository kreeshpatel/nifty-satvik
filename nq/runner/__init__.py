"""Runner: the live signal scanner + the research-run (backtest/CPCV) harness."""
from __future__ import annotations

from .research import cpcv_evaluate, paired_cpcv, run_backtest
from .scan import OUT_TODAY, run_scan

__all__ = ["run_scan", "OUT_TODAY", "run_backtest", "cpcv_evaluate", "paired_cpcv"]
