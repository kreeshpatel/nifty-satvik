"""Trades API — trade history and stats.

**Multi-user semantics (Sprint 1):**
The paper-trade log (`results/trade_log.csv`, `results/paper_trades.csv`)
is the admin's simulation data. Non-admin users get an empty response
here and should use `/api/kite/trades` for their own brokerage history.
"""

import re
import time
import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from auth import get_current_user
from config import get_sector
from database import User
from github_data import fetch_github_csv, fetch_github_file, fetch_github_json

router = APIRouter(tags=["trades"])

# In-memory stats cache — trade stats don't change often, avoid recomputing per request
_stats_cache = {"data": None, "ts": 0}
_STATS_CACHE_TTL = 600  # 10 minutes


def _load_trades():
    frames = []
    # Legacy CSV logs (kept for back-compat; absent in current deploys).
    for name in ["results/trade_log.csv", "results/paper_trades.csv"]:
        try:
            df = fetch_github_csv(name)
            if df is not None and not df.empty:
                frames.append(df)
        except Exception:
            pass
    # The live paper-broker closed-trade log is JSON (results/paper_trades.json). Map its fields to
    # the canonical trade-record columns the endpoints below expect (ticker/entry_date/exit_date/
    # return_pct/net_pnl/hold_days/exit_reason). This is why the trade history was empty before.
    try:
        rows = fetch_github_json("results/paper_trades.json")
        if isinstance(rows, list) and rows:
            # nifty-satvik's PaperBook emits entry_date/exit_date/entry/exit/reason/return_pct/pnl
            # (+ net_pct/net_pnl/hold_days aliases). The old mapping read buy_date/sell_date/
            # buy_price/sell_price/exit_reason — absent here, so every date/price/reason column came
            # back all-null → NaN → the JSON response failed and /api/trades returned empty (the
            # "Recently closed: 0 trades" bug). Read our field names, fall back to the legacy ones.
            frames.append(pd.DataFrame([{
                "ticker": t.get("ticker"),
                "qty": t.get("qty", t.get("shares")),
                "entry_date": t.get("entry_date", t.get("buy_date")),
                "entry_price": t.get("entry", t.get("buy_price")),
                "exit_date": t.get("exit_date", t.get("sell_date")),
                "exit_price": t.get("exit", t.get("sell_price")),
                "return_pct": t.get("net_pct", t.get("return_pct")),
                "net_pnl": t.get("net_pnl", t.get("pnl")),
                "hold_days": t.get("hold_days", t.get("days_held")),
                "exit_reason": t.get("exit_reason", t.get("reason")),
            } for t in rows]))
    except Exception:
        pass
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@router.get("/trades")
def get_trades(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=200),
    ticker: str = Query(""),
    start: str = Query(""),
    end: str = Query(""),
    exit_reason: str = Query(""),
    user: User = Depends(get_current_user),
):
    if not user.is_admin:
        return {"trades": [], "total": 0, "page": page, "pages": 0}

    try:
        df = _load_trades()
        if df.empty:
            return {"trades": [], "total": 0, "page": page, "pages": 0}

        if ticker:
            safe_ticker = re.escape(ticker)
            df = df[df["ticker"].str.contains(safe_ticker, case=False, na=False)]
        if start and "entry_date" in df.columns:
            df = df[df["entry_date"] >= start]
        if end and "entry_date" in df.columns:
            df = df[df["entry_date"] <= end]
        if exit_reason and "exit_reason" in df.columns:
            df = df[df["exit_reason"] == exit_reason]

        total = len(df)
        pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        page_df = df.iloc[start_idx:start_idx + per_page]

        return {"trades": page_df.to_dict("records"), "total": total, "page": page, "pages": pages}
    except Exception:
        return {"trades": [], "total": 0, "page": page, "pages": 0}


