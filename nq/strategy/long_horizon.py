"""The long-horizon scan — turn a ranked panel into today's actionable BUY signals.

Each scan day, over the eligible ranked panel (membership + large+mid + solvent, ranked by
``sma200_slope_63``): take the top-quantile **non-held**, **non-quarantined** names, fill up to
``max_positions`` free slots, and emit an indicative signal per name. The published ``entry`` is
indicative (``t_close × (1 + slippage)``) because the real fill is the next session's open —
identical in STRUCTURE to the backtest's entry, so the stop/target/exit contract a tracker reads
is live≡backtest by construction (the sizing is the shared :func:`base_risk_qty`; the slippage is
the shared :func:`leg_slippage`).

Lean by design: no dashboard/frontend coupling — just the actionable signal + the exit contract
the shared :func:`nq.engine.exits.decide_exit` consumes.
"""
from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from config import NSE_HOLIDAYS, get_sector
from nq.data.features import SIGNAL
from nq.engine.portfolio import base_risk_qty, leg_slippage

# Default paper-book equity for indicative sizing (override with $LH_EQUITY or the `equity` arg).
EQUITY = float(os.environ.get("LH_EQUITY", 1_000_000))
BUY_WINDOW_TRADING_DAYS = 3   # enter within T+1..T+3 (client-execution model)


def _grade(rank_pct: float) -> tuple[str, str]:
    """Map the cross-sectional trend-rank percentile to a display grade / conviction."""
    if rank_pct >= 0.97:
        return "A", "HIGH"
    if rank_pct >= 0.93:
        return "B", "MEDIUM"
    return "C", "LOW"


def _add_trading_days(d: date, n: int) -> date:
    """Add ``n`` NSE trading days to ``d`` (skip weekends + NSE holidays)."""
    cur, added = d, 0
    while added < n:
        cur += timedelta(days=1)
        if cur.weekday() >= 5 or cur.strftime("%Y-%m-%d") in NSE_HOLIDAYS:
            continue
        added += 1
    return cur


def build_signal(
    row: Mapping[str, Any], cfg: Mapping[str, Any], *,
    equity: float, signal_date: str, exposure_scalar: float = 1.0,
) -> dict[str, Any]:
    """Build one indicative BUY signal from a ranked-panel row. ``entry = close ×
    (1 + leg_slippage(adv))``; ``stop = entry × (1 − stop_atr_mult × atr_pct)``;
    ``target = entry × (1 + target_pct)`` — same structure as the backtest's exit contract."""
    close = float(row["close"])
    atr_pct = float(row["atr_pct_63"])
    adv = float(row.get("adv_rupees_20d", 0) or 0)
    stop_mult = float(cfg["stop_atr_mult"])
    target_pct_cfg = float(cfg["target_pct"])

    entry = close * (1 + leg_slippage(adv))
    atr_price = atr_pct / 100.0 * close
    stop = entry * (1 - stop_mult * atr_pct / 100.0)
    target = entry * (1 + target_pct_cfg / 100.0)

    stop_dist = max(entry - stop, 1e-9)
    shares = base_risk_qty(
        equity * exposure_scalar, entry, entry - stop, adv, float(cfg["risk_per_trade_pct"]),
        max_position_pct=float(cfg.get("max_position_pct", 15.0)),
        max_adv_participation=float(cfg.get("max_adv_participation_pct", 5.0)) / 100.0,
    )
    rank_pct = float(row["trend_rank"])
    grade, conv = _grade(rank_pct)
    min_hold, max_hold = int(cfg["min_hold_days"]), int(cfg["max_hold_days"])
    stop_pct = round((entry - stop) / entry * 100, 2)
    tgt_pct = round((target - entry) / entry * 100, 2)
    bw = _add_trading_days(datetime.strptime(signal_date, "%Y-%m-%d").date(), BUY_WINDOW_TRADING_DAYS)

    return {
        "ticker": row["ticker"], "strategy": "LONG_HORIZON", "signal_date": signal_date,
        "grade": grade, "conviction": conv,
        "trend_rank_pct": round(rank_pct * 100, 1), "trend_slope": round(float(row[SIGNAL]), 4),
        "close": round(close, 2),
        "entry": round(entry, 2), "entry_is_indicative": True, "entry_method": "t_close_plus_slip",
        "max_entry": round(entry * 1.01, 2), "order_type_hint": "LIMIT_AT_NEXT_OPEN",
        "stop": round(stop, 2), "stop_pct": stop_pct,
        "target": round(target, 2), "target_pct": tgt_pct,
        "rr": round((target - entry) / stop_dist, 2) if entry > stop else None,
        "atr": round(atr_price, 2),
        "shares": shares, "position_value": round(shares * entry, 0),
        "risk_amount": round(shares * stop_dist, 0), "risk_per_share": round(stop_dist, 2),
        "min_hold_days": min_hold, "max_hold_days": max_hold,
        "trailing_activate_pct": float(cfg["trailing_activate_pct"]),
        "trailing_pct": float(cfg["trailing_pct"]),
        "debt_equity": round(float(row.get("debt_equity", 0) or 0), 2),
        "adv_rupees_20d": round(adv, 0), "sector": get_sector(str(row["ticker"])),
        "buy_window_until": bw.strftime("%Y-%m-%d"),
        "exit_rules": (
            f"Hold min {min_hold} / max {max_hold}d. Stop: close < entry − "
            f"{stop_mult:.2f}×ATR ({stop_pct}%). Target +{tgt_pct}%. "
            f"Trail {float(cfg['trailing_pct']):.2f}% below peak after "
            f"+{float(cfg['trailing_activate_pct']):.0f}%."),
    }


def scan(
    panel: pd.DataFrame, cfg: Mapping[str, Any], *,
    held: Iterable[str] = (), suspect: Iterable[str] = (),
    equity: float = EQUITY, as_of: Any = None, exposure_scalar: float = 1.0,
    date_col: str = "date", rank_col: str = "trend_rank",
) -> list[dict[str, Any]]:
    """Select today's BUY signals from a ranked panel.

    Takes the ``as_of`` (latest if None) date's rows whose ``trend_rank >= 1 − gate_quantile``,
    drops ``held`` and ``suspect`` (demerger-quarantined) names, sorts by rank (best first), and
    fills the free slots (``max_positions − len(held)``). Returns the indicative signal records.
    """
    if panel.empty or rank_col not in panel.columns:
        return []
    df = panel.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    if as_of is None:
        as_of = df[date_col].max()
    else:
        as_of = pd.to_datetime(as_of)
    day = df[df[date_col] == as_of]
    if day.empty:
        return []

    held_set = {str(t).upper() for t in held}
    suspect_set = {str(t).upper() for t in suspect}
    q = float(cfg["gate_quantile"])
    free = int(cfg["max_positions"]) - len(held_set)
    if free <= 0:
        return []

    elig = day[day[rank_col] >= (1.0 - q)]
    elig = elig[~elig["ticker"].str.upper().isin(held_set | suspect_set)]
    elig = elig.dropna(subset=["close", "atr_pct_63", rank_col])
    elig = elig.sort_values(rank_col, ascending=False).head(free)

    signal_date = pd.Timestamp(as_of).strftime("%Y-%m-%d")
    return [build_signal(row, cfg, equity=equity, signal_date=signal_date,
                         exposure_scalar=exposure_scalar)
            for _, row in elig.iterrows()]
