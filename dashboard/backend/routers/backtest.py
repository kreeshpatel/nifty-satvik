"""Backtest API — single consolidated blob for each of live + historical.

Live = aggregated signal track record since LIVE_START (computed on-the-fly
       from results/signals_history.json).
Historical = the 2020-2025 backtest, regenerated monthly/quarterly by
             scripts/regenerate_backtest.py into results/backtest_data.json.
"""

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from auth import get_current_user
from config import PROJECT_ROOT
from database import User
from github_data import fetch_github_json

# signal analytics lived in the retired v1 engine (src/trading/signal_tracker); the
# clean nifty-satvik engine does not carry that module. The /backtest live series is
# instead derived here from results/signals_history.json, which the paper-book cron
# now emits (PaperBook.dashboard_files, 2026-07-02). Guard the legacy import so its
# absence degrades to an empty-analytics stub instead of crashing uvicorn at startup
# (main.py mounts this router at import time).
try:
    _SRC = os.path.join(PROJECT_ROOT, "src")
    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)
    from trading.signal_tracker import compute_signal_analytics  # noqa: E402
except Exception:
    def compute_signal_analytics(history):  # type: ignore[misc]
        return {}

router = APIRouter(tags=["backtest"])

# Hard floor — series cannot start before this date even if a stale signal
# slipped through with an earlier signal_date. The actual start used in the
# response is `max(LIVE_FLOOR, earliest_signal_date)` so users don't see
# a phantom flat prefix from before the system was actually issuing signals.
LIVE_FLOOR = date(2026, 1, 1)
INITIAL_NOTIONAL = 1_000_000  # ₹10L equal-weight basket for equity curve display


def _earliest_signal_date(history: list[dict]) -> date:
    """Earliest signal_date across all entries in history, floored at
    LIVE_FLOOR. Used to anchor the live equity curve so it doesn't render
    100+ days of misleading flat-zero before the first real signal.
    """
    earliest: date | None = None
    for s in history:
        sd = _parse_date(s.get("signal_date"))
        if sd is None:
            continue
        if earliest is None or sd < earliest:
            earliest = sd
    if earliest is None or earliest < LIVE_FLOOR:
        return LIVE_FLOOR
    return earliest

EXIT_REASON_LABEL = {
    "HIT_TARGET": "Target Hit",
    "HIT_STOP": "Stop Loss",
    "EXPIRED": "Time Expired",
}
# Donut palette — Target Hit and Trailing-at-Gain both shaded green
# (winning exits), Stop Loss red, Time Expired amber. The two greens
# differ in saturation so the eye can still distinguish target-hit
# (saturated bull-green) from trailing-stop-at-gain (lighter emerald).
EXIT_REASON_COLOR = {
    "Target Hit":       "#22C55E",
    "Trailing at Gain": "#10B981",
    "Stop Loss":        "#EF4444",
    "Time Expired":     "#F59E0B",
}


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _pnl(sig: dict) -> float:
    v = sig.get("close_pnl_pct")
    if v is None:
        v = sig.get("pnl_pct")
    return float(v or 0)


# ── Live (single consolidated blob) ────────────────────

def _build_live_equity_curve(history: list[dict], today: date, start: date) -> list[dict]:
    """Equal-weight equity curve from `start` to `today`.

    A signal contributes linearly from 0% on signal_date to its current/close
    pnl_pct at today/close_date. Portfolio return on day D = mean of
    contributions across signals emitted by D.

    `start` is normally the date of the first signal (computed by
    `_earliest_signal_date`). Earlier code used a hardcoded LIVE_START =
    Jan 1 which produced a misleading 100-day flat-zero prefix before the
    first real signal.
    """
    sigs = []
    for s in history:
        sd = _parse_date(s.get("signal_date"))
        if not sd or sd > today:
            continue
        cd = _parse_date(s.get("close_date"))
        end = cd if cd else today
        if end < sd:
            end = sd
        sigs.append({"start": sd, "end": end, "pnl": _pnl(s)})

    out = []
    d = start
    while d <= today:
        contribs = []
        for s in sigs:
            if d < s["start"]:
                continue
            span = max(1, (s["end"] - s["start"]).days)
            elapsed = (min(d, s["end"]) - s["start"]).days
            contribs.append(s["pnl"] * (elapsed / span))
        ret = sum(contribs) / len(contribs) if contribs else 0.0
        out.append({
            "date": d.isoformat(),
            "month": d.strftime("%b %d"),
            "strategy": round(INITIAL_NOTIONAL * (1 + ret / 100), 2),
            "strategy_pct": round(ret, 2),
            "nifty": None,
        })
        d += timedelta(days=1)
    return out


