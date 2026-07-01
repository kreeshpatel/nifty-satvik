#!/usr/bin/env python3
"""Dev-only mock API for the niftyquant dashboard — feeds test data into EVERY field so the
whole UI can be audited locally without a backend or Kite session.

Run:  python frontend/dev/mock-api.py   (listens on :8899)
Then start the frontend with frontend/.env.development.local set to:
    REACT_APP_PREVIEW_NO_AUTH=true
    LOCAL_PROXY_TARGET=http://localhost:8899
setupProxy.js proxies /api/* here; AuthContext's preview bypass seeds a stub user, so every
authenticated route renders fully populated. NOT shipped — dev tooling only.

Fixtures mirror the REAL backend response shapes (verified 2026-07-02 against
dashboard/backend/routers/*.py):
  - /api/kite/margins  → nested {equity:{available:{cash,live_balance,...}, utilised:{debits,
                          m2m_realised,m2m_unrealised,...}}, commodity:{...}}  (Kite raw shape)
  - /api/kite/orders   → array of Kite order objects (order_id/tradingsymbol/transaction_type/...)
  - /api/nq-orders     → {orders:[...], count}; status enum COMPLETE/OPEN; BUY+SELL matched pair
  - /api/nq-orders/stats → realised/stcg/ltcg/total_brokerage/total_stt/net_pnl aggregates
  - /api/backtest/live → live_blob {as_of,start_date,stats,equity_curve,monthly_returns,
                          exit_reasons,recent_closed,active}  (NOT the old {stats,equity,trades})
  - /api/signals/history → {today, history, analytics, source}
"""
from __future__ import annotations
import json, re
import math
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ── fixtures: realistic values in EVERY field the routers/hooks read ──────────
POSITIONS = [  # /api/positions (positions.py shape) — entry/stop/target/days drive the Positions tab
    {"ticker": "ADANIPOWER", "entry_date": "2026-07-01", "entry_price": 223.88, "shares": 494,
     "position_size": 110596.72, "atr_stop": 196.77, "target": 274.30, "current_price": 226.86,
     "current_value": 112068.84, "unrealised_pnl": 1472.12, "unrealised_pnl_pct": 1.33,
     "hold_days": 3, "sector": "Energy", "regime_at_entry": "BULL", "stop_distance_pct": 13.27},
    {"ticker": "HFCL", "entry_date": "2026-07-01", "entry_price": 214.11, "shares": 697,
     "position_size": 149234.67, "atr_stop": 181.27, "target": 262.32, "current_price": 212.09,
     "current_value": 147826.73, "unrealised_pnl": -1407.94, "unrealised_pnl_pct": -0.94,
     "hold_days": 3, "sector": "Telecom", "regime_at_entry": "BULL", "stop_distance_pct": 14.53},
    {"ticker": "NATIONALUM", "entry_date": "2026-07-01", "entry_price": 338.12, "shares": 443,
     "position_size": 149787.16, "atr_stop": 283.68, "target": 414.26, "current_price": 334.65,
     "current_value": 148249.95, "unrealised_pnl": -1537.21, "unrealised_pnl_pct": -1.03,
     "hold_days": 3, "sector": "Metals", "regime_at_entry": "BULL", "stop_distance_pct": 15.24},
    {"ticker": "HINDCOPPER", "entry_date": "2026-07-01", "entry_price": 501.35, "shares": 296,
     "position_size": 148399.60, "atr_stop": 431.05, "target": 614.25, "current_price": 490.60,
     "current_value": 145217.60, "unrealised_pnl": -3182.00, "unrealised_pnl_pct": -2.14,
     "hold_days": 3, "sector": "Metals", "regime_at_entry": "BULL", "stop_distance_pct": 12.13},
    {"ticker": "GVT&D", "entry_date": "2026-07-01", "entry_price": 4979.49, "shares": 29,
     "position_size": 144405.21, "atr_stop": 4124.47, "target": 6100.87, "current_price": 4895.70,
     "current_value": 141975.30, "unrealised_pnl": -2429.91, "unrealised_pnl_pct": -1.68,
     "hold_days": 3, "sector": "Industrials", "regime_at_entry": "BULL", "stop_distance_pct": 15.75},
]
TRADES = [  # /api/trades (trades.py canonical shape) — synthetic closed round-trips (all exit reasons)
    {"ticker": "HFCL", "qty": 2, "entry_date": "2026-06-11", "entry_price": 160.74,
     "exit_date": "2026-06-25", "exit_price": 196.84, "return_pct": 22.46, "net_pnl": 71.27,
     "hold_days": 10, "exit_reason": "target"},
    {"ticker": "GVT&D", "qty": 31, "entry_date": "2026-06-02", "entry_price": 4759.88,
     "exit_date": "2026-06-24", "exit_price": 5049.97, "return_pct": 6.09, "net_pnl": 8597.61,
     "hold_days": 16, "exit_reason": "trailing"},
    {"ticker": "LAURUSLABS", "qty": 75, "entry_date": "2026-06-02", "entry_price": 1388.69,
     "exit_date": "2026-06-16", "exit_price": 1375.71, "return_pct": -0.93, "net_pnl": -1243.19,
     "hold_days": 10, "exit_reason": "trailing"},
    {"ticker": "NATIONALUM", "qty": 343, "entry_date": "2026-06-02", "entry_price": 436.22,
     "exit_date": "2026-06-08", "exit_price": 378.01, "return_pct": -13.34, "net_pnl": -20328.10,
     "hold_days": 4, "exit_reason": "stop"},
    {"ticker": "MCX", "qty": 40, "entry_date": "2026-05-30", "entry_price": 2650.00,
     "exit_date": "2026-06-30", "exit_price": 2920.00, "return_pct": 10.19, "net_pnl": 10500.00,
     "hold_days": 21, "exit_reason": "time"},
]
_wins = [t for t in TRADES if t["return_pct"] > 0]
STATS = {"total_trades": len(TRADES), "win_rate": round(len(_wins) / len(TRADES) * 100, 1),
         "avg_win": 12.91, "avg_loss": -7.13, "profit_factor": 0.96, "avg_hold_days": 12.2,
         "sharpe_ratio": 0.71, "max_drawdown": -7.5,
         "by_sector": [{"sector": "Metals", "trades": 2, "wins": 0, "win_rate": 0.0},
                       {"sector": "Energy", "trades": 1, "wins": 1, "win_rate": 100.0}]}
