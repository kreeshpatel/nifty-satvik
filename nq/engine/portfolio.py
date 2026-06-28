"""The long-horizon cross-sectional portfolio backtest.

Each session: rank the eligible universe by the trend signal, fill the top non-held names as
slots free (capacity-bounded, like the live tracker), hold up to 63 trading days, and exit on
the FIRST of the shared stop / target / trailing / time rules (:func:`nq.engine.exits.decide_exit`).

Realism (matches the live conventions, no lookahead):
  * **Signal at close(t) → fill at open(t+1).** The day-t cross-sectional rank is acted on at the
    next session's open. The simulator walks OHLC; it never reads a forward label.
  * **Close-only hard stop** with gap-fill; **intraday target touch** (resting limit at the
    target); **trailing stop** on the running close-peak; **hard 63d time cap**; profit-taking
    gated below ``min_hold`` — all decided by the shared ``decide_exit``.
  * **Tiered costs**: per-leg brokerage 0.03% + STT 0.10% + rupee-ADV slippage tier
    (LARGE 0.05% / MID 0.22% / SMALL 0.40%) + 0.1% impact above 0.5% of daily turnover. Position
    size is risk-based, capped by position% and 5% of ADV (:func:`base_risk_qty`).

Ported behaviour-faithfully from the validated source ``long_horizon/backtest/portfolio.py`` with
the flag-gated overlays (vol-target / market-exposure / regime-to-cash / reallocation), all OFF on
the golden path, omitted — so the golden master reproduces byte-for-byte (the Stage-2 gate).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from config import (
    ADV_LARGE_CAP_RS,
    ADV_MID_CAP_RS,
    BROKERAGE_PCT,
    MAX_ADV_PARTICIPATION,
    SLIPPAGE,
    STT_PCT,
)

from .exits import decide_exit

LEG_COST = BROKERAGE_PCT + STT_PCT     # per-leg brokerage + STT (delivery, both legs)
TRADING_DAYS = 252
STALE_ABSENT_DAYS = 10                 # force-close a held name absent this many sessions


def _tier(adv_rupees: float) -> str:
    if adv_rupees >= ADV_LARGE_CAP_RS:
        return "LARGE_CAP"
    if adv_rupees >= ADV_MID_CAP_RS:
        return "MID_CAP"
    return "SMALL_CAP"


def _slip(adv_rupees: float, notional: float) -> float:
    """Per-leg slippage: the liquidity-tier rate, plus a flat 0.1% impact when the order exceeds
    0.5% of the name's daily rupee turnover."""
    s = SLIPPAGE[_tier(adv_rupees)]
    if adv_rupees > 0 and notional > 0.005 * adv_rupees:
        s += 0.001
    return s


def base_risk_qty(
    equity: float, fill: float, risk_per_share: float, adv: float, risk_pct: float,
    *, max_position_pct: float = 15.0, max_adv_participation: float = MAX_ADV_PARTICIPATION,
) -> int:
    """First-pass risk-budget share count — the SINGLE sizing source of truth shared by the
    backtest (``simulate``, before its market-impact re-pricing + cash cap) and the live scanner::

        qty = floor( risk_pct% of equity / risk_per_share ),
              capped by floor(max_position_pct% of equity / fill)
              and       floor(max_adv_participation × ADV / fill).
    """
    if fill <= 0 or risk_per_share <= 0:
        return 0
    qty = int(risk_pct / 100.0 * equity / risk_per_share)
    qty = min(qty, int(max_position_pct / 100.0 * equity / fill))
    if adv > 0:
        qty = min(qty, int(max_adv_participation * adv / fill))
    return max(0, qty)


@dataclass
class Position:
    ticker: str
    entry_date: object
    entry: float
    qty: int
    stop: float
    target: float
    peak: float
    atr_pct: float
    adv: float
    days_held: int = 0
    last_mark: float = 0.0      # last close seen — carries MTM across days a name has no quote
    absent_run: int = 0         # consecutive sessions with no quote (force-close if it runs long)


def _mark(p: Position, day: pd.DataFrame) -> float:
    """Mark a held position: today's close if it has a quote, else its last seen mark (prevents a
    sparse-data date from phantom-collapsing equity)."""
    if p.ticker in day.index:
        return float(day.loc[p.ticker, "close"])
    return p.last_mark


def _book_exit(p: Position, exit_price: float, t: object, reason: str) -> tuple[float, dict[str, Any]]:
    """Realize a position at ``exit_price`` (per-leg slippage + brokerage + STT). Returns the cash
    delta (proceeds net of cost) and the trade record."""
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
    }
    return proceeds - cost, rec


