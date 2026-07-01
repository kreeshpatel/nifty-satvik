"""Paper-trading layer — the backtest-to-real-capital bridge (Stage E).

The paper book reuses the SAME shared kernels the validated backtest uses (``base_risk_qty``,
``decide_exit``, ``leg_slippage``, ``vol_target_scalar``) so live paper P&L cannot drift from the
engine that was validated. The parity gate (``tests/test_stagee_paper_parity.py``) proves it: the
paper book stepped day-by-day over a panel produces byte-identical trades to ``portfolio.simulate``."""
