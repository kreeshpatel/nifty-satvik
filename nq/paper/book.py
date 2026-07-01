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
        self.peak = float(initial_capital)      # running max NAV (for the dashboard drawdown)
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
        nav = self.cash + mtm
        self.peak = max(self.peak, nav)
        self.equity_curve.append({"date": str(t)[:10], "equity": round(nav, 2),
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

    # ── dashboard-contract exports (the niftyquant FastAPI's expected shapes) ──
    def dashboard_files(self) -> dict[str, Any]:
        """The results/* files the niftyquant backend reads, in ITS shapes:
        paper_portfolio.json {cash, peak_value, positions:{tkr:{current_value,...}}},
        paper_trades.json [{..., net_pct, net_pnl, hold_days}], portfolio_history.csv [date,total_value],
        kill_state.json. (paper_ledger_history.csv is written as a copy of portfolio_history.)"""
        nav = self.equity_curve[-1]["equity"] if self.equity_curve else self.initial_capital
        # field names mirror what the niftyquant positions.py router reads (Holdings page):
        # entry_price/shares/atr_stop/current_price/current_value/unrealised_pnl(_pct)/entry_date.
        positions = {}
        for p in self.positions.values():
            mkt = round(p.qty * p.last_mark, 2)
            positions[p.ticker] = {
                "entry_date": str(p.entry_date)[:10], "entry_price": round(p.entry, 2),
                "shares": p.qty, "position_size": round(p.qty * p.entry, 2),
                "atr_stop": round(p.stop, 2), "target": round(p.target, 2),
                "current_price": round(p.last_mark, 2), "current_value": mkt,
                "unrealised_pnl": round(p.qty * (p.last_mark - p.entry), 2),
                "unrealised_pnl_pct": round((p.last_mark / p.entry - 1) * 100, 2) if p.entry else 0.0,
                "days_held": p.days_held,
            }
        portfolio = {"cash": round(self.cash, 2), "peak_value": round(self.peak, 2),
                     "total_value": round(nav, 2), "n_positions": len(self.positions),
                     "total_trades": len(self.trades), "positions": positions}
        trades = [{**t, "net_pct": t.get("return_pct"), "net_pnl": t.get("pnl"),
                   "hold_days": t.get("days_held")} for t in self.trades]
        hist = pd.DataFrame(self.equity_curve or [{"date": "", "equity": self.initial_capital,
                            "cash": self.initial_capital, "n_positions": 0}]).rename(
                            columns={"equity": "total_value"})
        # signal-history lifecycle — feeds /api/signals/history + /api/backtest/live + positions-nq
        # enrichment + StockDetail. Readers key on ticker/signal_date/status/entry/stop/target/
        # close_price/close_date/pnl_pct/days_since. Closed trades → HIT_TARGET/HIT_STOP/EXPIRED
        # (trailing counts as a stop-type exit so a profitable one shows "Trailing at Gain"); held → ACTIVE.
        _RSN = {"target": "HIT_TARGET", "stop": "HIT_STOP", "trailing": "HIT_STOP",
                "time": "EXPIRED", "stale": "EXPIRED"}
        sig_hist: list[dict[str, Any]] = []
        for t in self.trades:
            rp = t.get("return_pct")
            sig_hist.append({"ticker": t.get("ticker"), "signal_date": t.get("entry_date"),
                             "status": _RSN.get(t.get("reason"), "EXPIRED"), "entry": t.get("entry"),
                             "close_price": t.get("exit"), "close_date": t.get("exit_date"),
                             "return_pct": rp, "pnl_pct": rp, "close_pnl_pct": rp,
                             "days_since": t.get("days_held"), "hold_days": t.get("days_held"),
                             "exit_reason": t.get("reason")})
        for p in self.positions.values():
            pct = round((p.last_mark / p.entry - 1) * 100, 2) if p.entry else 0.0
            sig_hist.append({"ticker": p.ticker, "signal_date": str(p.entry_date)[:10], "status": "ACTIVE",
                             "entry": round(p.entry, 2), "stop": round(p.stop, 2), "target": round(p.target, 2),
                             "current_price": round(p.last_mark, 2), "close_price": round(p.last_mark, 2),
                             "pnl_pct": pct, "return_pct": pct, "days_since": p.days_held, "hold_days": p.days_held})
        _cr = [t.get("return_pct") or 0.0 for t in self.trades]
        _wins = [r for r in _cr if r > 0]
        sig_analytics = {"total_signals": len(sig_hist), "total_closed": len(self.trades),
                         "active": len(self.positions),
                         "win_rate": round(len(_wins) / len(_cr) * 100, 1) if _cr else None,
                         "avg_return_pct": round(sum(_cr) / len(_cr), 2) if _cr else None}
        return {"paper_portfolio.json": portfolio, "paper_trades.json": trades,
                "portfolio_history.csv": hist, "kill_state.json": self.kill_flags(),
                "signals_history.json": sig_hist, "signal_analytics.json": sig_analytics}

    # ── persistence (survives across cron runs) ──
    def save(self, state_dir: str | Path) -> None:
        d = Path(state_dir); d.mkdir(parents=True, exist_ok=True)
        # resume state (the ENGINE reload path — paper_state.json, internal shape)
        (d / "paper_state.json").write_text(json.dumps({
            "cash": self.cash, "peak": self.peak, "pending": self.pending,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "trades": self.trades, "equity_curve": self.equity_curve,
            "config": {"initial_capital": self.initial_capital, "vol_target": self.vt},
        }, indent=2, default=str), encoding="utf-8")
        # dashboard-contract exports (the FastAPI reads these via GitHub)
        for name, content in self.dashboard_files().items():
            p = d / name
            content.to_csv(p, index=False) if name.endswith(".csv") else \
                p.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
        self.dashboard_files()["portfolio_history.csv"].to_csv(
            d / "paper_ledger_history.csv", index=False)      # the realistic capital-constrained book

    def load(self, state_dir: str | Path) -> None:
        d = Path(state_dir); pf = d / "paper_state.json"
        if pf.exists():
            st = json.loads(pf.read_text(encoding="utf-8"))
            self.cash = float(st["cash"]); self.peak = float(st.get("peak", self.cash))
            self.pending = list(st.get("pending", []))
            self.positions = {k: Position(**v) for k, v in st.get("positions", {}).items()}
            self.trades = list(st.get("trades", []))
            self.equity_curve = list(st.get("equity_curve", []))
            return
        self._load_legacy(d)                       # one-time pre-split migration

    def _load_legacy(self, d: Path) -> None:
        """Resume from the pre-split state (internal-shape paper_portfolio.json + sibling
        paper_trades.json / portfolio_history.csv). Fires once; the next save() writes
        paper_state.json and this branch never runs again. A no-op if there's no legacy
        state, or if paper_portfolio.json is already the (dashboard) export shape."""
        legacy = d / "paper_portfolio.json"
        if not legacy.exists():
            return
        st = json.loads(legacy.read_text(encoding="utf-8"))
        if "pending" not in st:                    # already the dashboard export shape — no resume info
            return
        self.cash = float(st["cash"]); self.pending = list(st.get("pending", []))
        self.positions = {k: Position(**v) for k, v in st.get("positions", {}).items()}
        tp = d / "paper_trades.json"
        self.trades = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else []
        hp = d / "portfolio_history.csv"
        if hp.exists():
            hist = pd.read_csv(hp)
            col = "equity" if "equity" in hist.columns else "total_value"
            self.equity_curve = [{"date": str(r.get("date", "")), "equity": float(r.get(col, self.initial_capital)),
                                  "cash": float(r.get("cash", 0) or 0), "n_positions": int(r.get("n_positions", 0) or 0)}
                                 for r in hist.to_dict("records")]
            self.peak = max([e["equity"] for e in self.equity_curve] + [self.cash])
        else:
            self.equity_curve = []; self.peak = self.cash
