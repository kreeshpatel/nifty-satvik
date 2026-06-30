"""Validation: CPCV, block bootstrap, Deflated Sharpe, metrics — decoupled, no v1 engine."""
from __future__ import annotations

from .bootstrap import BootstrapResult, block_bootstrap_metric, bootstrap_delta
from .cpcv import (
    CPCVSplit,
    contiguous_blocks,
    cpcv_paths,
    cpcv_splits,
    make_groups,
    n_backtest_paths,
    n_splits,
)
from .dsr import cumulative_n_trials, deflated_sharpe_ratio, expected_max_sharpe
from .metrics import cagr, calmar, max_drawdown, sharpe, sortino, summary

__all__ = [
    "cpcv_splits", "cpcv_paths", "n_splits", "n_backtest_paths", "make_groups",
    "contiguous_blocks", "CPCVSplit",
    "block_bootstrap_metric", "bootstrap_delta", "BootstrapResult",
    "deflated_sharpe_ratio", "expected_max_sharpe", "cumulative_n_trials",
    "sharpe", "sortino", "cagr", "calmar", "max_drawdown", "summary",
]