def simulate(
    panel: pd.DataFrame,
    cfg: Mapping[str, Any],
    *,
    start: str | None = None,
    end: str | None = None,
    initial_capital: float = 1_000_000.0,
    date_col: str = "date",
    rank_col: str = "trend_rank",
    min_adv_rs: float = 0.0,
) -> dict[str, Any]:
    """Run the portfolio backtest over ``panel`` (a ranked eligible panel) with the frozen
    ``cfg``. ``min_adv_rs`` is an optional tradeability floor on ENTRIES (0 = trade everything the
    rank gate selects — the universe was already masked upstream). Returns
    ``{equity_curve, trades, metrics}``."""
    q = float(cfg["gate_quantile"])
    stop_mult = float(cfg["stop_atr_mult"])
    target_pct = float(cfg["target_pct"])
    min_hold = int(cfg["min_hold_days"])
    max_hold = int(cfg["max_hold_days"])
    risk_pct = float(cfg["risk_per_trade_pct"])
    max_pos = int(cfg["max_positions"])
    max_position_pct = float(cfg.get("max_position_pct", 15.0))
    max_adv_part = float(cfg.get("max_adv_participation_pct", 5.0)) / 100.0
    exit_cfg = {
        "min_hold_days": min_hold, "max_hold_days": max_hold,
        "trailing_activate_pct": float(cfg["trailing_activate_pct"]),
        "trailing_pct": float(cfg["trailing_pct"]),
    }

    df = panel.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    if start:
        df = df[df[date_col] >= pd.to_datetime(start)]
    if end:
        df = df[df[date_col] <= pd.to_datetime(end)]
    df = df.dropna(subset=["open", "high", "low", "close"])
    by_date: dict[Any, Any] = {d: g.set_index("ticker") for d, g in df.groupby(date_col, sort=True)}
    dates = sorted(by_date.keys())

    cash = float(initial_capital)
    positions: dict[str, Position] = {}
    pending: list[str] = []                 # tickers selected at t-1, fill at t's open
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []

    for t in dates:
        day = by_date[t]

        # ── 1. Fill pending entries at today's OPEN ──────────────────────────────
        for tkr in pending:
            if tkr in positions or tkr not in day.index or len(positions) >= max_pos:
                continue
            row = day.loc[tkr]
            o = float(row["open"])
            atr_pct = float(row.get("atr_pct_63", np.nan))
            adv = float(row.get("adv_rupees_20d", 0.0) or 0.0)
            if not (o > 0) or not (atr_pct > 0):
                continue
            slip = _slip(adv, 0.0)
            fill = o * (1 + slip)
            stop = fill * (1 - stop_mult * atr_pct / 100.0)
            risk_per_share = fill - stop
            if risk_per_share <= 0:
                continue
            equity = cash + sum(p.qty * _mark(p, day) for p in positions.values())
            qty = base_risk_qty(equity, fill, risk_per_share, adv, risk_pct,
                                max_position_pct=max_position_pct, max_adv_participation=max_adv_part)
            if qty <= 0:
                continue
            notional = qty * fill
            slip2 = _slip(adv, notional)
            fill = o * (1 + slip2)           # re-price with impact for the actual size
            qty = min(qty, int(cash / (fill * (1 + LEG_COST))))   # affordability incl. entry cost
            if qty <= 0:
                continue
            notional = qty * fill
            cost = notional * LEG_COST
            cash -= notional + cost
            stop = fill * (1 - stop_mult * atr_pct / 100.0)
            positions[tkr] = Position(
                ticker=tkr, entry_date=t, entry=fill, qty=qty, stop=stop,
                target=fill * (1 + target_pct / 100.0), peak=fill, atr_pct=atr_pct, adv=adv,
                last_mark=fill)
        pending = []

        # ── 2. Exit evaluation on open positions (today's OHLC) ──────────────────
        for tkr in list(positions.keys()):
            p = positions[tkr]
            if p.entry_date == t:
                continue                      # filled at today's open — first eligible to exit t+1
            p.days_held += 1                  # age one ELAPSED session
            if tkr not in day.index:          # no quote — carry, but force-close if timed-out/stuck
                p.absent_run += 1
                if p.days_held >= max_hold or p.absent_run >= STALE_ABSENT_DAYS:
                    delta, rec = _book_exit(p, p.last_mark, t, "stale")
                    cash += delta
                    trades.append(rec)
                    del positions[tkr]
                continue
            p.absent_run = 0
            row = day.loc[tkr]
            o, h, c = float(row["open"]), float(row["high"]), float(row["close"])
            decision = decide_exit(
                {"entry": p.entry, "stop": p.stop, "peak": p.peak, "target": p.target},
                {"open": o, "high": h, "close": c}, exit_cfg, p.days_held)
            if decision.close_reason:
                delta, rec = _book_exit(p, decision.exit_price, t, decision.close_reason)
                cash += delta
                trades.append(rec)
                del positions[tkr]
            else:
                if decision.new_peak is not None:
                    p.peak = decision.new_peak
                p.last_mark = c

        # ── 3. Selection: fill free slots with the top-ranked non-held names ─────
        free = max_pos - len(positions)
        if free > 0 and rank_col in day.columns:
            elig = day[day[rank_col] >= (1.0 - q)]
            elig = elig[~elig.index.isin(positions.keys())]
            if min_adv_rs > 0 and "adv_rupees_20d" in elig.columns:
                elig = elig[elig["adv_rupees_20d"].fillna(0.0) >= min_adv_rs]
            if "atr_pct_63" in elig.columns:
                elig = elig.dropna(subset=["close", "atr_pct_63"])
            elig = elig.sort_values(rank_col, ascending=False)
            pending = list(elig.index[:free])

        # ── 4. Mark-to-market equity (last-mark fallback for names absent today) ──
        mtm = sum(p.qty * _mark(p, day) for p in positions.values())
        equity_curve.append({"date": str(t)[:10], "equity": round(cash + mtm, 2),
                             "cash": round(cash, 2), "n_positions": len(positions)})

    return {"equity_curve": equity_curve, "trades": trades,
            "metrics": compute_metrics(equity_curve, trades, initial_capital)}


