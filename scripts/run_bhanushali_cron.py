"""Live / paper runner for the 0091 weekly-swing book (FORWARD-WATCH).

Self-sufficient: refreshes the live OHLCV cache itself, then re-runs the tested 0091 engine
(run_bhanushali_weekly_sma.prep_weekly_sma + run_bhanushali_weekly_full.backtest, finding 0034) from a
fixed inception, and serializes the CURRENT state to the dashboard envelope (results/*_weekly.json/.csv).
Live == backtest by construction: the same deterministic, PIT-clean engine that produced the +18.2% CAGR /
+0.87 Sharpe backtest generates the live signals — no re-implementation.

CADENCE — a weekly-swing book only changes after Friday's weekly close, so this runs on its OWN schedule:
**every Saturday 6 PM IST** (.github/workflows/cron-bhanushali-scanner.yml). Saturday's download picks up the
just-closed Friday bar; the signals it computes are actionable the following Mon/Tue (buy in the band).
Idempotent — recomputed from inception each run (see the known mutable-record caveat, finding-0035 TODO).

MODELED FILLS — the book models entries at the in-range open; live you place a limit order inside the
band. Forward-watch record, NOT a live broker ledger. Clean forward inception (owner choice): default
--start = go-live date, so the book only reflects trades from inception forward; empty until fresh
post-inception bars exist (valid, not an error).

    python scripts/run_bhanushali_cron.py --start 2026-07-04            # cron (downloads)
    python scripts/run_bhanushali_cron.py --start 2025-01-01 --no-download  # local/offline test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import RESULTS_DIR  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
import run_bhanushali_weekly_crs as CRS  # noqa: E402  (Nifty-50 CSV path + index plumbing)
import run_bhanushali_weekly_rank as R94  # noqa: E402  — LIVE strategy: 0093-N50 + ranked fill (finding 0038)

INCEPTION_DEFAULT = "2026-07-04"
TARGET_R = 2                     # 0091 books half at +2R -> the displayed target
HOLD_DAYS_DISPLAY = 65          # soft "hold ~N days" card hint only. The P2 exit is TREND-FOLLOWING (no hard
                                # cap; 52-week backstop) so actual holds vary widely — this is a nominal guide.
# LIVE EXIT (2026-07-15 owner decision — Phase-2 exit; see docs/decisions ADR + config_CHANGELOG). Replaces the
# 13-week time cap with a no-cap hold + a blow-off-bar exit @2.5R (+ a 20-week-close backstop). Owner-override of
# the forward-wall route (ships a portfolio Sharpe/CAGR give for -8pp drawdown + fewer/higher-return trades). The
# backtest() DEFAULTS are left OFF so the frozen 0094 research run stays byte-identical (1.132/255).
P2_EXIT = dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)
# LIVE DISCIPLINE (2026-07-16 owner decision — see docs/decisions/0009 + config_CHANGELOG +
# research/substrate/FINDING_owner_discipline.md). Owner-OVERRIDE on RISK APPETITE, not an edge claim:
# the owner pre-accepted a return cost ("i dont care even if it gave good returns, then our book is badly
# traded ... max 20 percent is fine, if more than 10 percent then our R is distorted").
#   ext_cap 0.20         skip any fill priced >20% above the signal-week 44w SMA (pure SELECTION; the
#                        stop is untouched — this is the rule-faithful half).
#   max_risk_pct 0.10    stop = max(signal-week low, entry x 0.90). NOTE this LIFTS the stop off the
#                        candle low when the low is further, which DEVIATES from the taught rule by
#                        explicit owner instruction.
#   max_notional_pct 0.20  no name exceeds 20% of sizing equity. A GUARDRAIL against runaway single-name
#                        risk — NOT a performance lever: FINDING_more_slots showed concentration is
#                        load-bearing (4-5 names 1.21 > 7 names 0.97 > 10 names 0.81 on the 22-26 slice).
# Measured on the A-ONLY book that actually trades (parity-checked against the recorded 1.004/171):
#   Sharpe 1.004->1.055, CAGR 20.9->20.2%, MaxDD -36.4->-31.2% (+5.2pp), median R 13.7->9.1%,
#   mean hold 19.1->12.4wk, win 54->51%, 2022-26 slice 1.17->1.04 (the one negative).
# Return-neutral, NOT certified: no DSR gate passes a +0.05 in-sample delta at cumulative trial 122.
# backtest() DEFAULTS stay OFF so the frozen 0094 research run is byte-identical (1.132/255).
LIVE_DISCIPLINE = dict(ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20)
# LIVE EXIT = config P (2026-07-16 owner decision — see docs/decisions/0010 + config_CHANGELOG +
# research/substrate/FINDING_pattern_exit.md). A THREE-TRANCHE scaled exit that REPLACES the P2 trend exit:
#   40% booked at +2R (resting limit, intraweek)
#   40% booked on the BLOW-OFF exhaustion pattern (a new-high week closing in its lower third, armed at
#       +2.5R MFE — the one validated 'pattern' exit; the zoo entry detectors are IC~0, finding 0079)
#   20% runner held until a weekly close below the 44-week SMA
# Owner-OVERRIDE (like the P2 exit + discipline adoptions): P maximises the fat tail (in-sample CAGR 27.2%,
# maxR 40.8R) but FAILS the 2022-26 gate (0.91) and runs a -39.5% DD; adopted on owner call, sole
# capital-at-risk. backtest() DEFAULTS stay OFF so the frozen 0094 research run is byte-identical (1.132/255).
P_EXIT = dict(scaled_exit=dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0,
                               pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0))

# ── THE LIVE EXIT — the single swap point (Stage-1 config-swappable interface) ──────────────
# Build the product against THIS object + the card schema in `_exit_plan` below, NOT against
# config P's specific numbers. To change the live book's exit, change ONLY `LIVE_EXIT`: the two
# backtest() calls and the card `exit_plan` both read it, so nothing downstream hard-codes P.
# Currently config P (docs/decisions/0010). To revert to the P2 trend exit: `LIVE_EXIT = P2_EXIT`
# (which has no `scaled_exit` key, so `_exit_plan` falls to its non-scaled branch automatically).
LIVE_EXIT = P_EXIT
# closed-trade exit reason -> the status vocabulary the frontend/history views already understand.
# Scaled-exit (config P) reasons: targets / sma_break / stop / stop_part / pattern / eos.
_STATUS = {"target3": "HIT_TARGET", "targets": "HIT_TARGET", "trail": "HIT_STOP", "stop": "HIT_STOP",
           "stop_half": "HIT_STOP", "stop_part": "HIT_STOP", "sma_break": "HIT_STOP", "pattern": "HIT_TARGET",
           "wk20": "HIT_STOP", "wk20_half": "HIT_STOP", "blowoff": "HIT_STOP", "blowoff_half": "HIT_STOP",
           "time": "EXPIRED", "eos": "EXPIRED"}


def _exit_plan(entry, stop, sma44, exit_cfg=None):
    """The card exit plan — the stable, config-AGNOSTIC interface the UI renders. Tranches are
    DERIVED from `exit_cfg` (defaults to LIVE_EXIT), so swapping the live config changes the card
    automatically; nothing hard-codes config P's numbers.

    SCHEMA (stable):
        { "entry_pattern": str,
          "tranches": [ { "pct": int, "type": "target"|"pattern"|"runner",
                          "level": float|None,   # a price (target/runner)
                          "arm": float,           # pattern-arm price (pattern only)
                          "do": str } ] }

    entry/stop define R; sma44 is the current 44-week SMA (the runner's exit reference)."""
    cfg = (exit_cfg if exit_cfg is not None else LIVE_EXIT).get("scaled_exit")
    r = entry - stop
    smaok = sma44 == sma44                                  # not NaN

    # Non-scaled (trend) exit, e.g. the P2 revert: half at 2R, then trail the rest.
    if not cfg:
        tp = round(entry + 2.0 * r, 2)
        return {"entry_pattern": "44-week SMA pullback", "tranches": [
            {"pct": 50, "type": "target", "level": tp,
             "do": f"Sell half at Rs {tp:,.2f} (the +2R target) — a resting limit order."},
            {"pct": 50, "type": "runner", "level": round(float(sma44), 2) if smaok else None,
             "do": ("Hold the rest as a trend runner; exit on a blow-off/exhaustion week or a weekly "
                    "close below the 20-week trail.")},
        ]}

    tranches = []
    tp1_frac = int(round(cfg.get("tp1_frac", 0) * 100))
    if tp1_frac:
        lvl = round(entry + cfg["tp1_r"] * r, 2)
        tranches.append({"pct": tp1_frac, "type": "target", "level": lvl,
                         "do": f"Sell {tp1_frac}% at Rs {lvl:,.2f} (the +{cfg['tp1_r']:g}R target) — a resting limit order."})
    tp2_frac = int(round(cfg.get("tp2_frac", 0) * 100))
    if tp2_frac:
        lvl = round(entry + cfg["tp2_r"] * r, 2)
        tranches.append({"pct": tp2_frac, "type": "target", "level": lvl,
                         "do": f"Sell {tp2_frac}% at Rs {lvl:,.2f} (the +{cfg['tp2_r']:g}R target)."})
    pat_frac = int(round(cfg.get("pattern_frac", 0) * 100))
    if pat_frac:
        arm_r = cfg.get("pattern_arm_r", 2.5)
        arm = round(entry + arm_r * r, 2)
        tranches.append({"pct": pat_frac, "type": "pattern", "arm": arm,
                         "do": (f"Sell {pat_frac}% on a blow-off/exhaustion week (a new high that CLOSES in the lower "
                                f"third of its range) once price has reached Rs {arm:,.2f} (+{arm_r:g}R). The Saturday scan flags it.")})
    runner = 100 - sum(t["pct"] for t in tranches)
    if runner > 0:
        buf = cfg.get("runner_sma_buffer", 0.0)
        lvl = round(float(sma44) * (1 - buf), 2) if smaok else None
        below = f" ({int(round(buf * 100))}% below)" if buf else ""
        if smaok:
            do = (f"Hold the last {runner}% as a runner. Exit only on a weekly CLOSE below the 44-week SMA{below} "
                  f"(now ~Rs {sma44:,.2f})." if not buf else
                  f"Hold the last {runner}% as a runner. Exit only on a weekly CLOSE more than {int(round(buf*100))}% "
                  f"below the 44-week SMA (~Rs {lvl:,.2f}).")
        else:
            do = f"Hold the last {runner}% as a runner; exit on a weekly close below the 44-week SMA."
        tranches.append({"pct": runner, "type": "runner", "level": lvl, "do": do})
    return {"entry_pattern": "44-week SMA pullback", "tranches": tranches}


def _sma44_now(P, t):
    """The most recent 44-week SMA for ticker t (the runner's exit reference)."""
    wa = P[t].get("wsma_at") or {}
    vals = [v for v in wa.values() if v == v]
    return vals[-1] if vals else float("nan")


def _last(P, t, key):
    arr = P[t][key]
    return arr[-1]


def _compute_regime(P, mem, as_of):
    """Market breadth + 10-bar strength across the CURRENT index universe.

    Real and PIT-safe: uses only each name's close series up to `as_of` (no
    look-ahead). Breadth = advancers − decliners on the latest bar. Strength =
    % of names trading above their trailing 10-bar mean (0–100). Status is a
    simple BULL/BEAR/CHOPPY read off the two. VIX stays 0 here — the dashboard
    overlays the live INDIA VIX quote (the universe cache carries no VIX bar).
    """
    from nq.data.membership import ticker_in_index_on
    d = pd.Timestamp(as_of).date()
    adv = dec = above = total = 0
    for t, s in P.items():
        c = s.get("c")
        if c is None or len(c) < 11:
            continue
        if mem is not None and not ticker_in_index_on(t, d, mem):
            continue
        try:
            last = float(c[-1]); prev = float(c[-2])
            win = [float(x) for x in c[-10:]]
            sma10 = sum(win) / len(win)
        except (TypeError, ValueError, IndexError):
            continue
        total += 1
        if last > prev:
            adv += 1
        elif last < prev:
            dec += 1
        if last > sma10:
            above += 1
    if not total:
        return {"status": "UNKNOWN", "strength": 0, "vix": 0, "breadth": 0}
    breadth = adv - dec
    strength = round(100.0 * above / total)
    if strength >= 60 and breadth > 0:
        status = "BULL"
    elif strength <= 40 and breadth < 0:
        status = "BEAR"
    else:
        status = "CHOPPY"
    return {"status": status, "strength": int(strength), "vix": 0, "breadth": int(breadth)}


def build_envelopes(P, out, ledger, out_paper, generated_at, mem=None):
    """Map the live state to the dashboard envelope.

    `out` / `ledger` = the UNCAPPED signal ledger (every signal tracked) — drives the OPEN buy cards,
    the HOLD/EXIT cards, and the completed history. `out_paper` = the ₹10L paper book, used ONLY for
    the NAV/equity portfolio. Buy-signals come from the latest completed week (P[t]['last_signal']),
    minus any name already being followed as a HOLD/EXIT card.
    """
    from nq.data.membership import ticker_in_index_on
    signals = []
    for t, s in P.items():
        ls = s.get("last_signal")
        if not ls:
            continue
        fri = pd.Timestamp(s["dates"][ls["fri_idx"]])
        if mem is not None and not ticker_in_index_on(t, fri.date(), mem):
            continue                                           # only currently-listed index members
        lo, hi = ls["lo"], ls["hi"]
        cur = float(_last(P, t, "c"))
        entry = round(cur if lo < cur < hi else (lo + hi) / 2.0, 2)   # buy inside the band
        stop = round(lo, 2)
        if entry <= stop:
            continue
        signals.append({
            "ticker": t, "entry": entry, "stop": stop,
            "target": round(entry + TARGET_R * (entry - stop), 2),
            "entry_low": round(lo, 2), "entry_high": round(hi, 2),
            "current_price": round(cur, 2), "close": round(cur, 2),
            "signal_date": str(fri.date()),                    # the just-closed setup week (stable)
            # Entry window is the FULL trading week AFTER the setup Friday (buy Mon–Fri). The
            # dashboard/backend reads buy_window_until to keep the signal actionable all week —
            # WITHOUT it the backend falls back to the momentum 2-calendar-day rule and wrongly
            # flags a Friday signal BUY_CLOSED by Monday. fri is always a Friday, so +7d = next Fri.
            "buy_window_until": str((fri + pd.Timedelta(days=7)).date()),
            "hold_days": HOLD_DAYS_DISPLAY,
            # CRS-rank fill priority (finding 0038): fund strongest-first. A-grade = top 5 by rank.
            "crs_rank": round(float(ls.get("rank", 0.0)), 4),
            "grade": "B", "tier": "signal", "status": "FRESH",
            "buy_window": "buy Mon–Fri this week, at the open inside the band [low, high] — fund strongest CRS rank first",
            # config-P surfacing: the entry pattern + the full 3-tranche exit plan with price levels.
            "pattern": "44-week SMA pullback",
            "exit_plan": _exit_plan(entry, stop, _sma44_now(P, t)),
        })
    # strongest-first on the page; top-5 flagged A so the grade filter surfaces the priority names
    signals.sort(key=lambda x: -x["crs_rank"])
    for j, sg in enumerate(signals):
        sg["grade"] = "A" if j < 5 else "B"
    # Grade-A only (owner rule): drop Grade-B buy cards entirely — only the top-5-CRS names show.
    signals = [s for s in signals if s["grade"] == "A"]
    # A name FOLLOWED as a hold from a PRIOR week must not also show as a fresh buy. But a name that
    # only just ENTERED this (still-incomplete) week is inside its buy window — keep it as a BUY card
    # (with its range), NOT a HOLD (fault 2026-07-13: a mid-week/Monday-data run showed every name as
    # HOLD with no buy range, because the uncapped tracking book had 'entered' the week's signals).
    gen = pd.Timestamp(generated_at)
    cur_week_open = gen.weekday() < 4                          # data ends Mon-Thu => this week not yet closed
    cur_week_start = (gen - pd.Timedelta(days=int(gen.weekday()))).normalize()   # Monday of gen's week

    def _entered_this_week(p):
        ed = p.get("rec", {}).get("entry_date")
        return cur_week_open and ed is not None and pd.Timestamp(ed) >= cur_week_start

    held_prior = {t: p for t, p in out["open_positions"].items() if not _entered_this_week(p)}
    signals = [s for s in signals if s["ticker"] not in set(held_prior)]

    # ── held positions (entered in a PRIOR week) -> HOLDING cards ("Bought on <date>"), or SELL cards
    # when the weekly close decided an exit (pending -> executes Monday open). The Saturday run tells
    # the owner exactly which held signals to SELL on Monday, on the same card the buy came from. ──
    for t, p in held_prior.items():
        s = P[t]
        cur = float(_last(P, t, "c"))
        entry = float(p["en"])
        stop = float(p["trail"] if p["half_done"] else p["stop"])
        bought = str(p["rec"]["entry_date"])[:10] if "rec" in p else None
        rec = {
            "ticker": t, "entry": round(entry, 2), "stop": round(stop, 2),
            "target": round(float(p["tp2"]), 2), "current_price": round(cur, 2),
            "close": round(cur, 2), "signal_date": bought, "bought_date": bought,
            "qty": round(float(p["sh"]), 2), "fill_price": round(entry, 2),
            "nq_position_id": f"{t}__{bought}",              # -> frontend 'holding' action
            "grade": "A",   # only Grade-A signals are ever entered now, so every hold is A
            "hold_days": HOLD_DAYS_DISPLAY,
            "tier": "signal", "status": "ACTIVE",
            # config-P surfacing: the exit plan + which tranches have already booked (exit_stage).
            "pattern": "44-week SMA pullback",
            "exit_plan": _exit_plan(entry, float(p["stop"]), _sma44_now(P, t)),
            "exit_stage": {
                "target_40_booked": bool(p.get("t1_done")),   # 40% @ +2R
                "pattern_40_booked": bool(p.get("pt_done")),  # 40% on the blow-off pattern
                "runner_20_open": round(float(p.get("frac_left", 1.0)), 2) > 0.01,
                "fraction_remaining": round(float(p.get("frac_left", 1.0)), 2),
            },
        }
        if p["pending"] is not None:                          # Friday close said EXIT -> act Monday open
            act, reason = p["pending"]
            rec["actionability"] = "EXIT_REQUIRED"
            if act == "part" and reason == "pattern":         # blow-off exhaustion -> book the 40% pattern tranche
                rec["status"] = "HIT_TARGET"
                rec["why"] = ("Blow-off/exhaustion week detected — SELL the 40% pattern tranche at Monday's "
                              "open. Keep the 20% runner until a weekly close below the 44-week SMA.")
            elif reason.startswith("stop"):
                rec["status"] = "HIT_STOP"
                rec["why"] = "Weekly close below the stop — SELL the remaining position at Monday's open."
            elif reason == "sma_break":
                rec["status"] = "HIT_STOP"
                rec["why"] = ("Weekly close below the 44-week SMA — the runner's trend has broken. SELL the "
                              "remaining position at Monday's open.")
            else:
                rec["status"] = "ACTIVE"
                rec["why"] = f"Weekly close triggered an exit ({reason}) — SELL the remaining position at Monday's open."
        signals.append(rec)

    # ── held positions ──
    positions = {}
    hist_active = []
    for t, p in out["open_positions"].items():
        cur = float(_last(P, t, "c"))
        entry = float(p["en"])
        stop = float(p["trail"] if p["half_done"] else p["stop"])
        shares = float(p["sh"])
        ed = str(p["rec"]["entry_date"])[:10] if "rec" in p else None
        pct = round((cur / entry - 1) * 100, 2) if entry else 0.0
        days = int(p["weeks"] * 5)
        positions[t] = {
            "entry_date": ed, "entry_price": round(entry, 2), "shares": round(shares, 2),
            "position_size": round(shares * entry, 2), "atr_stop": round(stop, 2),
            "target": round(float(p["tp2"]), 2), "current_price": round(cur, 2),
            "current_value": round(shares * cur, 2), "unrealised_pnl": round(shares * (cur - entry), 2),
            "unrealised_pnl_pct": pct, "days_held": days,
        }
        hist_active.append({
            "ticker": t, "signal_date": ed, "status": "ACTIVE", "entry": round(entry, 2),
            "stop": round(stop, 2), "target": round(float(p["tp2"]), 2), "current_price": round(cur, 2),
            "close_price": round(cur, 2), "pnl_pct": pct, "return_pct": pct,
            "days_since": days, "hold_days": days,
        })

    # ── closed trades -> history + analytics ──
    led = pd.DataFrame(ledger)
    hist_closed = []
    for _, r in led.iterrows():
        entry = float(r["entry"]); exitpx = float(r["exit_px"])
        ret_pct = round((exitpx / entry - 1) * 100, 2) if entry else 0.0
        hist_closed.append({
            "ticker": r["tkr"], "signal_date": str(r["entry_date"])[:10],
            "status": _STATUS.get(str(r["reason"]).replace("_half", ""), "EXPIRED"),
            "entry": round(entry, 2), "close_price": round(exitpx, 2),
            "close_date": str(r["exit_date"])[:10], "return_pct": ret_pct, "pnl_pct": ret_pct,
            "r_multiple": round(float(r["R"]), 2), "net_pnl": round(float(r["net_pnl"]), 2),
            "days_since": int(r["held_weeks"] * 5), "hold_days": int(r["held_weeks"] * 5),
            "exit_reason": str(r["reason"]),
        })
    sig_hist = hist_closed + hist_active
    n_closed = len(led)
    wins = int((led["R"] > 0).sum()) if n_closed else 0
    analytics = {
        "total_signals": len(sig_hist), "total_closed": n_closed, "active": len(positions),
        "win_rate": round(wins / n_closed * 100, 1) if n_closed else None,
        "avg_return_pct": round(float(pd.Series([h["return_pct"] for h in hist_closed]).mean()), 2) if n_closed else None,
        "avg_r": round(float(led["R"].mean()), 2) if n_closed else None,
    }

    # ── portfolio + NAV curve — the ₹10L PAPER book (kept for the owner's reference), NOT the
    #    uncapped ledger. Its positions are only the capital-constrained subset ₹10L could fund. ──
    paper_positions = {}
    for t, p in out_paper["open_positions"].items():
        cur = float(_last(P, t, "c")); entry = float(p["en"])
        stop = float(p["trail"] if p["half_done"] else p["stop"]); shares = float(p["sh"])
        ed = str(p["rec"]["entry_date"])[:10] if "rec" in p else None
        pct = round((cur / entry - 1) * 100, 2) if entry else 0.0
        paper_positions[t] = {
            "entry_date": ed, "entry_price": round(entry, 2), "shares": round(shares, 2),
            "position_size": round(shares * entry, 2), "atr_stop": round(stop, 2),
            "target": round(float(p["tp2"]), 2), "current_price": round(cur, 2),
            "current_value": round(shares * cur, 2), "unrealised_pnl": round(shares * (cur - entry), 2),
            "unrealised_pnl_pct": pct, "days_held": int(p["weeks"] * 5),
        }
    curve = out_paper["curve"]
    nav = float(out_paper["equity"])
    peak = float(curve.cummax().iloc[-1]) if len(curve) else nav
    portfolio = {"cash": round(float(out_paper["cash"]), 2), "peak_value": round(peak, 2),
                 "total_value": round(nav, 2), "n_positions": len(paper_positions),
                 "total_trades": n_closed, "positions": paper_positions}
    hist_df = (curve.rename("total_value").rename_axis("date").reset_index()
               if len(curve) else pd.DataFrame({"date": [], "total_value": []}))

    envelope = {
        "generated_at": generated_at, "model": "weekly-swing-0094-rank-P", "signals": signals,
        "regime": _compute_regime(P, mem, generated_at),
        "n_positions": len(positions), "cash": round(float(out_paper["cash"]), 2),
        "note": "forward-watch, modeled fills — 0094 weekly swing (0093-N50 signals, CRS-ranked fills; UNDERPOWERED DSR 0.89, not certified)",
    }
    return envelope, sig_hist, analytics, portfolio, hist_df


def _refresh_ohlcv(start: str, history_days: int, do_download: bool) -> dict:
    """Return the LIVE OHLCV cache, refreshed with recent bars unless --no-download.

    Self-sufficient so the weekly book can run in its OWN Saturday workflow (no momentum
    step to download first). Mirrors run_paper_cron's incremental logic: cold cache -> full
    history from (inception - history_days); warm cache -> last 15 days merged. Saturday runs
    pick up the just-closed Friday bar (NSE shut Sat, so yfinance returns through Friday).
    """
    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    if not do_download:
        return ohlcv
    from datetime import date, timedelta
    from nq.data.ohlcv import download_ohlcv, merge_ohlcv, save_ohlcv_cache
    from run_cpcv import build_universe
    universe = build_universe("current")
    hist_start = (pd.to_datetime(start) - pd.Timedelta(days=history_days)).date().isoformat()
    dl_start = hist_start if not ohlcv else (date.today() - timedelta(days=15)).isoformat()
    print(f"downloading OHLCV {dl_start}.. for {len(universe)} names ...", flush=True)
    try:
        fresh = download_ohlcv(universe, start=dl_start, end=date.today().isoformat())
        ohlcv = merge_ohlcv(ohlcv, fresh) if ohlcv else fresh
        save_ohlcv_cache(ohlcv, OHLCV_CACHE)
    except Exception as exc:  # noqa: BLE001 — a download hiccup must not lose the existing cache/book
        print(f"download failed ({type(exc).__name__}: {exc}); using cached bars", flush=True)
    return ohlcv


def _refresh_nifty50(do_download: bool) -> None:
    """Refresh the pinned Nifty-50 CSV (the CRS denominator) with recent bars. Non-fatal — a fetch
    hiccup falls back to the committed series so the book still runs."""
    if not do_download:
        return
    from datetime import date
    try:
        import yfinance as yf
        csv = CRS.NIFTY50_CSV
        existing = pd.read_csv(csv, parse_dates=["date"]) if Path(csv).exists() else pd.DataFrame(columns=["date", "nifty50_close"])
        d = yf.download("^NSEI", start="2015-01-01", end=date.today().isoformat(), progress=False, auto_adjust=False)
        close = d["Close"]; close = close.iloc[:, 0] if hasattr(close, "columns") else close
        fresh = pd.DataFrame({"date": pd.to_datetime(close.index).tz_localize(None),
                              "nifty50_close": close.values}).dropna()
        merged = pd.concat([existing, fresh]).drop_duplicates("date", keep="last").sort_values("date")
        merged.to_csv(csv, index=False)
        print(f"nifty-50 refreshed -> {merged['date'].max().date()} ({len(merged)} rows)", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"nifty-50 refresh failed ({type(exc).__name__}: {exc}); using committed CSV", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="weekly-swing (0093 + Nifty-50 CRS) forward-watch paper runner")
    ap.add_argument("--start", default=INCEPTION_DEFAULT, help="inception (clean forward start) YYYY-MM-DD")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    ap.add_argument("--no-download", action="store_true", help="use the cache as-is (test/offline)")
    ap.add_argument("--history-days", type=int, default=520, help="calendar days of history before inception for the 44-week-SMA warmup")
    args = ap.parse_args(argv)
    sd = Path(args.state_dir); sd.mkdir(parents=True, exist_ok=True)

    # LIVE data = data/ohlcv.pkl (self-refreshed here). NOT corrected_universe(): the backfill/alias
    # delisted names are a backtest-only survivorship tool, are not committed to the repo (would crash
    # the cron), and a forward book only ever trades currently-listed names. Empty -> valid empty book.
    ohlcv = _refresh_ohlcv(args.start, args.history_days, not args.no_download)
    _refresh_nifty50(not args.no_download)               # CRS denominator (finding 0037)
    mem = load_membership()
    # LIVE strategy = 0093 + Nifty-50 with CRS-ranked fills (finding 0038; supersedes arbitrary fill).
    P = R94.prep_weekly_rank(ohlcv)
    # Grade-A only: trade the TOP-5-by-CRS signals of each week. Owner rule — never surface or buy
    # Grade B; there are always enough strong A names.
    a_set = R94.grade_a_entries(P)
    # ── ₹10L paper book — realistic capital sim (A-only), kept for the NAV/equity portfolio.
    led_paper: list = []
    out_paper = R94.backtest(P, mem, ledger=led_paper, start=args.start, return_state=True, a_grade=a_set,
                             **LIVE_DISCIPLINE, **LIVE_EXIT)
    # ── UNCAPPED signal ledger — every A signal tracked (cash never runs out), so a name is followed
    #    week to week regardless of what ₹10L could afford. This drives the SIGNALS page.
    led_all: list = []
    out_all = R94.backtest(P, mem, ledger=led_all, start=args.start, return_state=True, uncapped=True,
                           a_grade=a_set, **LIVE_DISCIPLINE, **LIVE_EXIT)
    # data's last date = the "as of" the book is current to
    last = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=pd.Timestamp(args.start))
    generated_at = str(last.date())

    envelope, sig_hist, analytics, portfolio, hist_df = build_envelopes(
        P, out_all, led_all, out_paper, generated_at, mem)

    (sd / "signals_today_weekly.json").write_text(json.dumps(envelope, indent=2, default=str), encoding="utf-8")
    (sd / "signals_history_weekly.json").write_text(json.dumps(sig_hist, indent=2, default=str), encoding="utf-8")
    (sd / "signal_analytics_weekly.json").write_text(json.dumps(analytics, indent=2, default=str), encoding="utf-8")
    (sd / "paper_portfolio_weekly.json").write_text(json.dumps(portfolio, indent=2, default=str), encoding="utf-8")
    hist_df.to_csv(sd / "portfolio_history_weekly.csv", index=False)

    print(f"weekly cron: inception {args.start} | as-of {generated_at} | "
          f"{sum(1 for s in envelope['signals'] if s.get('tier') == 'signal' and not s.get('bought_date')):>3} open | "
          f"tracked-held {len(out_all['open_positions']):>3} | completed {analytics['total_closed']:>3} | "
          f"paper NAV {portfolio['total_value']:,.0f} -> {sd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