def _compute_sector_stats(df: pd.DataFrame) -> list:
    """Group trades by sector via SECTOR_MAP, return [{sector, trades, wins, win_rate}]."""
    if df.empty or "ticker" not in df.columns or "return_pct" not in df.columns:
        return []

    sectors = df.assign(sector=df["ticker"].astype(str).apply(get_sector))
    grouped = sectors.groupby("sector").agg(
        trades=("return_pct", "size"),
        wins=("return_pct", lambda s: int((s > 0).sum())),
    ).reset_index()
    grouped["win_rate"] = (grouped["wins"] / grouped["trades"] * 100).round(1)

    # Drop tiny buckets (<3 trades) and "Others" unless it's the only one
    filtered = grouped[grouped["trades"] >= 3]
    if filtered.empty:
        filtered = grouped
    filtered = filtered[filtered["sector"] != "Others"] if len(filtered) > 1 else filtered

    return (
        filtered.sort_values("trades", ascending=False)
        .head(12)
        .to_dict("records")
    )


def _compute_accuracy_trend(df: pd.DataFrame) -> list:
    """
    Rolling 30-day win rate — one point per day for the last 30 days,
    using trades that CLOSED on or before that date.
    """
    if df.empty or "return_pct" not in df.columns:
        return []

    date_col = "exit_date" if "exit_date" in df.columns else (
        "entry_date" if "entry_date" in df.columns else None
    )
    if date_col is None:
        return []

    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return []

    end = d[date_col].max()
    start = end - pd.Timedelta(days=30)
    window = pd.date_range(start, end, freq="D")

    points = []
    for day in window:
        # 30-day lookback window ending on `day`
        mask = (d[date_col] <= day) & (d[date_col] > day - pd.Timedelta(days=30))
        bucket = d[mask]
        if len(bucket) < 3:
            continue
        wr = round((bucket["return_pct"] > 0).sum() / len(bucket) * 100, 1)
        points.append({"date": day.strftime("%Y-%m-%d"), "win_rate": wr, "trades": int(len(bucket))})

    return points


@router.get("/trades/stats")
def get_trade_stats(user: User = Depends(get_current_user)):
    if not user.is_admin:
        return {"total_trades": 0, "sector_stats": [], "accuracy_trend_30d": []}

    # Serve from cache if fresh
    now = time.time()
    if _stats_cache["data"] is not None and (now - _stats_cache["ts"]) < _STATS_CACHE_TTL:
        return _stats_cache["data"]

    try:
        df = _load_trades()
        if df.empty or "return_pct" not in df.columns:
            empty = {"total_trades": 0, "sector_stats": [], "accuracy_trend_30d": []}
            _stats_cache["data"] = empty
            _stats_cache["ts"] = now
            return empty

        wins = df[df["return_pct"] > 0]
        losses = df[df["return_pct"] <= 0]
        stats = {
            "total_trades": len(df),
            "win_rate": round(len(wins) / len(df) * 100, 1) if len(df) > 0 else 0,
            "avg_win": round(wins["return_pct"].mean(), 2) if len(wins) > 0 else 0,
            "avg_loss": round(losses["return_pct"].mean(), 2) if len(losses) > 0 else 0,
            "best_trade": round(df["return_pct"].max(), 2),
            "worst_trade": round(df["return_pct"].min(), 2),
            "avg_hold_days": round(df["hold_days"].mean(), 1) if "hold_days" in df.columns else 0,
            "sector_stats": _compute_sector_stats(df),
            "accuracy_trend_30d": _compute_accuracy_trend(df),
        }
        if "exit_reason" in df.columns:
            stats["by_exit_reason"] = df["exit_reason"].value_counts().to_dict()

        _stats_cache["data"] = stats
        _stats_cache["ts"] = now
        return stats
    except Exception:
        return {"total_trades": 0, "sector_stats": [], "accuracy_trend_30d": []}


@router.get("/trades/export")
def export_trades(user: User = Depends(get_current_user)):
    if not user.is_admin:
        return {"error": "Trade export is admin-only"}
    try:
        text = fetch_github_file("results/trade_log.csv")
        if text:
            return PlainTextResponse(
                content=text,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=trade_log.csv"},
            )
    except Exception:
        pass
    return {"error": "No trade log found"}
