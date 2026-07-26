"""Thing (1) from the trade-planner boards: a structured per-signal DECISION MEMO — the operating-layer
artifact the forward plan (Tier-3) called for. Turns each weekly signal into an auditable
setup/strength/risk/plan/status record with an APPROVED / WATCHLIST / REJECTED stamp, so the owner's
manual call is logged against a fixed rubric (fights the execution-decay we measured). Pure + reporting
only — it does NOT touch the engine, cfg, or any backtest number.

    python scripts/gen_decision_memo.py            # memos for the current live signals
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import RESULTS_DIR  # noqa: E402

SIGNALS = RESULTS_DIR / "signals_today_weekly.json"
GRADE_STARS = {"A": 4, "B": 3, "C": 2}


def build_memo(sig: dict, ctx: dict | None = None) -> dict:
    """Pure: one signal (+ optional market ctx) -> a Decision Memo dict. No I/O, no engine."""
    ctx = ctx or {}
    entry = float(sig.get("entry") or 0.0)
    stop = float(sig.get("stop") or 0.0)
    target = float(sig.get("target") or 0.0)
    risk = entry - stop
    reward = target - entry
    rr = round(reward / risk, 2) if risk > 0 else None
    e2s = round((entry / stop - 1) * 100, 1) if stop > 0 else None   # entry-to-stop width %
    grade = str(sig.get("grade", "")).upper()
    stars = GRADE_STARS.get(grade, 2)
    # risk rating from the stop WIDTH (our real tail: wide stops on extended fills = the -15-23% blow-ups)
    risk_rating = ("MODERATE" if (e2s is not None and e2s <= 8)
                   else "MODERATE-HIGH" if (e2s is not None and e2s <= 12) else "HIGH")
    status_raw = str(sig.get("status", "")).upper()
    # decision: A-grade & still actionable -> APPROVED; closed/expired -> REJECTED; else WATCHLIST
    if status_raw in ("CLOSED", "EXPIRED", "BUY_CLOSED", "STOPPED"):
        decision, do = "REJECTED", "Do not trade — window closed / invalidated."
    elif grade == "A" and status_raw in ("ACTIVE", "FRESH", "BUY", "OPEN", ""):
        decision, do = "APPROVED", (f"Execute — buy in the band [{sig.get('entry_low')}, "
                                    f"{sig.get('entry_high')}]; fund strongest CRS rank first.")
    else:
        decision, do = "WATCHLIST", "Monitor — below the A-grade / actionable bar; do not fund yet."
    return {
        "id": f"{sig.get('ticker')}__{sig.get('signal_date')}",
        "ticker": sig.get("ticker"), "date": sig.get("signal_date"),
        "setup": {"direction": "LONG", "pattern": sig.get("pattern"),
                  "trend_alignment": ctx.get("regime", "n/a"), "timeframe": "weekly (44w SMA)"},
        "strength": {"confidence": "*" * stars + "." * (5 - stars), "grade": grade,
                     "crs_rank": sig.get("crs_rank")},
        "risk": {"rating": risk_rating, "stop_width_pct": e2s, "rr_ratio": rr,
                 "max_loss_within_plan": rr is not None},
        "plan": {"entry_band": [sig.get("entry_low"), sig.get("entry_high")], "entry_ref": entry,
                 "stop": stop, "target": target, "exit_plan": sig.get("exit_plan")},
        "status": decision, "do": do,
    }


def render_md(m: dict) -> str:
    r, s, p = m["risk"], m["strength"], m["plan"]
    mark = {"APPROVED": "[OK]", "WATCHLIST": "[WATCH]", "REJECTED": "[SKIP]"}.get(m["status"], "?")
    return (
        f"### DECISION MEMO — {m['ticker']}  ({m['id']})\n"
        f"1. **Setup** — {m['setup']['direction']} · {m['setup']['pattern']} · "
        f"trend {m['setup']['trend_alignment']} · {m['setup']['timeframe']}\n"
        f"2. **Signal strength** — {s['confidence']}  (grade {s['grade']}, CRS rank {s['crs_rank']})\n"
        f"3. **Risk** — {r['rating']} · stop width {r['stop_width_pct']}% · R:R 1:{r['rr_ratio']} · "
        f"max-loss-in-plan {'YES' if r['max_loss_within_plan'] else 'NO'}\n"
        f"4. **Trade plan** — entry {p['entry_ref']} (band {p['entry_band']}) · SL {p['stop']} · TP {p['target']}\n"
        f"5. **Status** — {mark} **{m['status']}** — {m['do']}\n"
    )


def main() -> int:
    d = json.loads(SIGNALS.read_text())
    _rg = d.get("regime")
    ctx = {"regime": _rg.get("status") if isinstance(_rg, dict) else _rg}
    sigs = d.get("signals") or []
    if isinstance(sigs, dict):
        sigs = [v for v in sigs.values() if isinstance(v, dict)]
    print(f"# Weekly Decision Memos — {d.get('generated_at','')} | regime {ctx['regime']} | "
          f"{len(sigs)} signals\n")
    tally = {}
    for sig in sigs:
        if not isinstance(sig, dict) or "entry" not in sig:
            continue
        m = build_memo(sig, ctx)
        tally[m["status"]] = tally.get(m["status"], 0) + 1
        print(render_md(m))
    print(f"\n**Summary:** " + " · ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
