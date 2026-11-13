"""Print the trade-management fields for every open model trade and every buy card.

Owner request 2026-11-13: until the This Week page shows them again (PR #181), print after each scan
and each daily monitor run:
- stop hit;
- +2R reached;
- the next exit (move-stop) instruction;
- fill price;
- distance to stop;
- the buy window.

Read-only; stdlib only. Writes a markdown table to stdout, and to $GITHUB_STEP_SUMMARY when set, so it
appears on the Actions run page.

    python scripts/print_trade_status.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _num(v, dp=2):
    return f"{v:,.{dp}f}" if isinstance(v, (int, float)) else "—"


def next_step(card: dict) -> str:
    """Same rule as cardStatus in frontend/src/lib/cards.js: a queued exit first, else the next open tranche."""
    stage = card.get("exit_stage") or {}
    pend = stage.get("pending_exit")
    if pend:
        what = "all remaining shares" if pend.get("kind") == "full" else f"the {pend.get('reason') or 'next'} tranche"
        return f"Sell {what} at the next open ({pend.get('reason')})."
    done = {"target": bool(stage.get("target_booked")), "pattern": bool(stage.get("pattern_booked")),
            "runner": stage.get("runner_open") is False}
    for t in (card.get("exit_plan") or {}).get("tranches", []):
        if not done.get(t.get("type"), False):
            return t.get("do") or ""
    return ""


def render() -> str:
    env = _load("results/signals_today_weekly.json")
    mon = _load("results/weekly_monitor.json")
    by = {m.get("ticker"): m for m in mon.get("monitors", []) if m.get("ticker")}
    cards = env.get("signals", [])
    hold = [c for c in cards if (c.get("status") or "").upper() == "ACTIVE"]
    buy = [c for c in cards if (c.get("status") or "").upper() != "ACTIVE"]
    out = [f"## Trade status — cards as of {env.get('generated_at', '?')}, monitor as of {mon.get('as_of', '?')}", ""]
    out += [f"### Open trades ({len(hold)})", "",
            "| ticker | flags | stop | fill | to stop | to +2R | P&L | R now | held | next exit |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(hold, key=lambda c: (not (by.get(c["ticker"]) or {}).get("stop_breached"), c["ticker"])):
        m = by.get(c["ticker"]) or {}
        flags = [f for f, on in (("**STOP HIT — exit at next open**", m.get("stop_breached")),
                                 ("+2R reached", m.get("target_reached")),
                                 ("near stop", isinstance(m.get("dist_to_stop_pct"), (int, float))
                                  and m["dist_to_stop_pct"] <= 2 and not m.get("stop_breached"))) if on]
        fill = m.get("filled_price") or c.get("fill_price") or c.get("entry_week_open")
        frac = (c.get("exit_stage") or {}).get("fraction_remaining")
        out.append(f"| {c['ticker']} | {', '.join(flags) or '—'} | {_num(c.get('stop'))} | {_num(fill)} | "
                   f"{_num(m.get('dist_to_stop_pct'), 1)}% | {_num(m.get('dist_to_target_pct'), 1)}% | "
                   f"{_num(m.get('pnl_pct'), 1)}% | {_num(m.get('r_multiple'))} | "
                   f"{'—' if frac is None else f'{frac:.0%}'} | {next_step(c)} |")
    out += ["", f"### Buy cards ({len(buy)})", "",
            "| ticker | window state | window closes | stop | do not chase above | window |", "|---|---|---|---|---|---|"]
    for c in sorted(buy, key=lambda c: c["ticker"]):
        m = by.get(c["ticker"]) or {}
        if m.get("window_filled"):
            state = f"filled {m.get('filled_on')} at {_num(m.get('filled_price'))}"
        elif m.get("expired"):
            state = "closed, no fill"
        elif m.get("buy_window_open") and m.get("filled_today") is False:
            state = "no open inside the band yet"
        else:
            state = "—"
        out.append(f"| {c['ticker']} | {state} | {c.get('buy_window_until') or m.get('buy_window_until') or '—'} | "
                   f"{_num(c.get('stop'))} | {_num(c.get('no_chase_above'))} | {c.get('buy_window') or '—'} |")
    return "\n".join(out) + "\n"


def main() -> int:
    text = render()
    sys.stdout.write(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