EQUITY = [{"date": f"2026-06-{d:02d}", "total_value": round(1_000_000 * (1 + (d - 15) * 0.002), 2),
           "value": round(1_000_000 * (1 + (d - 15) * 0.002), 2), "regime": "BULL"} for d in range(1, 31)]
OVERVIEW = {
    "portfolio": {"total_value": 986562.83, "cash": 34.71, "invested": 986528.12,
                  "total_return_pct": -1.34, "drawdown_pct": -6.5, "peak_value": 1006569.26,
                  "n_positions": 5, "total_trades": len(TRADES)},
    "equity_curve": [{"date": e["date"], "value": e["value"], "regime": e["regime"]} for e in EQUITY],
    "metrics": STATS, "source": "paper"}
SIGNALS = {"signals": [
    {"ticker": "CHENNPETRO", "name": "Chennai Petroleum", "entry": 1134.57, "stop": 959.91,
     "stop_loss": 959.91, "target": 1390.08, "target_pct": 22.52, "current_price": 1134.0,
     "grade": "B", "tier": "signal", "status": "FRESH", "signal_date": "2026-07-01", "hold_days": 63,
     "buy_window": "T+1..T+3 at open", "sector": "Energy", "predicted_return_pct": 22.52,
     "confidence": 0.6, "ml_score": 0.6, "actionability": "ACTIONABLE_BUY"}],
    "regime": {"status": "BULL", "strength": 62, "vix": 13.4, "breadth": 58},
    "portfolio": {"cash": 34.71, "total_value": 986562.83, "positions": 5, "total_trades": len(TRADES)},
    "model": {"version": "long-horizon-63d", "trained_at": None, "avg_auc": 0, "n_features": 0},
    "scan_time": "2026-07-01T16:30:00", "n_signals": 1, "sizing_capital": 986562.83, "sizing_risk_pct": 3.0,
    "cron_health": {"status": "OK", "expected_today": True, "last_run_today": True}}
KITE_HOLDINGS = [{"instrument_token": 738561, "tradingsymbol": "RELIANCE", "isin": "INE002A01018",
                  "quantity": 12, "t1_quantity": 0, "average_price": 2850.0, "last_price": 2912.0,
                  "day_change": 18.0, "day_change_percentage": 0.62, "product_type": "CNC",
                  "pnl": 744.0, "sector": "Energy"},
                 {"instrument_token": 2953217, "tradingsymbol": "TCS", "isin": "INE467B01029",
                  "quantity": 8, "t1_quantity": 0, "average_price": 3820.0, "last_price": 3765.0,
                  "day_change": -22.0, "day_change_percentage": -0.58, "product_type": "CNC",
                  "pnl": -440.0, "sector": "IT"}]
