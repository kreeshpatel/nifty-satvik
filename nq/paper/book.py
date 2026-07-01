"""PaperBook — the stateful, cron-resumable paper-trading book (Stage E).

Mirrors ``nq.engine.portfolio.simulate`` one day at a time, reusing the SAME shared kernels
(``base_risk_qty``, ``decide_exit``, ``leg_slippage``/``_slip``, ``vol_target_scalar``, ``_book_exit``)
so paper P&L is byte-consistent with the validated backtest. The daily cron calls :meth:`step` once per
session; state (cash, positions, pending, NAV history, trades, kill-state) persists to JSON/CSV across
runs. The parity gate (tests/test_stagee_paper_parity.py) proves ``run_batch`` ≡ ``simulate``.

Live conventions match the engine: signal at close(t) → fill at open(t+1) with tiered slippage;
close-only stop with gap-fill, intraday target touch, trailing on the running peak, 63d time cap; sizing
off the LIVE NAV de-grossed by the vol-target scalar (O-009). Kill-criteria run in OBSERVE mode.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nq.engine.exits import decide_exit
from nq.engine.portfolio import (LEG_COST, STALE_ABSENT_DAYS, Position, _book_exit, _mark, _slip,
                                 base_risk_qty, compute_metrics, vol_target_scalar)


class PaperBook:
    """A resumable paper book. Construct with the frozen ``cfg`` + optional ``vol_target`` (the
    O-009 live overlay); call :meth:`step` per session; :meth:`save`/:meth:`load` persist state."""

    def __init__(self, cfg: Mapping[str, Any], *, initial_capital: float = 1_000_000.0,
                 vol_target: Mapping[str, Any] | None = None,
                 rank_col: str = "trend_rank", min_adv_rs: float = 0.0):
        self.q = float(cfg["gate_quantile"])
        self.stop_mult = float(cfg["stop_atr_mult"])
        self.target_pct = float(cfg["target_pct"])
        self.max_hold = int(cfg["max_hold_days"])
        self.risk_pct = float(cfg["risk_per_trade_pct"])
        self.max_pos = int(cfg["max_positions"])
        self.max_position_pct = float(cfg.get("max_position_pct", 15.0))
        self.max_adv_part = float(cfg.get("max_adv_participation_pct", 5.0)) / 100.0
        self.exit_cfg = {"min_hold_days": int(cfg["min_hold_days"]), "max_hold_days": self.max_hold,
                         "trailing_activate_pct": float(cfg["trailing_activate_pct"]),
                         "trailing_pct": float(cfg["trailing_pct"])}
        self.rank_col = rank_col
        self.min_adv_rs = min_adv_rs
        vt = vol_target if vol_target and float(vol_target.get("vol_target_annual", 0.0)) > 0 else None
        self.vt = vt
        self.vt_target = float(vt["vol_target_annual"]) if vt else 0.0
        self.vt_window = int(vt.get("vol_window", 42)) if vt else 42
        self.vt_floor = float(vt.get("vol_floor", 0.40)) if vt else 0.40
        self.initial_capital = float(initial_capital)

        self.cash = float(initial_capital)
        self.positions: dict[str, Position] = {}
        self.pending: list[str] = []
        self.equity_curve: list[dict[str, Any]] = []
        self.trades: list[dict[str, Any]] = []

    # ── the daily step (mirrors simulate's per-day body; hooks off = shipped cfg) ──
    def step(self, t: Any, day: pd.DataFrame) -> None:
        """Advance one session. ``day`` = the panel rows for date ``t`` indexed by ticker
        (open/high/low/close + atr_pct_63 + adv_rupees_20d + rank_col)."""
        vscalar = 1.0
        if self.vt is not None and len(self.equity_curve) > 1:
            eq = np.array([e["equity"] for e in self.equity_curve[-(self.vt_window + 1):]], dtype=float)
            vscalar = vol_target_scalar(np.diff(eq) / eq[:-1], target_annual=self.vt_target,
                                        floor=self.vt_floor, window=self.vt_window)

        # 1. fill pending entries at today's OPEN
        for tkr in self.pending:
            if tkr in self.positions or tkr not in day.index or len(self.positions) >= self.max_pos:
                continue
            row = day.loc[tkr]
            o = float(row["open"]); atr_pct = float(row.get("atr_pct_63", np.nan))
            adv = float(row.get("adv_rupees_20d", 0.0) or 0.0)
            if not (o > 0) or not (atr_pct > 0):
                continue
            fill = o * (1 + _slip(adv, 0.0))
            stop = fill * (1 - self.stop_mult * atr_pct / 100.0)
            risk_per_share = fill - stop
            if risk_per_share <= 0:
                continue
            equity = self.cash + sum(p.qty * _mark(p, day) for p in self.positions.values())
            qty = base_risk_qty(equity * vscalar, fill, risk_per_share, adv, self.risk_pct,
                                max_position_pct=self.max_position_pct,
                                max_adv_participation=self.max_adv_part)
            if qty <= 0:
                continue
            fill = o * (1 + _slip(adv, qty * fill))          # re-price with impact for the size
            qty = min(qty, int(self.cash / (fill * (1 + LEG_COST))))
            if qty <= 0:
                continue
            notional = qty * fill
            self.cash -= notional + notional * LEG_COST
            stop = fill * (1 - self.stop_mult * atr_pct / 100.0)
            self.positions[tkr] = Position(
                ticker=tkr, entry_date=t, entry=fill, qty=qty, stop=stop,
                target=fill * (1 + self.target_pct / 100.0), peak=fill, atr_pct=atr_pct, adv=adv,
                last_mark=fill)
        self.pending = []

        # 2. exit evaluation on open positions
        for tkr in list(self.positions.keys()):
            p = self.positions[tkr]
            if p.entry_date == t:
                continue
            p.days_held += 1
            if tkr not in day.index:
                p.absent_run += 1
                if p.days_held >= self.max_hold or p.absent_run >= STALE_ABSENT_DAYS:
                    delta, rec = _book_exit(p, p.last_mark, t, "stale")
                    self.cash += delta; self.trades.append(rec); del self.positions[tkr]
                continue
            p.absent_run = 0
            row = day.loc[tkr]
            o, h, c = float(row["open"]), float(row["high"]), float(row["close"])
            decision = decide_exit({"entry": p.entry, "stop": p.stop, "peak": p.peak, "target": p.target},
                                   {"open": o, "high": h, "close": c}, self.exit_cfg, p.days_held)
            if decision.close_reason:
                delta, rec = _book_exit(p, decision.exit_price, t, decision.close_reason)
                self.cash += delta; self.trades.append(rec); del self.positions[tkr]
            else:
                if decision.new_peak is not None:
                    p.peak = decision.new_peak
                p.last_mark = c

        # 3. selection: fill free slots with the top-ranked non-held names
        free = self.max_pos - len(self.positions)
        if free > 0 and self.rank_col in day.columns:
            elig = day[day[self.rank_col] >= (1.0 - self.q)]
            elig = elig[~elig.index.isin(self.positions.keys())]
            if self.min_adv_rs > 0 and "adv_rupees_20d" in elig.columns:
                elig = elig[elig["adv_rupees_20d"].fillna(0.0) >= self.min_adv_rs]
            if "atr_pct_63" in elig.columns:
                elig = elig.dropna(subset=["close", "atr_pct_63"])
            self.pending = list(elig.sort_values(self.rank_col, ascending=False).index[:free])

        # 4. mark-to-market NAV
        mtm = sum(p.qty * _mark(p, day) for p in self.positions.values())
        self.equity_curve.append({"date": str(t)[:10], "equity": round(self.cash + mtm, 2),
                                  "cash": round(self.cash, 2), "n_positions": len(self.positions)})

    def run_batch(self, panel: pd.DataFrame, *, date_col: str = "date") -> dict[str, Any]:
        """Step the book over a whole panel (for the parity gate). Returns the simulate-shaped dict."""
        df = panel.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.dropna(subset=["open", "high", "low", "close"])
        for d, g in df.groupby(date_col, sort=True):
            self.step(d, g.set_index("ticker"))
        return {"equity_curve": self.equity_curve, "trades": self.trades,
                "metrics": compute_metrics(self.equity_curve, self.trades, self.initial_capital)}

    # ── kill-criteria (OBSERVE mode — logged, not enforced) ──
    def kill_flags(self, *, wr_min: float = 45.0, min_trades: int = 20,
                   zero_signal_streak: int = 5) -> dict[str, Any]:
        closed = self.trades[-min_trades:]
        wr = (100.0 * sum(1 for t in closed if t["return_pct"] > 0) / len(closed)) if closed else None
        rets = np.array([e["equity"] for e in self.equity_curve[-31:]], dtype=float)
        r30 = np.diff(rets) / rets[:-1] if rets.size > 1 else np.array([])
        sh30 = float(r30.mean() / r30.std() * np.sqrt(252)) if r30.size > 2 and r30.std() > 0 else None
        return {
            "wr_last20": round(wr, 1) if wr is not None else None,
            "wr_breach": bool(wr is not None and len(closed) >= min_trades and wr < wr_min),
            "sharpe_30d": round(sh30, 3) if sh30 is not None else None,
            "sharpe_30d_breach": bool(sh30 is not None and sh30 < 0),
            "mode": "observe",
        }

    # ── persistence (survives across cron runs) ──
    def save(self, state_dir: str | Path) -> None:
        d = Path(state_dir); d.mkdir(parents=True, exist_ok=True)
        state = {
            "cash": self.cash, "pending": self.pending,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "config": {"initial_capital": self.initial_capital, "vol_target": self.vt},
        }
        (d / "paper_portfolio.json").write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        (d / "paper_trades.json").write_text(json.dumps(self.trades, indent=2, default=str), encoding="utf-8")
        pd.DataFrame(self.equity_curve).to_csv(d / "portfolio_history.csv", index=False)
        (d / "kill_state.json").write_text(json.dumps(self.kill_flags(), indent=2), encoding="utf-8")

    def load(self, state_dir: str | Path) -> None:
        d = Path(state_dir)
        pf = d / "paper_portfolio.json"
        if not pf.exists():
            return
        st = json.loads(pf.read_text(encoding="utf-8"))
        self.cash = float(st["cash"]); self.pending = list(st.get("pending", []))
        self.positions = {k: Position(**v) for k, v in st.get("positions", {}).items()}
        tp = d / "paper_trades.json"
        self.trades = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else []
        hp = d / "portfolio_history.csv"
        self.equity_curve = pd.read_csv(hp).to_dict("records") if hp.exists() else []