def compute_metrics(
    equity_curve: list[dict[str, Any]], trades: list[dict[str, Any]], initial_capital: float,
) -> dict[str, Any]:
    """CAGR, Sharpe, Sortino, max-drawdown, Calmar, win-rate, profit factor, exposure, avg hold."""
    if not equity_curve:
        return {}
    eq = np.array([e["equity"] for e in equity_curve], dtype=float)
    n = len(eq)
    rets = np.diff(eq) / eq[:-1] if n > 1 else np.array([0.0])
    rets = rets[np.isfinite(rets)]
    years = n / TRADING_DAYS
    cagr = (eq[-1] / eq[0]) ** (1.0 / years) - 1.0 if years > 0 and eq[0] > 0 else float("nan")
    sharpe = (rets.mean() / rets.std() * np.sqrt(TRADING_DAYS)) if rets.std() > 0 else float("nan")
    downside = rets[rets < 0]
    sortino = ((rets.mean() / downside.std() * np.sqrt(TRADING_DAYS))
               if downside.size and downside.std() > 0 else float("nan"))
    cummax = np.maximum.accumulate(eq)
    max_dd = float((eq / cummax - 1.0).min()) if n else float("nan")
    wins = [t for t in trades if t["return_pct"] > 0]
    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    avg_pos = float(np.mean([e["n_positions"] for e in equity_curve]))
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    return {
        "final_equity": round(float(eq[-1]), 2),
        "total_return_pct": round((eq[-1] / eq[0] - 1.0) * 100.0, 2),
        "cagr_pct": round(cagr * 100.0, 2),
        "sharpe": round(float(sharpe), 3),
        "sortino": round(float(sortino), 3),
        "max_drawdown_pct": round(max_dd * 100.0, 2),
        "calmar": round(cagr * 100.0 / abs(max_dd * 100.0), 2) if max_dd != 0 and np.isfinite(cagr) else float("nan"),
        "turnover_per_year": round(len(trades) / years, 1) if years > 0 else float("nan"),
        "n_trades": len(trades),
        "n_reallocated_exits": reasons.get("reallocated", 0),
        "win_rate_pct": round(100.0 * len(wins) / len(trades), 2) if trades else float("nan"),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf"),
        "avg_return_per_trade_pct": round(float(np.mean([t["return_pct"] for t in trades])), 3) if trades else float("nan"),
        "avg_hold_days": round(float(np.mean([t["days_held"] for t in trades])), 1) if trades else float("nan"),
        "avg_positions_held": round(avg_pos, 2),
        "exit_reasons": reasons,
        "years": round(years, 2),
    }