# /api/kite/margins — REAL nested Kite shape (FundsV2 useRawMargins reads equity.available.cash /
# equity.utilised.debits / equity.utilised.m2m_realised / m2m_unrealised; BalanceCard reads
# equity.available.cash + equity.available.live_balance).
MARGINS = {
    "equity": {"enabled": True, "net": 638550.55,
               "available": {"adhoc_margin": 0.0, "cash": 152340.55, "opening_balance": 152340.55,
                             "live_balance": 152340.55, "collateral": 0.0, "intraday_payin": 0.0},
               "utilised": {"debits": 486210.0, "exposure": 486210.0, "option_premium": 0.0,
                            "holding_sales": 0.0, "span": 0.0, "leverage": 0.0,
                            "m2m_realised": 4120.30, "m2m_unrealised": -1875.60, "payout": 0.0}},
    "commodity": {"enabled": False, "net": 0.0,
                  "available": {"adhoc_margin": 0.0, "cash": 0.0, "opening_balance": 0.0,
                                "live_balance": 0.0, "collateral": 0.0, "intraday_payin": 0.0},
                  "utilised": {"debits": 0.0, "exposure": 0.0, "option_premium": 0.0,
                               "holding_sales": 0.0, "span": 0.0, "leverage": 0.0,
                               "m2m_realised": 0.0, "m2m_unrealised": 0.0, "payout": 0.0}}}
