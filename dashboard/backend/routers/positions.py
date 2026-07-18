"""Positions API.

Three layers of positions are served from this router:

  GET /positions           — legacy paper-portfolio positions (results/paper_portfolio_weekly.json).
                              Kept for the Kite-disconnected fallback in PortfolioV2.
  GET /positions/nq        — per-user NQ-tracked positions, joined from
                              nq_orders × signals_history × Kite holdings.
                              Drives the Portfolio "NiftyQuant Positions" section
                              and Signals "Held with Sell Guidance" tier.
  GET /positions/external  — Kite holdings minus NQ-attributed qty.
                              Drives the Portfolio "Other Kite Holdings" section.

The split exists because external Kite trades (placed outside our UI)
are intentionally not tracked in nq_orders — see CLAUDE.md "nq_orders
backend". The NQ vs External separation in the UI is the natural read of
that product decision.

A third endpoint (`GET /positions/nq/signal-ids`) is reserved for the
cron prune exemption — it requires a service token, not user auth, and
returns the union of held signal_ids across all users so the cron can
skip pruning held signals from signals_history.json.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from config import get_sector
from database import User, get_db
from github_data import fetch_github_json, fetch_github_csv
from services.nq_positions import (
    build_external_holdings,
    build_nq_positions,
    held_signal_ids_all_users,
)

logger = logging.getLogger("positions")

router = APIRouter(tags=["positions"])


# ── Legacy paper-portfolio endpoint (unchanged) ───────────────────────

@router.get("/positions")
def get_positions(user: User = Depends(get_current_user)):
    """Legacy paper-portfolio positions. Kept for the Kite-disconnected
    fallback path in PortfolioV2. New consumers should prefer
    /positions/nq + /positions/external.

    SECURITY: this serves the admin's single paper-trading portfolio
    (results/paper_portfolio_weekly.json). Gate it to admins like every sibling
    paper-data endpoint (overview.py) — previously it had no auth dependency
    at all, exposing the admin's entry prices / shares / P&L to any logged-in
    user. The frontend already tolerates an empty list for non-admins.
    """
    if not user.is_admin:
        return []
    try:
        state = fetch_github_json("results/paper_portfolio_weekly.json")
        if not state:
            return []

        # Live model status per signal, joined from signals_history. The
        # cron's track_signals re-evaluates every held signal daily
        # (ACTIVE / NEAR_TARGET / HIT_TARGET / HIT_STOP / EXPIRED) and the
        # paper broker sells the next session after an exit fires. Surfacing
        # the real status here lets the Holdings "Status" chip reflect that
        # tracking instead of a static "HOLD".
        # Join live model status by TICKER. Keying by ticker__signal_date is
        # fragile — the paper position's entry_date is T+1, not the signal_date,
        # so a composite join silently misses and the chip falls back to ACTIVE.
        # The held position is the most-recent signal for that name, so take the
        # status of the latest signal_date per ticker.
        status_map: dict[str, str] = {}
        try:
            hist = fetch_github_json("results/signals_history_weekly.json")
            hist_rows = hist if isinstance(hist, list) else (
                (hist or {}).get("signals") or (hist or {}).get("history") or []
            )
            latest_date: dict[str, str] = {}
            for s in hist_rows:
                if not isinstance(s, dict):
                    continue
                t = s.get("ticker")
                d = str(s.get("signal_date") or "")
                st = s.get("status")
                if t and st and d >= latest_date.get(t, ""):
                    latest_date[t] = d
                    status_map[t] = st
        except Exception:
            status_map = {}

        positions = []
        for ticker, pos in state.get("positions", {}).items():
            entry_date = pos.get("entry_date", "")
            hold_days = 0
            if entry_date:
                try:
                    hold_days = (datetime.now() - datetime.fromisoformat(entry_date)).days
                except ValueError:
                    pass

            current = pos.get("current_price", pos.get("entry_price", 0))
            stop = pos.get("atr_stop", 0)
            stop_dist = round((current - stop) / current * 100, 2) if current > 0 else 0

            positions.append({
                "ticker": ticker, "entry_date": entry_date,
                "entry_price": pos.get("entry_price", 0),
                "shares": pos.get("shares", 0),
                "position_size": pos.get("position_size", 0),
                "atr_stop": stop, "ml_score": pos.get("ml_score", 0),
                "current_price": current,
                "current_value": pos.get("current_value", 0),
                "unrealised_pnl": pos.get("unrealised_pnl", 0),
                "unrealised_pnl_pct": pos.get("unrealised_pnl_pct", 0),
                "hold_days": hold_days,
                "sector": pos.get("sector", get_sector(ticker)),
                "regime_at_entry": pos.get("regime_at_entry", ""),
                "stop_distance_pct": stop_dist,
                "target": pos.get("target", 0),
                "signal_status": status_map.get(
                    ticker, pos.get("status") or "ACTIVE"
                ),
            })

        positions.sort(key=lambda p: p["unrealised_pnl_pct"], reverse=True)
        return positions
    except Exception:
        return []


# ── NQ vs External (V2) ────────────────────────────────────────────────

def _safe_kite_holdings(user: User, db: Session) -> list[dict]:
    """No per-user broker connection (ADR 0011) — the user self-reports fills.
    Returns []; build_nq_positions() degrades gracefully off the per-user NQOrder
    ledger (no Kite qty/last-price join). The self-report source is wired in the
    Stage-4 execution ledger + Stage-5 quote join."""
    return []


def _safe_kite_margins(user: User, db: Session) -> dict | None:
    """No per-user broker connection (ADR 0011) — no Kite margins. Returns None;
    the NAV snapshot guards on None (no junk row). Self-report NAV source lands in
    Stage 5."""
    return None


@router.get("/positions/nq")
def get_nq_positions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-user NQ-tracked positions joined with Kite live truth.

    Empty list ≠ error — many users have signals but haven't bought any
    yet, in which case this returns []. Frontend should treat that as a
    happy-path state and render the empty-state with a "Browse signals"
    CTA.

    Side effect: opportunistically snapshots the user's NAV (cash +
    holdings value) into nav_history for today. Idempotent — multiple
    calls per day update the same row. This is how the Equity Curve
    accumulates data without requiring a server-side cron (per-user
    Kite sessions can't be refreshed non-interactively, so a cron can't
    reliably snapshot user NAV).
    """
    holdings = _safe_kite_holdings(user, db)
    positions = build_nq_positions(user.id, db, kite_holdings=holdings)

    # Best-effort NAV snapshot. Never raises into the response — if
    # Kite is disconnected or the snapshot fails, the user just doesn't
    # gain a row today. The chart degrades gracefully.
    if holdings:
        from services.nav_history import snapshot_nav
        margins = _safe_kite_margins(user, db)
        try:
            snapshot_nav(user.id, db, margins=margins, holdings=holdings)
        except Exception as exc:
            logger.warning("NAV snapshot exception (non-fatal): %s", exc)

    return {
        "positions": positions,
        "count": len(positions),
        "kite_connected": bool(holdings) or _has_kite_session(user, db),
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/portfolio/nav-history")
def get_portfolio_nav_history(
    days: int = 365,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User's NAV time series for the Equity Curve.

    Returns up to `days` rows of daily NAV snapshots, oldest-first.
    Snapshots are written by /api/positions/nq calls — no separate cron.
    Series starts whenever this endpoint shipped + the user first opened
    the dashboard with Kite connected.

    Response shape:
      { history: [{ date, value, cash, holdings_value, day_pnl }, ...],
        count: N,
        first_date, last_date }
    """
    from services.nav_history import get_nav_history
    rows = get_nav_history(user.id, db, limit=max(1, min(days, 1095)))
    return {
        "history": rows,
        "count": len(rows),
        "first_date": rows[0]["date"] if rows else None,
        "last_date": rows[-1]["date"] if rows else None,
    }


@router.get("/portfolio/paper-history")
def get_paper_equity_history(
    days: int = 365,
    user: User = Depends(get_current_user),
):
    """Paper-broker equity curve for the Paper view of the Equity Curve.

    This is deliberately distinct from the other two equity series:
      - /portfolio/nav-history  → live Kite NAV (real account, per-user).
      - /overview equity_curve  → the all-signals kill-criteria curve
        (results/portfolio_history.csv, unlimited capital — feeds the
        circuit breaker, NOT a tradeable portfolio).
      - THIS                    → the realistic capital-constrained ₹10L
        paper-broker ledger (results/paper_ledger_history.csv, written
        daily by src/trading/paper_broker.py).

    The Paper toggle must read THIS so it plots the bot's actual ₹10L
    equity rather than silently falling through to the live Kite NAV
    (the bug this endpoint fixes).

    Admin-only — the paper portfolio is a single owner simulation artifact
    (same gate as /overview + /positions). Non-admins get an empty series.

    Response shape mirrors /portfolio/nav-history so the frontend hook is
    symmetric:
      { history: [{ date, value, cash, invested, n_positions }, ...],
        count, first_date, last_date }
    """
    if not user.is_admin:
        return {"history": [], "count": 0, "first_date": None, "last_date": None}

    history: list[dict] = []
    try:
        df = fetch_github_csv("results/paper_ledger_history.csv")
        if df is not None and not df.empty:
            tail = df.tail(max(1, min(days, 1095)))
            for _, row in tail.iterrows():
                try:
                    value = float(row.get("total_value") or 0)
                except (TypeError, ValueError):
                    value = 0.0
                # Skip junk/zero/NaN rows so a bad write can't plant a
                # misleading ₹0 datapoint (or NaN → invalid JSON). Using
                # `not (value > 0)` rather than `value <= 0` because
                # `nan <= 0` is False and would let a NaN through.
                if not (value > 0):
                    continue
                history.append({
                    "date": str(row.get("date", "")),
                    "value": round(value, 2),
                    "cash": round(float(row.get("cash") or 0), 2),
                    "invested": round(float(row.get("invested") or 0), 2),
                    "n_positions": int(float(row.get("n_positions") or 0)),
                })
    except Exception as exc:
        logger.warning("paper-history read failed: %s", exc)

    # Baseline = the paper book's ₹10L cost basis, so the frontend anchors
    # "since-inception %" to INITIAL_CAPITAL (the same denominator /overview
    # uses for total_return_pct) rather than history[0].value — which is just
    # the first surviving ledger row and can drift after a deploy gap,
    # producing two disagreeing "return since inception" numbers (F7).
    try:
        from config import INITIAL_CAPITAL
        baseline = float(INITIAL_CAPITAL)
    except Exception:
        baseline = 1_000_000.0

    return {
        "history": history,
        "count": len(history),
        "first_date": history[0]["date"] if history else None,
        "last_date": history[-1]["date"] if history else None,
        "baseline": baseline,
    }


@router.get("/positions/external")
def get_external_holdings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kite holdings minus NQ-attributed qty.

    Strict-overlap rule: same-ticker partial overlap subtracts the NQ-
    tracked qty from the Kite qty. If the user owns 50 SBIN externally,
    NQ told them to buy 100, and Kite shows 150 → external returns
    SBIN with quantity=50 and nq_attributed_qty=100.
    """
    holdings = _safe_kite_holdings(user, db)
    if not holdings:
        return {"holdings": [], "count": 0, "kite_connected": False}

    nq_positions = build_nq_positions(user.id, db, kite_holdings=holdings)
    external = build_external_holdings(nq_positions, holdings)
    return {
        "holdings": external,
        "count": len(external),
        "kite_connected": True,
        "updated_at": datetime.utcnow().isoformat(),
    }


# ── Cron prune-exemption endpoint (service token) ──────────────────────

CRON_SERVICE_TOKEN = os.getenv("CRON_SERVICE_TOKEN", "")


@router.get("/positions/nq/signal-ids")
def get_held_signal_ids(
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
    db: Session = Depends(get_db),
):
    """Union of signal_ids with held_qty > 0 across all users.

    Service-token auth (NOT user JWT) — this endpoint is called by the
    Render cron before pruning signals_history.json. The cron must NOT
    delete a signal that any user is still holding, otherwise the
    Portfolio NQ Position card loses its anchoring entry/stop/target
    context.

    Fail-closed contract on the caller side: if this endpoint is
    unreachable, the cron MUST skip pruning that run rather than risk a
    bad delete. See PR5 in the implementation plan.

    The response leaks no per-user data — just the set of held signal_ids,
    which is itself derivable from the public signals_history.json
    contents.
    """
    if not CRON_SERVICE_TOKEN:
        # Misconfiguration — refuse rather than open up the endpoint.
        raise HTTPException(
            status_code=503,
            detail="Service token not configured on server",
        )
    if x_service_token != CRON_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid service token")

    signal_ids = held_signal_ids_all_users(db)
    return {
        "signal_ids": signal_ids,
        "count": len(signal_ids),
        "computed_at": datetime.utcnow().isoformat(),
    }


# ── Helpers ────────────────────────────────────────────────────────────

def _has_kite_session(user: User, db: Session) -> bool:
    """Cheap check used to populate kite_connected in /positions/nq when
    holdings happen to be empty (user has Kite linked but holds nothing
    in equity — e.g. only F&O positions)."""
    from database import KiteSession
    import time as _time
    sess = db.query(KiteSession).filter(KiteSession.user_id == user.id).first()
    return sess is not None and _time.time() < sess.expires_at
