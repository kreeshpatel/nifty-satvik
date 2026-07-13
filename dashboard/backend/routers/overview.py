"""Overview API — portfolio metrics and equity curve.

**Multi-user semantics (Sprint 1):**
This endpoint returns the **paper-trading portfolio**, which is a single
simulation artifact belonging to the admin/owner. Non-admin users get
an empty payload and should source portfolio data from the per-user
Kite endpoints (`/kite/holdings`, `/kite/positions`, `/kite/trades`)
which are already tenant-isolated.

Rationale: keeping paper-trading scoped to the admin preserves the
existing owner dashboard unchanged while giving dad/sister a clean
empty-state that prompts them to connect their Kite account.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from auth import get_current_user
from config import INITIAL_CAPITAL
from database import User
from github_data import fetch_github_json, fetch_github_csv, fetch_github_file

router = APIRouter(tags=["overview"])


def _empty_payload() -> dict:
    """Neutral empty response for users who shouldn't see paper data."""
    return {
        "portfolio": {
            "total_value": 0, "cash": 0, "invested": 0,
            "total_return_pct": 0, "drawdown_pct": 0,
            "peak_value": 0, "n_positions": 0,
        },
        "equity_curve": [],
        "metrics": {
            "total_trades": 0, "win_rate": 0, "profit_factor": 0,
            "avg_win": 0, "avg_loss": 0, "avg_hold_days": 0, "sharpe_ratio": 0,
        },
        "source": "none",
        "message": "Paper portfolio is admin-only. Connect Kite for your real data.",
    }


def _paper_payload() -> dict:
    """Build the admin's paper portfolio payload (previous shared shape)."""
    portfolio = {
        "total_value": INITIAL_CAPITAL, "cash": INITIAL_CAPITAL, "invested": 0,
        "total_return_pct": 0, "drawdown_pct": 0,
        "peak_value": INITIAL_CAPITAL, "n_positions": 0,
    }
    equity_curve = []
    stats = {
        "total_trades": 0, "win_rate": 0, "profit_factor": 0,
        "avg_win": 0, "avg_loss": 0, "avg_hold_days": 0, "sharpe_ratio": 0,
    }

    try:
        state = fetch_github_json("results/paper_portfolio_weekly.json")
        if state:
            positions = state.get("positions", {})
            invested = sum(p.get("current_value", 0) for p in positions.values())
            total = state.get("cash", INITIAL_CAPITAL) + invested
            peak = state.get("peak_value", total)
            portfolio = {
                "total_value": round(total, 2),
                "cash": round(state.get("cash", INITIAL_CAPITAL), 2),
                "invested": round(invested, 2),
                "total_return_pct": round((total / INITIAL_CAPITAL - 1) * 100, 2),
                "drawdown_pct": round((total - peak) / max(peak, 1) * 100, 2),
                "peak_value": peak,
                "n_positions": len(positions),
            }
    except Exception:
        pass

    try:
        df = fetch_github_csv("results/portfolio_history_weekly.csv")
        if df is not None and not df.empty:
            for _, row in df.tail(500).iterrows():
                equity_curve.append({
                    "date": row.get("date", ""),
                    "value": row.get("total_value", INITIAL_CAPITAL),
                    "regime": row.get("regime", "CHOPPY"),
                })
    except Exception:
        pass

    # Paper-broker CLOSED round-trips (results/paper_trades.json). The legacy code read a
    # NON-EXISTENT results/trade_log.csv, so every stat fell back to 0 and the KPI cards showed
    # "0 trades / 0% WR" despite real closed paper trades + a live equity curve. net_pct = the
    # after-cost realized return %; net_pnl = rupee P&L.
    try:
        trades = fetch_github_json("results/paper_trades.json") or []
        if isinstance(trades, list) and trades:
            rets = [float(t.get("net_pct", 0) or 0) for t in trades]
            pnls = [float(t.get("net_pnl", 0) or 0) for t in trades]
            holds = [float(t.get("hold_days", 0) or 0) for t in trades]
            wins = [r for r in rets if r > 0]
            losses = [r for r in rets if r <= 0]
            gw = sum(p for p in pnls if p > 0)
            gl = abs(sum(p for p in pnls if p <= 0))
            stats["total_trades"] = len(trades)
            stats["win_rate"] = round(len(wins) / len(trades) * 100, 1)
            stats["avg_win"] = round(sum(wins) / len(wins), 2) if wins else 0
            stats["avg_loss"] = round(sum(losses) / len(losses), 2) if losses else 0
            stats["profit_factor"] = round(gw / gl, 2) if gl > 0 else None  # None => no losses yet
            stats["avg_hold_days"] = round(sum(holds) / len(holds), 1) if holds else 0
    except Exception:
        pass

    # Sharpe + max drawdown from the REALISTIC paper-broker equity curve
    # (results/paper_ledger_history.csv — the capital-constrained book, not the unlimited-capital
    # portfolio_history.csv). Daily simple returns, 252-annualized. Replaces the hardcoded 0.
    try:
        led = fetch_github_csv("results/paper_ledger_history.csv")
        if led is not None and not led.empty and "total_value" in led.columns:
            vals = [float(v) for v in led["total_value"].tolist() if v == v]
            drets = [(vals[i] - vals[i - 1]) / vals[i - 1]
                     for i in range(1, len(vals)) if vals[i - 1]]
            # Only show an annualized Sharpe once there's ~1 month of history — a 6-day Sharpe
            # ×√252 is pure noise (would print an absurd ~6.0). None -> the UI renders "—".
            if len(drets) >= 20:
                from statistics import mean, pstdev
                sd = pstdev(drets)
                stats["sharpe_ratio"] = round(mean(drets) / sd * (252 ** 0.5), 2) if sd > 0 else 0
            else:
                stats["sharpe_ratio"] = None
            peak, mdd = (vals[0] if vals else 0), 0.0
            for v in vals:
                peak = max(peak, v)
                if peak:
                    mdd = min(mdd, (v - peak) / peak)
            stats["max_drawdown"] = round(mdd * 100, 2)
    except Exception:
        pass

    return {
        "portfolio": portfolio,
        "equity_curve": equity_curve,
        "metrics": stats,
        "source": "paper",
    }


@router.get("/overview")
def get_overview(user: User = Depends(get_current_user)):
    """Return paper portfolio for admin; empty state for non-admin.

    Non-admin users should use `/api/kite/holdings`, `/api/kite/positions`,
    and `/api/kite/trades` — these are already tenant-isolated per-user
    via the KiteSession table.
    """
    if not user.is_admin:
        return _empty_payload()
    return _paper_payload()


@router.get("/overview/paper")
def get_paper_overview(user: User = Depends(get_current_user)):
    """Admin-only explicit paper-portfolio endpoint.

    Same data as `/overview` when called as admin — exposed at a
    separate path so the frontend can tell "show paper" apart from
    "show real brokerage" without relying on admin-detection logic.
    """
    if not user.is_admin:
        return _empty_payload()
    return _paper_payload()


@router.get("/overview/tearsheet", response_class=HTMLResponse)
def get_tearsheet(user: User = Depends(get_current_user)):
    """Admin-only historical tearsheet (paper simulation artifact)."""
    if not user.is_admin:
        return "<html><body><h1>Tearsheet is admin-only.</h1></body></html>"
    try:
        html = fetch_github_file("results/tearsheet.html")
        if html:
            return html
    except Exception:
        pass
    return "<html><body><h1>No tearsheet generated yet.</h1></body></html>"