# /api/kite/orders — REAL Kite order array (OrdersV2 useKiteOrders). Varied status + side + type.
KITE_ORDERS = [
    {"order_id": "250702000000001", "exchange_order_id": "1300000012345678", "tradingsymbol": "ADANIPOWER",
     "exchange": "NSE", "order_timestamp": "2026-07-02 09:20:11", "variety": "regular", "status": "COMPLETE",
     "transaction_type": "BUY", "product": "CNC", "order_type": "LIMIT", "price": 224.0, "quantity": 494,
     "average_price": 223.88, "filled_quantity": 494, "pending_quantity": 0, "disclosed_quantity": None,
     "trigger_price": None, "validity": "DAY", "tag": "NQ", "exchange_timestamp": "2026-07-02 09:20:13"},
    {"order_id": "250702000000002", "exchange_order_id": None, "tradingsymbol": "HFCL",
     "exchange": "NSE", "order_timestamp": "2026-07-02 09:21:02", "variety": "regular", "status": "OPEN",
     "transaction_type": "BUY", "product": "CNC", "order_type": "LIMIT", "price": 214.5, "quantity": 697,
     "average_price": 0.0, "filled_quantity": 0, "pending_quantity": 697, "disclosed_quantity": None,
     "trigger_price": None, "validity": "DAY", "tag": "NQ", "exchange_timestamp": None},
    {"order_id": "250702000000003", "exchange_order_id": "1300000012345690", "tradingsymbol": "MCX",
     "exchange": "NSE", "order_timestamp": "2026-07-02 09:35:44", "variety": "regular", "status": "COMPLETE",
     "transaction_type": "SELL", "product": "CNC", "order_type": "MARKET", "price": 0.0, "quantity": 40,
     "average_price": 2920.0, "filled_quantity": 40, "pending_quantity": 0, "disclosed_quantity": None,
     "trigger_price": None, "validity": "DAY", "tag": "NQ", "exchange_timestamp": "2026-07-02 09:35:45"},
    {"order_id": "250702000000004", "exchange_order_id": None, "tradingsymbol": "LAURUSLABS",
     "exchange": "NSE", "order_timestamp": "2026-07-02 10:02:19", "variety": "regular", "status": "REJECTED",
     "transaction_type": "BUY", "product": "CNC", "order_type": "LIMIT", "price": 640.0, "quantity": 75,
     "average_price": 0.0, "filled_quantity": 0, "pending_quantity": 75, "disclosed_quantity": None,
     "trigger_price": None, "validity": "DAY", "tag": "NQ", "exchange_timestamp": None},
]
# /api/nq-orders — REAL nq_orders shape (Journal + Accounting). BUY+SELL matched pair (RELIANCE),
# an unmatched OPEN buy, and a second closed pair (MCX) so realised P&L / FIFO matching has rows.
NQ_ORDERS = [
    {"id": 1, "user_id": 1, "kite_order_id": "250615000000010", "signal_id": "RELIANCE__2026-06-15",
     "ticker": "RELIANCE", "action": "BUY", "qty": 5, "placed_price": 2850.0, "fill_price": 2851.2,
     "brokerage": 14.26, "stt": 0.0, "net_amount": -14256.0, "status": "COMPLETE",
     "placed_at": "2026-06-15T09:20:00", "filled_at": "2026-06-15T09:20:07", "source": "niftyquant_signal",
     "notes": "Textbook slope entry, breadth confirmed. Sized to 3% risk."},
    {"id": 2, "user_id": 1, "kite_order_id": "250628000000021", "signal_id": "RELIANCE__2026-06-15",
     "ticker": "RELIANCE", "action": "SELL", "qty": 5, "placed_price": 2999.0, "fill_price": 2998.4,
     "brokerage": 14.99, "stt": 14.99, "net_amount": 14992.0, "status": "COMPLETE",
     "placed_at": "2026-06-28T14:10:00", "filled_at": "2026-06-28T14:10:05", "source": "niftyquant_signal",
     "notes": "Target hit at +5.1%. Closed full position, no regret hold."},
    {"id": 3, "user_id": 1, "kite_order_id": "250630000000030", "signal_id": "MCX__2026-05-30",
     "ticker": "MCX", "action": "BUY", "qty": 40, "placed_price": 2650.0, "fill_price": 2651.0,
     "brokerage": 31.81, "stt": 0.0, "net_amount": -106040.0, "status": "COMPLETE",
     "placed_at": "2026-05-30T09:25:00", "filled_at": "2026-05-30T09:25:04", "source": "niftyquant_signal",
     "notes": None},
    {"id": 4, "user_id": 1, "kite_order_id": "250630000000031", "signal_id": "MCX__2026-05-30",
     "ticker": "MCX", "action": "SELL", "qty": 40, "placed_price": 2920.0, "fill_price": 2919.5,
     "brokerage": 35.03, "stt": 35.03, "net_amount": 116780.0, "status": "COMPLETE",
     "placed_at": "2026-06-30T15:05:00", "filled_at": "2026-06-30T15:05:06", "source": "niftyquant_signal",
     "notes": "63-day time cap. Trailed to +10.2%."},
    {"id": 5, "user_id": 1, "kite_order_id": "250701000000040", "signal_id": "ADANIPOWER__2026-07-01",
     "ticker": "ADANIPOWER", "action": "BUY", "qty": 494, "placed_price": 224.0, "fill_price": 223.88,
     "brokerage": 33.19, "stt": 0.0, "net_amount": -110596.72, "status": "COMPLETE",
     "placed_at": "2026-07-01T09:20:00", "filled_at": "2026-07-01T09:20:08", "source": "niftyquant_signal",
     "notes": "Fresh top-15 slope entry."},
    {"id": 6, "user_id": 1, "kite_order_id": None, "signal_id": "HFCL__2026-07-02",
     "ticker": "HFCL", "action": "BUY", "qty": 697, "placed_price": 214.5, "fill_price": None,
     "brokerage": 0.0, "stt": 0.0, "net_amount": None, "status": "OPEN",
     "placed_at": "2026-07-02T09:21:00", "filled_at": None, "source": "niftyquant_signal", "notes": None},
]
def _nq_stats():
    done = [o for o in NQ_ORDERS if o["status"] == "COMPLETE"]
    tb = round(sum(o["brokerage"] for o in done), 2)
    ts = round(sum(o["stt"] for o in done), 2)
    # realised = RELIANCE (2998.4-2851.2)*5 + MCX (2919.5-2651.0)*40
    realised = round((2998.4 - 2851.2) * 5 + (2919.5 - 2651.0) * 40, 2)
    return {"period": "all", "realised_pnl": realised, "unrealised_pnl": 0.0,
            "total_brokerage": tb, "total_stt": ts, "net_pnl": round(realised - tb - ts, 2),
            "stcg_pnl": realised, "ltcg_pnl": 0.0, "trades_matched": 2, "open_positions": 1}

# /api/backtest/live — REAL live_blob shape (TrackRecordV2 + BacktestV2). NOT {stats,equity,trades}.
_LIVE_PTS = [("2026-06-16", "Jun 16", 0.0), ("2026-06-17", "Jun 17", 0.35), ("2026-06-18", "Jun 18", 0.9),
             ("2026-06-19", "Jun 19", 0.6), ("2026-06-20", "Jun 20", 1.4), ("2026-06-23", "Jun 23", 1.1),
             ("2026-06-24", "Jun 24", 1.9), ("2026-06-25", "Jun 25", 2.4), ("2026-06-26", "Jun 26", 2.0),
             ("2026-06-27", "Jun 27", 1.7), ("2026-06-30", "Jun 30", 2.6), ("2026-07-01", "Jul 01", 2.2),
             ("2026-07-02", "Jul 02", 3.05)]