def _build_live_monthly_returns(history: list[dict], today: date, start: date) -> dict:
    by_month: dict[int, list[float]] = {}
    for s in history:
        cd = _parse_date(s.get("close_date"))
        if not cd or s.get("status") not in ("HIT_TARGET", "HIT_STOP", "EXPIRED"):
            continue
        by_month.setdefault(cd.month, []).append(_pnl(s))

    row: list[float | None] = []
    for m in range(1, 13):
        # null out months before the live series began (no signals were
        # being emitted yet) AND months after today (haven't happened).
        # Both render as empty cells in the heatmap rather than 0.0%.
        if m > today.month or m < start.month:
            row.append(None)
        elif m in by_month:
            # Equal-weight portfolio return = MEAN of trade P&L %, not
            # compound. The 21 trades that closed in a month happened in
            # parallel across position slots — they're not sequential
            # reinvestment. Earlier code used compound product which
            # produced absurd numbers (April 2026 showed +544% from
            # compounding 21 ~9% trades; the actual portfolio return
            # was +7.2% on the equity curve). Mean matches the AVG
            # RETURN KPI and is what a trader expects to see.
            pnls = by_month[m]
            avg = sum(pnls) / len(pnls)
            row.append(round(avg, 2))
        else:
            row.append(0.0)
    return {str(start.year): row}


def _build_live_exit_reasons(history: list[dict]) -> list[dict]:
    """Donut breakdown for the "How trades closed" panel.

    Splits HIT_STOP into "Trailing at Gain" (close_pnl_pct > 0, the
    trailing-stop-after-profit-lock case) and "Stop Loss" (the actual
    losing exits). Without this split the donut showed 48% red for
    "stops" — visually indistinguishable from a portfolio with 48%
    losers, when most of those stops were profitable trailing exits.
    Mirrors the win-rate KPI breakdown shipped alongside.
    """
    counts: dict[str, int] = {}
    for s in history:
        st = s.get("status")
        if st == "HIT_TARGET":
            lbl = "Target Hit"
        elif st == "HIT_STOP":
            lbl = "Trailing at Gain" if _pnl(s) > 0 else "Stop Loss"
        elif st == "EXPIRED":
            lbl = "Time Expired"
        else:
            continue
        counts[lbl] = counts.get(lbl, 0) + 1

    total = sum(counts.values())
    if total == 0:
        return []
    out = [{
        "reason": r,
        "value": round(n / total * 100, 1),
        "count": n,
        "color": EXIT_REASON_COLOR.get(r, "#CC8800"),
    } for r, n in counts.items()]
    out.sort(key=lambda x: x["value"], reverse=True)
    return out


def _build_live_recent_closed(history: list[dict], limit: int = 20) -> list[dict]:
    closed = [s for s in history if s.get("status") in ("HIT_TARGET", "HIT_STOP", "EXPIRED")]
    closed.sort(key=lambda s: s.get("close_date") or "", reverse=True)
    rows = []
    for i, s in enumerate(closed[:limit]):
        entry = float(s.get("entry") or 0)
        exit_p = float(s.get("close_price") or s.get("current_price") or 0)
        pnl_pct = _pnl(s)
        rows.append({
            "id": f"live-{i}",
            "date": s.get("close_date") or s.get("signal_date"),
            "symbol": s.get("ticker"),
            "side": "LONG",
            "entry": round(entry, 2),
            "exit": round(exit_p, 2),
            "pnl": round(100_000 * (pnl_pct / 100), 2),
            "pnlPct": round(pnl_pct, 2),
            "exitReason": EXIT_REASON_LABEL.get(s.get("status"), "Other"),
            "holdDays": int(s.get("days_since") or 0),
        })
    return rows


