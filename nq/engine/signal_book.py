"""Event-driven signal book — the second simulator, ``simulate``-compatible.

Why this exists
---------------
:func:`nq.engine.portfolio.simulate` hardcodes cross-sectional **rank-gate** selection and the four
:func:`nq.engine.exits.decide_exit` rules, so it cannot express an *event-driven* book: discrete
entry signals, a per-signal stop price, an R-multiple target, and a rule exit. That gap is why a
dozen ``scripts/diag_*.py`` explorers each grew their own portfolio loop — and their own bugs.

This module closes it. It returns **the same contract** as ``simulate`` —
``{equity_curve, trades, metrics}`` — which is the whole point: :mod:`nq.runner.research`
(``evaluate``, ``evaluate_overlay``) never touches the engine, it only reads those three keys. So a
book run through here inherits the entire mechanised promotion bar (paired block-bootstrap ΔSharpe
CI, DSR at the cumulative trial count, ΔCalmar, the **continuous-slice** sub-period gate,
walk-forward fold-pass, turnover, effective sample size) with no further work.

Separation of concerns
----------------------
**A strategy produces a signals table; this engine executes it.** The engine has no knowledge of
indicators, timeframes or rules, which is what makes it testable against hand-written signal tables
(``tests/test_signal_book.py``) rather than only against a strategy.

``signals`` — one row per entry signal, executed at the NEXT bar's open:

===============  ==========================================================================
``date``         the bar whose CLOSE produced the signal (never the execution bar)
``ticker``       instrument
``stop``         stop PRICE, computed from data available at ``date``
``target_r``     take-profit as an R multiple of ``entry - stop``; NaN/None = no target
``max_hold``     bar-count backstop
``priority``     fill order when signals exceed free slots (higher fills first)
===============  ==========================================================================

``exit_flags`` — optional ``(date, ticker) -> bool``; True means "close at the next open".

Execution and cost model (shared with ``simulate``, deliberately)
-----------------------------------------------------------------
Sizing is :func:`nq.engine.portfolio.base_risk_qty` — the single sizing source of truth, pinned by
``tests/test_stage2_golden.py::test_base_risk_qty_parity``. Costs are ``LEG_COST`` (brokerage + STT,
charged on BOTH legs) plus tiered slippage via ``_slip`` including the 0.5%-of-ADV impact term.

Intrabar ordering, stated because it is a real assumption: when one bar contains both the stop and
the target, the **stop is taken**. We hold no intraday data, so the ordering is unknowable; taking
the stop is the conservative choice. A stop that gaps through is filled at ``min(open, stop)`` —
worse of the two — so gap losses exceed 1R exactly as they do in life.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .portfolio import (LEG_COST, MAX_ADV_PARTICIPATION, STALE_ABSENT_DAYS, _slip, base_risk_qty,
                        compute_metrics)

__all__ = ["simulate_signal_book", "SignalBookConfig"]


@dataclass(frozen=True)
class SignalBookConfig:
    """Book shape. Defaults mirror the swing-survey book so its nine strategies port unchanged.

    ``max_position_pct`` is the notional cap. Note it BINDS on most trades: with a 2% risk budget
    and a 7% stop the risk term wants ~29% of equity, so the cap decides the size and the effective
    risk per trade is ``max_position_pct x stop_width``, not ``risk_pct``. Stated here because that
    surprised us once already.
    """
    max_positions: int = 10
    risk_pct: float = 2.0
    max_position_pct: float = 10.0
    max_adv_participation: float = MAX_ADV_PARTICIPATION
    allow_reentry: bool = True          # a name may be re-signalled after it closes
    one_position_per_ticker: bool = True


@dataclass
class _Pos:
    ticker: str
    entry: float
    stop: float
    r_unit: float
    target: float | None
    qty: int
    adv: float
    entry_date: Any
    max_hold: int
    days_held: int = 0
    pending_exit: bool = False
    mfe_r: float = 0.0
    mae_r: float = 0.0
    absent: int = 0
    marks: list[float] = field(default_factory=list)


def _exit_record(p: _Pos, exit_price: float, t: Any, reason: str) -> tuple[float, dict[str, Any]]:
    """Realise a position. Mirrors ``portfolio._book_exit`` exactly, plus R / MFE / MAE."""
    slip = _slip(p.adv, p.qty * exit_price)
    fill = exit_price * (1 - slip)
    proceeds = p.qty * fill
    cost = proceeds * LEG_COST
    rec = {
        "ticker": p.ticker, "entry_date": str(p.entry_date)[:10], "exit_date": str(t)[:10],
        "entry": round(p.entry, 2), "exit": round(fill, 2), "qty": p.qty,
        "days_held": p.days_held, "reason": reason,
        "return_pct": round((fill - p.entry) / p.entry * 100.0, 2),
        "pnl": round(p.qty * (fill - p.entry) - (p.qty * fill + p.qty * p.entry) * LEG_COST, 2),
        "r": round((fill - p.entry) / p.r_unit, 4) if p.r_unit > 0 else float("nan"),
        "stop_pct": round((p.entry - p.stop) / p.entry * 100.0, 3),
        "mfe_r": round(p.mfe_r, 3), "mae_r": round(p.mae_r, 3),
    }
    return proceeds - cost, rec


def simulate_signal_book(
    panel: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    cfg: SignalBookConfig | None = None,
    exit_flags: Mapping[tuple[Any, str], bool] | None = None,
    start: str | None = None,
    end: str | None = None,
    initial_capital: float = 1_000_000.0,
    date_col: str = "date",
) -> dict[str, Any]:
    """Execute ``signals`` against ``panel``; return ``{equity_curve, trades, metrics}``.

    ``panel`` is a tidy long frame with ``date, ticker, open, high, low, close`` and optionally
    ``adv_rupees_20d`` (0 when absent → tier slippage only, no impact term).
    """
    cfg = cfg or SignalBookConfig()
    need = {date_col, "ticker", "open", "high", "low", "close"}
    missing = need - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")

    p = panel.copy()
    p[date_col] = pd.to_datetime(p[date_col])
    if start:
        p = p[p[date_col] >= pd.Timestamp(start)]
    if end:
        p = p[p[date_col] <= pd.Timestamp(end)]
    if p.empty:
        return {"equity_curve": [], "trades": [], "metrics": {}}
    if "adv_rupees_20d" not in p.columns:
        p["adv_rupees_20d"] = 0.0

    sig = signals.copy()
    sig[date_col] = pd.to_datetime(sig[date_col])
    if "priority" not in sig.columns:
        sig["priority"] = 0.0
    if "target_r" not in sig.columns:
        sig["target_r"] = np.nan
    if "max_hold" not in sig.columns:
        sig["max_hold"] = 10_000

    dates = sorted(p[date_col].unique())
    dpos = {d: i for i, d in enumerate(dates)}
    by_date = {d: g.set_index("ticker") for d, g in p.groupby(date_col, sort=True)}
    # a signal on date d executes on the NEXT trading date present in the panel
    pending: dict[Any, list[tuple]] = {}
    for _, r in sig.iterrows():
        i = dpos.get(r[date_col])
        if i is None or i + 1 >= len(dates):
            continue
        pending.setdefault(dates[i + 1], []).append(
            (float(r["priority"]), str(r["ticker"]), float(r["stop"]),
             float(r["target_r"]), int(r["max_hold"])))

    cash = equity = float(initial_capital)
    positions: dict[str, _Pos] = {}
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    closed_tickers: set[str] = set()

    for t in dates:
        day = by_date.get(t)
        if day is None:
            continue

        # ---- 1. manage open positions (stop > target > rule > max-hold) -------------------
        for tkr in list(positions):
            pos = positions[tkr]
            if tkr not in day.index:
                # B-1 (absent bars): a delisted/suspended name must not hold a slot forever.
                # Mirrors simulate's STALE_ABSENT_DAYS force-close, at the last observed mark.
                pos.absent += 1
                if pos.absent >= STALE_ABSENT_DAYS:
                    mark = pos.marks[-1] if pos.marks else pos.entry
                    delta, rec = _exit_record(pos, mark, t, "stale")
                    cash += delta
                    trades.append(rec)
                    del positions[tkr]
                    closed_tickers.add(tkr)
                continue
            pos.absent = 0
            bar = day.loc[tkr]
            pos.days_held += 1
            if pos.r_unit > 0:
                pos.mfe_r = max(pos.mfe_r, (float(bar["high"]) - pos.entry) / pos.r_unit)
                pos.mae_r = min(pos.mae_r, (float(bar["low"]) - pos.entry) / pos.r_unit)
            px = reason = None
            if float(bar["low"]) <= pos.stop:
                px, reason = min(float(bar["open"]), pos.stop), "stop"
            elif pos.target is not None and float(bar["high"]) >= pos.target:
                px, reason = max(float(bar["open"]), pos.target), "target"
            elif pos.pending_exit:
                px, reason = float(bar["open"]), "rule"
            elif pos.days_held >= pos.max_hold:
                px, reason = float(bar["close"]), "time"
            if px is not None:
                delta, rec = _exit_record(pos, px, t, reason)
                cash += delta
                trades.append(rec)
                del positions[tkr]
                closed_tickers.add(tkr)
                continue
            pos.pending_exit = bool(exit_flags.get((t, tkr), False)) if exit_flags else False

        # ---- 2. fill pending entries at today's open, best priority first -----------------
        for _prio, tkr, stop, target_r, max_hold in sorted(pending.get(t, []), reverse=True):
            if len(positions) >= cfg.max_positions:
                break
            if cfg.one_position_per_ticker and tkr in positions:
                continue
            if not cfg.allow_reentry and tkr in closed_tickers:
                continue
            if tkr not in day.index:
                continue
            bar = day.loc[tkr]
            entry = float(bar["open"])
            if not np.isfinite(entry) or not np.isfinite(stop) or entry <= stop:
                continue
            adv = float(bar.get("adv_rupees_20d", 0.0) or 0.0)
            # Two-pass slippage, matching ``simulate``: size at the tier rate (the same
            # ``leg_slippage(adv)`` the live scan quotes as its indicative entry), then RE-PRICE
            # with the market-impact term now that the notional is known. Pricing entries at the
            # tier rate alone while charging impact on exits would understate round-trip friction.
            fill = entry * (1 + _slip(adv, 0.0))
            qty = base_risk_qty(equity, fill, fill - stop, adv, cfg.risk_pct,
                                max_position_pct=cfg.max_position_pct,
                                max_adv_participation=cfg.max_adv_participation)
            if qty <= 0:
                continue
            fill = entry * (1 + _slip(adv, qty * fill))
            if fill <= stop:
                continue
            notional = qty * fill
            outlay = notional * (1 + LEG_COST)
            if outlay > cash:                      # cap by affordable cash, never borrow
                qty = int(cash / (fill * (1 + LEG_COST)))
                if qty <= 0:
                    continue
                notional = qty * fill
                outlay = notional * (1 + LEG_COST)
            cash -= outlay
            r_unit = fill - stop
            positions[tkr] = _Pos(
                ticker=tkr, entry=fill, stop=stop, r_unit=r_unit,
                target=(fill + target_r * r_unit) if np.isfinite(target_r) else None,
                qty=qty, adv=adv, entry_date=t, max_hold=max_hold,
                pending_exit=bool(exit_flags.get((t, tkr), False)) if exit_flags else False)

        # ---- 3. mark to market -------------------------------------------------------------
        mtm = 0.0
        for tkr, pos in positions.items():
            if tkr in day.index:
                pos.marks.append(float(day.loc[tkr, "close"]))
            mtm += pos.qty * (pos.marks[-1] if pos.marks else pos.entry)
        equity = cash + mtm
        equity_curve.append({"date": str(t)[:10], "equity": round(equity, 2),
                             "cash": round(cash, 2), "n_positions": len(positions)})

    return {"equity_curve": equity_curve, "trades": trades,
            "metrics": compute_metrics(equity_curve, trades, initial_capital)}


def signals_from_arrays(
    dates: pd.DatetimeIndex, ticker: str, entry: np.ndarray, stop: np.ndarray,
    *, target_r: float | None = 2.0, max_hold: int = 252, priority: np.ndarray | None = None,
) -> pd.DataFrame:
    """Adapter: per-ticker boolean/price arrays -> the tidy ``signals`` frame.

    Lets the survey-era strategy functions (which return aligned numpy arrays) feed the engine
    without each one re-deriving a signals table.
    """
    idx = np.flatnonzero(np.asarray(entry, dtype=bool))
    if idx.size == 0:
        return pd.DataFrame(columns=["date", "ticker", "stop", "target_r", "max_hold", "priority"])
    return pd.DataFrame({
        "date": pd.DatetimeIndex(dates)[idx], "ticker": ticker,
        "stop": np.asarray(stop, dtype=float)[idx],
        "target_r": np.nan if target_r is None else float(target_r),
        "max_hold": int(max_hold),
        "priority": (np.asarray(priority, dtype=float)[idx] if priority is not None
                     else np.zeros(idx.size)),
    })