_LIVE_CURVE = [{"date": d, "month": m, "strategy": round(1_000_000 * (1 + p / 100), 2),
                "strategy_pct": p, "nifty": None} for d, m, p in _LIVE_PTS]
BACKTEST_LIVE = {
    "as_of": "2026-07-02", "start_date": "2026-06-16", "first_signal_date": "2026-06-16",
    "stats": {"days_live": 16, "total_signals": 12, "active_signals": 5, "closed_signals": 7,
              "win_rate": 71.4, "avg_return_pct": 1.24, "avg_win_pct": 3.45, "avg_loss_pct": -2.10,
              "best": "HFCL__2026-06-11", "worst": "NATIONALUM__2026-06-02", "hit_target": 3,
              "hit_stop": 2, "stops_at_gain": 1, "stops_at_loss": 1, "expired": 1,
              "avg_open_pnl_pct": 0.86, "profit_factor": 1.42, "sharpe_ratio": 0.71},
    "equity_curve": _LIVE_CURVE,
    "monthly_returns": {"2026": [None, None, None, None, None, 2.05, 3.05, None, None, None, None, None]},
    "exit_reasons": [{"reason": "Target Hit", "value": 42.9, "count": 3, "color": "#22C55E"},
                     {"reason": "Trailing at Gain", "value": 14.3, "count": 1, "color": "#10B981"},
                     {"reason": "Stop Loss", "value": 28.6, "count": 2, "color": "#EF4444"},
                     {"reason": "Time Expired", "value": 14.3, "count": 1, "color": "#F59E0B"}],
    "recent_closed": [
        {"id": "live-0", "date": "2026-06-25", "symbol": "HFCL", "side": "LONG", "entry": 160.74,
         "exit": 196.84, "pnl": 71.27, "pnlPct": 22.46, "exitReason": "Target Hit", "holdDays": 10},
        {"id": "live-1", "date": "2026-06-24", "symbol": "GVT&D", "side": "LONG", "entry": 4759.88,
         "exit": 5049.97, "pnl": 8597.61, "pnlPct": 6.09, "exitReason": "Trailing at Gain", "holdDays": 16},
        {"id": "live-2", "date": "2026-06-30", "symbol": "MCX", "side": "LONG", "entry": 2650.0,
         "exit": 2920.0, "pnl": 10500.0, "pnlPct": 10.19, "exitReason": "Time Expired", "holdDays": 21},
        {"id": "live-3", "date": "2026-06-16", "symbol": "LAURUSLABS", "side": "LONG", "entry": 1388.69,
         "exit": 1375.71, "pnl": -1243.19, "pnlPct": -0.93, "exitReason": "Trailing at Gain", "holdDays": 10},
        {"id": "live-4", "date": "2026-06-08", "symbol": "NATIONALUM", "side": "LONG", "entry": 436.22,
         "exit": 378.01, "pnl": -20328.10, "pnlPct": -13.34, "exitReason": "Stop Loss", "holdDays": 4}],
    "active": [{"ticker": p["ticker"], "sector": p["sector"], "entry": p["entry_price"],
                "target": p["target"], "stop": p["atr_stop"], "current_price": p["current_price"],
                "pnl_pct": p["unrealised_pnl_pct"], "days_since": p["hold_days"], "hold_days": p["hold_days"],
                "status": "NEAR_TARGET" if p["unrealised_pnl_pct"] > 0 else "ACTIVE",
                "signal_date": p["entry_date"]} for p in POSITIONS],
}
# /api/backtest/historical — same blob shape over a multi-year window (populated so the historical
# rendering is auditable; in PRODUCTION this 404s until results/backtest_data.json is generated).
def _hist_curve():
    pts, v = [], 100.0
    steps = [0.9, -0.4, 1.6, 0.8, -1.1, 2.0, 1.2, -0.6, 1.9, 0.5, -0.8, 2.4,
             1.1, 0.7, -1.4, 1.8, 0.9, 1.3, -0.7, 2.1, 0.6, -1.0, 1.7, 1.4]  # 24 months 2024-2025
    y, mo = 2024, 1
    for s in steps:
        v = round(v * (1 + s / 100), 4)
        pts.append({"date": f"{y}-{mo:02d}-01", "month": f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][mo-1]} {str(y)[2:]}",
                    "strategy": round(1_000_000 * v / 100, 2), "strategy_pct": round(v - 100, 2), "nifty": None})
        mo += 1
        if mo > 12:
            mo, y = 1, y + 1
    return pts, steps