def _build_live_active(history: list[dict]) -> list[dict]:
    active = [s for s in history if s.get("status") in ("ACTIVE", "NEAR_TARGET")]
    active.sort(key=lambda s: s.get("pnl_pct") or 0, reverse=True)
    return [{
        "ticker": s.get("ticker"),
        "sector": s.get("sector"),
        "entry": s.get("entry"),
        "target": s.get("target"),
        "stop": s.get("stop"),
        "current_price": s.get("current_price"),
        "pnl_pct": s.get("pnl_pct") or 0,
        "days_since": s.get("days_since") or 0,
        "hold_days": s.get("hold_days") or 0,
        "status": s.get("status"),
        "signal_date": s.get("signal_date"),
    } for s in active]


@router.get("/backtest/live")
def live_blob(user: User = Depends(get_current_user)):
    history = fetch_github_json("results/signals_history.json") or []
    if not isinstance(history, list):
        history = []
    today = date.today()
    # Anchor the series to the actual first signal_date instead of a
    # hardcoded LIVE_START. Without this, 100+ days of flat-zero render
    # before any signals exist and the page implies the system was idle.
    start = _earliest_signal_date(history)
    analytics = compute_signal_analytics(history) or {}
    active = [s for s in history if s.get("status") in ("ACTIVE", "NEAR_TARGET")]
    open_pnls = [float(s.get("pnl_pct") or 0) for s in active]

    # Win-rate breakdown — `compute_signal_analytics` lumps trailing-
    # stop-at-profit into the same bucket as plain stop-losses. Surface
    # the split separately so the UI can show "11 target hits + 9
    # trailing-at-gain + 1 stop-loss" instead of an undifferentiated
    # 95% win rate that reads as too-good-to-be-true.
    closed = [s for s in history if s.get("status") in ("HIT_TARGET", "HIT_STOP", "EXPIRED")]
    stops_at_gain = sum(
        1 for s in closed
        if s.get("status") == "HIT_STOP" and _pnl(s) > 0
    )
    stops_at_loss = sum(
        1 for s in closed
        if s.get("status") == "HIT_STOP" and _pnl(s) <= 0
    )

    stats = {
        "days_live": max(1, (today - start).days),
        "total_signals": len(history),
        "active_signals": len(active),
        "closed_signals": analytics.get("total_signals", 0),
        "win_rate": analytics.get("win_rate", 0),
        "avg_return_pct": analytics.get("avg_return", 0),
        "avg_win_pct": analytics.get("avg_win", 0),
        "avg_loss_pct": analytics.get("avg_loss", 0),
        "best": analytics.get("best_signal"),
        "worst": analytics.get("worst_signal"),
        "hit_target": analytics.get("hit_target", 0),
        "hit_stop": analytics.get("hit_stop", 0),
        "stops_at_gain": stops_at_gain,
        "stops_at_loss": stops_at_loss,
        "expired": analytics.get("expired", 0),
        "avg_open_pnl_pct": round(sum(open_pnls) / len(open_pnls), 2) if open_pnls else 0.0,
    }

    return {
        "as_of": today.isoformat(),
        # Both fields exposed for forward-compat; frontends that consumed
        # `start_date` keep working, new frontends prefer
        # `first_signal_date` (the truthful name).
        "start_date": start.isoformat(),
        "first_signal_date": start.isoformat(),
        "stats": stats,
        "equity_curve": _build_live_equity_curve(history, today, start),
        "monthly_returns": _build_live_monthly_returns(history, today, start),
        "exit_reasons": _build_live_exit_reasons(history),
        "recent_closed": _build_live_recent_closed(history, 20),
        "active": _build_live_active(history),
    }


# ── Historical (reads the single blob written by regenerate_backtest.py) ─

@router.get("/backtest/historical")
def historical_blob(user: User = Depends(get_current_user)):
    data = fetch_github_json("results/backtest_data.json")
    if not isinstance(data, dict):
        return JSONResponse(
            status_code=404,
            content={
                "error": "results/backtest_data.json not found",
                "hint": "Run `python scripts/regenerate_backtest.py` locally, commit the file, push.",
            },
        )
    return data


# ── Legacy / deprecated ────────────────────────────────

@router.post("/backtest/run")
def run_backtest(user: User = Depends(get_current_user)):
    return {"status": "error", "error": "Backtesting available in local mode only"}


@router.get("/backtest/result/{job_id}")
def get_backtest_result(job_id: str, user: User = Depends(get_current_user)):
    return {"status": "not_found"}


@router.get("/backtest/history")
def get_backtest_history(user: User = Depends(get_current_user)):
    """Deprecated alias kept for backwards compatibility with older builds."""
    return []
