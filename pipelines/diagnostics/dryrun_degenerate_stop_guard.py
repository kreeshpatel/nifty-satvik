"""Dry run of the latest scan WITH and WITHOUT the degenerate-stop guard, comparing every published payload.

Owner condition for wiring the guard (2026-11-17): the scan's published files must be IDENTICAL with the guard on
and off, on the latest data. This builds both and diffs them byte for byte.

It runs the live scan's own code path -- the same cache, the same engine calls, the same build_envelopes -- and
differs from `scripts/run_bhanushali_cron.py --no-download` only in that it writes nothing to results/ and skips
the post-publish bookkeeping. The guard is turned off by setting the module's MIN_STOP_DISTANCE to 0.0, which is
exactly the pre-amendment predicate (`entry <= stop`).

    python pipelines/diagnostics/dryrun_degenerate_stop_guard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import run_bhanushali_cron as C  # noqa: E402

PAYLOADS = ("signals_today_weekly", "signals_history_weekly", "signal_analytics_weekly", "paper_portfolio_weekly",
            "portfolio_history_weekly")


def build() -> dict[str, str]:
    """Everything build_envelopes publishes, serialised exactly as the scan serialises it."""
    import run_bhanushali_weekly_rank as R94
    ohlcv = C._refresh_ohlcv(C.INCEPTION_DEFAULT, 520, False, quarantine_out=None)
    C._refresh_nifty50(False)
    mem = C.load_membership()
    P = R94.prep_weekly_rank(ohlcv, **C.LIVE_PREP)
    ca_events = R94.build_demerger_events(ohlcv, C.load_demerger_rows(), **C.LIVE_PREP)
    a_set = R94.grade_a_entries(P)
    kw = dict(start=C.INCEPTION_DEFAULT, return_state=True, a_grade=a_set, demerger_events=ca_events,
              **C.LIVE_DISCIPLINE, **C.LIVE_EXIT, **C.LIVE_STALENESS)
    led_paper: list = []
    out_paper = R94.backtest(P, mem, ledger=led_paper, **kw)
    led_all: list = []
    out_all = R94.backtest(P, mem, ledger=led_all, uncapped=True, **kw)
    last = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=pd.Timestamp(C.INCEPTION_DEFAULT))
    env, hist, analytics, portfolio, hist_df = C.build_envelopes(P, out_all, led_all, out_paper, str(last.date()), mem)
    out = {k: json.dumps(v, indent=2, default=str) for k, v in
           zip(PAYLOADS[:4], (env, hist, analytics, portfolio))}
    out[PAYLOADS[4]] = hist_df.to_csv(index=False)
    return out


def main() -> int:
    with_guard = build()
    off = C.MIN_STOP_DISTANCE
    C.MIN_STOP_DISTANCE = 0.0          # the pre-amendment predicate: refuse only entry <= stop
    try:
        without_guard = build()
    finally:
        C.MIN_STOP_DISTANCE = off
    diffs = {k: (len(with_guard[k]), len(without_guard[k])) for k in PAYLOADS if with_guard[k] != without_guard[k]}
    env = json.loads(with_guard["signals_today_weekly"])
    print(json.dumps({"as_of": env.get("generated_at"), "n_signals": len(env.get("signals", [])),
                      "guard_threshold_pct": off * 100,
                      "signals_refused_by_the_guard": env.get("degenerate_stops", []),
                      "payloads_compared": list(PAYLOADS),
                      "payloads_that_differ": diffs,
                      "identical": not diffs}, indent=2))
    return 0 if not diffs else 2


if __name__ == "__main__":
    raise SystemExit(main())


def check_published(path: Path | None = None) -> dict:
    """Second leg: apply the guard predicate to the LATEST PUBLISHED scan's own cards.

    The code-path dry run above uses the local OHLCV cache, which on a developer machine lags the cron. This leg
    needs no cache at all: it replays the predicate over the cards the latest scan actually published, which is
    the output the owner's condition is about.
    """
    p = path or ROOT / "results" / "signals_today_weekly.json"
    env = json.loads(p.read_text(encoding="utf-8"))
    cards = [s for s in env.get("signals", []) if s.get("entry") and s.get("stop")]
    d = sorted(((s["entry"] - s["stop"]) / s["entry"], s["ticker"]) for s in cards)
    return {"published_as_of": env.get("generated_at"), "cards": len(cards),
            "would_be_refused": [t for x, t in d if x < C.MIN_STOP_DISTANCE],
            "smallest_stop_distance_pct": round(d[0][0] * 100, 3) if d else None,
            "smallest_on": d[0][1] if d else None}