_HIST_CURVE, _HIST_STEPS = _hist_curve()
BACKTEST_HISTORICAL = {
    "as_of": "2026-01-01", "start_date": "2024-01-01", "first_signal_date": "2024-01-15",
    "stats": {"days_live": 730, "total_signals": 312, "active_signals": 0, "closed_signals": 312,
              "win_rate": 60.4, "avg_return_pct": 1.06, "avg_win_pct": 4.12, "avg_loss_pct": -3.05,
              "best": "TATAELXSI__2024-05-02", "worst": "VEDL__2024-11-08", "hit_target": 168,
              "hit_stop": 96, "stops_at_gain": 30, "stops_at_loss": 66, "expired": 48,
              "avg_open_pnl_pct": 0.0, "profit_factor": 1.61, "sharpe_ratio": 0.667, "cagr": 15.46,
              "max_drawdown": -46.3, "alpha": 4.2},
    "equity_curve": _HIST_CURVE,
    "monthly_returns": {"2024": _HIST_STEPS[:12], "2025": _HIST_STEPS[12:24]},
    "exit_reasons": [{"reason": "Target Hit", "value": 53.8, "count": 168, "color": "#22C55E"},
                     {"reason": "Trailing at Gain", "value": 9.6, "count": 30, "color": "#10B981"},
                     {"reason": "Stop Loss", "value": 21.2, "count": 66, "color": "#EF4444"},
                     {"reason": "Time Expired", "value": 15.4, "count": 48, "color": "#F59E0B"}],
    "recent_closed": BACKTEST_LIVE["recent_closed"], "active": [],
}
# /api/signals/history — {today, history, analytics, source}. history = closed round-trips (HIT_TARGET/
# HIT_STOP/EXPIRED) + still-active positions; drives StockDetail's per-ticker history + analytics.
_HIST_CLOSED = [
    {"ticker": "HFCL", "entry": 160.74, "stop": 145.0, "target": 196.84, "signal_date": "2026-06-11",
     "grade": "A", "status": "HIT_TARGET", "current_price": 196.84, "close_price": 196.84,
     "close_date": "2026-06-25", "pnl_pct": 22.46, "close_pnl_pct": 22.46, "return_pct": 22.46,
     "days_since": 10, "hold_days": 10, "sector": "Telecom", "exit_reason": "target", "user_position": None},
    {"ticker": "NATIONALUM", "entry": 436.22, "stop": 378.0, "target": 520.0, "signal_date": "2026-06-02",
     "grade": "B", "status": "HIT_STOP", "current_price": 378.01, "close_price": 378.01,
     "close_date": "2026-06-08", "pnl_pct": -13.34, "close_pnl_pct": -13.34, "return_pct": -13.34,
     "days_since": 4, "hold_days": 4, "sector": "Metals", "exit_reason": "stop", "user_position": None},
    {"ticker": "MCX", "entry": 2650.0, "stop": 2400.0, "target": 3100.0, "signal_date": "2026-05-30",
     "grade": "A", "status": "EXPIRED", "current_price": 2920.0, "close_price": 2920.0,
     "close_date": "2026-06-30", "pnl_pct": 10.19, "close_pnl_pct": 10.19, "return_pct": 10.19,
     "days_since": 21, "hold_days": 21, "sector": "Financials", "exit_reason": "time", "user_position": None},
]
_HIST_ACTIVE = [
    {"ticker": p["ticker"], "entry": p["entry_price"], "stop": p["atr_stop"], "target": p["target"],
     "signal_date": p["entry_date"], "grade": "B", "status": "ACTIVE", "current_price": p["current_price"],
     "close_price": p["current_price"], "close_date": None, "pnl_pct": p["unrealised_pnl_pct"],
     "close_pnl_pct": None, "return_pct": p["unrealised_pnl_pct"], "days_since": p["hold_days"],
     "hold_days": p["hold_days"], "sector": p["sector"], "user_position": None} for p in POSITIONS]
_SH_HISTORY = _HIST_CLOSED + _HIST_ACTIVE
_cr = [r["return_pct"] for r in _HIST_CLOSED]
_cw = [r for r in _cr if r > 0]
SIGNAL_HISTORY = {"today": SIGNALS["signals"], "history": _SH_HISTORY,
                  "analytics": {"win_rate": round(len(_cw) / len(_cr) * 100, 1), "avg_return": round(sum(_cr) / len(_cr), 2),
                                "avg_win": 16.33, "avg_loss": -13.34, "total_signals": len(_HIST_CLOSED),
                                "hit_target": 1, "hit_stop": 1, "expired": 1,
                                "best_signal": "HFCL__2026-06-11", "worst_signal": "NATIONALUM__2026-06-02"},
                  "source": "mock"}
