#!/usr/bin/env python3
"""Dev-only mock API for the niftyquant dashboard — feeds test data into EVERY field so the
whole UI can be audited locally without a backend or Kite session.

Run:  python frontend/dev/mock-api.py   (listens on :8899)
Then start the frontend with frontend/.env.development.local set to:
    REACT_APP_PREVIEW_NO_AUTH=true
    LOCAL_PROXY_TARGET=http://localhost:8899
setupProxy.js proxies /api/* here; AuthContext's preview bypass seeds a stub user, so every
authenticated route renders fully populated. NOT shipped — dev tooling only.
"""
from __future__ import annotations
import json, re
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
    {"ticker": "CHENNPETRO", "entry": 1134.57, "stop": 959.91, "target": 1390.08, "target_pct": 22.52,
     "current_price": 1134.0, "grade": "B", "tier": "signal", "status": "FRESH", "signal_date": "2026-07-01",
     "hold_days": 63, "buy_window": "T+1..T+3 at open", "sector": "Energy"}],
    "regime": {"status": "BULL", "strength": 62, "vix": 13.4, "breadth": 58},
    "portfolio": {"cash": 34.71, "total_value": 986562.83, "positions": 5, "total_trades": len(TRADES)},
    "model": {"version": "long-horizon-63d", "trained_at": None, "avg_auc": 0, "n_features": 0},
    "scan_time": "2026-07-01T16:30:00", "n_signals": 1, "sizing_capital": 986562.83, "sizing_risk_pct": 3.0,
    "cron_health": {"status": "OK", "expected_today": True, "last_run_today": True}}
KITE_HOLDINGS = [{"tradingsymbol": "RELIANCE", "quantity": 12, "average_price": 2850.0,
                  "last_price": 2912.0, "day_change": 18.0, "day_change_percentage": 0.62, "sector": "Energy"},
                 {"tradingsymbol": "TCS", "quantity": 8, "average_price": 3820.0,
                  "last_price": 3765.0, "day_change": -22.0, "day_change_percentage": -0.58, "sector": "IT"}]
MARGINS = {"available": 152340.55, "used": 486210.0, "net": 638550.55, "cash": 152340.55}
NQ_ORDERS = [{"id": 1, "ticker": "ADANIPOWER", "action": "BUY", "qty": 494, "placed_price": 224.0,
              "fill_price": 223.88, "brokerage": 33.19, "stt": 110.6, "net_amount": 110740.5,
              "status": "FILLED", "placed_at": "2026-07-01T09:20:00", "signal_id": "ADANIPOWER__2026-06-30",
              "source": "niftyquant_signal", "notes": "top-15 slope entry"}]
BACKTEST = {"stats": {"cagr": 15.46, "sharpe": 0.667, "max_drawdown": -46.3, "win_rate": 60.36,
                      "n_trades": 1279, "alpha": 4.2}, "as_of": "2026-07-01",
            "equity": [[e["date"], e["value"]] for e in EQUITY], "trades": TRADES[:3]}

def _match(path):
    p = path.split("?")[0]
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
        r"^/api/signals/history$": {"today": SIGNALS["signals"], "history": [], "analytics": {},
                                    "source": "mock"},
        r"^/api/signals/watchlist$": {"signals": [], "count": 0, "generated_at": "2026-07-01",
                                      "tier": "watchlist"},
        r"^/api/signals/regime$": SIGNALS["regime"],
        r"^/api/signals/sell-guidance$": {"positions": [], "count": 0, "updated_at": "2026-07-01T16:30:00"},
        r"^/api/portfolio/paper-history$": EQUITY,
        r"^/api/portfolio/nav-history$": [{"date": e["date"], "nav": e["value"]} for e in EQUITY],
        r"^/api/kite/holdings$": KITE_HOLDINGS,
        r"^/api/kite/margins$": MARGINS,
        r"^/api/kite/session/status$": {"connected": True, "kite_user_id": "AB1234"},
        r"^/api/kite/orders$": [],
        r"^/api/nq-orders$": {"orders": NQ_ORDERS, "count": len(NQ_ORDERS)},
        r"^/api/backtest/(live|historical)$": BACKTEST,
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
    def do_OPTIONS(self): self._send({}, 204)
    def log_message(self, *a): pass

if __name__ == "__main__":
    print("mock-api on http://localhost:8899  (Ctrl-C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8899), H).serve_forever()
