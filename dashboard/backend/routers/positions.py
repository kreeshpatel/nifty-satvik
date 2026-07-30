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
from github_data import fetch_github_json, fetch_github_csv, fetch_github_jsonl
from services.nq_positions import (
    build_external_holdings,
    build_nq_positions,
    held_signal_ids_all_users,
)

logger = logging.getLogger("positions")

router = APIRouter(tags=["positions"])


def _num(v, default=0.0):
    """Tolerant float coercion shared by the paper-ref builders."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


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


# ─────────────────────────────────────────────────────────────────────────────
# Paper (ref) — the bhanushali modelled paper book, for the Portfolio page.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/portfolio/paper-ref")
def get_paper_reference_book(user: User = Depends(get_current_user)):
    """The bhanushali weekly-swing PAPER book — modelled fills, not live holdings.

    Reads the SAME canonical artifacts the record of record uses, through the same
    GitHub-contents path every other cron-published reader uses (the deployed service has no
    `results/` on disk). No parallel computation, so there is no drift surface:

      results/paper_portfolio_weekly.json  — book + open positions (written by the weekly
                                             scanner, re-priced by the daily monitor)
      results/portfolio_history_weekly.csv — NAV series
      results/weekly_monitor.json          — freshness stamp of the last re-price

    NOT the momentum forward-wall books: those have never produced a log (their producer has
    no scheduled trigger — an open owner question), so there is nothing to render and this
    endpoint deliberately does not reference them.

    NOT `results/paper_ledger_history.csv` either — that fed the old momentum paper broker,
    whose producer was removed with the momentum book; the file is absent from the repo, so
    anything reading it renders an empty series that merely *looks* live.

    Admin-only, matching the existing paper/overview gate: the paper book is a single-owner
    simulation artifact.

    Response:
      { available, as_of, summary{...}, positions[...], closed[...], nav[...], sources{...} }
    """
    empty = {
        "available": False, "as_of": None,
        "summary": {}, "positions": [], "closed": [], "nav": [],
        "sources": {}, "note": "",
    }
    if not user.is_admin:
        return empty

    book = fetch_github_json("results/paper_portfolio_weekly.json")
    if not isinstance(book, dict) or not book:
        return {**empty, "note": "paper book artifact unavailable"}

    # ── freshness: the monitor's re-price stamp is the honest "as of" ──────────
    as_of = None
    monitor = fetch_github_json("results/weekly_monitor.json")
    if isinstance(monitor, dict):
        as_of = monitor.get("generated_utc") or monitor.get("generated_ist")

    def _f(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    # ── open positions, with unrealised R derived from the book's own stop ─────
    positions = []
    raw_positions = book.get("positions")
    if isinstance(raw_positions, dict):
        for ticker, p in raw_positions.items():
            if not isinstance(p, dict):
                continue
            entry = _f(p.get("entry_price"))
            stop = _f(p.get("atr_stop"))
            cur = _f(p.get("current_price"))
            risk = entry - stop
            positions.append({
                "ticker": ticker,
                "entry_date": p.get("entry_date"),
                "entry_price": round(entry, 2),
                "stop": round(stop, 2),
                "target": round(_f(p.get("target")), 2),
                "current_price": round(cur, 2),
                "shares": round(_f(p.get("shares")), 2),
                "position_size": round(_f(p.get("position_size")), 2),
                "current_value": round(_f(p.get("current_value")), 2),
                "unrealised_pnl": round(_f(p.get("unrealised_pnl")), 2),
                "unrealised_pnl_pct": round(_f(p.get("unrealised_pnl_pct")), 2),
                # R is capital-independent and is how the book is judged internally.
                "unrealised_r": round((cur - entry) / risk, 2) if risk > 0 else None,
                "days_held": int(_f(p.get("days_held"))),
            })
    positions.sort(key=lambda r: (r["entry_date"] or "", r["ticker"]))

    # ── closed trades ─────────────────────────────────────────────────────────
    # The book records `total_trades`; a closed-trade ledger is only present once exits
    # occur. Report the count honestly and return [] rather than fabricating rows.
    closed: list[dict] = []
    raw_closed = book.get("closed_trades") or book.get("trades")
    if isinstance(raw_closed, list):
        for t in raw_closed:
            if not isinstance(t, dict):
                continue
            e, x = _f(t.get("entry_price")), _f(t.get("exit_price"))
            st = _f(t.get("atr_stop") or t.get("stop"))
            risk = e - st
            closed.append({
                "ticker": t.get("ticker") or t.get("symbol"),
                "entry_date": t.get("entry_date"), "exit_date": t.get("exit_date"),
                "entry_price": round(e, 2), "exit_price": round(x, 2),
                "exit_reason": t.get("exit_reason") or t.get("reason"),
                "realised_pnl": round(_f(t.get("realised_pnl") or t.get("pnl")), 2),
                "realised_r": (round(_f(t.get("R")), 2) if t.get("R") is not None
                               else (round((x - e) / risk, 2) if risk > 0 else None)),
            })
        closed.sort(key=lambda r: (r["exit_date"] or ""), reverse=True)

    # ── NAV series ────────────────────────────────────────────────────────────
    nav = []
    try:
        df = fetch_github_csv("results/portfolio_history_weekly.csv")
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                v = _f(row.get("total_value"))
                if not (v > 0):        # NaN-safe: `nan <= 0` is False
                    continue
                nav.append({"date": str(row.get("date", "")), "value": round(v, 2)})
    except Exception as exc:
        logger.warning("paper-ref nav read failed: %s", exc)

    total_value = _f(book.get("total_value"))
    peak = _f(book.get("peak_value"))
    # Anchor since-inception to the book's cost basis, not nav[0] — the same F7 lesson the
    # paper-history endpoint above records: nav[0] is merely the first surviving ledger row and
    # drifts after any deploy/collection gap, producing two disagreeing "since inception" numbers.
    try:
        from config import INITIAL_CAPITAL
        baseline = float(INITIAL_CAPITAL)
    except Exception:
        baseline = 1_000_000.0
    summary = {
        "total_value": round(total_value, 2),
        "cash": round(_f(book.get("cash")), 2),
        "peak_value": round(peak, 2),
        "n_positions": int(_f(book.get("n_positions"))),
        "total_trades": int(_f(book.get("total_trades"))),
        "invested": round(total_value - _f(book.get("cash")), 2),
        "unrealised_pnl": round(sum(p["unrealised_pnl"] for p in positions), 2),
        "since_inception_pct": (round((total_value / baseline - 1) * 100, 2)
                                if baseline > 0 else None),
        "drawdown_from_peak_pct": (round((total_value / peak - 1) * 100, 2)
                                   if peak > 0 else None),
        "inception_date": nav[0]["date"] if nav else None,
    }

    from datetime import date as _date
    recommendations, retention = _paper_recommendations(book, _date.today().isoformat())

    return {
        "available": True,
        "as_of": as_of,
        "summary": summary,
        "positions": positions,
        "closed": closed,
        "nav": nav,
        "recommendations": recommendations,
        "retention": retention,
        "sources": {
            "book": "results/paper_portfolio_weekly.json",
            "nav": "results/portfolio_history_weekly.csv",
            "freshness": "results/weekly_monitor.json",
        },
        "note": ("Modelled fills on a paper reference book — not live holdings, not advice. "
                 "Positions are re-priced by the daily monitor; the book is rebuilt by the "
                 "weekly scanner."),
    }



def _rr(target, price, stop):
    """Reward:risk at a given price. None when the geometry is degenerate (price at/below stop)."""
    t_, p_, s_ = _num(target), _num(price), _num(stop)
    if not (t_ and p_ and s_) or p_ <= s_ or t_ <= p_:
        return None
    return round((t_ - p_) / (p_ - s_), 2)


def _card_live_context(sig: dict) -> dict:
    """Live decision-time context for an open card.

    The card prints its zone, stop and target once, on Saturday. A buyer acting on Wednesday
    faces different geometry: every rupee of price paid above the zone bottom buys the same
    target with more risk, so R:R decays across the zone. The record's modelled fill takes the
    next-week in-range OPEN, which is usually near the bottom of the band — a user buying at
    zone-top gets materially worse geometry than the book records. Showing both numbers side by
    side is what makes that gap visible; it is execution guidance, not a system rule.

    `ext_at_zone_low` is reported because the deep-touch findings are per-trade real and are NOT
    expressed in live sizing (LIVE_DISCIPLINE ships a blunt 20% blow-off cap only), so the band a
    card sits in is information the owner currently has no other way to see.
    """
    price = _num(sig.get("current_price")) or _num(sig.get("close"))
    lo, hi = _num(sig.get("entry_low")), _num(sig.get("entry_high"))
    stop, target = _num(sig.get("stop")), _num(sig.get("target"))
    out = {
        "live_price": round(price, 2) if price else None,
        "rr_at_zone_low": _rr(target, lo, stop),
        "rr_at_price": _rr(target, price, stop),
        "position_in_zone": None,
        "late_in_zone": None,
        "ext_at_zone_low_pct": None,
        "ext_band": None,
    }
    if price and lo and hi and hi > lo:
        out["position_in_zone"] = round(max(0.0, min(1.0, (price - lo) / (hi - lo))) * 100, 1)
    if out["rr_at_price"] is not None:
        out["late_in_zone"] = out["rr_at_price"] < 1.5
    # Extension at the band bottom vs the signal-week 44w SMA. The card does not carry the SMA, so
    # this is derived from the printed stop only when the engine set stop == zone_low (the touch
    # geometry); otherwise it is left None rather than guessed.
    sma = _num(sig.get("sma")) or _num(sig.get("signal_sma"))
    if sma and lo:
        ext = (lo / sma - 1) * 100
        out["ext_at_zone_low_pct"] = round(ext, 2)
        out["ext_band"] = "<5%" if ext < 5 else ("5-10%" if ext < 10 else ">10%")
    return out

def _paper_recommendations(book: dict, today: str) -> tuple[list[dict], dict]:
    """Every card the scanner issued, with its fate — derived from artifacts, never recomputed.

    D5 parity: entry zone, stop and target are echoed EXACTLY as the card printed them
    (`entry`, `entry_low`, `entry_high`, `stop`, `target` on the envelope). Nothing here
    re-derives trading logic; status is read off the artifacts:

      filled   — the name is a position in the capital-constrained paper book.
      skipped  — the signal tracker recorded a modelled entry (`bought_date`) but the ₹10L book
                 never held it. The tracker is the UNLIMITED-CAPITAL view; the book is the
                 constrained one, so the difference is the capital constraint biting. Safe to
                 assert only because the book has closed no trades (`total_trades == 0`): a name
                 absent from an exit-free book was never funded, not funded-then-exited.
      pending  — issued, unfilled, and the printed buy window has not closed yet.
      lapsed   — issued, unfilled, window closed: the price never entered the printed band.
      unknown  — the artifacts do not settle it (e.g. the book HAS closed trades, so absence can
                 no longer be read as "never funded"). Reported as unknown rather than guessed.

    Retention gap, stated honestly: `signals_today_weekly.json` is overwritten every Saturday and
    `signals_history_weekly.json` retains only names the tracker marked bought — so a card from a
    PRIOR week that lapsed unfilled leaves no artifact behind. `results/cards_archive.jsonl`
    (append-only, written by the scanner) is what preserves them going forward; before its first
    write only the current week is classifiable, and that is said in `retention`.
    """
    positions = book.get("positions") or {}
    held = set(positions.keys())
    exits_recorded = int(_num(book.get("total_trades")) or 0) > 0

    cards: dict[tuple, dict] = {}

    def _ingest(sig: dict, source: str) -> None:
        if not isinstance(sig, dict):
            return
        ticker = sig.get("ticker")
        sdate = str(sig.get("signal_date") or "")
        if not ticker:
            return
        key = (ticker, sdate)
        if key in cards and source != "archive":
            return
        until = sig.get("buy_window_until")
        bought = sig.get("bought_date")

        if ticker in held:
            status, why = "filled", None
        elif bought:
            if exits_recorded:
                status, why = "unknown", (
                    "the tracker recorded a modelled entry but the book does not hold it; the book "
                    "has closed trades, so absence no longer proves it was never funded")
            else:
                status, why = "skipped", "book at capital limit — the ₹10L book could not fund it"
        elif until and str(until) >= today:
            status, why = "pending", None
        elif until:
            status, why = "lapsed", "price never entered the printed buy band before the window closed"
        else:
            status, why = "unknown", "no buy window recorded on the card"

        cards[key] = {
            "ticker": ticker,
            "week": sdate,
            "signal_date": sdate,
            # D5 parity — exactly as printed on the card.
            "entry": round(_num(sig.get("entry")), 2) if sig.get("entry") is not None else None,
            "entry_low": round(_num(sig.get("entry_low")), 2) if sig.get("entry_low") is not None else None,
            "entry_high": round(_num(sig.get("entry_high")), 2) if sig.get("entry_high") is not None else None,
            "stop": round(_num(sig.get("stop")), 2) if sig.get("stop") is not None else None,
            "target": round(_num(sig.get("target")), 2) if sig.get("target") is not None else None,
            "grade": sig.get("grade"),
            "buy_window_until": until,
            "buy_window": sig.get("buy_window"),
            "status": status,
            "status_reason": why,
            # ── Decision-time context (ADDITIONAL to the printed card, never a reprint of it).
            # D5 parity: entry/entry_low/entry_high/stop/target above are verbatim from the card;
            # everything in this block is live and is labelled as such in the UI.
            **_card_live_context(sig),
            # filled cards point at the position they became
            "position_id": ticker if status == "filled" else None,
            "entry_date": (positions.get(ticker) or {}).get("entry_date") if status == "filled" else bought,
            "source": source,
        }

    archive = fetch_github_jsonl("results/cards_archive.jsonl")
    for row in (archive or []):
        _ingest(row, "archive")

    envelope = fetch_github_json("results/signals_today_weekly.json") or {}
    for sig in (envelope.get("signals") or []):
        _ingest(sig, "envelope")

    rows = sorted(cards.values(), key=lambda r: (r["week"], r["ticker"]), reverse=True)
    weeks = sorted({r["week"] for r in rows if r["week"]}, reverse=True)
    retention = {
        "archive_present": bool(archive),
        "weeks_retained": len(weeks),
        "current_week": weeks[0] if weeks else None,
        "note": ("Prior-week cards are preserved in results/cards_archive.jsonl (append-only, "
                 "written by the Saturday scanner)." if archive else
                 "No card archive yet — the weekly envelope is overwritten each Saturday and the "
                 "history file keeps only names the tracker marked bought, so cards that lapsed "
                 "unfilled in PRIOR weeks left no artifact and cannot be shown. Cards are "
                 "preserved from the next scanner run onward."),
    }
    return rows, retention