# /api/yahoo/index-sparklines — RegimeStrip NIFTY 50 / VIX / bank / USDINR.
INDEX_SPARKLINES = {
    "NIFTY 50": {"last": 24580.35, "ltp": 24580.35, "change": 125.40, "change_pct": 0.51, "changePct": 0.51,
                 "series": [{"t": f"2026-07-02T{9 + i // 4:02d}:{(i % 4) * 15:02d}:00", "v": round(24450 + i * 9.2, 2)} for i in range(24)]},
    "NIFTY BANK": {"last": 56234.75, "ltp": 56234.75, "change": 345.25, "change_pct": 0.62, "changePct": 0.62, "series": []},
    "INDIA VIX": {"last": 13.40, "ltp": 13.40, "change": -0.85, "change_pct": -5.96, "changePct": -5.96, "series": []},
    "USDINR": {"last": 83.25, "ltp": 83.25, "change": 0.15, "change_pct": 0.18, "changePct": 0.18, "series": []}}
# /api/yahoo/quote-batch — holdings previous_close for the Dashboard StocksTable.
QUOTE_BATCH = {
    "RELIANCE": {"symbol": "RELIANCE", "last_price": 2912.0, "previous_close": 2894.0, "open": 2900.0,
                 "high": 2925.0, "low": 2896.0, "change": 18.0, "change_pct": 0.62, "volume": 2150000},
    "TCS": {"symbol": "TCS", "last_price": 3765.0, "previous_close": 3787.0, "open": 3785.0,
            "high": 3792.0, "low": 3758.0, "change": -22.0, "change_pct": -0.58, "volume": 1420000}}
# StockDetailV2 live feed (useStockData → yahooQuote /api/yahoo/quote/{sym} + yahooHistorical
# /api/yahoo/historical/{sym}). Symbol-aware so the price header + candle chart populate.
_PX = {p["ticker"]: p["current_price"] for p in POSITIONS}
_PX.update({"RELIANCE": 2912.0, "TCS": 3765.0, "MCX": 2920.0, "CHENNPETRO": 1134.0,
            "HFCL": 212.09, "LAURUSLABS": 640.0})
_NAMES = {"ADANIPOWER": "Adani Power", "HFCL": "HFCL Ltd", "NATIONALUM": "National Aluminium",
          "HINDCOPPER": "Hindustan Copper", "GVT&D": "GE Vernova T&D India", "RELIANCE": "Reliance Industries",
          "TCS": "Tata Consultancy Services", "MCX": "Multi Commodity Exchange", "CHENNPETRO": "Chennai Petroleum"}
def _price_for(sym):
    return _PX.get(sym.upper(), 1000.0)
def _yquote(sym):
    sym = sym.upper(); px = _price_for(sym); prev = round(px * 0.994, 2)
    return {"symbol": sym, "name": _NAMES.get(sym, sym.title()), "last_price": px, "previous_close": prev,
            "close": prev, "open": round(px * 0.997, 2), "high": round(px * 1.011, 2),
            "low": round(px * 0.988, 2), "change": round(px - prev, 2),
            "change_pct": round((px / prev - 1) * 100, 2), "volume": 1_850_000,
            "fifty_two_week_high": round(px * 1.35, 2), "fifty_two_week_low": round(px * 0.62, 2),
            "market_cap": int(px * 3_50_00_000), "sector": "Equity", "industry": "—"}
def _candles(sym, n=90):
    # Backend historical shape is OHLCV array-tuples [date, open, high, low, close, volume]
    # — lib/candles.js reads c[0]/c[1]/… and computeAllIndicators (kiteStock.js) reads
    # c[2..5]. Oscillating walk (up + down days) so RSI/ADX/etc. resolve to real numbers.
    sym = sym.upper(); px = _price_for(sym); end = date(2026, 7, 2); out = []
    for i in range(n):
        d = end - timedelta(days=(n - 1 - i))
        drift = 0.05 * ((i / (n - 1)) - 0.55)
        wave = 0.045 * math.sin(i / 5.5) + 0.02 * math.sin(i / 2.3)
        c = round(px * (1 + drift + wave), 2)
        rng = 0.006 + 0.004 * abs(math.sin(i / 3.0))
        out.append([d.isoformat(), round(c * (1 - rng * 0.4), 2), round(c * (1 + rng), 2),
                    round(c * (1 - rng), 2), c, 1_000_000 + (i % 7) * 130_000])
    return out

