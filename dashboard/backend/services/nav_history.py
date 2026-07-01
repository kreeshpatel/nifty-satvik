"""
NAV-history snapshot service — keeps the Equity Curve fed.

Called from /api/positions/nq on every request (idempotent — once per day
per user). Best-effort: if Kite is disconnected or any leg of the snapshot
math fails, the call returns silently and the user's history just doesn't
gain a row that day. Never raises into the caller's request flow.

Why dashboard-load triggered instead of cron:
  Per-user Kite sessions expire daily at 6 AM IST and need interactive
  reconnect. A server-side cron can't reliably refresh user sessions, so
  it can't reliably snapshot user NAV either. Dashboard-load triggered
  snapshots happen exactly when the user IS connected — guaranteed live
  Kite session, guaranteed real numbers.

  Trade-off: gaps on days a general user doesn't open the app. Acceptable
  for v1. A future v2 could add a user-opt-in "background snapshot via
  passive session" flow if Zerodha ever exposes one.

  EXCEPTION — the ADMIN/owner: the admin Kite session IS auto-refreshed
  server-side daily (refresh_kite_session.py, the niftyquant-kite-refresh
  cron, 6:15 AM IST via TOTP). That cron now also calls snapshot_nav for the
  admin right after the refresh, so the OWNER's equity curve fills daily with
  no app-open required (closes the "chart only updates when I open the app"
  gap for the owner). General users still rely on dashboard-load snapshots.
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from database import NavHistory

logger = logging.getLogger("nav_history")


def _effective_qty(h: dict) -> float:
    """Settled + T+1 — matches the normalization in
    services/nq_positions._index_kite_holdings and the frontend
    useKiteHoldings.select(). Without this, freshly-bought delivery
    holdings count as 0 in the snapshot since Kite's `quantity` field
    only reflects settled shares."""
    return float(h.get("quantity") or 0) + float(h.get("t1_quantity") or 0)


def _compute_day_pnl(holdings: list[dict]) -> float:
    """Mirror the frontend KPI fallback: prefer Kite's day_change, fall
    back to total unrealised when day_change is uniformly 0 (T+1 case).

    Keeping this in sync with PortfolioV2/DashboardV2 is intentional —
    we want the snapshot value to match what the user saw in the KPI tile
    at the moment of the snapshot.
    """
    day_change_sum = 0.0
    for h in holdings:
        qty = _effective_qty(h)
        day = float(h.get("day_change") or 0)
        day_change_sum += day * qty
    if day_change_sum != 0:
        return round(day_change_sum, 2)

    # All-zero day_change → total unrealised P&L fallback.
    fallback = 0.0
    for h in holdings:
        qty = _effective_qty(h)
        ltp = float(h.get("last_price") or 0)
        avg = float(h.get("average_price") or 0)
        fallback += (ltp - avg) * qty
    return round(fallback, 2)


def _holdings_value(holdings: list[dict]) -> float:
    return round(
        sum(
            float(h.get("last_price") or 0) * _effective_qty(h)
            for h in holdings or []
        ),
        2,
    )


def snapshot_nav(
    user_id: int,
    db: Session,
    margins: Optional[dict] = None,
    holdings: Optional[list[dict]] = None,
) -> Optional[NavHistory]:
    """Idempotent NAV snapshot for `user_id` for today's date.

    Called from get_nq_positions; the holdings + margins are already
    fetched in that flow so we accept them as args to avoid duplicate
    Kite calls.

    Behaviour:
      - If margins is None OR holdings_value computes to 0 (likely
        Kite disconnected / 401), do nothing — don't write a junk
        zero-NAV row that would skew the chart.
      - If a row exists for (user_id, today), update it with the latest
        NAV / holdings_value / day_pnl. Otherwise insert.
      - On DB error, log and return None — never raise into the caller.

    Returns the NavHistory row (created or updated), or None on no-op.
    """
    if margins is None and not holdings:
        return None

    holdings_val = _holdings_value(holdings or [])
    cash = 0.0
    if margins:
        cash = float(margins.get("available") or 0) + float(margins.get("used") or 0)

    nav = round(cash + holdings_val, 2)

    # Don't write a row if NAV is 0 — likely a Kite disconnect leaking
    # zeros into the snapshot. Better to skip than to plot a misleading
    # ₹0 datapoint that contaminates the equity curve.
    if nav <= 0:
        return None

    day_pnl = _compute_day_pnl(holdings or [])
    today = date.today()
    now = datetime.utcnow()

    try:
        existing = (
            db.query(NavHistory)
            .filter(
                NavHistory.user_id == user_id,
                NavHistory.snapshot_date == today,
            )
            .first()
        )
        if existing:
            existing.nav = nav
            existing.cash = cash
            existing.holdings_value = holdings_val
            existing.day_pnl = day_pnl
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        row = NavHistory(
            user_id=user_id,
            snapshot_date=today,
            nav=nav,
            cash=cash,
            holdings_value=holdings_val,
            day_pnl=day_pnl,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        logger.warning("NAV snapshot failed for user %s: %s", user_id, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def get_nav_history(user_id: int, db: Session, limit: int = 365) -> list[dict]:
    """Return the user's NAV history newest-first, capped at `limit` rows.

    Output is the shape the Equity Curve consumes:
      [{ date: 'YYYY-MM-DD', value: <nav>, day_pnl: <pnl> }, ...]
    Sorted oldest-to-newest so the chart's x-axis renders left-to-right
    chronologically without a frontend sort.
    """
    rows = (
        db.query(NavHistory)
        .filter(NavHistory.user_id == user_id)
        .order_by(NavHistory.snapshot_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "date": r.snapshot_date.isoformat(),
            "value": round(r.nav, 2),
            "cash": round(r.cash, 2),
            "holdings_value": round(r.holdings_value, 2),
            "day_pnl": round(r.day_pnl, 2),
        }
        for r in reversed(rows)
    ]
