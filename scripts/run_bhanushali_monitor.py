"""Daily OBSERVATIONAL monitor for the Weekly-Swing forward-watch book.

Why this exists: the weekly-swing engine only recomputes on Saturday (run_bhanushali_cron.py),
so all week the dashboard's weekly cards carry SATURDAY's price / P&L / distance-to-stop. This job
re-prices those FROZEN cards against fresh daily bars and flags intra-week events so the owner can
act on resting broker orders without watching the screen all day.

STRICTLY observational — it is the weekly book's analogue of the intraday shadow scan:
  * It NEVER recomputes the weekly signal set. Re-running the weekly engine daily would risk
    emitting/retracting signals off a PARTIAL current-week bar and break the weekly decision
    cadence the forward paper record is certified on.
  * It NEVER changes the frozen entry / stop / target — those are decided only at the Friday
    weekly close. It only reports live price vs those fixed lines.
  * It NEVER touches the paper book, NAV, ledger, wall log, or kill state.

Reads : results/signals_today_weekly.json   (the frozen weekly envelope: buy signals + held cards)
Writes: results/weekly_monitor.json         (fresh current_price + per-ticker event flags)

The dashboard backend (routers/signals.py) overlays this file's current_price and flags onto the
frozen weekly cards, so prices/P&L stay live all week for every viewer — Kite-connected or not —
without a second signal engine.

    python scripts/run_bhanushali_monitor.py               # cron (refreshes recent daily bars)
    python scripts/run_bhanushali_monitor.py --no-download # offline / local test (cache as-is)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import RESULTS_DIR  # noqa: E402
from nq.data.ohlcv import (  # noqa: E402
    OHLCV_CACHE,
    download_ohlcv,
    load_ohlcv_cache,
    merge_ohlcv,
    save_ohlcv_cache,
)

TRAIL_PCT = 0.04          # the runner's ratchet trail = 20-day SMA x (1 - 4%); shown as info only
NEAR_PCT = 2.0            # "approaching" band for stop / target proximity flags (percent)
CAP_WEEKS = 13            # ~3-month time cap; flag when a held position nears it
IST = timezone(timedelta(hours=5, minutes=30))


class _Bar:
    """The last daily bar of a ticker, with the fields the tranche mapper needs."""
    __slots__ = ("close", "open", "high", "low", "sma20", "date")

    def __init__(self, close, open_, high, low, sma20, dt):
        self.close, self.open, self.high, self.low, self.sma20, self.date = close, open_, high, low, sma20, dt


def _last_bar(df: pd.DataFrame) -> "_Bar | None":
    """The last daily bar (close/open/high/low + 20-day SMA of close + bar date) from a raw frame."""
    if df is None or len(df) == 0 or "Close" not in df.columns:
        return None
    c = df["Close"].astype(float)
    o = df["Open"].astype(float) if "Open" in df.columns else c
    h = df["High"].astype(float) if "High" in df.columns else c
    lo = df["Low"].astype(float) if "Low" in df.columns else c
    sma20 = float(c.tail(20).mean()) if len(c) >= 1 else float("nan")
    return _Bar(float(c.iloc[-1]), float(o.iloc[-1]), float(h.iloc[-1]), float(lo.iloc[-1]),
                sma20, pd.Timestamp(df.index[-1]))


def _r_multiple(price: float, entry: float, stop: float) -> float | None:
    """How many R above entry `price` sits, where 1R = entry - stop (the initial risk)."""
    risk = entry - stop
    return (price - entry) / risk if risk > 0 else None


def _tranche_status(tr: dict, bar: "_Bar", entry: float, stop: float) -> dict:
    """Map ONE frozen exit tranche to its live intra-week status.

    The keystone cadence rule lives here: the +2R target tranche is a resting broker LIMIT, so it
    is the ONLY tranche that can be `actionable` intra-week. The blow-off `pattern` and the 44w-SMA
    `runner` are WEEKLY-CLOSE decisions — this daily job may only WATCH them (never `actionable`),
    because acting on a partial-week bar would break the weekly decision cadence the paper record is
    certified on. The Saturday recompute is what actually decides those two tranches.
    """
    typ = tr.get("type")
    pct = tr.get("pct")
    lvl = tr.get("level")
    out = {"type": typ, "pct": pct, "level": lvl, "actionable": False, "status": "", "hit": False}

    if typ == "target" and lvl:
        # Booked with a resting limit order — intra-week actionable the moment price trades through it.
        hit = bar.high >= float(lvl) if bar.high else bar.close >= float(lvl)
        dist = round((float(lvl) / bar.close - 1) * 100, 2) if bar.close else None
        out.update(hit=bool(hit), actionable=bool(hit), dist_pct=dist,
                   status=(f"reached — your resting limit to sell {pct}% should fill"
                           if hit else f"{dist:.1f}% away" if dist is not None else "n/a"))

    elif typ == "pattern":
        # Blow-off / exhaustion tranche — decided ONLY at the weekly close. Never actionable here.
        arm = tr.get("arm")
        r = _r_multiple(bar.close, entry, stop)
        armed = bool(arm is not None and r is not None and r >= float(arm))
        rng = bar.high - bar.low
        weak_close = bool(rng > 0 and (bar.close - bar.low) / rng < 0.5 and bar.high >= bar.close)
        out.update(actionable=False, armed=armed, r_multiple=round(r, 2) if r is not None else None,
                   weak_close_today=weak_close,
                   status=(f"armed (>+{arm}R): a blow-off/exhaustion WEEKLY close would sell {pct}% — "
                           f"decided at Saturday's recompute, not intra-week"
                           + (" · possible exhaustion bar today (daily proxy)" if armed and weak_close else "")
                           if armed else f"watching — sells {pct}% on a blow-off weekly close (Sat decides)"))

    elif typ == "runner":
        # Held to the 44w-SMA; exits ONLY on a weekly CLOSE below it. Never actionable intra-week.
        below = bool(lvl and bar.close < float(lvl))
        dist = round((bar.close / float(lvl) - 1) * 100, 2) if lvl else None
        out.update(actionable=False, below_sma=below, dist_pct=dist,
                   status=(f"below the 44w-SMA {lvl} intra-week ({dist:+.1f}%) — only a Friday weekly "
                           f"close confirms the runner exit (Sat decides)" if below
                           else f"{dist:+.1f}% vs the 44w-SMA {lvl}; hold the last {pct}% runner"
                                if dist is not None else f"hold the last {pct}% runner to the 44w-SMA"))
    return out


# ── MISSED EXITS — the daily "you were supposed to be out of this" recommendation ──────────
# WHY THIS EXISTS. The book's stop is a WEEKLY-CLOSE stop, executed at the NEXT session's open
# (run_bhanushali_cron: "Weekly close below the stop — SELL the remaining position at Monday's
# open"). A reader who does not sell at that open is off-plan — and until now nothing told them so
# on any day but Saturday. The EXIT_REQUIRED card is dropped from the NEXT weekly envelope the
# moment the model books the trade, so a missed exit simply VANISHED from the surface that was
# meant to instruct it, and the position went dark exactly when it was costing the most.
#
# This block re-prices, EVERY DAY, every exit the model has already taken, so a reader still
# holding one is told what it now costs to keep waiting. It invents NO new judgement: the exit
# decision, its date and its booked price are all the model's own, read back off the record
# (signals_history_weekly.json) or off the card the Saturday scan already stamped EXIT_REQUIRED.
# The only thing computed here is the DRIFT since — which is a fact, not an opinion.
#
# Strictly observational like the rest of this job: it never books, retracts, or re-decides
# anything, and the paper record never reads it.
MISSED_LOOKBACK_DAYS = 120        # stop re-pricing an exit the reader has clearly abandoned
_MISSED_CLOSED_STATUS = {"HIT_STOP", "HIT_TARGET", "EXPIRED", "CLOSED", "RESOLVED"}
# exit reason (or status) -> (severity, plain-English cause). "stop" is the risk line, so it is the
# only family that carries `high`: a missed target leaves money on the table, a missed stop keeps
# unbounded risk on the book.
_MISSED_CAUSE = {
    "stop": ("high", "the weekly close broke its stop"),
    "stop_part": ("high", "the weekly close broke its stop"),
    "stop_half": ("high", "the weekly close broke its stop"),
    "trail": ("high", "the trailing stop broke"),
    "sma_break": ("high", "the weekly close broke the 44-week SMA — the runner's trend is gone"),
    "wk20": ("high", "the weekly close broke the 20-week trail"),
    "HIT_STOP": ("high", "the weekly close broke its stop"),
    "target": ("action", "the +2R target was reached"),
    "targets": ("action", "the +2R target was reached"),
    "target3": ("action", "the target was reached"),
    "pattern": ("action", "a blow-off/exhaustion week closed"),
    "blowoff": ("action", "a blow-off/exhaustion week closed"),
    "HIT_TARGET": ("action", "the model's profit target was reached"),
    "time": ("action", "the position hit its time cap"),
    "eos": ("action", "the position hit its time cap"),
    "stale": ("action", "the position went stale (no tradable bars)"),
    "EXPIRED": ("action", "the position hit its time cap"),
}


def _first_session_at_or_after(df: pd.DataFrame, when: str) -> "tuple[pd.Timestamp, float] | None":
    """(date, OPEN) of the first daily bar at/after `when` — the model's execution price.

    The engine executes a weekly-close decision at the NEXT session's open, so that bar's open IS
    the booked exit. Reading it back here means the "you should have sold at" price the reader sees
    is the same number the record used, never a reconstruction of it.
    """
    if df is None or len(df) == 0 or "Close" not in df.columns:
        return None
    try:
        ts = pd.Timestamp(when).normalize()
    except (ValueError, TypeError):
        return None
    idx = pd.DatetimeIndex(df.index).normalize()
    hit = int(idx.searchsorted(ts, side="left"))
    if hit >= len(df):
        return None                                   # the due open has not happened yet
    o = df["Open"] if "Open" in df.columns else df["Close"]
    return pd.Timestamp(df.index[hit]), float(o.iloc[hit])


def _window_fill(df, *, signal_date, buy_window_until, lo: float, hi: float) -> "dict | None":
    """The FIRST session in the buy window whose OPEN fell inside the band, or None.

    WHY THIS EXISTS. `filled_today` is recomputed against the LAST bar every run, so it answers
    "can I buy at today's open", not "did this signal ever trigger". Those are the same question
    on Monday and opposite questions by Thursday: JSWSTEEL opened 1,298.00 inside its band on
    Monday 2026-08-24 -- a clean fill, exactly as the card instructs -- then ran to 1,326 / 1,329
    / 1,351 on the next three opens, at which point the surface said "Gapped - wait" about a trade
    that had already been taken. A card cannot instruct with a fact that forgets itself daily.

    The window opens at the first session AFTER the signal date (the card is issued at the
    Saturday close and executed at the next open) and closes at `buy_window_until` inclusive.
    """
    if df is None or len(df) == 0 or not (lo and hi) or "Open" not in df.columns:
        return None
    try:
        start = pd.Timestamp(signal_date).normalize()
        end = pd.Timestamp(buy_window_until).normalize() if buy_window_until else None
    except (ValueError, TypeError):
        return None
    idx = pd.DatetimeIndex(df.index).normalize()
    for i in range(len(df)):
        d = idx[i]
        if d <= start:
            continue                                   # the signal's own week, not yet buyable
        if end is not None and d > end:
            break                                      # window closed
        o = float(df["Open"].iloc[i])
        if lo <= o <= hi:
            return {"date": str(d.date()), "open": round(o, 2)}
    return None


def _why_unpriceable(df, due_date) -> str:
    """Plain-English reason a closed trade could not be re-priced — the fix differs per cause."""
    bar = _last_bar(df)
    if bar is None:
        return "no daily bars cached for this ticker"
    try:
        if pd.Timestamp(bar.date).normalize() < pd.Timestamp(due_date).normalize():
            return f"last bar {str(bar.date)[:10]} predates the exit - stale cache or failed download"
    except (ValueError, TypeError):
        return "unparseable exit date on the record"
    return "no exit price on the record"


def _missed_row(*, ticker, signal_date, reason, due_date, due_price, entry, stop, bar,
                r_at_exit=None) -> "dict | None":
    """One re-priced missed exit. `bar` is today's daily bar; every other input is the record's."""
    if bar is None or not due_price or float(due_price) <= 0:
        return None
    # STALE-BAR GUARD. `drift` only means anything if today's bar is at/after the exit. On a cold or
    # part-refreshed cache the last bar can PREDATE the due date, and the row would then quote a
    # price from before the sell as "where it is now" — a confident number pointing the wrong way.
    # Say nothing rather than say that.
    try:
        if pd.Timestamp(bar.date).normalize() < pd.Timestamp(due_date).normalize():
            return None
    except (ValueError, TypeError):
        return None
    sev, cause = _MISSED_CAUSE.get(reason, ("high", "the model closed this trade"))
    last = float(bar.close)
    due_px = float(due_price)
    drift = (last / due_px - 1) * 100.0
    row = {
        "ticker": ticker,
        "signal_id": f"{ticker}__{signal_date}" if signal_date else None,
        "signal_date": signal_date,
        "reason": reason,
        "severity": sev,
        "cause": cause,
        "due_date": str(due_date)[:10],
        "due_price": round(due_px, 2),
        "last_close": round(last, 2),
        "as_of": str(bar.date.date()),
        # NEGATIVE = waiting has cost you; POSITIVE = it happens to have recovered since. Reported
        # both ways, because a rule that only speaks when it looks right is not a rule.
        "drift_pct": round(drift, 2),
        "entry": round(float(entry), 2) if entry else None,
        "stop": round(float(stop), 2) if stop else None,
    }
    if r_at_exit is not None:
        row["r_at_exit"] = round(float(r_at_exit), 2)
    if entry and stop and float(entry) > float(stop):
        risk = float(entry) - float(stop)
        row["r_at_exit"] = round((due_px - float(entry)) / risk, 2)
        row["r_now"] = round((last - float(entry)) / risk, 2)
    verb = "still" if drift <= 0 else "now"
    row["do"] = (f"The model sold {ticker} on {row['due_date']} at Rs {row['due_price']:,.2f} — "
                 f"{cause}. If you did not sell, you are holding a position the record is flat on: "
                 f"sell the remainder at market at the next open. It is {verb} at "
                 f"Rs {row['last_close']:,.2f} ({drift:+.1f}% vs the model's exit).")
    return row


def build_missed_exits(envelope: dict, history: list, ohlcv: dict,
                       today: "pd.Timestamp | None" = None) -> list:
    """The priced half of `build_missed_exits_report` — every exit we could re-price (pure)."""
    return build_missed_exits_report(envelope, history, ohlcv, today=today)["rows"]


def build_missed_exits_report(envelope: dict, history: list, ohlcv: dict,
                              today: "pd.Timestamp | None" = None) -> dict:
    """Every exit the model has ALREADY taken, re-priced against today's bar (pure).

    Returns BOTH halves — `{"rows": [...], "unpriceable": [...]}` — because the guard that keeps
    this safe is also the one that can silence it. `_missed_row` says nothing when the bar it would
    quote predates the exit, which is exactly right for a cold cache and exactly WRONG to report as
    "no missed exits": a failed download in the cron produces the same empty list as a reader who
    is perfectly on-plan. Two very different facts must not share one number. So a candidate the
    record says is closed, but whose drift we cannot compute, is returned separately and annotated
    ::warning by the caller rather than dropped into silence.

    Two sources, because a missed exit changes shape the moment the weekend recompute runs:
      1. `signals_history_weekly.json` — the BOOKED record. Authoritative: it carries the exit price
         and date the record actually used, so nothing here is reconstructed.
      2. the live envelope's `actionability == EXIT_REQUIRED` cards — the sell the Saturday scan has
         issued but the record has not booked yet. Counted only once its due OPEN has PASSED; before
         then it is simply this week's instruction, not a missed one.

    History WINS on conflict — a booked price beats an inferred one.
    """
    cutoff = (today or pd.Timestamp.today()).normalize() - pd.Timedelta(days=MISSED_LOOKBACK_DAYS)
    rows: dict = {}
    unpriceable: list[dict] = []

    for h in history or []:
        status = str(h.get("status") or "").upper()
        if status not in _MISSED_CLOSED_STATUS:
            continue
        t, cd, px = h.get("ticker"), h.get("close_date"), h.get("close_price")
        if not (t and cd and px):
            continue
        try:
            if pd.Timestamp(cd).normalize() < cutoff:
                continue
        except (ValueError, TypeError):
            continue
        row = _missed_row(ticker=t, signal_date=h.get("signal_date"),
                          reason=str(h.get("exit_reason") or status), due_date=cd, due_price=px,
                          entry=h.get("entry"), stop=h.get("stop"), bar=_last_bar(ohlcv.get(t)),
                          r_at_exit=h.get("r_multiple"))
        if row:
            row["source"] = "booked"
            rows[row["signal_id"] or f"{t}__"] = row
        else:
            # In the lookback and closed by the record, yet unpriceable: no bars for the name, or
            # the last bar predates the sell. Either way the reader still holding it hears nothing,
            # so the RUN has to say so even though the page cannot.
            unpriceable.append({"ticker": t, "due_date": str(cd)[:10], "source": "booked",
                                "why": _why_unpriceable(ohlcv.get(t), cd)})

    gen = (envelope or {}).get("generated_at")
    for sig in (envelope or {}).get("signals", []):
        if str(sig.get("actionability") or "").upper() != "EXIT_REQUIRED":
            continue
        t = sig.get("ticker")
        sid = f"{t}__{sig.get('signal_date')}"
        if not t or sid in rows:
            continue                                  # already booked — the record's price wins
        df = ohlcv.get(t)
        bar = _last_bar(df)
        if bar is None:
            continue
        # The sell was due at the first OPEN after the weekly close that decided it.
        due = _first_session_at_or_after(df, str(gen)[:10]) if gen else None
        if due is None:
            continue                                  # due open still ahead — not a miss
        due_dt, due_px = due
        if due_dt.normalize() >= pd.Timestamp(bar.date).normalize():
            continue                                  # the due open IS today — not missed yet
        row = _missed_row(ticker=t, signal_date=sig.get("signal_date"),
                          reason=str(sig.get("status") or "HIT_STOP").upper(), due_date=due_dt,
                          due_price=due_px, entry=sig.get("entry"), stop=sig.get("stop"), bar=bar)
        if row:
            row["source"] = "issued"
            rows[sid] = row

    order = {"high": 0, "action": 1}
    return {
        "rows": sorted(rows.values(), key=lambda r: (order.get(r["severity"], 9), r["due_date"])),
        # A ticker already reported in `rows` under a newer episode is still listed here for the
        # older one — the two are different positions and only one of them is being watched.
        "unpriceable": sorted(unpriceable, key=lambda u: (u["due_date"], u["ticker"])),
    }


def _refresh(tickers: list[str], do_download: bool) -> dict:
    """Return the OHLCV cache, refreshed for just the envelope's tickers.

    Cheap by design — only the handful of names on the weekly cards, not the whole universe. A
    download hiccup is non-fatal: we fall back to whatever the cache already holds.

    The window is ~120 calendar days (~80 trading bars), NOT the ~20 the monitor itself needs:
    download_ohlcv() drops any name with < 50 usable bars, so a 20-day pull returns ZERO names on
    a fresh checkout (the GitHub runner has no local cache) and the monitor silently re-priced
    nothing — the bug that shipped an empty weekly_monitor.json on the first cloud run."""
    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    if not do_download or not tickers:
        return ohlcv
    dl_start = (date.today() - timedelta(days=120)).isoformat()
    try:
        fresh = download_ohlcv(tickers, start=dl_start, end=date.today().isoformat())
        ohlcv = merge_ohlcv(ohlcv, fresh) if ohlcv else fresh
        save_ohlcv_cache(ohlcv, OHLCV_CACHE)
        print(f"refreshed {len(fresh)}/{len(tickers)} tickers from {dl_start}", flush=True)
    except Exception as exc:  # noqa: BLE001 — never lose the cache over a fetch hiccup
        print(f"download failed ({type(exc).__name__}: {exc}); using cached bars", flush=True)
    return ohlcv


def build_monitor(envelope: dict, ohlcv: dict, history: list | None = None) -> dict:
    """Re-price the frozen weekly cards and flag intra-week events. Pure — reads, never mutates.

    `history` is the booked weekly record (signals_history_weekly.json). It is what lets the
    MISSED-EXIT pass see trades the model has already closed and DROPPED from the envelope —
    the exact positions a reader who skipped the sell is still carrying, unwatched.
    """
    monitors: list[dict] = []
    flags: list[dict] = []
    as_of: pd.Timestamp | None = None

    for sig in envelope.get("signals", []):
        t = sig.get("ticker")
        bar = _last_bar(ohlcv.get(t))
        if bar is None:
            continue
        last_close, last_open, sma20, bar_dt = bar.close, bar.open, bar.sma20, bar.date
        as_of = bar_dt if as_of is None or bar_dt > as_of else as_of
        frozen_price = float(sig.get("current_price") or sig.get("close") or last_close)
        is_held = bool(sig.get("bought_date"))

        rec = {
            "ticker": t,
            "kind": "hold" if is_held else "buy",
            "current_price": round(last_close, 2),
            "frozen_price": round(frozen_price, 2),
            "sma20": round(sma20, 2) if pd.notna(sma20) else None,
            "as_of": str(bar_dt.date()),
        }

        if is_held:
            entry = float(sig.get("entry") or 0.0)
            stop = float(sig.get("stop") or 0.0)
            target = float(sig.get("target") or 0.0)
            pnl_pct = round((last_close / entry - 1) * 100, 2) if entry else None
            dist_stop = round((last_close / stop - 1) * 100, 2) if stop else None
            dist_tgt = round((target / last_close - 1) * 100, 2) if last_close and target else None
            stop_breach = bool(stop and last_close <= stop)
            target_hit = bool(target and last_close >= target)
            r_now = _r_multiple(last_close, entry, stop)
            rec.update({
                "entry": round(entry, 2), "stop": round(stop, 2), "target": round(target, 2),
                "pnl_pct": pnl_pct, "dist_to_stop_pct": dist_stop, "dist_to_target_pct": dist_tgt,
                "r_multiple": round(r_now, 2) if r_now is not None else None,
                "stop_breached": stop_breach, "target_reached": target_hit,
                # informational: where next Saturday's ratchet trail would sit if it recomputed now.
                # NOT an active level — the trail only moves at the weekly close.
                "implied_trail_sma20": round(sma20 * (1 - TRAIL_PCT), 2) if pd.notna(sma20) else None,
            })

            # Map the FROZEN 3-tranche exit plan (config P, or whatever LIVE_EXIT the Saturday cron
            # froze onto the card) to its live intra-week status. The monitor is config-agnostic: it
            # reports whatever tranches the card carries, so a P->P2 swap needs no change here.
            plan = sig.get("exit_plan") or {}
            tranches = plan.get("tranches") if isinstance(plan, dict) else None
            tranche_live: list[dict] = []
            plan_tags: list[str] = []
            for tr in (tranches or []):
                st = _tranche_status(tr, bar, entry, stop)
                tranche_live.append(st)
                typ, pct = st["type"], st["pct"]
                if typ == "target":
                    plan_tags.append(f"Sell {pct}% at Rs {tr.get('level')} (+2R) — resting limit"
                                     + (" (REACHED)" if st["hit"] else ""))
                    if st["hit"]:
                        flags.append({"ticker": t, "event": "TRANCHE_TARGET_2R", "severity": "action",
                                      "message": f"{t}: +2R target {tr.get('level')} reached (last {last_close:.2f}) — "
                                                 f"your resting limit to sell {pct}% should fill (intra-week OK)."})
                elif typ == "pattern":
                    plan_tags.append(f"Sell {pct}% on a blow-off/exhaustion WEEKLY close (Sat decides)")
                    if st.get("armed"):
                        flags.append({"ticker": t, "event": "PATTERN_ARMED", "severity": "info",
                                      "message": f"{t}: trading above +{tr.get('arm')}R "
                                                 f"(now {st.get('r_multiple')}R) — a blow-off/exhaustion WEEKLY close "
                                                 f"would sell {pct}%. NOT actionable intra-week; the Saturday recompute decides."
                                                 + (" Possible exhaustion bar today (daily proxy)." if st.get("weak_close_today") else "")})
                elif typ == "runner":
                    plan_tags.append(f"Hold {pct}% runner to the 44w-SMA {tr.get('level')}")
                    if st.get("below_sma"):
                        flags.append({"ticker": t, "event": "RUNNER_BELOW_SMA", "severity": "warn",
                                      "message": f"{t}: closed {last_close:.2f} below its 44w-SMA runner line {tr.get('level')} "
                                                 f"intra-week. NOT actionable — only a FRIDAY WEEKLY close confirms the "
                                                 f"runner exit; the Saturday recompute decides."})
            rec["tranches"] = tranche_live
            rec["plan_tags"] = plan_tags

            # Stop is the risk line (not a profit tranche) — a weekly-close confirmation, flagged here for lead time.
            if stop_breach:
                flags.append({"ticker": t, "event": "STOP_BREACH", "severity": "high",
                              "message": f"{t} closed {last_close:.2f} at/under its stop {stop:.2f} — the weekly close will confirm the exit"})
            elif not tranches and target_hit:
                # Legacy fallback: card with no frozen exit_plan — keep the old single 2R flag.
                flags.append({"ticker": t, "event": "TARGET_2R", "severity": "info",
                              "message": f"{t} reached +2R target {target:.2f} (last {last_close:.2f}) — sell half is due at the weekly close"})
            elif dist_stop is not None and 0 < dist_stop <= NEAR_PCT:
                flags.append({"ticker": t, "event": "NEAR_STOP", "severity": "warn",
                              "message": f"{t} is {dist_stop:.1f}% above its stop {stop:.2f}"})
        else:
            # The band is `buy_zone_low/high` where the cron writes it. `entry_low/high` is the
            # whole SIGNAL WEEK's candle, whose low IS the stop -- reading that as the buy band
            # counts a fill at the stop as a fill inside the zone. Candle stays as the fallback
            # for cards written before the zone fields existed.
            lo = float(sig.get("buy_zone_low") or sig.get("entry_low") or 0.0)
            hi = float(sig.get("buy_zone_high") or sig.get("entry_high") or 0.0)
            bw = sig.get("buy_window_until")
            in_range = bool(lo and hi and lo <= last_open <= hi)
            window_open = bool(bw and str(as_of.date()) <= bw) if as_of else None
            expired = bool(bw and str(as_of.date()) > bw) if as_of else False
            # Did the window EVER fill? `in_range` above only knows about today.
            fill = _window_fill(ohlcv.get(t), signal_date=sig.get("signal_date"),
                                buy_window_until=bw, lo=lo, hi=hi)
            rec.update({
                "entry_low": round(lo, 2), "entry_high": round(hi, 2),
                "buy_window_until": bw, "buy_window_open": window_open,
                "filled_today": in_range, "expired": expired,
                "today_open": round(last_open, 2),
                # The window's memory. `filled_on`/`filled_price` are what the card should say
                # once the trade has triggered; `filled_today` stays for back-compat and means
                # only what its name says.
                "window_filled": fill is not None,
                "filled_on": fill["date"] if fill else None,
                "filled_price": fill["open"] if fill else None,
            })
            if window_open and in_range:
                flags.append({"ticker": t, "event": "FILLED_TODAY", "severity": "action",
                              "message": f"{t} opened {last_open:.2f} inside the band [{lo:.2f}, {hi:.2f}] — buyable at today's open"})
            elif expired and fill:
                flags.append({"ticker": t, "event": "WINDOW_FILLED", "severity": "info",
                              "message": f"{t} filled {fill['date']} at {fill['open']:.2f} — buy window now closed"})
            elif expired:
                flags.append({"ticker": t, "event": "WINDOW_EXPIRED", "severity": "info",
                              "message": f"{t} buy-window closed {bw} with no in-range open — signal expired, no trade"})
        monitors.append(rec)

    # Exits the model has already TAKEN. Emitted as flags so they travel the same path every other
    # event does (reconciliation only raises one for a reader whose ledger still shows the shares),
    # and published whole under `missed_exits` so the surface can show the drift, not just the fact.
    missed_report = build_missed_exits_report(envelope, history or [], ohlcv, today=as_of)
    missed, unpriceable = missed_report["rows"], missed_report["unpriceable"]
    for m in missed:
        flags.append({"ticker": m["ticker"], "event": "MISSED_EXIT", "severity": m["severity"],
                      "message": m["do"]})

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generated_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "as_of": str(as_of.date()) if as_of is not None else None,
        "model": envelope.get("model", "weekly-swing-0094-rank-P"),
        "source": "signals_today_weekly.json",
        "note": ("OBSERVATIONAL re-pricing of the frozen Saturday weekly signals — live current_price + "
                 "intra-week event flags mapped to the frozen exit tranches. Does NOT recompute signals "
                 "or move any frozen level; the paper record is untouched and the weekly decision cadence "
                 "is unchanged. ONLY the +2R target tranche (a resting broker limit) is actionable "
                 "intra-week; the blow-off pattern and the 44w-SMA runner are decided ONLY at the Saturday "
                 "weekly recompute and are flagged here as WATCH-only, never actionable."),
        "n_monitored": len(monitors),
        "n_flags": len(flags),
        "n_actionable": sum(1 for f in flags if f.get("severity") == "action"),
        "monitors": monitors,
        "flags": flags,
        "n_missed_exits": len(missed),
        "missed_exits": missed,
        # Published NEXT TO the count it would otherwise hide inside. `n_missed_exits: 0` means
        # "nobody is off-plan" only when this is also 0; with bars missing it means "we could not
        # look". See build_missed_exits_report.
        "n_missed_unpriceable": len(unpriceable),
        "missed_unpriceable": unpriceable,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="daily observational monitor for the weekly-swing book")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    ap.add_argument("--no-download", action="store_true", help="use the cache as-is (offline/test)")
    args = ap.parse_args(argv)
    sd = Path(args.state_dir)

    env_path = sd / "signals_today_weekly.json"
    if not env_path.exists():
        print(f"no frozen weekly envelope at {env_path} — nothing to monitor (run the weekly cron first)")
        return 0
    envelope = json.loads(env_path.read_text(encoding="utf-8"))
    # The BOOKED record. A trade the model has closed is gone from the envelope, so without this the
    # missed-exit pass could only ever see the current week's un-booked sells — i.e. it would go
    # blind on exactly the positions that have been missed the longest.
    hist_path = sd / "signals_history_weekly.json"
    history: list = []
    if hist_path.exists():
        try:
            loaded = json.loads(hist_path.read_text(encoding="utf-8"))
            history = loaded if isinstance(loaded, list) else loaded.get("signals", [])
        except (ValueError, OSError) as exc:      # a malformed record must not kill the re-pricing
            print(f"could not read {hist_path} ({type(exc).__name__}: {exc}); missed exits limited "
                  f"to this week's issued sells", flush=True)

    tickers = sorted({s.get("ticker") for s in envelope.get("signals", []) if s.get("ticker")}
                     | {h.get("ticker") for h in history if h.get("ticker")})
    if not tickers:
        print("weekly envelope has no signals — nothing to monitor")
        return 0

    ohlcv = _refresh(tickers, not args.no_download)
    monitor = build_monitor(envelope, ohlcv, history=history)

    # DEAD-MAN'S SWITCH (scheduler appendix): the daily monitor is the one job proven to fire every
    # weekday, so it reconstructs every OTHER job's freshness from committed artifacts and folds a
    # consolidated `scheduler_health` block into its output. Defensively wrapped — a health-probe
    # fault must never break the core re-pricing. If the monitor itself dies, this block's
    # checked_utc goes stale and the dead heartbeat is visible from one timestamp.
    try:
        from scheduler_health import scheduler_health
        monitor["scheduler_health"] = scheduler_health(sd)
    except Exception as exc:  # noqa: BLE001
        monitor["scheduler_health"] = {"overall": "ERROR", "error": f"{type(exc).__name__}: {exc}"}

    # OUTPUT CONTRACTS (2026-08-05). scheduler_health proves a job FIRED; this proves it PERSISTED.
    # The gap between the two cost $4.00/week of judge verdicts while every heartbeat stayed green,
    # because `git add` on an ignored path exits 0 and stages nothing. The commit diff is the receipt.
    # Breaches are annotated ::error so they are loud on the very next monitor run.
    try:
        from output_contracts import annotations, check_output_contracts, fold_into_health
        oc = check_output_contracts()
        # The fold lets a contract breach move the TOP-LEVEL overall, not just a nested key: an
        # alarm subsection nobody has to remember to read is half an alarm.
        fold_into_health(monitor["scheduler_health"], oc)
        for line in annotations(oc):
            print(line)
    except Exception as exc:  # noqa: BLE001
        monitor["scheduler_health"]["output_contracts"] = {
            "overall": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
        print(f"::error::output-contract checker failed: {type(exc).__name__}: {exc}")

    (sd / "weekly_monitor.json").write_text(json.dumps(monitor, indent=2, default=str), encoding="utf-8")
    fired = ", ".join(f"{f['event']}:{f['ticker']}" for f in monitor["flags"]) or "none"
    sh = monitor.get("scheduler_health", {})
    overdue = [j["job"] for j in sh.get("jobs", []) if j.get("status") != "OK"]
    print(f"weekly monitor: as-of {monitor['as_of']} | {monitor['n_monitored']} cards re-priced | "
          f"{monitor['n_flags']} flags [{fired}] | {monitor['n_missed_exits']} missed exits "
          f"-> {sd / 'weekly_monitor.json'}")
    # A missed exit we could not price is a reader holding a position nothing on the site mentions.
    # ::warning so it is visible on the run that caused it, not only to whoever opens the JSON.
    for u in monitor.get("missed_unpriceable", []):
        print(f"::warning::missed-exit re-pricing suppressed for {u['ticker']} "
              f"(exit {u['due_date']}): {u['why']}")
    print(f"scheduler health: {sh.get('overall', 'n/a')}"
          + (f" | attention: {', '.join(overdue)}" if overdue else " | all jobs fresh")
          + f" | unscheduled: {', '.join(u['job'] for u in sh.get('unscheduled', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