def _match(path):
    p = path.split("?")[0]
    # symbol-path-param endpoints (StockDetailV2 live feed) — matched before the table
    m = re.match(r"^/api/yahoo/quote/([^/]+)$", p)
    if m:
        return _yquote(m.group(1))
    m = re.match(r"^/api/yahoo/historical/([^/]+)$", p)
    if m:
        return _candles(m.group(1))
    m = re.match(r"^/api/yahoo/fundamentals/([^/]+)$", p)
    if m:
        s = m.group(1).upper()
        return {"symbol": s, "name": _NAMES.get(s, s.title()), "sector": "Equity", "industry": "—",
                "market_cap": int(_price_for(s) * 3_50_00_000), "pe_ratio": 18.4, "pb_ratio": 2.6,
                "roe": 15.2, "debt_to_equity": 0.44, "dividend_yield": 1.1, "eps": round(_price_for(s) / 18.4, 2),
                "book_value": round(_price_for(s) / 2.6, 2), "week52_high": round(_price_for(s) * 1.35, 2),
                "week52_low": round(_price_for(s) * 0.62, 2)}
    if re.match(r"^/api/kite/quote$", p):
        return {}
    R = {
        r"^/api/auth/me$": {"id": "preview", "email": "preview@local", "name": "Kreesh",
                            "is_admin": True, "role": "admin", "mfa_enabled": False},
        r"^/api/auth/mfa/status$": {"enabled": False},
        r"^/api/overview(/paper)?$": OVERVIEW,
        r"^/api/overview/tearsheet$": "<html><body><h1>Preview tearsheet</h1></body></html>",
        r"^/api/positions$": POSITIONS,
        r"^/api/positions/nq$": {"positions": [], "count": 0, "kite_connected": True,
                                 "updated_at": "2026-07-01T16:30:00"},
        r"^/api/positions/external$": [],
        r"^/api/trades$": {"trades": TRADES, "total": len(TRADES), "page": 1, "pages": 1},
        r"^/api/trades/stats$": STATS,
        r"^/api/signals$": SIGNALS,
        r"^/api/signals/history$": SIGNAL_HISTORY,
        r"^/api/signals/watchlist$": {"signals": [], "count": 0, "generated_at": "2026-07-01",
                                      "tier": "watchlist"},
        r"^/api/signals/regime$": SIGNALS["regime"],
        r"^/api/signals/sell-guidance$": {"positions": [], "count": 0, "updated_at": "2026-07-01T16:30:00"},
        r"^/api/portfolio/paper-history$": EQUITY,
        r"^/api/portfolio/nav-history$": [{"date": e["date"], "nav": e["value"]} for e in EQUITY],
        r"^/api/kite/holdings$": KITE_HOLDINGS,
        r"^/api/kite/margins$": MARGINS,
        r"^/api/kite/orders$": KITE_ORDERS,
        r"^/api/kite/session/status$": {"connected": True, "kite_user_id": "AB1234", "user_id": "AB1234"},
        r"^/api/nq-orders/stats$": _nq_stats(),
        r"^/api/nq-orders$": {"orders": NQ_ORDERS, "count": len(NQ_ORDERS)},
        r"^/api/backtest/live$": BACKTEST_LIVE,
        r"^/api/backtest/historical$": BACKTEST_HISTORICAL,
        r"^/api/yahoo/index-sparklines$": INDEX_SPARKLINES,
        r"^/api/yahoo/quote-batch$": QUOTE_BATCH,
        r"^/api/landing-stats$": {"cagr": 15.46, "sharpe": 0.667, "win_rate": 60.36, "n_trades": 1279},
    }
    for pat, body in R.items():
        if re.match(pat, p):
            return body
    return {} if p.endswith(("status", "me")) else []

class H(BaseHTTPRequestHandler):
    def _send(self, body, code=200):
        if isinstance(body, str):
            data = body.encode(); ctype = "text/html"
        else:
            data = json.dumps(body).encode(); ctype = "application/json"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):  self._send(_match(self.path))
    def do_POST(self):
        if self.path.startswith("/api/auth/refresh"):
            self._send({"access_token": "mock", "refresh_token": "mock", "user": _match("/api/auth/me")})
        else:
            self._send({"ok": True})
    def do_PATCH(self): self._send({"ok": True})
    def do_OPTIONS(self): self._send({}, 204)
    def log_message(self, *a): pass

if __name__ == "__main__":
    print("mock-api on http://localhost:8899  (Ctrl-C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8899), H).serve_forever()
