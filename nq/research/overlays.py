"""Candidate overlays — panel transforms / cfg flags scored against the frozen baseline.

An overlay is a *candidate* change to the strategy that the research harness
(:func:`nq.runner.research.evaluate_overlay`) must PROMOTE/UNDERPOWERED/KILL on its own merits.
The engine stays frozen; an overlay either (a) flips a cfg flag the engine honours, or (b) adds a
column the engine reads when that flag is on. Both are inert on the golden path, so the Stage-2
byte-for-byte gate is untouched.

**Regime-to-cash** (the A5 harness-trust gate). When the broad market is in a downtrend, suppress
NEW entries (sit in cash); held names still exit on the normal rules. For a trend-following rule
that already cuts losers via ATR stops, a 200-day market filter classically does NOT add
risk-adjusted value (it adds whipsaw + misses V-recoveries) — a known §11 KILL. A5 runs it through
the real harness and asserts the verdict is NOT a promotion: the proof the harness won't
false-promote a no-edge overlay before we trust it for Stage-C conviction work.
"""
from __future__ import annotations

import pandas as pd

REGIME_SMA_WINDOW = 200          # the classic 200-session market-trend filter
REGIME_COL = "regime_risk_off"   # per-date bool the engine reads when cfg["regime_gate"] is on


def equal_weight_market_index(
    panel: pd.DataFrame, *, price_col: str = "close", date_col: str = "date",
) -> pd.Series:
    """An equal-weight market index from the panel's OWN names — a fully reproducible market proxy
    (no extra download; rides the same PINNED OHLCV snapshot as the backtest).

    Built from cross-sectional MEAN DAILY RETURNS (not price levels) so it is robust to the
    universe growing over time and not dominated by high-priced names: each session's market return
    is the equal-weight mean of per-name returns; the index is their cumulative product. Indexed by
    date (sorted)."""
    df = panel[[date_col, "ticker", price_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col])
    wide = df.pivot_table(index=date_col, columns="ticker", values=price_col, aggfunc="last")
    wide = wide.sort_index()
    mkt_ret = wide.pct_change().mean(axis=1)              # equal-weight daily market return
    return (1.0 + mkt_ret.fillna(0.0)).cumprod()


def add_regime_gate_column(
    panel: pd.DataFrame, *, price_col: str = "close", date_col: str = "date",
    sma_window: int = REGIME_SMA_WINDOW,
) -> pd.DataFrame:
    """Return a copy of ``panel`` with a boolean :data:`REGIME_COL` per row: True when the
    equal-weight market index is BELOW its ``sma_window``-session SMA on that date (risk-off).

    Until the SMA has ``sma_window`` observations the date is risk-ON (no suppression) — no
    lookahead, the SMA uses only trailing closes. All rows sharing a date get the same value, so
    the engine can read it off any row for that session."""
    idx = equal_weight_market_index(panel, price_col=price_col, date_col=date_col)
    sma = idx.rolling(sma_window, min_periods=sma_window).mean()
    risk_off = (idx < sma).fillna(False)
    out = panel.copy()
    d = pd.to_datetime(out[date_col])
    out[REGIME_COL] = d.map(risk_off.to_dict()).fillna(False).astype(bool).to_numpy()
    return out
